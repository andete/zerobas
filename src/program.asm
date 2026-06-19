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
; crunch. Control-flow keyword tokens and the $0E line-number-reference code come
; from the MSX2 Technical Handbook (Table 2.20 / Figure 2.12, an allowed source;
; see sysvars.inc and spec-controlflow.md). The line-link layout + text base are
; allowed-source / oracle-confirmed. No disassembly.

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
; Clears variables and the control stacks, then runs lines from CURLINE. A
; statement may redirect the flow: GOTO sets GOTOFLAG + GOTOTGT (branch to a
; line start); RETURN / a continuing NEXT set RESUMEFLAG + RESUMEPTR (resume at
; an exact token position, CURLINE already pointing at its line); END/STOP set
; ENDFLAG (stop). Otherwise execution falls through to the next line. BLOAD,R
; hands off.
run_prog:
                call    clear_vars
                xor     a
                ld      (GOTOFLAG),a
                ld      (ENDFLAG),a
                ld      (RESUMEFLAG),a
                ld      hl,GOSUB_STK        ; empty return stack
                ld      (GSP),hl
                ld      hl,FOR_STK          ; empty FOR stack
                ld      (FSP),hl
                ld      hl,TXTBASE
                ld      (CURLINE),hl
rp_lp:
                ld      a,(RESUMEFLAG)      ; resume mid-line (RETURN / NEXT)?
                or      a
                jr      nz,rp_resume
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
                jr      rp_exec
rp_resume:
                xor     a
                ld      (RESUMEFLAG),a
                ld      hl,(RESUMEPTR)      ; HL -> exact statement to resume at
rp_exec:
                call    exec                ; run line (may set flags or hand off)
                ld      a,(ENDFLAG)
                or      a
                ret     nz                  ; END / STOP
                ld      a,(RESUMEFLAG)      ; RETURN / continuing NEXT -> resume
                or      a
                jr      nz,rp_lp
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

; --- ex_gosub: GOSUB <line> --------------------------------------------------
; Push a return frame [CURLINE:2][resume-ptr:2] (resume = the token position
; right after this GOSUB statement), then branch to the target line exactly like
; GOTO. RETURN pops the frame and resumes there. (HL enters on the GOSUB token.)
ex_gosub:
                inc     hl                  ; past the GOSUB token
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E,<lineno LE> expected
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL = resume point (after the statement)
                push    bc                  ; guard target line number
                ; bounds: GSP must stay below GOSUB_STK_END
                push    hl                  ; save resume ptr
                ld      hl,(GSP)
                ld      de,GOSUB_STK_END
                or      a
                sbc     hl,de
                jr      nc,egs_over         ; GSP >= end -> too many GOSUBs
                ld      de,(GSP)            ; write frame at GSP
                ld      hl,(CURLINE)
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                pop     hl                  ; HL = resume ptr
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                ld      (GSP),de            ; advance (push complete)
                pop     bc                  ; BC = target line number
                call    find_line_bc        ; CF set + HL = line addr if found
                jp      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
egs_over:
                pop     hl                  ; discard saved resume ptr
                pop     bc                  ; discard saved target
                ld      a,$CE               ; control-stack overflow landmark
                ld      (ERRMARK),a
                ld      hl,err_stack
                jp      print_string

; --- ex_return: RETURN -------------------------------------------------------
; Pop the top GOSUB frame and resume at its saved (CURLINE, resume-ptr) via the
; RUN loop's mid-line resume path. (HL enters on the RETURN token.)
ex_return:
                ld      hl,(GSP)            ; empty stack -> RETURN without GOSUB
                ld      de,GOSUB_STK
                or      a
                sbc     hl,de
                jp      z,ex_ret_under
                ld      hl,(GSP)
                dec     hl                  ; pop 4 bytes, reading high-to-low
                ld      b,(hl)              ; resume ptr high
                dec     hl
                ld      c,(hl)              ; resume ptr low   -> BC = resume ptr
                dec     hl
                ld      d,(hl)              ; curline high
                dec     hl
                ld      e,(hl)              ; curline low      -> DE = saved CURLINE
                ld      (GSP),hl            ; GSP -= 4 (popped)
                ld      (CURLINE),de
                ld      (RESUMEPTR),bc
                ld      a,1
                ld      (RESUMEFLAG),a
                ret
ex_ret_under:
                ld      a,$CD               ; "return without gosub" landmark
                ld      (ERRMARK),a
                ld      hl,err_noret
                jp      print_string

; --- ex_for: FOR <var> = <init> TO <limit> [STEP <step>] ---------------------
; Assign init to the loop variable, then push a frame
; [var:1][limit:2][step:2][CURLINE:2][resume-ptr:2] and fall through to run the
; loop body (the statements following FOR). NEXT consults the top frame.
ex_for:
                inc     hl                  ; past the FOR token
                call    skip_spaces
                ld      a,(hl)
                call    is_letter
                jp      nc,stmt_error
                call    upcase
                ld      (FOR_CUR),a         ; frame[0] = loop variable name
                inc     hl                  ; consume the letter
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '=' -> $EF
                jp      nz,stmt_error
                inc     hl
                call    eval                ; DE = initial value, HL advanced
                ld      a,(FOR_CUR)
                push    hl                  ; guard cursor across var_set
                call    var_set             ; var := initial value
                pop     hl
                call    skip_spaces
                ld      a,(hl)
                cp      TO_TOKEN           ; TO -> $D9
                jp      nz,stmt_error
                inc     hl
                call    eval                ; DE = limit
                ld      (FOR_CUR+1),de      ; frame[1..2] = limit
                call    skip_spaces
                ld      a,(hl)
                cp      STEP_TOKEN         ; STEP -> $DC (optional)
                jr      z,ef_step
                ld      de,1                ; default step = +1
                jr      ef_havestep
