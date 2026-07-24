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
                ld      a,1
                ld      (DIRECTF),a         ; D-2: direct-mode exec -> error carries NO
                                            ; " in <line>" suffix (there is no line)
                ld      (SAVSTK),sp         ; error-handling S2b §6: direct-mode anchor
                                            ; (a direct ERROR n/error WITH a handler
                                            ; resets cleanly; without one, S1's REPL
                                            ; return already worked)
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
    IF ROM_BASE < $4000
                ; NEW clears ALL variables (VARTAB / DEFtbl / strings), not just
                ; the stored program — MS-BASIC semantics. Gated to the repack
                ; build: the lean 16 KB basic.rom is byte-full at its $8000
                ; ceiling AND has no typed vars / DEFtbl, so it stays byte-
                ; identical. LOAD's own new_prog calls stay variable-safe.
                call    clear_vars
    ENDIF
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
    IF ROM_BASE < $4000
                jp      vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b):
                                            ; rebase BOTH the scalar region (ARYTAB=
                                            ; PRGEND+2) and the array area's "no
                                            ; arrays" sentinel to the new PRGEND+2
                                            ; (tail call; vars_reset/ary_reset just ret)
    ELSE
                ret
    ENDIF

; --- run_prog: execute the stored program (RUN) ------------------------------
; Clears variables and the control stacks, then runs lines from CURLINE. A
; statement may redirect the flow: GOTO sets GOTOFLAG + GOTOTGT (branch to a
; line start); RETURN / a continuing NEXT set RESUMEFLAG + RESUMEPTR (resume at
; an exact token position, CURLINE already pointing at its line); END/STOP set
; ENDFLAG (stop). Otherwise execution falls through to the next line. BLOAD,R
; hands off.
run_prog:
                call    clear_vars
    IF ROM_BASE < $4000
                call    vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b): a
                                            ; fresh RUN has no live scalars/arrays
                                            ; either; PRGEND is already correct here
                                            ; (unlike at boot -- see ary_alloc's own
                                            ; ceiling note, sub/arrays.asm). Redundant
                                            ; with clear_vars's own vars_reset just
                                            ; above (same PRGEND, same result) --
                                            ; harmless, kept for the "four call sites"
                                            ; symmetry (§3b).
    ENDIF
                xor     a
                ld      (CONTVALID),a       ; a fresh RUN has no CONT resume point yet
                ld      (GOTOFLAG),a
                ld      (ENDFLAG),a
                ld      (RESUMEFLAG),a
    IF ROM_BASE < $4000
                ld      (DIRECTF),a         ; D-2: run mode (0) — errors get " in <line>"
                ld      (SAVSTK),sp         ; error-handling S2b §6: run anchor — the
                                            ; trap resets SP here before jumping to
                                            ; the handler (a trap fires from
                                            ; arbitrary call depth)
                ld      hl,0
                ld      (ONELIN),hl         ; error-handling S2b §7 hypothesis: RUN
                                            ; re-arms, so a fresh RUN starts with no
                                            ; ON ERROR handler armed. UNVERIFIED,
                                            ; flagged for the lead's VG-8020 pin
                                            ; (packet §7).
                ld      (ONEFLG),a          ; not inside a handler at RUN start (A is
                                            ; still 0 from the xor a above -- nothing
                                            ; since touches it: the ERR-reset-on-RESUME
                                            ; follow-up reclaimed the redundant xor a)
                ; interrupt-traps T1: `call trap_init` (RUN re-arm) goes here once the
                ; crash is root-caused (see basic/traps.asm / main.asm).
    ENDIF
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
    IF ROM_BASE < $4000
                ; repack (D-2): the " in <lineno>" + CRLF tail is the SHARED
                ; print_in_lineno routine (below) — the same one fre_abort_low uses
                ; for a runtime error's " in <line>" suffix. do_break is always
                ; reached in run mode, so the suffix is unconditional here; output is
                ; byte-for-byte the old inline tail ("break" + " in " + <N> + CRLF).
                jp      print_in_lineno
    ELSE
                ld      hl,(CURLINE)
                inc     hl
                inc     hl
                ld      e,(hl)              ; lineno LE -> DE
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = line number
                call    ln_div_entry        ; print HL as bare unsigned decimal
                jp      print_crlf
    ENDIF
    IF ROM_BASE < $4000
