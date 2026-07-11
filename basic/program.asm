; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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
    IF ROM_BASE < $4000
                ld      a,(TKOVF)           ; float-literal crunch-time overflow (F1,
                or      a                   ; basic/float.asm) -> reject the whole line,
                jp      nz,dl_overflow      ; own wording (D-F1-1); never execute/store
    ENDIF
                ld      hl,TOKBUF
                jp      exec                ; returns to the REPL
dl_store:
                call    parse_lineno        ; HL -> first digit; BC = number, HL past
                push    bc                  ; guard line number across tokenise
                call    skip_spaces         ; one or more spaces before the body
                ld      de,TOKBUF
                call    tokenise            ; crunch the remainder of the line
    IF ROM_BASE < $4000
                ld      a,(TKOVF)
                or      a
                jr      nz,dl_overflow_pop
    ENDIF
                pop     bc
                ld      hl,TOKBUF
                jp      store_line          ; returns to the REPL
    IF ROM_BASE < $4000
dl_overflow_pop:
                pop     bc                  ; balance the stack (line number now unused)
dl_overflow:
                ld      hl,err_overflow
                jp      print_string        ; reports and returns to the REPL
err_overflow:   db      "overflow",13,10,0
    ENDIF
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
                xor     a
                ld      (CONTVALID),a       ; NEW wipes the program -> no CONT resume
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
                ld      (CONTVALID),a       ; a fresh RUN has no CONT resume point yet
                ld      (GOTOFLAG),a
                ld      (ENDFLAG),a
                ld      (RESUMEFLAG),a
                ld      hl,GOSUB_STK        ; empty return stack
                ld      (GSP),hl
                ld      hl,FOR_STK          ; empty FOR stack
                ld      (FSP),hl
                xor     a                   ; DATA pointer unpositioned (read seeks
                ld      (DATASTATE),a       ;  from the program start on first READ)
                ld      hl,TXTBASE
                ld      (RESTORE_LINE),hl
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
                ; Ctrl-STOP poll: between statements/lines, before running the
                ; next one. BREAKX ($00B7) scans keyboard matrix row 6 (CF set =
                ; Ctrl-STOP held). If pressed, break here — resume point is HL
                ; (the statement about to run), CURLINE already correct.
                push    hl                  ; guard the resume pointer across BREAKX
                call    BREAKX
                pop     hl
                jr      c,rp_break
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
rp_break:
                ; Ctrl-STOP pressed between lines/statements. HL = the statement
                ; that was about to run -> the CONT resume point. do_break records
                ; it, prints "Break in <line>", and sets ENDFLAG; we then return
                ; to the REPL (the run is suspended, not torn down).
                call    do_break
                ret

; --- do_break: record a CONT resume point and report "Break in <line>" -------
; in: HL = the token position to resume at; CURLINE = the line being interrupted
;     (its link-field address). Used by both Ctrl-STOP (resume = next statement
;     to run) and the STOP statement (resume = statement after STOP).
; Saves CONTLINE/CONTPTR, raises CONTVALID, prints the break message, and sets
; ENDFLAG so the run loop unwinds back to the REPL. Clobbers A, BC, DE, HL.
do_break:
                ld      (CONTPTR),hl        ; resume token pointer
                ld      hl,(CURLINE)
                ld      (CONTLINE),hl       ; line to resume in (link-field addr)
                ld      a,1
                ld      (CONTVALID),a       ; a CONT resume point is now live
                ld      a,1
                ld      (ENDFLAG),a         ; stop the run, fall back to the REPL
                ; report: "break in <lineno>" + CR/LF. The line number is at
                ; CURLINE+2 (the lineno field after the 2-byte link).
                ld      hl,brk_msg
                call    print_string
                ld      hl,(CURLINE)
                inc     hl
                inc     hl
                ld      e,(hl)              ; lineno LE -> DE
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = line number
                call    ln_div_entry        ; print HL as bare unsigned decimal
                jp      print_crlf
brk_msg:        db      "break in ",0

; --- ex_stop: STOP statement — break and record a CONT resume point ----------
; STOP halts the program exactly like END, but ALSO records where to continue so
; a following CONT resumes at the statement after STOP. (END does not: it ends
; the run with no resume point, so CONT after END is "Can't CONTINUE".)
; HL enters on the STOP token.
ex_stop:
                inc     hl                  ; HL = resume point (statement after STOP)
                jp      do_break            ; record + "Break in <line>", set ENDFLAG