ef_step:
                inc     hl
                call    eval                ; DE = step
ef_havestep:
                ld      (FOR_CUR+3),de      ; frame[3..4] = step
                ld      (FOR_CUR+7),hl      ; frame[7..8] = resume ptr (loop body)
                ld      de,(CURLINE)
                ld      (FOR_CUR+5),de      ; frame[5..6] = CURLINE
                ld      hl,(FSP)            ; bounds: FSP must stay below FOR_STK_END
                ld      de,FOR_STK_END
                or      a
                sbc     hl,de
                jr      nc,ef_over          ; too many nested FORs
                ld      hl,FOR_CUR          ; push the 9-byte frame
                ld      de,(FSP)
                ld      bc,9
                ldir
                ld      (FSP),de            ; advance FSP by 9
                ld      hl,(FOR_CUR+7)      ; HL = loop body -> run it
                jp      exec_stmt
ef_over:
                ld      a,$CE
                ld      (ERRMARK),a
                ld      hl,err_stack
                jp      print_string

; --- ex_next: NEXT [<var>] ---------------------------------------------------
; Step the loop variable of the matching FOR frame, test against the limit, and
; either resume at the frame's body (loop continues) or pop the frame and run on
; (loop ends). A named NEXT closes any inner frames above the matching one.
ex_next:
                inc     hl                  ; past the NEXT token
                call    skip_spaces
                ld      a,(hl)
                call    is_letter
                jr      nc,nx_top           ; bare NEXT -> the top frame
                call    upcase
                ld      c,a                 ; C = named loop variable
                inc     hl                  ; consume the letter
                jr      nx_find
nx_top:
                ld      c,0                 ; 0 = match the top frame (no letter)
nx_find:
                push    hl                  ; save the post-NEXT cursor
                ld      hl,(FSP)            ; empty stack -> NEXT without FOR
                ld      de,FOR_STK
                or      a
                sbc     hl,de
                jp      z,nx_nofor
nx_scan:
                ld      hl,(FSP)            ; HL = top frame base (FSP - 9)
                ld      de,9
                or      a
                sbc     hl,de
                ld      a,c
                or      a
                jr      z,nx_have           ; bare NEXT accepts the top frame
                ld      a,(hl)              ; frame's loop variable
                cp      c
                jr      z,nx_have           ; named NEXT matches this frame
                ld      (FSP),hl            ; mismatch -> close this inner frame
                ld      hl,(FSP)
                ld      de,FOR_STK
                or      a
                sbc     hl,de
                jp      z,nx_nofor          ; ran out -> no matching FOR
                jr      nx_scan
nx_have:
                push    hl                  ; save the frame base (for pop / keep)
                ld      de,FOR_CUR          ; work on a copy of the frame
                ld      bc,9
                ldir
                ld      a,(FOR_CUR)         ; var := var + step
                call    var_get             ; DE = current value
                ld      hl,(FOR_CUR+3)      ; step
                add     hl,de               ; HL = stepped value
                ld      (FOR_NEW),hl
                ex      de,hl               ; DE = stepped value
                ld      a,(FOR_CUR)
                call    var_set
                ld      hl,(FOR_CUR+3)      ; loop test depends on the step sign
                bit     7,h
                jr      nz,nx_neg
                ld      hl,(FOR_NEW)        ; step >= 0: end when value > limit
                ld      de,(FOR_CUR+1)
                call    cmp16_bits          ; 1=<, 2==, 4=>
                cp      4
                jr      z,nx_end
                jr      nx_again
nx_neg:
                ld      hl,(FOR_NEW)        ; step < 0: end when value < limit
                ld      de,(FOR_CUR+1)
                call    cmp16_bits
                cp      1
                jr      z,nx_end
nx_again:
                pop     hl                  ; frame stays on the stack
                ld      hl,(FOR_CUR+5)      ; resume at the loop body
                ld      (CURLINE),hl
                ld      hl,(FOR_CUR+7)
                ld      (RESUMEPTR),hl
                ld      a,1
                ld      (RESUMEFLAG),a
                pop     bc                  ; discard the post-NEXT cursor
                ret
nx_end:
                pop     hl                  ; frame base -> pop the frame
                ld      (FSP),hl
                pop     hl                  ; restore the post-NEXT cursor
                jp      exec_stmt           ; run on past NEXT
nx_nofor:
                pop     hl                  ; discard the saved cursor
                ld      a,$CB               ; "next without for" landmark
                ld      (ERRMARK),a
                ld      hl,err_nofor
                jp      print_string

err_stack:      db      "out of memory",13,10,0
err_noret:      db      "return without gosub",13,10,0
err_nofor:      db      "next without for",13,10,0