brk_msg:        db      "break",0           ; repack: " in " moved into print_in_lineno
    ELSE
brk_msg:        db      "break in ",0
    ENDIF

    IF ROM_BASE < $4000
; --- print_in_lineno: " in <CURLINE lineno>" + CRLF (repack, error-handling D-2) --
; Shared by do_break ("break in <N>") and fre_abort_low (a runtime error's run-mode
; " in <line>" suffix). CURLINE = the current line's link-field address; the line
; number is the 2-byte field at CURLINE+2. ln_div_entry prints HL as a bare unsigned
; decimal. Clobbers A, BC, DE, HL. See docs/spec-basic-error-handling.md §5.4.
print_in_lineno:
                ld      hl,in_msg
                call    print_string        ; " in "
                ld      hl,(CURLINE)
                inc     hl
                inc     hl
                ld      e,(hl)              ; lineno LE -> DE
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = line number
                call    ln_div_entry
                jp      print_crlf
in_msg:         db      " in ",0

; --- print_string_stopcr: print (HL) up to (not including) the first CR (13) -----
; Runtime-error message strings end 13,10,0. In run mode fre_abort_low prints the
; body with this, then appends print_in_lineno; so it must halt at the baked CR.
; Returns HL pointing AT the CR, letting the DIRECT-mode path resume print_string
; there to emit the string's own 13,10 (= CRLF). Clobbers A. (No NUL check — every
; caller's string carries a CR before its terminator.)
print_string_stopcr:
                ld      a,(hl)
                cp      13
                ret     z
                call    pchar               ; PRDEST sink (fre_abort_low zeroed it)
                inc     hl
                jr      print_string_stopcr
    ENDIF

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
    IF ROM_BASE < $4000
                ld      (DIRECTF),a         ; D-2: CONT resumes the RUN -> run mode (0)
    ENDIF
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

    IF ROM_BASE < $4000
