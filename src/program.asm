; program.asm — stored numbered-line program: storage, NEW, RUN (Step B).
;
; The interpreter so far is direct-mode only: a typed line is crunched and run
; immediately. This module adds a *stored* program — numbered lines kept in the
; real MSX line-link format at the real text base ($8001) — plus the editor
; logic that decides, per input line, whether to store it, run the program, or
; clear it. RUN walks the stored lines top-to-bottom, feeding each line's token
; body to the existing `exec`.
;
; Line-link format (one line):
;     [link:2 LE] [lineno:2 LE] [crunched tokens...] [00]
; The program ends with a link word of $0000. `link` is the absolute address of
; the next line's link field; it is recomputed (`relink`) after every edit, so
; the bytes are identical to a reference ROM's for the same program.
;
; CLEAN-ROOM: the leading line number is parsed as plain ASCII *before* crunch
; (no token involved), and RUN/NEW are recognised as editor commands before
; crunch — so this module needs no new keyword-token bytes (RUN/NEW tokens and
; the $0E line-number-reference tokens are not yet oracle-captured, so GOTO /
; FOR…NEXT remain out of scope). Line-link layout + text base are allowed-source
; / oracle-confirmed (see sysvars.inc). No disassembly.

; --- dispatch_line: decide what to do with the freshly read LINEBUF ----------
; Called by the REPL after read_line. Leading digit -> store/replace/delete a
; numbered line; "RUN"/"NEW" -> run/clear; anything else -> direct execution.
; Tail-calls into a handler that returns to the REPL.
dispatch_line:
                ld      hl,LINEBUF
                call    skip_spaces
                ld      a,(hl)
                or      a
                ret     z                   ; blank line -> nothing to do
                cp      '0'
                jr      c,dl_cmd
                cp      '9'+1
                jr      c,dl_store          ; leading digit -> numbered line
dl_cmd:
                ld      de,run_kw
                call    is_cmd
                jr      c,dl_run
                ld      de,new_kw
                call    is_cmd
                jr      c,dl_new
                ; direct mode: crunch the whole line and execute it now
                ld      hl,LINEBUF
                ld      de,TOKBUF
                call    tokenise
                ld      hl,TOKBUF
                jp      exec                ; returns to the REPL
dl_store:
                call    parse_lineno        ; HL -> first digit; BC = number, HL past
                push    bc                  ; guard line number across tokenise
                call    skip_spaces         ; one or more spaces before the body
                ld      de,TOKBUF
                call    tokenise            ; crunch the remainder of the line
                pop     bc
                ld      hl,TOKBUF
                jp      store_line          ; returns to the REPL
dl_run:
                jp      run_prog
dl_new:
                jp      new_prog

; --- is_cmd: does the word at (HL) match the uppercase template at (DE)? ------
; CF set iff (HL) case-folds to the 0-terminated template AND the next input
; byte is a delimiter (end / space / ':'), so "RUN" matches but "RUNNER" does
; not. HL and DE are preserved. Clobbers A, C.
is_cmd:
                push    hl
                push    de
ic_lp:
                ld      a,(de)
                or      a
                jr      z,ic_endword        ; template consumed
                ld      c,a
                ld      a,(hl)
                call    upcase
                cp      c
                jr      nz,ic_no
                inc     hl
                inc     de
                jr      ic_lp
ic_endword:
                ld      a,(hl)
                or      a
                jr      z,ic_yes
                cp      ' '
                jr      z,ic_yes
                cp      COLON
                jr      z,ic_yes
ic_no:
                pop     de
                pop     hl
                or      a                   ; CF clear
                ret
ic_yes:
                pop     de
                pop     hl
                scf
                ret

run_kw:         db      "RUN",0
new_kw:         db      "NEW",0

; --- parse_lineno: ASCII decimal at (HL) -> BC, HL advanced past the digits --
; Accumulates BC = BC*10 + digit (16-bit, wraps past 65535; line numbers above
; 65529 are out of the documented range and not guarded here). Clobbers A, HL.
parse_lineno:
                ld      bc,0
pl_lp:
                ld      a,(hl)
                cp      '0'
                ret     c
                cp      '9'+1
                ret     nc
                sub     '0'
                push    hl                  ; BC = BC*10 + A
                ld      h,b
                ld      l,c
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,bc               ; 5*acc
                add     hl,hl               ; 10*acc
                ld      c,a
                ld      b,0
                add     hl,bc               ; + digit
                ld      b,h
                ld      c,l
                pop     hl
                inc     hl
                jr      pl_lp