; --- ex_cont: CONT statement — resume a STOPped / broken program -------------
; If a CONT resume point is live (set by STOP or Ctrl-STOP and not invalidated by
; a program edit), restore CURLINE + RESUMEPTR and re-enter the run loop via its
; mid-line resume path. Otherwise report "Can't CONTINUE". CONT consumes the
; resume point (CONTVALID -> 0) so a second bare CONT does not re-resume a run
; that has since finished. Reached as a direct-mode statement from the REPL.
ex_cont:
                ld      a,(CONTVALID)
                or      a
                jr      z,ex_cont_no        ; nothing to continue
                xor     a
                ld      (CONTVALID),a       ; consume the resume point
                ; re-arm the run loop's flags and stacks are already intact from
                ; the suspended run (we never cleared them on break); just point
                ; the loop at the saved resume position and run.
                xor     a
                ld      (ENDFLAG),a
                ld      (GOTOFLAG),a
                ld      hl,(CONTLINE)
                ld      (CURLINE),hl
                ld      hl,(CONTPTR)
                ld      (RESUMEPTR),hl
                ld      a,1
                ld      (RESUMEFLAG),a      ; resume mid-line at CONTPTR
                jp      rp_lp               ; re-enter the run loop
ex_cont_no:
                ld      a,$C9               ; "can't continue" landmark (distinct byte)
                ld      (ERRMARK),a
                ld      hl,err_cont
                jp      print_string
err_cont:       db      "can't continue",13,10,0

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
                xor     a
                ld      (CONTVALID),a       ; editing the program invalidates CONT
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
;
; DOCUMENTED DIVERGENCE (PROVENANCE.md): the FOR/NEXT loop variable is a SINGLE
; letter only — the frame stores it in one byte (frame[0]) and NEXT matches on
; one char. LET/PRINT/READ honour 2-significant-char names (var_name_key), so a
; `FOR INDEX=…` reads only 'I' and then fails the '=' check (it sees 'N'). The
; keying is consistent — `FOR I` and `I=` address the same cell, no aliasing —
; this is purely a parse limit. Game-loader stubs use `FOR I=…`/`FOR X=…`, so
; single-letter loop vars suffice; multi-char loop vars are Phase-2 scope.
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

; --- ex_read: READ <var> [, <var> ...] ---------------------------------------
; Fill each variable from the next DATA item. DATA items are stored as verbatim
; ASCII (oracle), so read_one_value parses ASCII from the program text.
ex_read:
                inc     hl                  ; past the READ token
exr_lp:
                call    skip_spaces
                ld      a,(hl)
                call    is_letter
                jp      nc,stmt_error       ; READ needs a variable
                call    upcase
                ld      (READVAR),a         ; remember the target name
                inc     hl                  ; consume the letter
                push    hl                  ; guard exec cursor across the DATA read
                call    read_one_value      ; CF set + DE = value, else out of data
                jr      nc,exr_nodata
                ld      a,(READVAR)
                call    var_set             ; var := DE
                pop     hl                  ; restore exec cursor
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; more variables to fill?
                jr      z,exr_more
                jp      exec_stmt           ; READ statement done
exr_more:
                inc     hl
                jr      exr_lp
exr_nodata:
                pop     hl                  ; discard exec cursor (balance the stack)
                ld      a,$CA               ; "out of data" landmark
                ld      (ERRMARK),a
                ld      hl,err_data
                jp      print_string
err_data:       db      "out of data",13,10,0

; --- ex_restore: RESTORE [<line>] --------------------------------------------
; Reset the DATA cursor to the program start, or to a given line. The optional
; line arrives as the $0E line-number reference (branch_lineno tokenises it).
ex_restore:
                inc     hl                  ; past the RESTORE token
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E,<lineno LE> -> restore to a line
                jr      z,ers_line
                ld      hl,TXTBASE          ; bare RESTORE -> program start
                ld      (RESTORE_LINE),hl
                xor     a
                ld      (DATASTATE),a
                ret                         ; nothing else on a bare RESTORE word
ers_line:
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL past the $0E operand (exec cursor)
                push    hl
                call    find_line_bc        ; CF set + HL = line link-field
                jr      nc,ers_undef
                ld      (RESTORE_LINE),hl
                xor     a
                ld      (DATASTATE),a
                pop     hl
                jp      exec_stmt
ers_undef:
                pop     hl                  ; balance the stack
                jp      ex_goto_undef       ; reuse "undefined line"

; --- read_one_value: fetch the next DATA item -------------------------------
; out: CF set + DE = value (DATA cursor advanced to the following item); CF clear
; if no DATA remains. Clobbers A, BC, HL.
read_one_value:
                ld      a,(DATASTATE)
                cp      2
                jr      z,rov_none          ; exhausted
                or      a
                jr      nz,rov_at           ; already positioned
                ; unpositioned: seek the first DATA item from RESTORE_LINE
                ld      hl,(RESTORE_LINE)
                ld      (DATALINE),hl
                ld      a,(hl)              ; empty program / no line -> no data
                inc     hl
                or      (hl)
                jr      z,rov_none
                ld      hl,(DATALINE)
                inc     hl                  ; HL = body of RESTORE_LINE (link+4)
                inc     hl
                inc     hl
                inc     hl
                call    data_seek           ; -> DATAPTR at first item, or CF clear
                jr      nc,rov_none