; --- store_line / relink: resident marshalling shims -----------------------
; docs/spec-eviction-g4-space.md §4 (carve #2). prog_find_del/delete_at/
; open_gap AND the relink loop moved whole to sub/lineedit.asm
; (SUBROM_IDX_LINEEDIT); store_line marshals {SL_NUM,SL_TOK} (already RAM
; cells, unchanged) then subrom_calls the tenant, which does the full
; store/delete + relink + vars_reset internally (vars_reset is page-0 low-
; region resident, directly `call`-reachable sub-side -- see sub/
; lineedit.asm's own header) and reports back only an OOM status byte; the
; actual err_mem RAISE stays here (raise_error is main page-1 resident,
; unreachable from a page-1 tenant). `relink` itself stays as a thin shim
; too, for cload.asm's 2 plain `call relink` sites (own header, same file).
store_line:
                xor     a
                ld      (CONTVALID),a       ; editing the program invalidates CONT
                ld      (SL_NUM),bc
                ld      (SL_TOK),hl
                xor     a                   ; LE_OP_STORE = 0
                ld      (LE_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LINEEDIT
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(LE_STATUS)
                or      a
                ret     z                   ; ok (tenant already relinked +
                                            ; vars_reset)
                ld      a,$CC               ; out-of-memory landmark (distinct byte)
                ld      (ERRMARK),a
                ld      a,7                 ; ERR 7: out of memory (error-handling S2a)
                jp      raise_error
; err_mem: the message STRING must stay resident even though sl_oom's own
; CODE moved sub-side -- interp.asm's err_msgtab (repack-only, ERR 7) takes
; its ADDRESS directly (`dw err_mem`), which must resolve to a main-ROM
; address, never a sub-ROM one. err_stack (further down this file) and
; cload.asm's err_prog_mem both `equ err_mem` unchanged.
err_mem:        db      "out of memory",13,10,0

relink:
                ld      a,1                 ; LE_OP_RELINK
                ld      (LE_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LINEEDIT
                call    subrom_call
                jp      c,subrom_absent_error
                ret
    ELSE
                include "basic/lineedit-body.inc"   ; lean: inline, byte-identical
    ENDIF

    IF ROM_BASE < $4000
; --- gosub_push: push a bounds-checked GOSUB return frame (repack golf) -------
; The 4-byte frame is [CURLINE:2][resume-ptr:2]; resume = the token position to
; run when RETURN pops it. Factored out of ex_gosub / eon_gosub (which each used
; to inline this) so the interrupt-trap dispatcher can reuse it as its GOSUB-into-
; handler branch (docs/spec-basic-interrupt-traps.md §2.1/§10.1). Repack-only: the
; lean ROM keeps the original inline push below (byte-frozen), same discipline as
; the input-devices ev_f_ff golf.
;   IN:  HL = resume token pointer; CURLINE = the line to resume in.
;   OUT: CF clear = pushed, GSP advanced by 4.  CF set = stack full (nothing pushed).
;        Preserves BC (the target line number). Clobbers A, DE, HL.
gosub_push:
                push    bc                  ; guard the caller's target line number
                push    hl                  ; save resume ptr
                ld      hl,(GSP)
                ld      de,GOSUB_STK_END
                or      a
                sbc     hl,de
                jr      nc,gp_full          ; GSP >= end -> too many GOSUBs
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
                pop     bc                  ; restore target line number
                or      a                   ; CF = 0 -> success
                ret
gp_full:
                pop     hl                  ; discard resume ptr
                pop     bc                  ; discard target
                scf                         ; CF = 1 -> stack full
                ret
; gosub_stk_over: shared control-stack-overflow tail (ex_gosub + eon_gosub).
gosub_stk_over:
                ld      a,$CE               ; control-stack overflow landmark
                ld      (ERRMARK),a
                ld      a,7                 ; ERR 7: out of memory (error-handling S2a)
                jp      raise_error
; --- ex_gosub: GOSUB <line> (repack: via gosub_push) -------------------------
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
                call    gosub_push          ; push frame; BC=target kept; CF set = full
                jr      c,gosub_stk_over
                call    find_line_bc        ; CF set + HL = line addr if found
                jp      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
    ELSE
; --- ex_gosub: GOSUB <line> (lean: inline push, byte-frozen) -----------------
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
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF

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
; set_resumeflag_ret: shared tail (error-handling S2b space fix) -- ex_resume's
; res_setptr (basic/interp.asm, repack-only) jumps in here after its own
; `ld (RESUMEPTR),hl`, reusing the RESUMEFLAG:=1 + ret verbatim. A zero-cost
; label: RETURN's own bytes/behaviour here are completely unchanged, and this
; label costs nothing in the lean build either (nothing lean-side jumps to it).
set_resumeflag_ret:
                ld      a,1
                ld      (RESUMEFLAG),a
                ret
ex_ret_under:
                ld      a,$CD               ; "return without gosub" landmark
                ld      (ERRMARK),a
    IF ROM_BASE < $4000
                ld      a,3                 ; ERR 3: return without gosub (error-handling S2a)
                jp      raise_error
    ELSE
                ld      hl,err_noret
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF

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
    IF ROM_BASE < $4000
                cp      '$'                 ; `FOR A$=…` is ERR 13, not ERR 2 (measured
                jp      z,type_mismatch_error ; VG-8020) -- the ONE lvalue shape in this
                                            ; statement that is a type error rather than
                                            ; a syntax error. Repack-only: the lean cart
                                            ; has no error-code machinery (and stays
                                            ; byte-identical).
    ENDIF
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
    IF ROM_BASE < $4000
                ld      a,7                 ; ERR 7: out of memory (error-handling S2a)
                jp      raise_error
    ELSE
                ld      hl,err_stack
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF

; --- ex_next: NEXT [<var>] ---------------------------------------------------
; Step the loop variable of the matching FOR frame, test against the limit, and
; either resume at the frame's body (loop continues) or pop the frame and run on
; (loop ends). A named NEXT closes any inner frames above the matching one.
ex_next:
                inc     hl                  ; past the NEXT token
                call    skip_spaces
                ld      a,(hl)
                call    is_letter
                jr      nc,nx_notletter     ; bare NEXT (or junk -> ERR 2 below)
                call    upcase
                ld      c,a                 ; C = named loop variable
                inc     hl                  ; consume the letter
                jr      nx_find
nx_notletter:
    IF ROM_BASE < $4000
                ; `NEXT 1` is ERR 2 on the reference, not "next without for" --
                ; only a genuine BARE next (statement terminator) takes the top
                ; frame. Measured with the rest of the trap-class family.
                or      a
                jr      z,nx_top
                cp      COLON
                jp      nz,stmt_error
    ENDIF
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
    IF ROM_BASE < $4000
                ld      a,1                 ; ERR 1: next without for (error-handling S2a)
                jp      raise_error
    ELSE
                ld      hl,err_nofor
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF

    IF ROM_BASE < $4000
err_stack       equ     err_mem             ; repack: share sl_oom's "out of memory"
                                            ; (D-2 self-funding — the string bytes are
                                            ; identical; lean keeps its own copy below,
                                            ; byte-identical). Saves 15 B in the repack
                                            ; page-1 budget for the run-mode " in <line>"
                                            ; suffix (docs/spec-basic-error-handling.md S1 D-2).
    ELSE
err_stack:      db      "out of memory",13,10,0
    ENDIF
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
    IF ROM_BASE < $4000
                ld      a,4                 ; ERR 4: out of data (error-handling S2a)
                jp      raise_error
    ELSE
                ld      hl,err_data
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF
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

; --- READ/DATA value engine (read_one_value / data_seek / data_parse_int) ---
; Carved out to a PAGE-0 sub-ROM tenant in the repack build to fund graphics G7
; (docs/spec-eviction-g7-space.md); the lean cart keeps the body inline and stays
; byte-identical. The body itself is basic/readdata-body.inc.
    IF ROM_BASE < $4000
; Resident stub: CALSLT the tenant, then rebuild the (CF, DE) contract from the
; RDV_ST/RDV_VAL cells -- CF cannot ride back through subrom_call.
read_one_value:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_READVAL
                call    subrom_call         ; CF=1 iff the sub-ROM is absent
                ld      de,(RDV_VAL)
                jr      c,rov_stub_none     ; defensive: no tenant -> out of data
                ld      a,(RDV_ST)
                or      a
                ret     z                   ; 0 = out of data (CF clear)
                scf
                ret
rov_stub_none:
                or      a                   ; CF clear -> out of data
                ret
    ELSE
                include "basic/readdata-body.inc"
    ENDIF

; --- ex_on: ON <expr> GOTO/GOSUB <line>[,<line>...] -------------------------
; Evaluates expr (1-based index N). Finds the Nth branch target in the
; comma-separated $0E list and branches (GOTO) or calls (GOSUB) to it.
; N=0 or N > count of targets falls through to the next statement.
; Source: public MSX-BASIC language reference (ON…GOTO/GOSUB semantics).
ex_on:
                inc     hl                  ; past ON_TOKEN
    IF ROM_BASE < $4000
                call    skip_spaces         ; A = (hl)
                cp      ERROR_TOKEN         ; ON ERROR GOTO / GOTO 0 (error-handling S2b)
                jp      z,ex_on_error       ; -- NOT an <expr> ON...GOTO/GOSUB list
    ENDIF
                call    eval                ; DE = N (1-based index), HL past expression
    IF ROM_BASE < $4000
                call    get_byte_arg        ; D-F2-2 stage B: ON's selector is a byte 0..255
                                            ; (>int16 ERR 6, 256.. ERR 5); DE=N, D=0 for
                                            ; eon_seek_nth. ON 0 = valid no-branch (falls thru).
    ENDIF
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

    IF ROM_BASE < $4000
; eon_gosub (repack: via gosub_push, sharing gosub_stk_over)
eon_gosub:
                inc     hl                  ; past GOSUB token
                call    eon_seek_nth        ; BC = line number, HL past list; CF set if found
                jp      nc,exec_stmt        ; N=0 or N > count -> fall through
                call    gosub_push          ; push [CURLINE][resume=HL]; BC kept; CF=full
                jp      c,gosub_stk_over    ; jp (not jr): gosub_stk_over is far back
                call    find_line_bc
                jp      nc,ex_goto_undef
                ld      (GOTOTGT),hl
                ld      a,1
                ld      (GOTOFLAG),a
                ret
    ELSE
; eon_gosub (lean: original inline push, byte-frozen)
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
                jp      fre_abort_low       ; abort the RUN (D-1); lean == print_string
    ENDIF

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

; --- ex_on_error: ON ERROR GOTO <line> / GOTO 0 -----------------------------
; (docs/spec-basic-error-handling-s2b-packet.md §5.3). HL enters on the
; ERROR token (ex_on has already peeked ON_TOKEN,ERROR_TOKEN before jumping
; here). `GOTO 0` disables the handler (ONELIN:=0) and also clears an
; in-progress handler state (real-MSX: ON ERROR GOTO 0 re-enables normal
; aborts even from inside a handler). An undefined <line> aborts with
; "Undefined line number" at definition time (reference behaviour). Success
; falls through to exec_stmt: ON ERROR GOTO is an ordinary non-branching
; statement (unlike GOTO/RESUME), so `ON ERROR GOTO 100:PRINT"x"` must still
; run the rest of the line. Clobbers A, BC, DE, HL.
    IF ROM_BASE < $4000
ex_on_error:
                inc     hl                  ; past ERROR_TOKEN
                call    skip_spaces         ; A = (hl)
                cp      GOTO_TOKEN          ; syntax: ON ERROR *GOTO* <line>
                jp      nz,stmt_error
                inc     hl                  ; past GOTO_TOKEN
                call    skip_spaces
                cp      LINENO_TOKEN        ; $0E,lo,hi expected (GOTO's own operand shape)
                jp      nz,stmt_error
                inc     hl
                ld      c,(hl)              ; target line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL -> cursor past the $0E operand
                ld      a,b
                or      c
                jr      z,oe_disable        ; GOTO 0 -> disable
                push    hl                  ; [cursor] guard across find_line_bc (which
                                            ; clobbers HL, returning the match in it)
                call    find_line_bc        ; CF set + HL = link addr if found
                jr      nc,oe_undef
                ld      (ONELIN),hl         ; ONELIN := the handler line's LINK address
                                            ; (find_line_bc's return convention -- exactly
                                            ; what raise_error's trap / rp_goto expect)
                pop     hl                  ; HL = cursor again (ON ERROR GOTO does not
                                            ; redirect flow -- continue the same line)
                jp      exec_stmt
oe_undef:
                pop     hl                  ; balance the stack (cursor unused, aborting)
                jp      ex_goto_undef       ; undefined line -> Undefined line number
oe_disable:
                ld      de,0                ; (DE, not HL -- HL still holds the cursor
                ld      (ONELIN),de         ; to continue the line with)
                ld      (ONEFLG),a          ; GOTO 0 inside a handler clears the in-
                                            ; handler state (re-enables normal aborts).
                                            ; A is already 0 (the `or c` that branched
                                            ; here left it 0; ld de,0/ld (nn),de don't
                                            ; touch A) -- ERR-reset-on-RESUME follow-up
                                            ; reclaimed the redundant xor a
                jp      exec_stmt
    ENDIF
