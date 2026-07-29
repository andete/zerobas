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
                                            ; (D-2's explicit `DIRECTF := 1` used to sit
                                            ; here; it is now DERIVED in rp_exec, which
                                            ; this path always reaches before any
                                            ; statement runs -- and nothing between here
                                            ; and there can raise an error to read it)
                ld      (SAVSTK),sp         ; error-handling S2b §6: direct-mode anchor
                                            ; (a direct ERROR n/error WITH a handler
                                            ; resets cleanly; without one, S1's REPL
                                            ; return already worked)
                ; --- direct-mode control flow (docs/spec-basic-direct-ctrl.md §3) ---
                ; The typed line is executed as a VIRTUAL LINE through the ordinary
                ; run loop, NOT by a bare `jp exec`. `exec` only walks statements; the
                ; three CONTROL-TRANSFER protocols are all serviced by the loop AROUND
                ; it (GOTOFLAG, RESUMEFLAG+RESUMEPTR, ENDFLAG), so a plain `jp exec`
                ; ran a GOTO / GOSUB / RETURN / continuing NEXT for its side effects
                ; and then returned to the prompt with the transfer still pending --
                ; SILENTLY (measured: direct `GOTO 10`, `IF 1 THEN 10`, `ON 1 GOTO 10`
                ; all no-ops; a direct FOR/NEXT looped zero times and left RESUMEFLAG
                ; raised for the next RUN to trip over).
                ld      hl,dir_line         ; CURLINE := the ROM line header -- which IS
                ld      (CURLINE),hl        ; the definition of direct mode (see rp_exec)
                xor     a                   ; the loop's own flags must start clean:
                ld      (ENDFLAG),a         ; a leftover ENDFLAG from the last STOP
                ld      (RESUMEFLAG),a      ; would abort this line before statement 1,
                ld      (GOTOFLAG),a        ; and a stale RESUMEFLAG would divert it
                ld      hl,TOKBUF
                jp      rp_exec             ; unwinds to the REPL at end of line
    ELSE
                ld      hl,TOKBUF
                jp      exec                ; lean: statement walk only (byte-frozen)
    ENDIF
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
                ; TKOVF carries the REASON the crunch rejected the line: 1 = a float
                ; literal overflowed (F1, sub/tkfloat.asm), 25 = the crunched body
                ; exceeded TOKMAX_BODY (D-LINEMAX R-2, tokenise.inc tk_end). Either
                ; way the line is never executed and never stored -- only the report
                ; differs.
                ;
                ; This reports rather than calling raise_error, and that is deliberate
                ; (not an oversight inherited from the float path). The error happens at
                ; line ENTRY, before anything executes, and raise_error's trap arm does
                ; `ld sp,(SAVSTK)` + `jp rp_lp` whenever a handler is armed -- from the
                ; REPL, with the SAVSTK anchor of whatever ran last, that would jump
                ; INTO a finished program on a mistyped line. The reference cannot trap
                ; this either: it is raised by the editor, not by a running program.
                ; ERRCODE is still set so PRINT ERR reads 25, as measured.
                ; TKOVF=25 CARRIES THE ERR CODE rather than a second constant
                ; here -- page 1 had 10 free bytes when this landed, so the reason
                ; code and the error code are deliberately the same byte.
                ld      a,(TKOVF)
                ld      hl,err_overflow     ; the float arm's message (the fallthrough)
                cp      1
                jr      z,dl_ovf_report
                ld      (ERRCODE),a         ; A = 25: PRINT ERR reads it, as measured
                ld      hl,err_linebuf_overflow ; low-region string pool (basic/main.asm)
dl_ovf_report:
                jp      print_msg           ; reports and returns to the REPL (D-MSGENC:
                                            ; this arm is repack-only, and both its
                                            ; messages are now encoded)
; err_overflow moved to the LOW-REGION STRING POOL (basic/main.asm), where it is the
; shared TAIL of `Line buffer overflow` -- 11 bytes of page 1 reclaimed to pay for
; the arm above. Read its header before editing either message.
; --- dir_line: the VIRTUAL LINE a typed line executes under -----------------
; docs/spec-basic-direct-ctrl.md §3. Laid out exactly like a stored line's
; header -- [link:2][lineno:2] -- so the run loop needs no direct-mode special
; case anywhere: CURLINE := dir_line and every existing path just works.
;
; It lives in ROM, not RAM, for three reasons: it is entirely constant, so a
; per-line write would be pure cost; nothing can corrupt it; and it claims no
; RAM. The two words OVERLAP by design -- the link points at the lineno field,
; whose value 0 is simultaneously the $0000 end-of-program marker. So running
; off the end of a typed line takes the loop's ordinary fall-through (CURLINE
; := link) and then its ordinary "$0000 link -> end of program" exit, back to
; the REPL. Deliberately NOT the stored program's own end marker at (PRGEND):
; a typed `NEW` / `LOAD` / line edit moves that MID-LINE, and the snapshot
; would already be stale by the time the line ended.
;
; The lineno field is never printed: print_in_lineno and record_errline are the
; only two readers of CURLINE+2 in this build and both take their DIRECTF branch
; first. Its value is 0 regardless, so even a missed gate could only print
; "in 0" rather than garbage.
dir_line:       dw      dir_line + 2        ; [link] -> the word below
                dw      0                   ; [lineno] = 0 == the $0000 end marker
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
    IF ROM_BASE < $4000
                ld      (TRACEFLAG),a       ; NEW is the ONLY thing that clears TRON.
                                            ; RUN does not reset it, END does not clear
                                            ; it, and a line carrying TROFF is itself
                                            ; traced -- all measured (spec §3.4). A is
                                            ; still 0 from the xor above.
    ENDIF
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
                                            ; D-ONELIN (docs/spec-basic-onelin-reset-
                                            ; scope.md §4): the `ld hl,0 / ld (ONELIN),hl`
                                            ; that used to sit HERE moved down into
                                            ; vars_reset (basic/arrays.asm), called six
                                            ; lines up. RUN really does disarm -- that
                                            ; half of the §7 hypothesis MEASURED true
                                            ; (`run_after_arm`) -- but it is not RUN's
                                            ; OWN rule: the reference disarms whenever
                                            ; the variable world is reset, which is RUN,
                                            ; NEW, CLEAR/MAXFILES *and every program
                                            ; EDIT*. vars_reset is the one routine all
                                            ; five reach. Net zero bytes: this site
                                            ; funded that one.
                ld      (ONEFLG),a          ; not inside a handler at RUN start (A is
                                            ; still 0 from the xor a above -- nothing
                                            ; since touches it: the ERR-reset-on-RESUME
                                            ; follow-up reclaimed the redundant xor a)
                call    trap_init           ; interrupt-traps T1: RUN re-arm — clear the
                                            ; ZTRAP table so a prior run's traps never
                                            ; leak into this one (traps.asm). Inert until
                                            ; the arming statements land (TRAPENA==0).
    ENDIF
    IF ROM_BASE >= $4000
                ld      hl,GOSUB_STK        ; empty return stack
                ld      (GSP),hl
                ld      hl,FOR_STK          ; empty FOR stack
                ld      (FSP),hl
    ENDIF                                   ; repack: MOVED into clear_vars (called
                                            ; three lines up) so cold boot / NEW /
                                            ; CLEAR reset the control stacks too --
                                            ; docs/spec-basic-direct-ctrl.md §4.
                                            ; Net zero bytes; the lean cart keeps the
                                            ; inline copy and stays byte-identical.
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
    IF ROM_BASE < $4000
                ; D-ONEFLG site C (docs/spec-basic-oneflg-reset-scope.md §4):
                ; running off the end of the program TERMINATES the run, so the
                ; handler context dies here too -- and A is ALREADY 0 on this
                ; arm (it is d|e, and the branch is taken exactly when that is
                ; zero), so the clear costs no `xor a`. 5 B over the `ret z` it
                ; replaces. ⚠️ The reference does not reach a silent end here at
                ; all: falling off the end while INSIDE a handler raises ERR 21
                ; "No RESUME" (spec §2 c3b), which zerobas does not raise --
                ; filed separately (spec §7). When that lands, this site becomes
                ; redundant with site A and can be reclaimed.
                jr      nz,rp_notend
                ld      (ONEFLG),a
                ret