rov_at:
                ld      hl,(DATAPTR)
                call    data_parse_int      ; DE = value, HL past the ASCII number
                push    de                  ; guard the value
                call    skip_spaces
                ld      a,(hl)
                cp      ','                 ; another item in this DATA statement?
                jr      z,rov_comma
                call    data_seek           ; else seek the next DATA statement
                jr      nc,rov_exhaust
                jr      rov_ok              ; DATAPTR updated, DATASTATE set below
rov_comma:
                inc     hl                  ; step past the comma
                ld      (DATAPTR),hl
rov_ok:
                ld      a,1
                ld      (DATASTATE),a
                pop     de                  ; DE = value
                scf
                ret
rov_exhaust:
                ld      a,2                 ; this was the last item
                ld      (DATASTATE),a
                pop     de                  ; DE = value (this read still succeeds)
                scf
                ret
rov_none:
                or      a                   ; CF clear -> out of data
                ret

; --- data_seek: scan forward for the next DATA statement --------------------
; in:  HL = a token position; DATALINE = link-field of the line containing it.
; out: CF set -> DATAPTR = first ASCII item after the next DATA token (DATALINE
;      updated if a line boundary was crossed); CF clear -> end of program.
; Token-aware via tok_skip so a constant's operand byte is never mistaken for a
; DATA token; a DATA statement's own ASCII body is never scanned (we stop AT the
; DATA token and the caller resumes past the statement's ':' / EOL).
data_seek:
ds_lp:
                ld      a,(hl)
                or      a
                jr      z,ds_eol            ; end of line -> follow the link
                cp      DATA_TOKEN
                jr      z,ds_found
                call    tok_skip
                jr      ds_lp
ds_eol:
                ld      hl,(DATALINE)       ; advance to the next line
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      a,d
                or      e
                jr      z,ds_none           ; $0000 link -> program end
                ex      de,hl               ; HL = next line link-field
                ld      (DATALINE),hl
                inc     hl                  ; HL = its body (link+4)
                inc     hl
                inc     hl
                inc     hl
                jr      ds_lp
ds_found:
                inc     hl                  ; past the DATA token
ds_sp:
                ld      a,(hl)              ; skip spaces before the first item
                cp      ' '
                jr      nz,ds_set
                inc     hl
                jr      ds_sp
ds_set:
                ld      (DATAPTR),hl
                scf
                ret
ds_none:
                or      a
                ret

; --- data_parse_int: parse an ASCII integer at (HL) -> DE -------------------
; Leading spaces, an optional '-', then decimal digits or a "&H" hex constant.
; HL stops at the first non-numeric byte. Clobbers A, BC, HL.
data_parse_int:
                call    skip_spaces
                ld      a,(hl)
                cp      '-'
                jr      z,dp_neg
                cp      '&'
                jr      z,dp_hex
                jp      dp_decimal
dp_neg:
                inc     hl
                call    skip_spaces
                ld      a,(hl)
                cp      '&'
                jr      z,dp_neghex
                call    dp_decimal
                jr      dp_negate
dp_neghex:
                call    dp_hex
dp_negate:
                push    hl                  ; preserve the cursor across the negate
                ld      hl,0
                or      a
                sbc     hl,de
                ex      de,hl               ; DE = -value
                pop     hl
                ret
dp_decimal:
                ld      de,0
dp_dlp:
                ld      a,(hl)
                cp      '0'
                ret     c
                cp      '9'+1
                ret     nc
                sub     '0'
                ld      c,a                 ; C = digit
                push    hl
                ld      h,d
                ld      l,e                 ; HL = acc
                add     hl,hl               ; 2*acc
                add     hl,hl               ; 4*acc
                add     hl,de               ; 5*acc
                add     hl,hl               ; 10*acc
                ld      b,0
                add     hl,bc               ; + digit
                ex      de,hl               ; DE = new acc
                pop     hl
                inc     hl
                jr      dp_dlp
dp_hex:
                inc     hl                  ; past '&'
                ld      a,(hl)
                call    upcase
                cp      'H'
                jr      nz,dp_hbad          ; only &H is supported here
                inc     hl                  ; past 'H'
                ld      de,0
dp_hlp:
                ld      a,(hl)
                call    upcase
                cp      '0'
                jr      c,dp_hdone
                cp      '9'+1
                jr      c,dp_hdig           ; '0'..'9'
                cp      'A'
                jr      c,dp_hdone
                cp      'F'+1
                jr      nc,dp_hdone
                sub     'A'-10              ; 'A'..'F' -> 10..15
                jr      dp_hacc