; --- new_prog: clear the stored program (NEW) --------------------------------
; Empty program = a $0000 link word at the text base. Clobbers A, HL.
new_prog:
                ld      hl,TXTBASE
                ld      (TXTTAB),hl         ; keep the real sysvar consistent ($8001)
                ld      (PRGEND),hl         ; end marker sits at the base
                ld      hl,0
                ld      (TXTBASE),hl        ; $0000 end marker at the base
                ret

; --- run_prog: execute the stored program (RUN) ------------------------------
; Clears variables, then runs lines from CURLINE. A statement may redirect the
; flow: GOTO sets GOTOFLAG + GOTOTGT (branch to a line), END/STOP sets ENDFLAG
; (stop). Otherwise execution falls through to the next line. BLOAD,R hands off.
run_prog:
                call    clear_vars
                xor     a
                ld      (GOTOFLAG),a
                ld      (ENDFLAG),a
                ld      hl,TXTBASE
                ld      (CURLINE),hl
rp_lp:
                ld      hl,(CURLINE)
                ld      e,(hl)              ; DE = link to next line
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                ret     z                   ; $0000 link -> end of program
                inc     hl                  ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> token body
                call    exec                ; run line (may set flags or hand off)
                ld      a,(ENDFLAG)
                or      a
                ret     nz                  ; END / STOP
                ld      a,(GOTOFLAG)
                or      a
                jr      nz,rp_goto
                ld      hl,(CURLINE)        ; fall through to the next line
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = link (next line)
                ld      (CURLINE),hl
                jr      rp_lp
rp_goto:
                xor     a
                ld      (GOTOFLAG),a
                ld      hl,(GOTOTGT)
                ld      (CURLINE),hl
                jr      rp_lp

; --- find_line_bc: locate a stored line by number ----------------------------
; in: BC = line number. out: CF set + HL = the line's link-field address if
; found; CF clear otherwise. Clobbers A, DE, HL.
find_line_bc:
                ld      hl,TXTBASE
flb_lp:
                ld      e,(hl)              ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,flb_no            ; $0000 -> not found
                push    hl                  ; compare line number at HL+2,+3
                inc     hl
                inc     hl
                ld      a,(hl)
                cp      c
                jr      nz,flb_next
                inc     hl
                ld      a,(hl)
                cp      b
                jr      nz,flb_next
                pop     hl                  ; match: HL = link field
                scf
                ret
flb_next:
                pop     hl                  ; HL = current slot; DE = its link
                ex      de,hl               ; HL = next line
                jr      flb_lp
flb_no:
                or      a                   ; CF clear
                ret

; --- store_line: insert / replace / delete a numbered line -------------------
; in: BC = line number, HL = crunched token body (0-terminated, in TOKBUF).
; An empty body (first byte 00) deletes the line; otherwise the line replaces
; any existing line of the same number, else is inserted in number order.
store_line:
                ld      (SL_NUM),bc
                ld      (SL_TOK),hl
                ld      a,(hl)
                or      a
                jr      z,sl_delete         ; empty body -> delete only
                ; line size = 4 (link+lineno) + body length (incl 00), found by a
                ; token-aware walk so embedded 00 operand bytes don't truncate it.
                call    skip_to_eol         ; HL (= TOKBUF) -> past the body's 00
                ld      de,(SL_TOK)
                or      a
                sbc     hl,de               ; HL = body length incl. terminator
                ld      bc,4
                add     hl,bc               ; HL = full line size
                ld      (SL_SIZE),hl
                ld      b,h
                ld      c,l                 ; BC = size (for the bounds check)
                ; bounds: PRGEND + size must stay below TXTMAX
                ld      hl,(PRGEND)
                add     hl,bc
                ld      de,TXTMAX
                or      a
                sbc     hl,de               ; (PRGEND+size) - TXTMAX
                jr      nc,sl_oom           ; >= TXTMAX -> out of memory
                call    prog_find_del       ; SL_SLOT = insertion point (post-delete)
                call    open_gap            ; make room of SL_SIZE at SL_SLOT
                ld      hl,(SL_SLOT)
                ld      (hl),0              ; link placeholder (relink fills it)
                inc     hl
                ld      (hl),0
                inc     hl
                ld      a,(SL_NUM)          ; line number, LE
                ld      (hl),a
                inc     hl
                ld      a,(SL_NUM+1)
                ld      (hl),a
                inc     hl
                ld      de,(SL_TOK)         ; source = tokenised body
                ex      de,hl               ; HL = source, DE = dest (after lineno)
                ld      bc,(SL_SIZE)        ; body length = full size - 4 header bytes
                dec     bc
                dec     bc
                dec     bc
                dec     bc
                ldir                        ; copy body incl. its 00 terminator
                jp      relink
sl_delete:
                call    prog_find_del       ; deletes a matching line if present
                jp      relink
sl_oom:
                ld      a,$CC               ; out-of-memory landmark (distinct byte)
                ld      (ERRMARK),a
                ld      hl,err_mem
                jp      print_string        ; reports and returns to the REPL