rp_notend:
    ELSE
                ret     z                   ; $0000 link -> end of program
    ENDIF
                inc     hl                  ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> token body
    IF ROM_BASE < $4000
                ; TRON: decorate this line with `[<lineno>]` before it runs
                ; (basic/missing.asm). THIS IS THE FRESH-LINE-ENTRY POINT, and it
                ; is the ONLY one -- which is what makes the measured trace shapes
                ; come out right without a single extra test:
                ;   * rp_goto (GOTO/GOSUB/trap dispatch) and the fall-through to
                ;     the next line both re-enter at rp_lp, so both are traced;
                ;   * a MID-LINE RESUME (RETURN, a continuing NEXT) takes the
                ;     rp_resume branch ABOVE this and reaches rp_exec without
                ;     passing here, so it is silent.
                ; That is exactly the measured FOR/NEXT trace [20][30][30][40]
                ; (line 20 entered once, resumed silently) and GOSUB's [40][20].
                ;
                ; ⚠️ NO DIRECT-MODE TEST IS NEEDED HERE, and the reason is
                ; structural rather than lucky: a typed line runs via `jp rp_exec`
                ; (dispatch_line), which never enters rp_lp at all. The spec
                ; expected to re-derive DIRECTF here from CURLINE+1 vs
                ; dir_line >> 8, because DIRECTF is stale before rp_exec computes
                ; it -- but the branch that would have needed the test is
                ; unreachable. The one case that DOES come back through here after
                ; a typed line, the fall-through off dir_line, returns to the REPL
                ; on the $0000 link two instructions above.
                ld      a,(TRACEFLAG)
                or      a
                call    nz,trace_line       ; preserves HL (the token cursor)
    ENDIF
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
    IF ROM_BASE < $4000
                ; Direct-mode control flow (docs/spec-basic-direct-ctrl.md §5):
                ; DIRECTF is DERIVED here, not carried. It is exactly "the line I
                ; am about to run is the typed one", and this is the single point
                ; every line entry AND every mid-line resume passes through, so it
                ; cannot go stale. A sticky flag would be wrong in both directions
                ; and both were MEASURED on the VG-8020: a direct `GOSUB 10` into a
                ; broken line 10 reports "Syntax error IN 10" (run mode), and the
                ; RETURN back into the rest of the typed line reports a bare
                ; "Syntax error" (direct mode again).
                ; The HIGH BYTE alone decides it. CURLINE's value set is small and
                ; enumerable: a stored line's link address, always in [TXTBASE
                ; $8001, TXTMAX $BE00); dir_line; and dir_line+2 (what the loop's
                ; fall-through leaves behind after a typed line ends). ROM and the
                ; text area are disjoint, so the only address sharing dir_line's
                ; page is dir_line+2 -- and rp_lp returns to the REPL on that one
                ; before ever reaching here.
                ld      a,(CURLINE+1)
                cp      dir_line >> 8
                ld      a,0                 ; (xor a would clobber the flags)
                jr      nz,rpe_mode
                inc     a
rpe_mode:
                ld      (DIRECTF),a
    ENDIF
                call    BREAKX
                pop     hl
                jr      c,rp_break
    IF ROM_BASE < $4000
                ; Ctrl-STOP is NOT down: RELEASE the STOP entry's edge shadow, so the
                ; next press reads as a fresh 0->1 edge. This is the release observation
                ; the run-loop seam needs — rp_break is only reached when the key IS
                ; down, so without it the shadow would latch on forever after the first
                ; press and every later press would be ignored. (ep_strig gets the same
                ; observation for free: it polls GTTRIG every frame, pressed or not.)
                ld      a,(ZTRAP+ZTI_STOP*ZTRAP_ENTSZ)
                res     6,a                 ; ZTS_SHADOW — the level follows the key
                ld      (ZTRAP+ZTI_STOP*ZTRAP_ENTSZ),a
rp_trapchk:                                 ; interrupt-trap dispatch point (T1); also
                                            ; re-entered by rp_break after latching STOP.
                                            ; Gate is one RAM load in the no-trap case.
                ; DIRECT MODE DOES NOT DISPATCH TRAPS (docs/spec-basic-direct-
                ; ctrl.md §6, DEFERRED). Before this slice a typed line never
                ; reached this loop at all, so no trap could ever fire at the
                ; prompt; routing direct mode through the loop would have made
                ; that happen as a SIDE EFFECT of a FOR/NEXT fix. Whether the
                ; reference fires traps at command level is UNMEASURED, so the
                ; conservative reading -- preserve today's behaviour -- wins
                ; until it is characterized. Same reason rp_break skips the STOP
                ; trap's latch arm in direct mode.
                ld      a,(DIRECTF)
                or      a
                jr      nz,rp_run
                ld      a,(TRAPPEND)
                or      a
                call    nz,check_traps      ; HL = stmt ptr; CF=1 -> fired, CURLINE=handler
                jr      c,rp_lp             ; fired: run the handler line fresh (RESUMEFLAG=0)