dp_hdig:
                sub     '0'
dp_hacc:
                ld      c,a                 ; nibble
                push    hl
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; 16*acc
                ld      b,0
                add     hl,bc               ; + nibble
                ex      de,hl
                pop     hl
                inc     hl
                jr      dp_hlp
dp_hdone:
                ret
dp_hbad:
                ld      de,0
                ret

; --- ex_on: ON <expr> GOTO/GOSUB <line>[,<line>...] -------------------------
; Evaluates expr (1-based index N). Finds the Nth branch target in the
; comma-separated $0E list and branches (GOTO) or calls (GOSUB) to it.
; N=0 or N > count of targets falls through to the next statement.
; Source: public MSX-BASIC language reference (ON…GOTO/GOSUB semantics).
ex_on:
                inc     hl                  ; past ON_TOKEN
                call    eval                ; DE = N (1-based index), HL past expression
                call    skip_spaces
                ld      a,(hl)
                cp      GOTO_TOKEN
                jr      z,eon_goto
                cp      GOSUB_TOKEN
                jr      z,eon_gosub
                jp      stmt_error

eon_goto:
                inc     hl                  ; past GOTO token
                call    eon_seek_nth        ; BC = line number, HL past list; CF set if found
                jp      nc,exec_stmt        ; N=0 or N > count -> fall through
                call    find_line_bc
                jp      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret

eon_gosub:
                inc     hl                  ; past GOSUB token
                call    eon_seek_nth        ; BC = line number, HL past list; CF set if found
                jp      nc,exec_stmt        ; N=0 or N > count -> fall through
                ; push GOSUB frame [CURLINE:2][resume:2]; resume = HL (past the list)
                push    bc                  ; guard target line number
                push    hl                  ; save resume ptr
                ld      hl,(GSP)
                ld      de,GOSUB_STK_END
                or      a
                sbc     hl,de
                jr      nc,eon_over
                ld      de,(GSP)
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
                ld      (GSP),de
                pop     bc                  ; BC = target line number
                call    find_line_bc
                jp      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
eon_over:
                pop     hl                  ; discard resume ptr
                pop     bc                  ; discard target
                ld      a,$CE
                ld      (ERRMARK),a
                ld      hl,err_stack
                jp      print_string

; --- eon_seek_nth: find Nth $0E entry in an ON...GOTO/GOSUB target list ------
; in:  HL = first token after the GOTO/GOSUB token, DE = N (1-based index)
; out: CF set + BC = Nth line number, HL past the full target list
;      CF clear + HL past the full target list (N=0 or N > count)
; Token stream: [$20*] $0E lo hi [, [$20*] $0E lo hi ...]
; Clobbers A, BC, DE, HL.
eon_seek_nth:
                ld      a,d
                or      e
                jr      z,esn_scan          ; N=0: scan past list, return CF clear
; Phase 1: count down to the Nth entry.
esn_p1:
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E expected
                jr      nz,esn_nocf         ; list shorter than N -> not found
                inc     hl
                ld      c,(hl)              ; lineno lo
                inc     hl
                ld      b,(hl)              ; lineno hi -> BC = this entry's line number
                inc     hl                  ; HL past this $0E,lo,hi
                dec     de
                ld      a,d
                or      e
                jr      z,esn_found         ; DE == 0 -> this was the Nth entry
                ; still counting: expect a comma before the next entry
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,esn_nocf         ; no comma -> list shorter than N
                inc     hl                  ; past comma
                jr      esn_p1
; Phase 2: Nth entry found (BC = line number). Scan past any remaining entries.
esn_found:
                push    bc                  ; guard the found line number
esn_p2:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,esn_ok           ; no more commas -> HL past the list
                inc     hl                  ; past comma
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      nz,esn_ok           ; malformed: stop here
                inc     hl
                inc     hl
                inc     hl                  ; skip $0E,lo,hi
                jr      esn_p2
esn_ok:
                pop     bc                  ; BC = Nth line number
                scf
                ret
; N=0: scan past the entire list and return CF clear.
esn_scan:
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      nz,esn_nocf         ; no entries at all
                inc     hl
                inc     hl
                inc     hl                  ; skip first $0E,lo,hi
esn_scan_lp:
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,esn_nocf         ; no more commas -> done
                inc     hl                  ; past comma
                call    skip_spaces
                ld      a,(hl)
                cp      LINENO_TOKEN
                jr      nz,esn_nocf
                inc     hl
                inc     hl
                inc     hl                  ; skip $0E,lo,hi
                jr      esn_scan_lp
esn_nocf:
                or      a                   ; CF clear
                ret