err_mem:        db      "out of memory",13,10,0

; --- prog_find_del: locate the slot for SL_NUM, deleting an exact match ------
; Walks the (currently valid) link chain. Sets SL_SLOT to the first line whose
; number >= SL_NUM (or the end marker). If a line of exactly SL_NUM exists, it
; is removed first so the caller can insert in its place. Clobbers A, BC, DE, HL.
prog_find_del:
                ld      hl,TXTBASE
pfd_lp:
                ld      e,(hl)              ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,pfd_here          ; end marker -> insert here, no match
                push    hl                  ; stored number at slot+2..+3
                inc     hl
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = stored line number
                pop     hl
                ld      de,(SL_NUM)
                ld      a,c                 ; compare stored(BC) - target(DE)
                sub     e
                ld      a,b
                sbc     a,d
                jr      c,pfd_next          ; stored < target -> keep walking
                ; stored >= target: this is the slot
                ld      a,c                 ; exact match?
                cp      e
                jr      nz,pfd_here
                ld      a,b
                cp      d
                jr      nz,pfd_here
                ld      (SL_SLOT),hl        ; same number -> delete then reuse slot
                call    delete_at
                ld      hl,(SL_SLOT)
                ret
pfd_here:
                ld      (SL_SLOT),hl
                ret
pfd_next:
                ld      e,(hl)              ; reload link (the compare clobbered DE
                inc     hl                  ;  with SL_NUM), then advance to it
                ld      d,(hl)
                ex      de,hl               ; HL = link -> next line
                jr      pfd_lp

; --- delete_at: remove the line whose slot is in SL_SLOT ---------------------
; Shifts the rest of the program (including the end marker) down over it and
; shrinks PRGEND. Clobbers A, BC, DE, HL.
delete_at:
                ld      hl,(SL_SLOT)
                inc     hl                  ; skip link(2)+lineno(2) -> body
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol         ; HL = next-line address (token-aware)
                ex      de,hl               ; DE = next-line address
                ; count = (PRGEND+2) - next   (bytes to move, incl. end marker)
                push    de                  ; next (move source)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                 ; BC = count
                ; PRGEND -= (next - slot)
                ld      hl,(SL_SLOT)
                ex      de,hl               ; DE = slot, HL = next
                or      a
                sbc     hl,de               ; HL = removed size (next - slot)
                ex      de,hl               ; DE = size, HL = slot
                ld      hl,(PRGEND)
                or      a
                sbc     hl,de
                ld      (PRGEND),hl
                pop     hl                  ; HL = next (source)
                ld      de,(SL_SLOT)        ; DE = slot (dest)
                ld      a,b
                or      c
                ret     z                   ; nothing trailing to move
                ldir
                ret

; --- open_gap: insert SL_SIZE bytes at SL_SLOT, shifting the tail up ----------
; Moves [SL_SLOT .. PRGEND+1] (program tail incl. end marker) up by SL_SIZE and
; grows PRGEND. Caller has already bounds-checked. Clobbers A, BC, DE, HL.
open_gap:
                ld      hl,(PRGEND)         ; count = (PRGEND+2) - slot
                inc     hl
                inc     hl
                ld      de,(SL_SLOT)
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                 ; BC = count
                ld      hl,(PRGEND)
                inc     hl                  ; HL = last tail byte (PRGEND+1) = source end
                ld      de,(SL_SIZE)
                push    hl
                add     hl,de               ; dest end = source end + size
                ex      de,hl               ; DE = dest end
                pop     hl                  ; HL = source end
                ld      a,b
                or      c
                jr      z,og_end
                lddr                        ; shift the tail upward
og_end:
                ld      hl,(PRGEND)         ; PRGEND += SL_SIZE
                ld      de,(SL_SIZE)
                add     hl,de
                ld      (PRGEND),hl
                ret

; --- relink: recompute every line's link pointer, stopping at the end marker -
; A line's link = the address of the following line's link field. Clobbers
; A, DE, HL.
relink:
                ld      hl,TXTBASE
rl_lp:
                ld      a,(PRGEND+1)        ; reached the end marker (HL == PRGEND)?
                cp      h                   ; (a fresh line's link is a placeholder
                jr      nz,rl_more          ;  0000, so we cannot stop on link==0)
                ld      a,(PRGEND)
                cp      l
                ret     z                   ; HL == PRGEND -> all lines linked
rl_more:
                push    hl                  ; remember this link field
                inc     hl                  ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol         ; HL = next line (token-aware end-find)
                ex      de,hl               ; DE = next-line address
                pop     hl                  ; HL = link field to fill
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ex      de,hl               ; HL = next-line address
                jr      rl_lp