rp_run:
    ENDIF
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
    IF ROM_BASE < $4000
                ld      a,(DIRECTF)         ; direct mode: no trap machinery (see
                or      a                   ; rp_trapchk) -> always the classic break,
                jr      nz,rp_do_break      ; reported as a bare "break" by do_break
                ; STOP trap (T1, spec-traps-t1-stop-reslice.md §6/§12.3). `ON STOP GOSUB`
                ; + `STOP ON` makes the program UNBREAKABLE from the keyboard — that is
                ; what the statement is FOR. VG-8020-measured (2026-07-25): while the STOP
                ; entry is ON *or* SERVICING the key NEVER breaks; it is EDGE-latched into
                ; PENDING against the entry's shadow bit and fires the handler once.
                ;   ON / SERVICING -> latch on a 0->1 edge, never break
                ;   OFF / STOP     -> the classic break
                ; Both sampled states have bit 0 set (ON=01, SERVICING=11) and neither
                ; unsampled one does (OFF=00, STOP=10), so the state test is one `bit 0` —
                ; the same test ep_strig_lp uses. This IS the T2 STRIG model (spec-traps-
                ; t2-strig.md §4) applied to Ctrl-STOP, and it is deliberately shaped to
                ; read the same.
                ; WHY SERVICING LATCHES RATHER THAN BREAKS: a press while the handler runs
                ; cannot fire then (state != ON), but trap_return_check re-raises TRAPPEND
                ; when RETURN restores ON, so it fires exactly ONCE afterwards. The oracle
                ; gives one extra fire for a 100 ms tap AND for a 3 s hold — edge, not
                ; level — and never breaks out of the handler in either case.
                ; THIS REPLACES STOPGRACE, the one-VBLANK window this seam used to carry.
                ; That was a timing proxy for exactly what the shadow does properly: the
                ; triggering key is usually still down when the handler is entered, and
                ; check_traps PRESERVES ZTS_SHADOW across a fire, so it cannot re-latch —
                ; with no timing window at all. The old grace expired after one frame and
                ; a key still held then aborted the handler, which the reference does not
                ; do (found by basic_probe_stop_trap.py's D case once it was gated on
                ; `done`; its old green was two mid-loop readings, not an agreement).
                push    hl                  ; guard the resume stmt ptr across the entry test
                ld      hl,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ
                bit     0,(hl)              ; ON or SERVICING -> sampled, never breaks
                jr      z,rp_real_break     ; OFF / suspended -> the classic break
                ; ...AND ONLY IF THE ENTRY ACTUALLY HAS A HANDLER. Suppressing the
                ; break on the STATE ALONE is a MEASURED DIVERGENCE (VG-8020 flag 0
                ; vs zerobas flag 5, basic_probe_stop_trap.py case F): with `STOP ON`
                ; but a CLEARED handler the reference breaks the program normally.
                ; Note this is the OPPOSITE of the KEY trap, where `KEY(n) ON` with an
                ; empty handler slot still swallows the key (spec-traps-t3-key.md §1.2
                ; -- diversion there follows the state alone). The two traps genuinely
                ; differ, so do not "harmonise" them; STOP tracks handler != 0, which
                ; is also what check_traps' fire condition requires.
                ; Reachable only now that `ON STOP GOSUB` with no line CLEARS the slot
                ; instead of raising ERR 2 -- before that fix a live entry with a zero
                ; handler could not be built, which is why this hid for so long.
                inc     hl
                ld      a,(hl)              ; handler LINK, lo
                inc     hl
                or      (hl)                ; ..or hi -> ZF iff the link is 0
                dec     hl
                dec     hl                  ; HL back to the state byte
                jr      z,rp_real_break     ; no handler -> the break happens normally
                bit     6,(hl)              ; shadow: still down since the last sample?
                jr      nz,rp_brk_run       ; no edge -> ignore the key, run the statement
                set     6,(hl)              ; 0->1 edge: latch the level...
                set     7,(hl)              ; ...and the entry's PENDING
                ld      a,1
                ld      (TRAPPEND),a        ; wake the run-loop dispatcher
rp_brk_run:
                pop     hl                  ; HL = resume stmt ptr, intact
                jr      rp_trapchk          ; dispatch now (do NOT break)
rp_real_break:
                pop     hl                  ; HL = resume stmt ptr
    ENDIF
rp_do_break:
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
    IF ROM_BASE < $4000
                ; ...but a DIRECT-mode break leaves NO resume point (docs/spec-
                ; basic-direct-ctrl.md §5). MEASURED on the VG-8020: `PRINT 1:STOP:
                ; PRINT 2` typed at the prompt reports "Break", and the CONT that
                ; follows reports "Can't CONTINUE" -- there is nothing to go back
                ; to, the typed line's buffer is about to be overwritten. DIRECTF
                ; is 0/1, so `xor 1` is the whole gate.
                ld      a,(DIRECTF)
                xor     1
    ELSE
                ld      a,1
    ENDIF
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
                ; for a runtime error's " in <line>" suffix. Output in run mode is
                ; byte-for-byte the old inline tail ("break" + " in " + <N> + CRLF).
                ; in DIRECT mode print_in_lineno now suppresses the suffix itself
                ; (the reference prints a bare "Break" for a typed STOP -- measured),
                ; so this tail stays a single unconditional jump.
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
                ; DIRECT mode names no line (docs/spec-basic-direct-ctrl.md §5):
                ; a typed `STOP` reports a bare "Break" and a typed error carries no
                ; suffix -- both MEASURED on the VG-8020. The gate lives HERE, at the
                ; single place that reads CURLINE+2 for output, so do_break's tail
                ; stays one unconditional jump and the direct line's [lineno] field
                ; never has to be initialised. (fre_abort_low keeps its own DIRECTF
                ; test: it picks print_string vs print_string_stopcr, so it must
                ; branch before it prints, not after.)
                ld      a,(DIRECTF)
                or      a
                jp      nz,print_crlf
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

; --- print_msg_stopcr / print_msg: the D-MSGENC message decoder ----------------
; docs/spec-basic-msgenc-carve.md §4.3. Error message strings are PHRASE-ENCODED
; in the repack build: bytes MSGESC_LO..MSGESC_HI index msg_phrase_tab, everything
; >= $20 is a literal, and the CRLF is emitted HERE instead of being baked into
; every message (§4.2 — 2 B x 25 messages).
;
; 🔴 THIS CANNOT GO INTO print_string. print_string also carries USER DATA --
; DETOKBUF (LIST output), NUMBUF, FOUTBUF -- so an escape check there would expand
; a phrase into a user's own program text the moment a string literal contained a
; CHR$(1). Messages get their own entry; print_string is untouched and is what
; emits the phrases themselves.
;
; This REPLACES print_string_stopcr (10 B), whose whole job was to halt at the
; baked CR so print_in_lineno could append " in <line>". With the CRLF no longer
; baked, the body-only routine is the primitive and the CRLF is the wrapper --
; fre_abort_low's DIRECTF test now picks print_msg vs print_msg_stopcr.
; Clobbers A (+ the HL walk), exactly as print_string/print_string_stopcr did:
; pchar preserves every register, so the abort path's depth-independence
; (D-CUR-D, basic/arrays.asm) is unchanged.
print_msg_stopcr:                           ; run mode: body only, no CRLF
pm_lp:          ld      a,(hl)
                inc     hl
                or      a
                ret     z
                cp      MSGESC_HI + 1       ; MSGESC_LO..MSGESC_HI -> phrase escape;
                jr      nc,pm_lit           ; every literal is >= $20 (the baked
                                            ; 13,10 are gone), so this is exact
                push    hl
                ld      hl,msg_phrase_tab
                dec     a                   ; escape 1 -> phrase 0 (no skip)
                jr      z,pm_emit
                ld      b,a                 ; skip B whole NUL-terminated phrases
pm_skip:        ld      a,(hl)
                inc     hl
                or      a
                jr      nz,pm_skip
                djnz    pm_skip
pm_emit:        call    print_string        ; phrases are plain NUL-terminated text
                pop     hl
                jr      pm_lp
pm_lit:         call    pchar               ; PRDEST sink (fre_abort_low zeroed it)
                jr      pm_lp

print_msg:      call    print_msg_stopcr    ; direct mode: body + CRLF
                jp      print_crlf

; --- msg_phrase_tab: §4.1's four phrases, NUL-terminated, in escape order ------
; ⚠️ MSGESC_UTOF and MSGESC_ILLFN DELIBERATELY DROP THE LEADING LETTER so that
; "Out of"/"out of" and "Illegal"/"illegal" share ONE entry with no case-fold flag
; in the decoder above. The arrays arc's §9.5 capitalisation split and PROVENANCE
; §851's lowercase-strings policy are therefore untouched: each message still
; spells its own first letter.
msg_phrase_tab:
                db      " error",0          ; MSGESC_ERROR
                db      "ut of ",0          ; MSGESC_UTOF
                db      "llegal function call",0 ; MSGESC_ILLFN
                db      " without",0        ; MSGESC_WITHOUT
                db      "file ",0           ; MSGESC_FILE (S-FCH-2)
    ENDIF

; --- ex_stop: STOP statement — break and record a CONT resume point ----------
; STOP halts the program exactly like END, but ALSO records where to continue so
; a following CONT resumes at the statement after STOP. (END does not: it ends
; the run with no resume point, so CONT after END is "Can't CONTINUE".)
; HL enters on the STOP token. Repack (T1): `STOP ON|OFF|STOP` instead arms the
; STOP interrupt trap's tri-state (spec-traps-t1-stop-reslice.md §5.2); a bare STOP
; (EOL / ':' / anything else) still halts. Lean stays `inc hl / jp do_break`
; byte-identically (both IF blocks vanish).
ex_stop:
                inc     hl                  ; past STOP token
    IF ROM_BASE < $4000
                call    skip_spaces
                ld      a,(hl)
                call    onoff_decode        ; STOP ON|OFF|STOP -> A = the ZTS_ state
                jr      c,es_set
    ENDIF
                jp      do_break            ; bare STOP -> record + "Break in <line>"
    IF ROM_BASE < $4000
es_set:
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the exec-continue ptr across set_state
                ld      hl,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ
                ; DELIBERATELY NO EDGE-SHADOW SEED HERE — and that is a MEASURED
                ; difference from `STRIG(n) ON`/`KEY(n) ON`, not an omission. Do not
                ; "harmonise" this with ex_strig_set.
                ; STRIG seeds because a trigger already held when its trap is enabled
                ; must not manufacture a press (T2 oracle, E/F). Ctrl-STOP does NOT
                ; behave that way: with the key held, a handler that re-arms itself
                ; (`102 STOP OFF:STOP ON` — one line, so the run loop's per-LINE BREAKX
                ; poll never sees the OFF window) fires AGAIN on the reference, over and
                ; over. VG-8020, key held for the whole run: 122 fires, reproducible;
                ; with a seed here zerobas gave exactly 1. The seed was written first and
                ; the oracle removed it.
                ; The "held key predates the enable" case that STRIG needs a seed for is
                ; UNREACHABLE for STOP anyway: OFF (00) and STOP (10) both clear bit 0, so
                ; a Ctrl-STOP held while the trap is not ON hits rp_real_break and stops
                ; the program at the line boundary BEFORE `STOP ON` can run.
                call    set_state
                pop     hl                  ; HL = cursor past the sub-keyword (':'/EOL)
                jp      exec_stmt           ; continue the line -- a bare `ret` here would
                                            ; SWALLOW the rest of the line (STOP ON:STOP OFF
                                            ; left OFF a no-op; VG-8020 differential caught it)
    ENDIF

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
                                            ; (an explicit `DIRECTF := 0` used to sit
                                            ; here. It is DEAD since the direct-mode
                                            ; slice: DIRECTF is DERIVED at rp_exec from
                                            ; CURLINE (docs/spec-basic-direct-ctrl.md
                                            ; §5), and the `jp rp_lp` below reaches it
                                            ; -- via rp_resume, RESUMEFLAG being set --
                                            ; before any statement runs, with nothing on
                                            ; the way able to read the flag or raise an
                                            ; error. It derives the SAME 0: CONTLINE is
                                            ; always a stored line's link address, since
                                            ; do_break gates CONTVALID on DIRECTF and a
                                            ; direct-mode break leaves no resume point
                                            ; at all. 3 B of page 1 reclaimed.)
                ld      hl,(CONTLINE)
                ld      (CURLINE),hl
                ld      hl,(CONTPTR)
                ld      (RESUMEPTR),hl
                ld      a,1
                ld      (RESUMEFLAG),a      ; resume mid-line at CONTPTR
    IF ROM_BASE < $4000
                ; D-CONTD (docs/spec-basic-cont-depth.md §2/§3): re-enter the
                ; loop at the depth its exit `ret` unwinds FROM. Without this,
                ; CONT starts a fresh loop iteration from STATEMENT depth -- it
                ; is reached from inside the loop's own `call exec` -- so a
                ; stale return frame sits underneath, and the loop's exit `ret`
                ; lands back INSIDE the loop body instead of at the REPL. That
                ; re-entry reads ENDFLAG: after an END it is 1 and the `ret nz`
                ; fires again (clean BY LUCK, which is why only ONE of the two
                ; exits ever showed a symptom); after the $0000-link exit it is
                ; 0, so the loop advances to a "next line" with HL still on the
                ; end marker and executes whatever follows the program --
                ; measured as `Illegal function call in 3346`, a line that does
                ; not exist. Same class as D-CUR-D's abort chain: a `ret` that
                ; only unwinds correctly at one depth.
                ; SAVSTK is dl_cmd's anchor for THE CONT LINE ITSELF (written
                ; immediately before its own `jp rp_exec`), so it is fresh here
                ; -- the same anchor raise_error's trap branch already restores.
                ; ⚠️ This DISCARDS exec's frame, so anything after CONT on the
                ; typed line is dropped. That is REFERENCE BEHAVIOUR, measured:
                ; `CONT:PRINT…` prints nothing extra on the VG-8020 either
                ; (spec §3, `cont_rest_of_line`). GOSUB/FOR frames are untouched
                ; -- they live in their own RAM stacks (GSP/FSP), gated by the
                ; cont_gosub_live / cont_for_live rows.
                ld      sp,(SAVSTK)
    ENDIF
                jp      rp_lp               ; re-enter the run loop
ex_cont_no:
                ld      a,$C9               ; "can't continue" landmark (distinct byte)
                ld      (ERRMARK),a
                ld      hl,err_cont
    IF ROM_BASE < $4000
                jp      print_msg           ; D-MSGENC: encoded body + emitted CRLF
err_cont:       db      "can't continue",0  ; (no phrase hit; the 2 B is §4.2's CRLF)
    ELSE
                jp      print_string
err_cont:       db      "can't continue",13,10,0
    ENDIF

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
    IF ROM_BASE < $4000
err_mem:        db      "o",MSGESC_UTOF,"memory",0      ; D-MSGENC: 16 B -> 9 B
    ELSE
err_mem:        db      "out of memory",13,10,0
    ENDIF

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
    IF ROM_BASE < $4000
                ; interrupt-trap re-enable (T1): if any trap is servicing and THIS
                ; RETURN's frame is the trap's own (GSP match), auto-resume it to ON
                ; before the normal pop (spec-traps-t1-stop-reslice.md §8). The gate
                ; is one RAM load on every RETURN in the common (no-trap) case.
                ld      a,(TRAPSVC)
                or      a
                call    nz,trap_return_check
    ENDIF
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
    IF ROM_BASE < $4000
err_noret:      db      "return",MSGESC_WITHOUT," gosub",0  ; D-MSGENC: 23 B -> 14 B
err_nofor:      db      "next",MSGESC_WITHOUT," for",0      ; D-MSGENC: 19 B -> 10 B
    ELSE
err_noret:      db      "return without gosub",13,10,0
err_nofor:      db      "next without for",13,10,0
    ENDIF

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
    IF ROM_BASE < $4000
err_data:       db      "o",MSGESC_UTOF,"data",0        ; D-MSGENC: 14 B -> 7 B
    ELSE
err_data:       db      "out of data",13,10,0
    ENDIF

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
                cp      STOP_TOKEN          ; ON STOP GOSUB <line> (interrupt-traps T1)
                jp      z,ex_on_stop        ; -- arm the STOP trap handler
    IF TRAPS_T4
                cp      SPRITE_TOKEN        ; ON SPRITE GOSUB <line> (traps T4) -- also
                jp      z,ex_on_sprite      ; a SINGLE-byte token ($C7), like KEY
    ENDIF
    IF TRAPS_T3
                cp      KEY_TOKEN           ; ON KEY GOSUB <list> (interrupt-traps T3)
                jp      z,ex_on_key         ; -- a SINGLE-byte token, so cheaper than the
                                            ; two-byte $FF $A3 STRIG peek below
    ENDIF
                cp      PEEK_PREFIX         ; $FF -> a two-byte function token. STRIG
                jr      nz,ex_on_expr       ; ($FF $A3) is the ONE trap event spelled that
                inc     hl                  ; way; every other $FF function is an ordinary
                ld      a,(hl)              ; selector expression (`ON VAL(x$) GOTO ...`),
                cp      STRIG_TOKEN         ; so put the cursor back and fall through.
                jp      z,ex_on_strig       ; (entered with HL on the selector byte)
    IF TRAPS_T5
                call    iv_match            ; ON INTERVAL=n GOSUB <line> (traps T5) --
                jp      c,ex_on_interval    ; a reserved-word COMPOUND, not a token, so
                                            ; this is a 6-byte literal compare rather
                                            ; than a `cp` (arc spec §0). CF=0 leaves HL
                                            ; on the selector for the dec below.
    ENDIF
                dec     hl
    ENDIF
ex_on_expr:                                 ; ON <expr> GOTO/GOSUB -- the ordinary form
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

; --- ex_on_stop: ON STOP GOSUB <line> -- arm the STOP interrupt trap ----------
; Reached from ex_on's sibling peek (HL on the STOP token). Stores the resolved
; handler LINK into the ZTRAP STOP entry; state is left as-is (arm != enable --
; `STOP ON` enables). Undefined line -> Undefined line number, like GOSUB. Does
; not redirect flow (continues the same line, as ON ERROR GOTO does).
; spec-traps-t1-stop-reslice.md §5.1.
; T4 shares this whole body: `ON SPRITE GOSUB <line>` is `ON STOP GOSUB <line>`
; with a different entry index, and after the no-line fix below they are otherwise
; identical token for token. The two heads load the ADDRESS of the entry's handler
; field and fall into one parser (measured cheaper than duplicate-and-specialise
; here -- unlike T3, where the duplicate won by 11 B; the difference is that T3 was
; generalising a five-slot LIST parser with a live second caller, while this is a
; single-line parser whose second caller is new. Both variants were built).
ex_on_stop:
                ld      de,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ+1
                jr      eos_common
    IF TRAPS_T4
ex_on_sprite:                               ; ON SPRITE GOSUB <line> (traps T4)
                ld      de,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ+1
    ENDIF
eos_common:                                 ; DE = &entry.handler; HL on the event token
                push    de                  ; ...guarded: trap_line_link RETURNS in DE
                inc     hl                  ; past STOP_TOKEN / SPRITE_TOKEN
                call    skip_spaces
                cp      GOSUB_TOKEN         ; syntax: ON <event> *GOSUB* <line>
                jp      nz,trap_syntax      ; (abandons the pushed DE -- trap_syntax
                                            ; raises, and raise_error resets SP)
                inc     hl
                call    skip_spaces
eos_line:                                   ; T5 enters HERE: `ON INTERVAL=n GOSUB` has
                                            ; already consumed its own `=n` and GOSUB, so
                                            ; it pushes &entry.handler itself and joins
                                            ; the shared store below. Costs nothing -- a
                                            ; label is zero bytes.
                call    trap_line_link      ; CF=1 -> DE = handler LINK
                jr      c,eos_store
                ; NO LINE REFERENCE -> CLEAR THE HANDLER. This used to be
                ; `jp nc,trap_syntax` (ERR 2) and that was a MEASURED DIVERGENCE,
                ; caught by the T4 characterization round's family sweep
                ; (spec-traps-t4-sprite.md §1.5): the reference ACCEPTS a bare
                ; `ON <event> GOSUB` for all four events and clears that entry's
                ; handler -- VG-8020 err=0 vs zerobas err=2, and `ON STOP GOSUB:
                ; POKE&HD004,77` still writes 77 there, so the reference's parser
                ; stops cleanly rather than swallowing the rest of the statement.
                ; ex_on_strig and ex_on_key have always had this shape (an empty
                ; list slot writes 0); STOP was the only one that did not, because
                ; it takes a single line and so never went through the list loop.
                ld      de,0
eos_store:
                pop     bc                  ; BC = &entry.handler (trap_line_link
                                            ; clobbers BC, so it is popped only now)
                ld      a,e
                ld      (bc),a
                inc     bc
                ld      a,d
                ld      (bc),a
                jp      exec_stmt           ; continue the same line (as ON ERROR GOTO)

; --- trap_syntax: a TRAPPABLE Syntax error (ERR 2) for the trap statements ----
; NOT `jp stmt_error`: that prints and aborts the RUN, so an `ON ERROR GOTO`
; program would never see it. The reference raises a trappable ERR 2 for every
; malformed trap statement -- VG-8020-measured for `ON STRIG` and `ON STRIG GOTO`
; (spec-traps-t2-strig.md §1.3, cases S6/S7), which is also what arc spec §7
; specified. Same convention as graphics' gfx_syntax.
trap_syntax:
                ld      a,2
                jp      raise_error

; --- onoff_decode: the shared ON | OFF | STOP sub-keyword decode -------------
; Six statements in this tree decode the same three sub-keywords into the same
; three ZTRAP states, and each one had spelled it out: `STOP ON|OFF|STOP`,
; `INTERVAL ...`, `STRIG(n) ...`, `KEY(n) ...`, `SPRITE ...`, and now `MOTOR`.
; ~19-23 B apiece for a decode that is character-for-character the same.
;
; The share was proposed as a DEFERRED funding lever (spec-traps-t5-interval
; §4.3, and again as spec-basic-missing-class §6.3) and taken instead as the
; FIRST step of the MISSING slice (S-MC-4, overridden). The reason is worth
; keeping: a reserve lever only ever gets pulled mid-overrun, when the budget is
; already spent and the only acceptable outcome is "it fits" -- which is the
; worst condition under which to restructure six live call sites.
;
;   IN:  A  = the token byte under the cursor (callers have already skipped
;             spaces; HL is left pointing AT the token, not past it -- every
;             caller consumes it itself, because each has its own guard-the-
;             cursor dance around set_state).
;   OUT: CF=1 -> matched; A = ZTS_OFF(0) / ZTS_ON(1) / ZTS_STOP(2), which is the
;                set_state argument directly (sysvars.inc: the ZTS_ values ARE
;                0/1/2, so there is no second mapping step at any call site).
;        CF=0 -> not one of the three; A = the original token, so a caller can
;                still test it (ex_stop's bare-`STOP` path needs exactly that).
;   Clobbers A, B, F. **Preserves HL and DE** -- non-negotiable: HL is the token
;   cursor at every site, and ex_strig_stmt/ex_key_stmt hold the ZTRAP entry
;   pointer in DE across this call.
;
; ⚠️ It returns "which one", NOT "is this allowed". Acceptance stays with the
; caller, which is what lets a 2-way site share a 3-way decoder: `MOTOR STOP` is
; a Syntax error (measured, spec §3.5) and that is MOTOR's own one-line `cp
; ZTS_STOP` -- not a variant of this routine. `SCF` preserves Z on the Z80, which
; is what lets each arm be cp/scf/ld/ret-z with no branch.
onoff_decode:
                ld      b,a                 ; keep the token: A is about to be the answer
                cp      OFF_TOKEN
                ld      a,ZTS_OFF
                scf
                ret     z
                ld      a,b
                cp      ON_TOKEN
                ld      a,ZTS_ON
                scf
                ret     z
                ld      a,b
                cp      STOP_TOKEN
                ld      a,ZTS_STOP
                scf
                ret     z
                ld      a,b                 ; no match: hand the token back...
                or      a                   ; ...with CF=0
                ret

; --- trap_line_link: resolve an OPTIONAL `$0E,lo,hi` line reference ----------
; The shared handler-line resolver for the whole `ON <event> GOSUB` family: one
; line for STOP, a comma-list with possibly-empty slots for STRIG (and, later,
; KEY). Factoring it out of ex_on_stop pays for ex_on_strig and pre-pays T3.
;   IN:  HL = token cursor.
;   OUT: CF=1 -> DE = the handler LINK, HL past the 3-byte operand.
;        CF=0 -> the token is not a line reference (an empty list slot / end of
;                list); HL unmoved, DE undefined.
; A reference to a line that does not exist aborts with Undefined line number
; (ERR 8, VG-8020-measured case S5), exactly as GOTO does. Clobbers A, BC.
trap_line_link:
                ld      a,(hl)
                cp      LINENO_TOKEN        ; $0E,lo,hi
                jr      z,tll_have
                or      a                   ; not a line ref -> CF = 0
                ret
tll_have:
                inc     hl
                ld      c,(hl)              ; handler line number, LE
                inc     hl
                ld      b,(hl)
                inc     hl                  ; HL -> cursor past the $0E operand
                push    hl                  ; guard cursor across find_line_bc
                call    find_line_bc        ; CF set + HL = link addr if found
                jr      nc,tll_undef
                ex      de,hl               ; DE = handler LINK
                pop     hl                  ; HL = cursor
                scf
                ret
tll_undef:
                pop     hl                  ; balance the stack (aborting)
                jp      ex_goto_undef       ; undefined line -> ERR 8

    IF TRAPS_T5
; ===========================================================================
; INTERVAL -- interrupt-traps T5 (docs/spec-traps-t5-interval.md).
;
; INTERVAL IS NOT A KEYWORD. It is a reserved-word COMPOUND -- `INT` + the
; literal bytes "ER" + `VAL`, i.e. FF 85 45 52 FF 94 -- the same shape
; kwtable.inc already documents for MAXFILES = MAX+FILES. The first-match-wins
; crunch finds INT before it can consider a longer word, and the statement layer
; matches the resulting byte sequence. So zerobas ALREADY crunched
; `INTERVAL ON` and `ON INTERVAL=10 GOSUB 100` byte-identically to the VG-8020
; before this slice: T5 needs no token, no kwtable row and no crunch work, and
; adding a keyword would have BROKEN the byte-identical crunch (arc spec §0 --
; that retraction is why this slice exists at all).
;
; The price is that both entry points need a literal compare instead of a `cp`.
; It is the one place T5 costs more than T1-T4, all four of which peek a one- or
; two-byte token.

; --- iv_match: does the cursor spell INTERVAL's compound? --------------------
;   IN:  HL -> the selector byte AFTER the $FF prefix (the caller consumed it).
;   OUT: CF=1 -> HL is past the whole compound (on the `=` or the ON/OFF/STOP).
;        CF=0 -> HL UNMOVED, so the caller's fall-through is undisturbed.
;   Clobbers A, B, DE.
iv_match:
                push    hl
                ld      de,iv_seq
                ld      b,5
iv_m_lp:
                ld      a,(de)
                cp      (hl)
                jr      nz,iv_m_no
                inc     hl
                inc     de
                djnz    iv_m_lp
                pop     de                  ; discard the saved cursor; HL is past
                scf
                ret
iv_m_no:
                pop     hl                  ; restore -- the caller still needs it
                or      a                   ; CF = 0
                ret
iv_seq:
                db      INT_TOKEN,"ER",PEEK_PREFIX,VAL_TOKEN

; --- ex_interval: INTERVAL ON | OFF | STOP -----------------------------------
; Entry: HL past the compound. Pure state, exactly like `STOP ON/OFF/STOP`.
; NO EDGE-SHADOW SEED, and no counter reload -- both MEASURED, not inherited:
;   * no shadow because the event is GENERATED, not sampled, so there is no
;     level to de-bounce (contrast STRIG/KEY, which must seed);
;   * no reload because `OFF` then `ON` does NOT restart the period on the
;     reference (§1.4 H3_off_reloads: the next fire lands inside a 60-frame
;     window after re-enabling, where a reload would have put it 100 frames out).
;     Only the ARMING statement reloads. set_state touches the state byte alone,
;     so this falls out for free -- it is recorded here because it is a fact that
;     was checked, not an omission.
ex_interval:
                call    skip_spaces         ; returns A = (HL)
                call    onoff_decode        ; A = the ZTS_ state
                jp      nc,trap_syntax      ; bare `INTERVAL` / `INTERVAL FOO` -> ERR 2
ei_set:
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the cursor across set_state
                ld      hl,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ
                call    set_state           ; (preserves HL)
                ; --- RELEASE A LATCH THAT SURVIVED THE STATE CHANGE -----------
                ; ⚠️ Not optional, and NOT something the shared machinery does for
                ; us -- three gate cases failed on exactly this (G_stop_latch 2/1,
                ; P_on_reloads 2/1, G2_stop_release 1/0, reference/zerobas).
                ; event_poll raises TRAPPEND when it latches, but check_traps
                ; CLEARS TRAPPEND whenever it finds nothing FIRABLE -- and a
                ; STOPped entry is not firable. So the PENDING bit survives the
                ; suspension exactly as the reference requires, and then nothing
                ; ever looks at it again: `INTERVAL ON` restored the state but the
                ; dispatcher had already been told to stop asking.
                ; T2/T3/T4 never hit this because their sources re-latch every
                ; frame while ON, which re-raises TRAPPEND on its own; INTERVAL's
                ; latch is a ONE-SHOT (§1.3 G2: three elapsed periods release
                ; exactly one), so it has to re-raise here.
                ; OFF needs no guard: set_state clears PENDING, so bit 7 is 0.
                bit     7,(hl)
                jr      z,ei_done
                ld      a,1
                ld      (TRAPPEND),a        ; make check_traps look once more
ei_done:
                pop     hl
                jp      exec_stmt           ; continue the line (`INTERVAL ON:...`)

; --- ex_on_interval: ON INTERVAL = <expr> GOSUB [<line>] ---------------------
; Entry: HL past the compound, on the `=`.
;
; THE PERIOD ARGUMENT IS THE ADDRESS DOMAIN, and that is a measurement, not a
; convenience: §1.2 puts 255/256/32767/32768/65535/-1/-32768 all inside it,
; 2.7 -> 2 (truncate), and 65536 / -32769 / **-65531** outside it with ERR 6.
; -65531 is the decisive one -- under a raw mod-65536 reading it would be a
; perfectly legal 5-frame period. So this is `eval_addr`, the same conversion
; POKE and `TIME=n` use, which is why the TIME slice landed first.
; n = 0 is the one addition: ERR 5, not ERR 6.
ex_on_interval:
                call    skip_spaces
                cp      EQ_TOKEN
                jp      nz,trap_syntax      ; `ON INTERVAL GOSUB 800` -> ERR 2
                inc     hl
                call    eval_addr           ; DE = n (checked address domain)
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error ; outside -32768..65535 -> Overflow (ERR 6)
                ld      a,d
                or      e
                jr      z,eoi_err5          ; ON INTERVAL=0 -> Illegal function call
                ld      (ZINTVAL),de        ; the period...
                ld      (ZINTCNT),de        ; ...and RELOAD the live counter: arming
                                            ; restarts the period (§1.4 P2, measured --
                                            ; re-arming mid-run moves the next fire)
                call    skip_spaces
                cp      GOSUB_TOKEN
                jp      nz,trap_syntax      ; `ON INTERVAL=10 GOTO 800` -> ERR 2
                inc     hl
                call    skip_spaces
                ld      de,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ+1
                push    de                  ; eos_line pops it as the store target
                jp      eos_line            ; shared tail: optional line ref, else CLEAR
                                            ; the slot (§1.6 -- the reference accepts a
                                            ; bare `ON INTERVAL=n GOSUB` and disarms)
eoi_err5:
                ld      a,5
                jp      raise_error
    ENDIF

; --- ex_ff_stmt: the `$FF <selector>` STATEMENT fork -------------------------
; A statement that starts with a two-byte function token. MID$ ($FF $83) is the
; string-assignment form; STRIG ($FF $A3) is the T2 arming statement (this is the
; site that used to be the blanket ERR 2 of the input-devices D-I-5 handoff).
; Anything else falls into ex_mid_stmt's Syntax error, entered at ex_mid_sel --
; its post-`inc hl` label, so the selector byte is not re-fetched.
ex_ff_stmt:
                inc     hl                  ; -> the selector byte
                ld      a,(hl)
                cp      STRIG_TOKEN         ; STRIG(n) ON|OFF|STOP  (traps T2)
                jp      z,ex_strig_stmt     ; (entered with HL on the selector)
    IF TRAPS_T5
                call    iv_match            ; INTERVAL ON|OFF|STOP  (traps T5)
                jp      c,ex_interval       ; CF=0 leaves HL on the selector, so
    ENDIF                                   ; ex_mid_sel's Syntax error is unchanged
                jp      ex_mid_sel

; --- ex_on_strig: ON STRIG GOSUB [<l0>][,<l1>[,<l2>[,<l3>[,<l4>]]]] ----------
; Arm up to five trigger handlers. Reached from ex_on's sibling peek with HL on
; the STRIG selector byte ($A3; ex_on consumed the $FF prefix).
; VG-8020-measured semantics (spec-traps-t2-strig.md §1.3):
;   * the list is POSITIONAL -- slot n is trigger n (R5);
;   * an EMPTY slot writes 0, i.e. it CLEARS that trigger's handler (S3);
;   * absent trailing slots are left untouched (D-T2-5);
;   * state is NOT touched -- arm != enable, `STRIG(n) ON` enables (Q5);
;   * a 6th slot is a DELIBERATE DEVIATION: the reference runs off the end of its
;     handler table and takes the machine down (case S2, reproducible x3); we
;     raise a trappable ERR 2 instead (D-T2-4).
; Flow continues on the same line.
ex_on_strig:
                inc     hl                  ; past the STRIG selector byte
                call    skip_spaces
                cp      GOSUB_TOKEN         ; syntax: ON STRIG *GOSUB* <list>
                jp      nz,trap_syntax
                inc     hl
                ld      c,0                 ; C = slot index 0..4
eostr_lp:
                call    skip_spaces
                push    bc                  ; trap_line_link clobbers BC (find_line_bc)
                call    trap_line_link
                pop     bc                  ; pop does not disturb CF
                jr      c,eostr_store
                ld      de,0                ; empty slot -> CLEAR this trigger's handler
eostr_store:
                push    hl                  ; guard the cursor
                push    de                  ; guard the LINK across ztrap_entry (clobbers DE)
                ld      a,c
                add     a,ZTI_STRIG0
                call    ztrap_entry         ; HL = &ZTRAP[3+C] (the state byte)
                pop     de
                inc     hl                  ; -> the handler field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = cursor
                inc     c
                call    skip_spaces
                cp      ','                 ; another slot?
                jp      nz,exec_stmt        ; no -> statement done, continue the line
                inc     hl                  ; consume the comma
                ld      a,c
                cp      5                   ; slots 0..4 only
                jp      nc,trap_syntax      ; a 6th slot -> trappable ERR 2 (D-T2-4)
                jr      eostr_lp

; --- ex_strig_stmt: STRIG(n) ON | OFF | STOP ---------------------------------
; The D-I-5 handoff: this replaces input-devices' blanket ERR 2 for `STRIG(n)`
; used as a statement. Reached from the interpreter's $FF statement dispatch with
; HL on the STRIG selector byte. VG-8020-measured (spec-traps-t2-strig.md §1.3):
; n is a normal numeric expression truncated to a byte (`STRIG(.4) ON` == trigger
; 0, S8), n > 4 is ERR 5 (Q11), and a bare `STRIG(0)` with no ON/OFF/STOP is a
; trappable ERR 2 (Q10). `STRIG(0)ON` unspaced is legal (S4) -- free, since the
; crunched form has no space to skip.
ex_strig_stmt:
                inc     hl                  ; past the STRIG selector byte
                call    skip_spaces
                cp      '('
                jp      nz,trap_syntax
                inc     hl
                call    eval                ; DE = n; HL past the expression
                call    get_byte_arg        ; A = E = n (ERR 6 > int16, ERR 5 > 255/neg)
                cp      5                   ; triggers 0..4
                jp      nc,strig_illegal    ; STRIG(5..255) -> ERR 5
                add     a,ZTI_STRIG0
                push    hl                  ; guard the cursor across ztrap_entry
                call    ztrap_entry         ; HL = &ZTRAP[3+n]
                ex      de,hl               ; DE = the entry pointer, kept until the end
                pop     hl                  ; HL = cursor
                call    skip_spaces
                cp      ')'
                jp      nz,trap_syntax
                inc     hl
                call    skip_spaces
                call    onoff_decode        ; STRIG(n) ON|OFF|STOP; DE (the entry
                                            ; pointer) survives -- see its header
                jp      nc,trap_syntax      ; bare `STRIG(n)` / junk -> trappable ERR 2
                ld      b,a                 ; B = the state, as the seed logic below wants
strig_set:
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the exec-continue cursor
                ex      de,hl               ; HL = the entry pointer
                ; Decide "seed the edge shadow?" == (new == ON && old != ON) BEFORE
                ; set_state, which clobbers A/B/C and rewrites the state bits. Seeding
                ; means "assume pressed", so a trigger already held when the trap is
                ; enabled cannot manufacture a spurious 0->1 edge (VG-8020 R1/R2/R3).
                ; The old != ON half matters: re-issuing `STRIG(n) ON` while already ON
                ; must be a no-op, or a program that re-enables on every statement
                ; would hold the shadow set forever and never see a real press.
                ld      a,b
                cp      ZTS_ON
                jr      nz,strig_noseed     ; not enabling
                ld      a,(hl)
                and     ZTS_STATE_MASK
                cp      ZTS_ON              ; ZF=1 iff already ON -> not a transition
                jr      strig_flag
strig_noseed:   xor     a                   ; ZF = 1 -> do not seed
strig_flag:     push    af                  ; carry the decision across set_state
                ld      a,b                 ; A = the new state
                call    set_state           ; maintains the TRAPENA "# ON" count
                pop     af
                jr      z,strig_done
                set     6,(hl)              ; seed the edge shadow (ZTS_SHADOW)
strig_done:
                pop     hl                  ; HL = cursor past the sub-keyword
                jp      exec_stmt           ; continue the line -- a bare `ret` here would
                                            ; SWALLOW the rest of it (the T1 es_set lesson)
strig_illegal:
                ld      a,5
                jp      raise_error         ; ERR 5 Illegal function call (n out of 0..4)

    IF TRAPS_T3
; ===========================================================================
; Interrupt-traps T3 (KEY) — the parse surface, DUPLICATED AND SPECIALISED.
; ===========================================================================
; docs/spec-traps-t3-key.md §5/§7.5. These are deliberately NOT a generalisation
; of the STRIG parsers above, even though they are visibly the same shape. That
; was tried and MEASURED (§7.2): turning the five differing constants into RAM
; parameters cost **76 B on its own**, before a single byte of KEY behaviour --
; more than the constants it replaced, because an immediate operand inside an
; instruction is free while a parameter costs a RAM byte, a store per setter, a
; load per use and a helper call. Generalisation pays across MANY callers; with
; two it is a net loss. So: duplicate, specialise, and let each copy be small.
;
; The KEY band is laid out REVERSED -- KEY 10 at ZTI_KEY1, KEY 1 at ZTI_KEY1+9 --
; so ct_find's ASCENDING scan services the family high-numbered-first as the
; reference does (§1.3 V2: F1+F2+F3 in one frame -> 3, 2, 1). That costs zero
; bytes in ct_find and leaves T2's STRIG scan order untouched (D-T3-4).

; --- ex_on_key: ON KEY GOSUB <l1>[,<l2>...[,<l10>]] -------------------------
; Reached from ex_on's peek with HL on the KEY token -- a SINGLE-byte token
; ($CC), so unlike STRIG's `$FF $A3` there is no prefix to put back. Positional,
; slot k = KEY k+1 (§1.4 K8); an empty slot clears that key's handler; absent
; trailing slots are untouched -- all exactly as T2. An 11th slot is ERR 2, and
; here NO deviation is needed: the reference raises a clean ERR 2 itself, unlike
; T2's 6th STRIG slot which takes the machine down.
ex_on_key:
                inc     hl                  ; past the KEY token
                call    skip_spaces
                cp      GOSUB_TOKEN         ; syntax: ON KEY *GOSUB* <list>
                jp      nz,trap_syntax
                inc     hl
                ld      c,0                 ; C = slot index 0..9
eokey_lp:
                call    skip_spaces
                push    bc                  ; trap_line_link clobbers BC (find_line_bc)
                call    trap_line_link
                pop     bc                  ; pop does not disturb CF
                jr      c,eokey_store
                ld      de,0                ; empty slot -> CLEAR this key's handler
eokey_store:
                push    hl                  ; guard the cursor
                push    de                  ; guard the LINK across ztrap_entry
                ld      a,ZTI_KEY1+9
                sub     c                   ; REVERSED band (see above)
                call    ztrap_entry         ; HL = &ZTRAP[...] (the state byte)
                pop     de
                inc     hl                  ; -> the handler field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = cursor
                inc     c
                call    skip_spaces
                cp      ','                 ; another slot?
                jp      nz,exec_stmt        ; no -> statement done, continue the line
                inc     hl                  ; consume the comma
                ld      a,c
                cp      10                  ; slots 0..9 only
                jp      nc,trap_syntax      ; an 11th slot -> ERR 2 (§1.4 K15)
                jr      eokey_lp

; --- ex_key_stmt: KEY(n) ON | OFF | STOP ------------------------------------
; Reached from ex_key's `(` peek (basic/screen.asm) with HL on the `(`, tested
; AHEAD of ON/OFF so the display form `KEY ON`/`KEY OFF` keeps working (K10).
; n is a normal numeric expression truncated to a byte; KEY(0) and KEY(11) are
; both ERR 5 (§1.4 K11/K12), the same shape as T2's STRIG(5).
; SHORTER than ex_strig_stmt despite the duplication, because KEY needs NO edge
; shadow: it is a DELIVERY trap, so a key already held when the trap is enabled
; simply produces its next repeat delivery -- there is no spurious edge to
; suppress, and T2's whole seed-decision block disappears (§2).
ex_key_stmt:
                inc     hl                  ; past the '('
                call    eval                ; DE = n; HL past the expression
                call    get_byte_arg        ; A = E = n (ERR 6 > int16, ERR 5 > 255/neg)
                dec     a                   ; 1..10 -> slot 0..9; KEY(0) wraps to 255
                cp      10
                jp      nc,strig_illegal    ; KEY(0) and KEY(11..255) -> ERR 5
                ld      c,a
                ld      a,ZTI_KEY1+9
                sub     c                   ; REVERSED band
                push    hl                  ; guard the cursor across ztrap_entry
                call    ztrap_entry
                ex      de,hl               ; DE = the entry pointer, kept to the end
                pop     hl                  ; HL = cursor
                call    skip_spaces
                cp      ')'
                jp      nz,trap_syntax
                inc     hl
                call    skip_spaces
                call    onoff_decode        ; KEY(n) ON|OFF|STOP (STOP == OFF, D-T3-6);
                                            ; DE (the entry pointer) survives
                jp      nc,trap_syntax      ; bare `KEY(n)` / junk -> trappable ERR 2
                ld      b,a
key_set:
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the exec-continue cursor
                ex      de,hl               ; HL = the entry pointer
                ld      a,b
                call    set_state           ; maintains the TRAPENA "# ON" count
                pop     hl
                jp      exec_stmt           ; continue the line (the T1 es_set lesson)
    ENDIF
    ENDIF
