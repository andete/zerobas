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
                call    skipsp_test
                jr      z,dl_quiet          ; blank line -> nothing to do, no prompt
                cp      '0'
                jr      c,dl_cmd
                cp      '9'+1
                jr      c,dl_store          ; leading digit -> numbered line
dl_cmd:
                ld      (PRMWANT),a         ; D-OKSTORE: a direct command -- its first
                                            ; char (printable: bit 5/6 set) survives
                                            ; dl_quiet's `res 1` in any nested store
                ld      de,run_kw
                call    is_cmd
                call    c,dl_bare           ; matched -- but ONLY the BARE form is
                jp      c,dl_run            ; the REPL's own (D-RUNARG below).
                                            ; `jp`, not `jr`: dl_bare's body pushed
                                            ; dl_run out of relative range.
                ; 🔴 THE PRE-TOKENISE `NEW` MATCH IS GONE (D-NEWSTMT, 2026-09-12).
                ; It existed because NEW had no `stmt_table` entry, so the only way
                ; to reach it was to spot the bare word BEFORE crunching -- which is
                ; exactly why a PROGRAM reaching NEW got `Syntax error`. Now that
                ; NEW_TOKEN dispatches to `ex_new` like every other statement, a
                ; typed `NEW` crunches and executes down the SAME path a program
                ; takes, and one implementation serves both. The bytes this frees
                ; are what pays for the table entry and the handler.
                ; direct mode: crunch the whole line and execute it now
                ld      hl,LINEBUF
                ld      de,TOKBUF
                call    tokenise
                ld      a,(TKOVF)           ; float-literal crunch-time overflow (F1,
                or      a                   ; basic/float.asm) -> reject the whole line,
                jr      nz,dl_overflow      ; own wording (D-F1-1); never execute/store
                                            ; (D-2's explicit `DIRECTF := 1` used to sit
                                            ; here; it is now DERIVED in rp_exec, which
                                            ; this path always reaches before any
                                            ; statement runs -- and nothing between here
                                            ; and there can raise an error to read it)
                ; 🔴 THE ANCHOR STORE THAT SAT HERE IS DELETED (D-SPMERGE step 5).
                ; `rp_lp` now writes `SAVSTK` on EVERY pass, and every path out of
                ; here reaches it before anything can read the anchor -- so this
                ; store was overwritten with the right value before it could ever be
                ; used, and its value was the WRONG one anyway: the re-base moves SP
                ; to the frontier, so the anchor has to be `CSP-2`, not this depth.
                ld      (SAVSTK),sp         ; BISECT: direct-mode anchor restored
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
dl_store:
                call    parse_lineno        ; HL -> first digit; BC = number, HL at
                                            ; the body (parse_lineno eats the ONE
                                            ; separator blank itself -- D-LNBLANK
                                            ; R3, so no skip_spaces here: that ate
                                            ; the WHOLE run and lost the body offset)
                ; D-LNBLANK R4: a line number past 65529 is REFUSED, not stored and
                ; not wrapped. Measured on both references: `65530 REM` and
                ; `99999 REM` print `Syntax error` and store nothing, and `PRINT ERR`
                ; then reads 2 (65529 is accepted and leaves ERR at 0).
                ;
                ; 🔴 UNGUARDED, THIS WAS A SILENT WRONG ANSWER: `99999 REM` stored a
                ; line numbered 99999-65536 = 34463 and reported nothing. It was
                ; live before the blank fix and independent of it -- but the blank
                ; fix WIDENS its reach (`9 9 9 9 9 REM` went from a visibly wrong
                ; line 9 to a silent 34463), which is why it lands in the same
                ; slice. Shipping the one without the other repeats D-LINEMAX, where
                ; raising one limit turned a previously-safe unbounded path into a
                ; live defect.
                ld      a,b
                cp      high (LINENO_CEIL+1)
                jr      c,dl_lnok
                ld      a,c
                cp      low (LINENO_CEIL+1)
                jr      c,dl_lnok
                ld      a,2                 ; ERR 2 -- measured, not assumed
                ld      (ERRFLG),a
                ld      hl,err_syntax       ; low-region string pool (arrays.asm)
                jr      dl_ovf_report       ; reports and returns to the REPL. Like
                                            ; the overflow arm above this reports
                                            ; rather than calling raise_error: the
                                            ; error happens at line ENTRY, and
                                            ; raise_error's trap arm would jump INTO
                                            ; a finished program on a mistyped line.
                                            ; The reference cannot trap it either.
dl_lnok:
                push    bc                  ; guard line number across tokenise
    IF CLEARPOOL
                ; D-TXTCEIL: publish the VARIABLE-region ceiling for the lineedit
                ; tenant, which bounds the store. It compared against the CONSTANT
                ; TXTMAX ($DB00), so `CLEAR n,himem` never reached it and the
                ; program grew PAST HIMEM into the string and variable area --
                ; silent corruption, pinned by scratchpad/prgend_overrun.py at
                ; 225 B past the pool floor on a `CLEAR 300,TXTTAB+1000` fixture.
                ;
                ; CHANNEL 1'S BLOCK BASE **IS** strheap_varceil(): min(HIMEM,
                ; TXTMAX) - POOLSIZE - MAXF*FCH_CTXSZ is exactly what
                ; fch_ctx_addr(1) returns, DERIVED on every call rather than
                ; stored, so `CLEAR ,himem` falls out and no new sub-ROM op is
                ; needed.
                ;
                ; 🔴 THE `push hl` IS NOT OPTIONAL AND ITS ABSENCE COST A WHOLE
                ; BUILD-AND-REVERT CYCLE. HL here is tokenise's SOURCE CURSOR
                ; (parse_lineno left it at the body) and fch_ctx_addr RETURNS in
                ; HL -- its header lists "Clobbers A, BC, DE, IX" and does not
                ; mention HL precisely BECAUSE HL is the result, so a reader
                ; checking the clobber list sees nothing wrong. Without the save,
                ; `10 PRINT"HI"` echoed and the machine stopped.
                ; ⚠️ BC is already saved by the push above, which is why the
                ; fetch is HERE and not beside `jp store_line`, where BC is the
                ; line number and fch_ctx_addr would eat it.
                ; ⚠️ THE IX CONTRACT fch_ctx_addr's header demands of every NEW
                ; caller is satisfied by argument, not by a guard: store_line
                ; reaches the tenant through le_call_op, which does `ld ix,
                ; SUBROM_ENTRY_BASE_P1 + ...` itself and never reads an inherited
                ; IX.
                ; ⚠️ THIS DOES NOT MAKE `crf-oom*` AGREE AND IS NOT MEANT TO.
                ; D-HIMEMRES measured the references reserving 293 + 267*MAXFILES
                ; below HIMEM against 12 + 50*MAXFILES here, because D-FCH's block
                ; is "state ONLY (no buffer)". Those rows compare FRE(0) across
                ; that architectural difference; this fix is about not writing
                ; past HIMEM at all.
                ; 🔴 GUARDED, because `make switch-build-check` BUILDS CLEARPOOL=0
                ; on every run and sh_chan_addr does not exist there.
                push    hl                  ; tokenise's source cursor
                xor     a                   ; D-FCBSHAPE FCB #0: channel 0 is the LOWEST
                call    fch_ctx_addr        ; block now, 2*(MAXF+1) B above the table
                                            ; base; the edge reserve below keeps the
                                            ; text clear of the table as well
                ; 🔴 AND THE STORE MUST LEAVE THE STACK ITS RESERVE (D-SPMERGE §9).
                ; `strheap_varceil()` is ALSO the pool's top, and since cut 2 the
                ; machine stack descends from there. Growing the program text pushes
                ; the variable area up behind it, so a store bounded only by the
                ; varceil walks the variables INTO the live stack.
                ; MEASURED without this: txtceil-acceptance types lines toward a
                ; deliberately low HIMEM (`CLEAR 200,A+1000`) and the machine started
                ; SWALLOWING TYPED CHARACTERS as the text approached the ceiling --
                ; the editor's own stack was being overwritten by the text it was
                ; storing. The same reserve ctl_alloc keeps below the frontier.
                ; D-DIMRESERVE S3: STK_STORE_RESERVE (141, the VG-8020's own store
                ; edge, above the 116 B stack floor -- sysvars.inc), not the 256 B
                ; page it was; DE is reloaded below.
                ld      de,-STK_STORE_RESERVE
                add     hl,de               ; -= STK_STORE_RESERVE
                ld      (SL_CEIL),hl
                pop     hl
    ENDIF
                ld      de,TOKBUF
                call    tokenise            ; crunch the remainder of the line
                ld      a,(TKOVF)
                or      a
                jr      nz,dl_overflow_pop
                pop     bc
                ld      hl,TOKBUF
                call    store_line          ; OOM raises and never returns here
; D-OKSTORE: the two SILENT exits -- a stored/deleted line, an empty Enter. `res 1`
; silences only repl's own 2; a direct command's character keeps its prompt.
dl_quiet:
                ld      hl,PRMWANT
                res     1,(hl)
                ret
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
                ; ERRFLG is still set so PRINT ERR reads 25, as measured.
                ; TKOVF=25 CARRIES THE ERR CODE rather than a second constant
                ; here -- page 1 had 10 free bytes when this landed, so the reason
                ; code and the error code are deliberately the same byte.
                ; 🎯 D-MSGMIGRATE: NO BRANCH LEFT. TKOVF now carries the ERR code on
                ; BOTH arms (6 float literal, 25 body too long -- sub/tkfloat.asm), and
                ; both messages are sub-ROM-hosted, so the reason code goes straight
                ; into ERRFLG and the tenant picks the text off it. That deleted the
                ; `cp 1` / `jr z` pair, one `ld hl`, and 30 B of string -- and it FIXED
                ; a defect: the old float arm skipped the `ld (ERRFLG),a` entirely, so
                ; `PRINT ERR` after `20 A=1E99` read whatever the previous error left.
                ; Both references read 6 there (measured 2026-08-02, spec §6.4).
                ld      a,(TKOVF)
                ld      (ERRFLG),a          ; the reject reason IS the ERR code
                ld      hl,err_subhosted    ; ERR 6 -> em_overflow, 25 -> em_linebuf_overflow
dl_ovf_report:
                ; --- D-ERLENTRY: A LINE-ENTRY ERROR LEAVES ERL = 65535 --------
                ; Both arms below set ERRFLG and neither ever set ERRLIN, so after
                ; a rejected line `PRINT ERL` read whatever the last RUN left --
                ; 0 on a fresh machine. Both references read 65535, the direct-mode
                ; sentinel record_error_line (interp.asm rel_direct) already writes
                ; for a direct-mode RUNTIME error; a line typed at the prompt is
                ; direct mode too, so the sentinel is the same one.
                ; 🟢 SITED ON THE SHARED TAIL DELIBERATELY, and only because BOTH
                ; arms were measured, not because the tail was convenient: `70 X=1E99`
                ; (the crunch reject, ERR 6) and `70000 X=1` (the out-of-range line
                ; number, ERR 2) each read 65535 on both references, and the control
                ; that types no bad line at all reads 0 on all three.
                ; [[a-shared-tail-is-not-a-decision]] -- the point of that rule is to
                ; ENUMERATE the jumps, not to avoid shared tails.
                ; ⚠️ ERRLIN ONLY. `.` (DOT) is NOT written by a direct-mode error --
                ; interp.asm's rel_direct carries the row that says so, and the same
                ; reasoning applies here.
                ; DE rather than HL because HL is already the message pointer, which
                ; is this tail's whole input.
                ld      de,65535
                ld      (ERRLIN),de
                                            ; 🔴 SHARED TAIL, AND MY ENUMERATION MISSED
                                            ; IT. The line-number-out-of-range arm above
                                            ; (ERR 2, err_syntax) reaches print_msg by
                                            ; `jr` to THIS label, never naming print_msg
                                            ; -- so the D-MSGMIGRATE blast-radius sweep,
                                            ; which grepped for `jp|call|jr .*print_msg`,
                                            ; did not list it. The BUILD found it, by the
                                            ; same property that catches a missed repoint:
                                            ; the label vanished with the collapsed
                                            ; branch. ⚠️ It passes err_syntax, a resident
                                            ; low-region string, so it does NOT reach
                                            ; pm_sub today -- but it WOULD have, silently,
                                            ; if err_syntax were ever migrated. That is an
                                            ; argument FOR pm_sub's register fence that
                                            ; the spec did not have: an indirect reacher
                                            ; cannot be enumerated by naming the callee.
                jp      print_msg           ; reports and returns to the REPL
; err_overflow and err_linebuf_overflow are GONE from main entirely (D-MSGMIGRATE)
; -- they were page-1 residents in basic/main.asm's promoted string pool and are
; now em_overflow / em_linebuf_overflow in sub/errmsg.asm, keyed on ERRFLG 6 / 25.
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
; 📌 dir_line's 4 B is a PIN REFILL in basic/field.asm since D-FCHNUM (2026-10-17).
; --- dl_bare: is the REPL keyword at (HL) FOLLOWED BY AN ARGUMENT? ------------
; 🔴 D-RUNARG. `is_cmd` matches when the next input byte is a DELIMITER -- end,
; SPACE or ':' -- which is exactly right for telling `RUN` from `RUNNER` and
; exactly wrong as a "takes no argument" test. So `RUN 20`, `RUN A$` and
; `RUN "name"` all matched the REPL's bare-RUN fast path and their argument was
; DISCARDED: the resident program ran from the top. Measured against the
; CF-3300 (scratchpad/fnamedev_probe.py):
;
;     RUN 20      ref runs from line 20      here ran from the TOP
;     RUN "f"     ref File not found         here ran the resident program
;     RUN A$      ref File not found         here ran the resident program
;     RUN20 / RUN"f"   agree -- no space, so `is_cmd` never matched
;
; 🎯 A SILENT WRONG PROGRAM RUN, not a wrong message, which is the class this
; project ranks worst. Only the bare form belongs on the fast path; everything
; else is crunched and reaches `do_run` as a statement, where the argument is
; already handled.
;   in: HL -> the keyword.  out: CF set iff nothing but ':' or end follows.
;   HL is preserved; the caller still needs it.
; 📌 dl_bare's body is a PIN REFILL in basic/files.asm (beside fch_select) since
; S10.E (2026-10-19): it refills bytes the channel switch freed in front of $72D4.

dl_run:
                jr      run_prog

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

; 📌 run_kw's 4 B is a PIN REFILL in basic/field.asm since D-FCHNUM (2026-10-17).

; (parse_lineno lives in basic/vars.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)

; --- new_prog: clear the stored program (NEW) --------------------------------
; Empty program = a $0000 link word at the text base. Clobbers A, HL.
; 📌 new_prog's BODY is a PIN REFILL in basic/files.asm (OPEN's mode dispatch)
; since S10.E (2026-10-19): it refills bytes S10.E freed in front of $6CF3. Its
; notes, which belong to the body: NEW is the ONLY thing that clears TRON (RUN
; does not reset it, END does not clear it, and a line carrying TROFF is itself
; traced -- all measured, spec §3.4); the tail `jp vars_reset` rebases BOTH the
; scalar region (ARYTAB = PRGEND+2) and the array area's "no arrays" sentinel
; (arrays slice-1 §9.6 + slice-4b §3b).

; --- run_prog: execute the stored program (RUN) ------------------------------
; Clears variables and the control stacks, then runs lines from CURLINE. A
; statement may redirect the flow: GOTO sets GOTOFLAG + GOTOTGT (branch to a
; line start); RETURN / a continuing NEXT set RESUMEFLAG + RESUMEPTR (resume at
; an exact token position, CURLINE already pointing at its line); END/STOP set
; ENDFLAG (stop). Otherwise execution falls through to the next line. BLOAD,R
; hands off.
; D-RUNLINE (docs/spec-basic-runline.md): `RUN <lineno>` starts execution AT
; that line, and the ONE thing that differs from a bare RUN is which line
; CURLINE names. GOTOTGT carries it -- its SECOND tenant, and safe because
; run_prog clears GOTOFLAG, so the only reader (rp_goto) cannot fire on a stale
; value: every path that reads GOTOTGT sets it first. Bare RUN seeds it with
; TXTBASE here, so run_prog_at below is entered with the invariant already true
; and there is no flag and no second code path.
run_prog:
                ld      hl,(TXTTAB)  ; D-BASICROM: the program START is TXTTAB (a cartridge program sits at TEXT+1)
                ld      (GOTOTGT),hl        ; bare RUN: start at the top
run_prog_at:                                ; RUN <lineno>: GOTOTGT = that line
                ; 🔴 D-RUNCLOSE (2026-09-27): RUN CLOSES EVERY OPEN FILE FIRST, and
                ; it never did. Measured on the CF-3300: a program that opens #1
                ; and ends, then a second program's `PRINT #1` -> 59 File not OPEN
                ; after the RUN; zerobas kept #1 open and wrote to it. NEW and END
                ; do NOT close on the reference (both measured), which is why this
                ; sits here and not in clear_vars. Found because kwsweep's stored
                ; disk rows (each one a RUN) leaked channels into their
                ; neighbours and read 38 fake EXTRAs (D-KWT6 batch 8).
                call    fch_close_all       ; nothing live: GOTOTGT is in RAM
                call    clear_vars
                call    vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b): a
                                            ; fresh RUN has no live scalars/arrays
                                            ; either; PRGEND is already correct here
                                            ; (unlike at boot -- see ary_alloc's own
                                            ; ceiling note, sub/arrays.asm). Redundant
                                            ; with clear_vars's own vars_reset just
                                            ; above (same PRGEND, same result) --
                                            ; harmless, kept for the "four call sites"
                                            ; symmetry (§3b).
                xor     a
                ld      (CONTVALID),a       ; a fresh RUN has no CONT resume point yet
                ld      (GOTOFLAG),a
                ld      (ENDFLAG),a
                ld      (RESUMEFLAG),a
                ld      (DIRECTF),a         ; D-2: run mode (0) — errors get " in <line>"
                ; 🔴 THE ANCHOR STORE THAT SAT HERE IS DELETED (D-SPMERGE step 5).
                ; `rp_lp` now writes `SAVSTK` on EVERY pass, and every path out of
                ; here reaches it before anything can read the anchor -- so this
                ; store was overwritten with the right value before it could ever be
                ; used, and its value was the WRONG one anyway: the re-base moves SP
                ; to the frontier, so the anchor has to be `CSP-2`, not this depth.
                                            ; (was: the run anchor)
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
                                            ; three lines up) so cold boot / NEW /
                                            ; CLEAR reset the control stacks too --
                                            ; docs/spec-basic-direct-ctrl.md §4.
                                            ; Net zero bytes.
                xor     a                   ; DATA pointer unpositioned (read seeks
                ld      (DATASTATE),a       ;  from the program start on first READ)
                ld      hl,(TXTTAB)  ; D-BASICROM: the program START is TXTTAB (a cartridge program sits at TEXT+1)
                ld      (RESTORE_LINE),hl   ; ⚠️ DATA restores from the PROGRAM TOP even
                                            ; for RUN <lineno> -- RUN resets the DATA
                                            ; cursor, and the start line does not move it
                ld      hl,(GOTOTGT)        ; D-RUNLINE: the line to begin at (TXTBASE
                ld      (CURLINE),hl        ; for a bare RUN, set at run_prog above)
rp_lp:
                ; --- D-SPMERGE step 4: RE-BASE THE STACK ON THE FRONTIER --------
                ; 🔴 THIS IS WHAT MAKES THE POOL'S FREE SITES SYMMETRIC, AND WITHOUT
                ; IT THE MERGE DRAINS THE STACK TO DEATH. `ctl_alloc` is the only
                ; path that MOVES the stack (ctl_reloc, below); the six sites that
                ; RAISE the frontier -- RETURN, NEXT x2, the DEF FN frame x3, the
                ; string-heap frame -- move nothing, so every alloc/free CYCLE used
                ; to leak the frame's size out of the machine stack for good.
                ; MEASURED before this existed (scratchpad/spmerge_gosubdrain.py):
                ; `FOR I=1 TO 800:GOSUB:RETURN:NEXT` printed nothing past ~360
                ; iterations, with no trap and no error anywhere, while both
                ; references print every one.
                ; 🎯 THE RE-BASE IS THE FREE OPERATION. Rather than teach six sites
                ; to slide the stack back up, this reclaims whatever was freed --
                ; wherever, and by whoever -- on the next pass through the loop.
                ; 🎯 SITED HERE BECAUSE THE LIVE BLOCK IS EXACTLY ONE WORD: the loop
                ; is entered by `call run_loop` and everything a line pushed is gone
                ; by the time it comes back, so `run_prog`'s return is all there is.
                ; Every entry -- rp_run's fallthrough, rp_goto, the trap-fired
                ; branch and rp_resume -- arrives with SP == SAVSTK, so the word is
                ; in the same place on all four.
                ; ⚠️ SP IS BRIEFLY CSP ITSELF, which is safe: frames live ABOVE the
                ; frontier, in [CSP, CTLTOP), so an interrupt landing in the two
                ; instructions pushes into stack territory and pops back out.
                pop     de                  ; run_prog's return address
                ld      sp,(CSP)            ; the frontier, re-read every line so the
                                            ; stack follows CLEAR/RUN for free
                push    de
                ld      (SAVSTK),sp         ; the anchor moves with it -- an abort or
                                            ; RESUME unwinds to the word just pushed
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
                ; D-ERR21 (docs/spec-basic-err21-no-resume.md §3.1): falling off
                ; the end while STILL OWING A RESUME is an ERROR, not a silent
                ; stop -- `No RESUME in <line>`. The raise condition is exactly
                ; "this exit is reached while ONEFLG is set", so the test goes in
                ; as a PREFIX, above everything else this exit does.
                ;
                ; D-ONEFLG SITE C USED TO SIT HERE (`ld (ONEFLG),a`, 3 B) and is
                ; DELETED: on the arm that survives, ONEFLG is 0 by the test just
                ; below, so the store was a no-op; on the arm that does not, the
                ; ERR 21 abort funnels through fre_abort_low, i.e. D-ONEFLG SITE A,
                ; which clears ONEFLG unconditionally. Deleting it also FIXES a
                ; third defect the site was causing (spec §2.2, row c1): a TYPED
                ; line ends by falling through dir_line's own $0000 link into THIS
                ; exit, so site C silently killed the handler context on every
                ; benign direct line typed at a `Break in <handler>` prompt. The
                ; reference keeps it -- measured.
                ;
                ; A is d|e, i.e. already 0 on this arm; the test clobbers it, which
                ; is why the deleted store could not simply have been kept.
                jr      nz,rp_notend
                ld      a,(ONEFLG)
                or      a
                jp      nz,e21_no_resume    ; basic/arrays.asm, low region
                ; D-CONTR (docs/spec-basic-cont-record.md §3.3): running off the
                ; end IS a run stop, so it records a resume point like every other
                ; one -- CONTPTR = 0, the "re-enter FRESH at CONTLINE" sentinel
                ; (a real resume pointer is a text-area / TOKBUF address and is
                ; never $0000). CONTLINE is CURLINE, i.e. the address of the $0000
                ; end marker itself, so a CONT resumes here, immediately re-detects
                ; end-of-program and returns to Ok SILENTLY -- for ever, which is
                ; what the reference does (spec §2.1, cont2_falloff/_twice/_thrice).
                ; ⚠️ THE RECORD IS IDEMPOTENT AT THIS EXIT, which is what makes the
                ; second CONT safe rather than lucky: re-entering here writes the
                ; same three values back. DIRECTF is stale-1 on that re-entry (the
                ; typed CONT line's, never re-derived because rp_exec is not
                ; reached), so cont_record skips -- and had it been 0 the values
                ; written would have been byte-identical anyway. Spec §3.6.
                ld      hl,0
                jp      cont_record         ; tail call: ITS `ret` is the loop's own
                                            ; exit `ret`, at the same depth (D-CUR-D /
                                            ; D-CONTD both rest on that depth)
rp_notend:
                inc     hl                  ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl                  ; HL -> token body
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
                ; Direct-mode control flow (docs/spec-basic-direct-ctrl.md §5):
                ; DIRECTF is DERIVED, not carried, and this is the point every
                ; line entry AND every mid-line resume passes through. The derive
                ; itself moved to derive_directf just above; see its header for
                ; why the high byte alone decides it.
                call    derive_directf
                call    BREAKX
                pop     hl
                jr      c,rp_break
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
                jp      rp_lp               ; D-CONTR: `jp`, not `jr` -- the 5 B the
                                            ; $0000-link exit gained pushed this
                                            ; backward span past -128. +1 B, no
                                            ; behaviour. (The assembler CAUGHT it and
                                            ; the build failed, which is why the probe
                                            ; never ran on a stale machine.)

; --- end_line_end: ENDFLAG := 1, and the line is over -----------------------
; D-JUMPLOOP step 1 (docs/spec-basic-spmerge.md §8.3). FIVE handlers ended with
; some spelling of `ld a,1 / ld (ENDFLAG),a / ret` -- END, LIST/LLIST, DELETE,
; RENUM and AUTO's stop -- 5 to 6 bytes each for one idea. They now share this,
; at 3 bytes a site.
; 🎯 IT IS A CARVE AND A PRECONDITION AT THE SAME TIME. Stage A has to turn every
; `ret` that leaves `exec` into a jump, because a `ret` needs a stack word and the
; merge needs ZERO words above the frontier at a statement boundary (§8.1). Five
; such `ret`s just became ONE, so the conversion that follows has five fewer sites
; to get right -- which is worth more than the bytes.
; --- ex_new: NEW as a STATEMENT, not just a direct-mode command --------------
; 🔴 D-NEWSTMT (2026-09-12): `stmt_table` had RUN and CLEAR but NO `NEW_TOKEN`, so
; a PROGRAM that reached `NEW` fell through to `Syntax error in <line>` while the
; reference ran it. MEASURED on the VG-8020 (scratchpad/kwdrain_newdefect.py):
; `10 NEW` answers `Ok`, and `10 PRINT"[A]":NEW` / `20 LIST` prints `[A]` then
; `Ok` with NO LISTING -- so NEW ERASES the program AND STOPS, and line 20 never
; runs. That second reading is why this sets ENDFLAG: a fix that merely stopped
; raising the error would leave `exec` walking a program that no longer exists.
; ⚠️ SITED IMMEDIATELY ABOVE `end_line_end` SO THE STOP IS A FALL-THROUGH, not a
; `jp` -- 3 bytes, in a region that had 2 free.
    IF BASICINT_PINS
                                            ; (ex_new and the end_line_end it falls
                                            ; into live in basic/files.asm in the
                                            ; shipping build: with ctl_get they REFILL
                                            ; the 25 B S10.C freed between the pinned
                                            ; $6CF3 and $73AC, 2026-10-15)
    ELSE
ex_new:
                ; 🔴 D-NEWARG (2026-09-28): `NEW 1` ERASED THE PROGRAM. NEW takes no
                ; argument; the VG-8020 answers `20 NEW 1` with `Syntax error in 20`
                ; and LIST still shows the program, where zerobas erased it
                ; (scratchpad/newarg_before.out; T6 batch 10, t6enum_b10.out). The
                ; check comes FIRST, before anything is cleared.
                call    stmt_bare_end       ; Z iff the statement ends here
                jp      nz,stmt_error       ; anything else: ERR 2, nothing erased
                call    clear_vars          ; NEW clears variables too (dl_new's
                                            ; own comment: MS-BASIC semantics)
                call    new_prog            ; then the stored program itself
                                            ; falls into end_line_end: ENDFLAG := 1,
                                            ; so the run loop returns to the REPL
                                            ; instead of walking erased text
end_line_end:
                ld      a,1
                ld      (ENDFLAG),a
                ret                         ; -> stage A turns THIS into `jp rp_after`
    ENDIF
; --- derive_directf: DIRECTF := "the line CURLINE names is the TYPED one" ----
; Clobbers A (and the flags). Everything else is preserved -- rp_exec calls it
; with the resume pointer live in HL.
;
; DIRECTF is DERIVED, never carried. A sticky flag would be wrong in BOTH
; directions and both were MEASURED on the VG-8020: a direct `GOSUB 10` into a
; broken line 10 reports "Syntax error IN 10" (run mode), and the RETURN back
; into the rest of the typed line reports a bare "Syntax error" (direct mode
; again). docs/spec-basic-direct-ctrl.md §5.
; The HIGH BYTE alone decides it. CURLINE's value set is small and enumerable:
; a stored line's link address, always in [TXTBASE $8001, TXTMAX $BE00);
; dir_line; and dir_line+2 (what the run loop's fall-through leaves behind after
; a typed line ends). ROM and the text area are disjoint, so the only address
; sharing dir_line's page is dir_line+2 -- and rp_lp returns to the REPL on that
; one before ever reaching rp_exec.
;
; 🔴 IT IS A ROUTINE, AND NOT INLINE IN rp_exec, BECAUSE rp_exec IS NOT THE ONLY
; PLACE THAT NEEDS IT (D-LOCARG, docs/spec-basic-locarg.md §5). D-ONERR0's
; re-raise restores the ERRORING statement's CURLINE and then aborts through
; rerr_msg, which never passes rp_exec -- so the mode cell kept whatever the
; RE-RAISING statement had, and the two rows where those disagree failed in
; OPPOSITE directions (`make onerr0-acceptance` d.instop / d.dirtrap):
;   d.instop   the disarm is TYPED but the error was a STORED line -> the
;              " in <line>" suffix was suppressed when it must be printed
;   d.dirtrap  the disarm is in a STORED handler but the error was TYPED -> a
;              suffix was printed (`in 0`, dir_line's own never-initialised
;              lineno field) when there must be none
; 🎯 OPPOSITE DIRECTIONS IS WHAT SAYS THE ANSWER IS THIS DERIVE AND NOT A
; CONSTANT: forcing DIRECTF := 0 fixes the first and breaks the second, and
; forcing 1 does the reverse. Both readings were predicted before the fix was
; measured (docs/spec-basic-onerr0.md §7).
; 📌 (derive_directf's BODY is a PIN REFILL in basic/field.asm since D-FLDDESC,
; 2026-10-17, in front of the $73AC pin; this header still describes it. It is
; entered only by `call`, from rp_exec.)
rp_break:
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
                call    trap_pend   ; wake the run-loop dispatcher
rp_brk_run:
                pop     hl                  ; HL = resume stmt ptr, intact
                jp      rp_trapchk          ; dispatch now (do NOT break) -- `jp`:
                                            ; D-CURLIN's 16 B in derive_directf put
                                            ; the backward span past -128 (+1 B).
                                            ; The shipping build is back in reach
                                            ; (scratchpad/jr_mapper.py proposes it),
                                            ; but with any switch off it is not:
                                            ; `make switch-build-check` (D-JRSLICE3)
rp_real_break:
                ; 🔴 D-STOPEDGE (2026-09-16): THE BREAK IS EDGE-TRIGGERED ON THIS
                ; PATH TOO. Measured against the VG-8020 with a 2 s hold
                ; (scratchpad/ctrlstop_probe.py): with `ON STOP GOSUB` + `STOP ON`,
                ; the handler running, and THEN `STOP OFF` while the key is STILL
                ; DOWN, the reference answers `< 1 >` and this tree answered
                ; `Break in 50`. The reference's edge was already consumed by the
                ; trap; ours re-read the LEVEL once the state went OFF and raised a
                ; fresh break.
                ; 🎯 SO THE SHADOW IS TESTED HERE AND DELIBERATELY *NOT* SET. The
                ; ON/SERVICING path below sets it on a 0->1 edge; this one only
                ; asks whether that already happened. Setting it here as well would
                ; give every plain break an edge latch and change cases nothing has
                ; measured -- a program with no trap at all that breaks, CONTs, and
                ; is still holding the key. Four of the probe's five cases pass
                ; today and must keep passing: with the shadow never set on those
                ; paths, this test is inert for them by construction, not by luck.
                bit     6,(hl)              ; the trap already consumed this press?
                jr      nz,rp_brk_run       ; yes -> no new edge, no break
                pop     hl                  ; HL = resume stmt ptr
rp_do_break:
                ; Ctrl-STOP pressed between lines/statements. HL = the statement
                ; that was about to run -> the CONT resume point. do_break records
                ; it, prints "Break in <line>", and sets ENDFLAG; we then return
                ; to the REPL (the run is suspended, not torn down).
                jr      do_break            ; D-SCRBAUD carve: in jr range (measured
                                            ; by scratchpad/jr_mapper.py, not assumed)

; --- do_break: record a CONT resume point and report "Break in <line>" -------
; in: HL = the token position to resume at; CURLINE = the line being interrupted
;     (its link-field address). Used by both Ctrl-STOP (resume = next statement
;     to run) and the STOP statement (resume = statement after STOP).
; Saves CONTLINE/CONTPTR, raises CONTVALID, prints the break message, and sets
; ENDFLAG so the run loop unwinds back to the REPL. Clobbers A, BC, DE, HL.
do_break:
                call    cont_record         ; D-CONTR: the shared record (below). A
                                            ; DIRECT-mode break records NOTHING and
                                            ; INVALIDATES NOTHING -- see cont_record's
                                            ; own header for why this stopped being an
                                            ; `xor 1` on DIRECTF here.
                ; D-GICINI (docs/spec-basic-gicini.md): a break DESTROYS the PLAY
                ; queue on both references, and `CONT` does not bring it back --
                ; rows e.stop and e.cont. `psg_silence` lives in the low region
                ; (basic/sound.asm) and is reached from page 1 by an ordinary
                ; in-slot call. cont_record above has already consumed HL.
                call    psg_silence
                ld      a,1
                ld      (ENDFLAG),a         ; stop the run, fall back to the REPL
                ; report: "break in <lineno>" + CR/LF. The line number is at
                ; CURLINE+2 (the lineno field after the 2-byte link).
                call    txt_mode            ; D-GFXERRMSG: `Break in 10` on the TEXT
                                            ; screen, as ra_abort does for an error --
                                            ; in SCREEN 2 it went into the bitmap and
                                            ; only `ZB` showed (VG-8020: `Break in 10`)
                ld      hl,brk_msg
                call    print_string
                ; repack (D-2): the " in <lineno>" + CRLF tail is the SHARED
                ; print_in_lineno routine (below) — the same one fre_abort_low uses
                ; for a runtime error's " in <line>" suffix. Output in run mode is
                ; byte-for-byte the old inline tail ("break" + " in " + <N> + CRLF).
                ; in DIRECT mode print_in_lineno now suppresses the suffix itself
                ; (the reference prints a bare "Break" for a typed STOP -- measured),
                ; so this tail stays a single unconditional jump.
                jr      print_in_lineno
; brk_msg -- MOVED to basic/islands.asm (D-ISLDATA2, 2026-10-03): pure data,
; read only by absolute `ld` from main; now in the font island.

; --- cont_record: record a CONT resume point (D-CONTR) -----------------------
; docs/spec-basic-cont-record.md §3.0. THE RUN LOOP RECORDS WHERE IT STOPPED AT
; EVERY RUN STOP, and the four stops differ only in the pointer they hand in:
;   do_break (STOP / Ctrl-STOP)  HL = the next statement to run
;   ex_end   (END, interp.asm)   HL = the position AFTER the END token -- mid-line
;   ra_abort (interp.asm)        HL = SAVTXT, the FAILING statement's own start
;   rp_lp's $0000-link exit      HL = 0, the "re-enter FRESH at CONTLINE" sentinel
; in: HL = resume token position, or 0. CURLINE = the line to resume in.
; Clobbers A, HL.
;
; 🔴 DIRECT MODE RECORDS NOTHING AND CHANGES NOTHING -- it does NOT invalidate.
; This site used to do `ld a,(DIRECTF) / xor 1 / ld (CONTVALID),a` on the strength
; of ONE measured row (docs/spec-basic-direct-ctrl.md §5: a typed
; `PRINT 1:STOP:PRINT 2` reports "Break", and the CONT after it reports "Can't
; CONTINUE"). That row was taken WITH NOTHING LIVE, where "invalidate" and "do
; nothing" are indistinguishable -- it agreed for the wrong reason. With a live
; resume point underneath, the reference KEEPS it across a typed STOP, a typed
; END, a typed error and any ordinary typed line (spec §2.2, rows
; cont2_typed_stop / _end / _err / _keep). The old row stays green because
; CONTVALID is already 0 there and doing nothing leaves it 0.
;
; CONT does NOT consume what this records (spec §2.1, cont2_thrice /
; cont2_err_twice): only RUN, NEW and a program edit clear CONTVALID.
    IF BASICINT_PINS
                                            ; (cont_record lives in basic/fat.asm in
                                            ; the shipping build: S10.C's $6CF3 refill)
    ELSE
cont_record:
                ld      a,(DIRECTF)
                or      a
                ret     nz                  ; direct mode: leave the resume point alone
                ld      (CONTPTR),hl        ; resume token pointer (0 = fresh-line entry)
                ld      hl,(CURLINE)
                ld      (CONTLINE),hl       ; line to resume in (link-field addr)
                inc     a                   ; A is still 0 -> 1
                ld      (CONTVALID),a       ; a CONT resume point is now live
                ret
    ENDIF

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
                call    cur_lineno          ; HL = line number
print_in_hl:                                ; D-READERL: " in <HL>" + CRLF -- the
                push    hl                  ; error abort names ERRLIN, which a bad
                ld      hl,in_msg           ; DATA item sets to the DATA line
                call    print_string        ; " in "
                pop     hl
                call    ln_div_entry
                jp      print_crlf
; in_msg -- MOVED to basic/islands.asm (D-ISLDATA2, 2026-10-03): pure data,
; read only by absolute `ld` from main; now in the font island.

; --- print_msg_stopcr / print_msg: the D-MSGENC message decoder ----------------
; docs/spec-basic-msgenc-carve.md §4.3. Error message strings WERE phrase-encoded
; (bytes MSGESC_LO..MSGESC_HI indexed msg_phrase_tab); DT-6 retired that: after
; D-MSGMIGRATE moved sixteen messages sub-side, the phrase arm (25 B) plus the
; table (35 B) cost MORE than the 54 B of literal text its eight remaining users
; saved (measured on the .sym at fab3f01d), so the strings are plain again and
; MSGESC_SUB is the one escape left. Everything >= $20 is a literal, and the CRLF
; is still emitted HERE instead of being baked into every message (§4.2).
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
                cp      MSGESC_SUB          ; D-MSGSUB: the sub-ROM-hosted marker --
                jr      z,pm_sub            ; since DT-6 the ONLY escape; every other
                                            ; byte is a literal >= $20 (the baked
                                            ; 13,10 are gone)
                rst     $18                 ; PRDEST sink (fre_abort_low zeroed it)
                jr      pm_lp

; --- pm_sub: the body lives in the sub-ROM (D-MSGSUB, docs/spec-basic- --------
; msgsub.md §3.1). The fourteen ERR codes zerobas never RAISES cost ~227 B of
; text against a page 1 that has tens, so they live in sub-ROM PAGE 1
; (SUBROM_IDX_ERRMSG) and are emitted there through BIOS CHPUT. The tenant reads
; ERRFLG itself, so NOTHING marshals -- HL is guarded only for the fall-through
; below, not to pass anything.
;
; ⚠️ PAGE 1, and main's own printer is why. print_string ($4673) and print_msg
; ($7717) are main PAGE 1, which is exactly what a page-1 CALSLT switches out;
; check_tenant_closure --page1 enforces "no main-page-1 escape". So the sub-ROM
; CANNOT call back into this routine, and duplicating a nine-instruction CHPUT
; loop sub-side is contract-forced, not a convenience.
;
; 🎯 `ret nc` / `jr pm_lp` IS THE ABSENT-SUB-ROM DEGRADATION, AND IT IS WHY
; err_subhosted IS ONE BYTE SITED DIRECTLY BEFORE err_unprintable
; (basic/interp.asm). subrom_call returns CF=1 without calling when there is no
; sub-ROM; the loop then resumes at the NEXT byte, which is the `U` of
; `Unprintable` -- i.e. the machine prints exactly what it printed before this
; slice. D-MSGSUB §4.2 argued the absent case was unreachable (you cannot
; tokenise `ERROR 12` without the sub-ROM, since `tokenise` is itself a tenant);
; that argument has a hole -- a TOKENISED program can arrive from tape or disk --
; so the design does not rest on it. Knife K1 MEASURES the degradation with a
; plain `POKE &HF107,0` and no rebuild.
;
; ⚠️ NOTHING RIDES BACK BUT CF. `A` is not preserved across CALSLT (basic/
; float-arith.asm, the SQR/ATN/EXP/LOG lesson) and subrom_call's own CF means
; "absent", never a tenant result -- so the tenant cannot say "not my code" and
; must answer EVERY code, out-of-table ones with its own `Unprintable error`.
; That is what lets rerr_unprintable route the whole out-of-dense range here for
; zero bytes. `pop hl` does not disturb the flags, so the CF tested below is
; still subrom_call's.
;
; 🎯 D-MSGMIGRATE RETIRED THIS ROUTINE'S PRECONDITION, AND PAID FOR IT (8 B).
; It used to read: "Clobbers BC/DE/IX on top of print_msg_stopcr's documented
; A+HL, because CALSLT does. Safe at the one site that can reach it: only the
; ABORT path resolves a message containing MSGESC_SUB." That is no longer true --
; sixteen ordinary messages are sub-hosted now, so THREE sites reach here:
;   fre_abort_low   the abort path (SP reset, statement abandoned)
;   ex_cont_no      `jp print_msg` at statement level
;   dl_overflow     `jp print_msg` at line ENTRY -- and its caller is `repl` OR
;                   mrg_storeline, the ASCII LOAD/MERGE reader (basic/files.asm)
; The reasoned argument that all three tolerate the clobber is genuinely
; available (dispatch_line already performs a CALSLT of its own, `call tokenise`,
; so every caller in that chain demonstrably survives one). It was declined:
; whoever adds the FOURTH caller would have to re-derive it, and
; print_msg_stopcr's documented "clobbers A, plus the HL walk" was ALREADY a lie.
; The push/pop fence below makes it true again for 8 bytes, out of a 289 B carve.
; ⚠️ Knife K5 built WITHOUT the fence and predicted -- correctly -- that NOTHING
; reddens. This is a structural guarantee retiring a precondition, NOT a measured
; bug repair, and recording it the other way round would be a false claim.
pm_sub:         push    bc                  ; 🎯 D-MSGMIGRATE: THE FENCE. See below.
                push    de
                push    ix
                push    hl                  ; the fall-through pointer, not an arg
                call    sr_inl1             ; D-STUBINL
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ERRMSG)
                pop     hl
                pop     ix                  ; ⚠️ POP does not touch flags, so the CF
                pop     de                  ;    tested below is still subrom_call's --
                pop     bc                  ;    the property `pop hl` already relied on
                ret     nc                  ; the tenant printed the body -> done
                jr      pm_lp               ; ABSENT -> "Unprintable error", as before

print_msg:      call    print_msg_stopcr    ; direct mode: body + CRLF
                jp      print_crlf

; --- err_subscript / err_redim: fp_runtime_error's message strings (interp.asm's
; fre_msgtab, `dw` entries). DT-6's REBALANCE: retiring msg_phrase_tab (which sat
; right here) freed 60 B of page 1, but re-spelling the five LOW-REGION escape
; users grew that region by 39 B against a 1 B wall, so these two (43 B plain,
; 38 B encoded) moved UP from basic/arrays.asm into the slot the table vacated.
; Both readers are absolute addresses, so placement is free -- arrays.asm's own
; note said exactly that when it homed them low for the mirror-image reason.
; Wording is reference-VERBATIM capitalised text (spec-basic-arrays.md §9.5),
; unchanged; tests/test_msgenc.py pins it out of the ROM image.
; C5-LOW (2026-10-12): err_subscript and err_redim are GONE from main -- ERR
; 9 / 10's text is sub-hosted (sub/errmsg.asm em_subscript / em_redim) and
; err_msgtab's rows 9 / 10 point at err_subhosted; the table was their only
; reader.

; --- ex_stop: STOP statement — break and record a CONT resume point ----------
; STOP halts the program and records where to continue, so a following CONT
; resumes at the statement after STOP.
; ⚠️ THIS HEADER USED TO SAY "(END does not: it ends the run with no resume
; point, so CONT after END is Can't CONTINUE.)" THAT WAS NEVER MEASURED AND IS
; WRONG. The rule is docs/spec-basic-cont-record.md §1: the run loop records a
; resume point at EVERY run stop -- STOP, Ctrl-STOP, END, an untrapped abort,
; and running off the end -- whenever it is in RUN mode; in DIRECT mode it
; records nothing and invalidates nothing. STOP is not special here; only the
; POSITION each stop hands to cont_record differs (see that routine's header).
; HL enters on the STOP token. Repack (T1): `STOP ON|OFF|STOP` instead arms the
; STOP interrupt trap's tri-state (spec-traps-t1-stop-reslice.md §5.2); a bare STOP
; (EOL / ':' / anything else) still halts.
ex_stop:
                rst    $10                ; past STOP token
                call    onoff_decode        ; STOP ON|OFF|STOP -> A = the ZTS_ state
                jr      c,es_set
                jr      do_break            ; bare STOP -> record + "Break in <line>"
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
                ; 🎯 D-CARVE2: THE CANONICAL "set a trap state and resume" tail.
                ; It lives HERE because this arm is assembled unconditionally,
                ; while its other two callers sit under IF G7_RESIDENT / IF
                ; TRAPS_T4. The trap INDEX is set by each caller; only the
                ; call-and-resume is shared.
trap_state_done:
                call    set_state
                jp      pop_exec            ; continue the line (a bare `ret` would
                                            ; SWALLOW the rest of the line (STOP ON:STOP OFF
                                            ; left OFF a no-op; VG-8020 differential caught it)

; --- ex_cont: CONT statement — resume a STOPped / broken program -------------
; If a CONT resume point is live (recorded by cont_record at whichever run stop
; happened last, and not invalidated by RUN / NEW / a program edit), restore
; CURLINE + RESUMEPTR and re-enter the run loop. Otherwise report "Can't
; CONTINUE". Reached as a direct-mode statement from the REPL.
; ⚠️ D-CONTR: CONT does NOT CONSUME the resume point -- this header used to say
; it did ("so a second bare CONT does not re-resume a run that has since
; finished"), and BOTH halves were wrong. A second bare CONT re-resumes exactly
; the same point; after a run that has since finished that point is the $0000
; end marker, so it resumes past the end, runs nothing and returns SILENTLY to
; Ok. Measured n-deep (docs/spec-basic-cont-record.md §2.1, cont2_thrice).
ex_cont:
                ld      a,(CONTVALID)
                or      a
                jr      z,ex_cont_no        ; nothing to continue
                ; D-CONTR (docs/spec-basic-cont-record.md §3.5): the `xor a /
                ; ld (CONTVALID),a` that used to CONSUME the resume point here is
                ; GONE. The reference never consumes it -- a second, third, n-th
                ; bare CONT re-resumes the same point (cont2_thrice), and after a
                ; run that has since finished that means "resume past the end and
                ; run nothing", i.e. a silent Ok, not "Can't CONTINUE". Only RUN,
                ; NEW and a program edit clear CONTVALID.
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
                ; D-CONTR §3.5: RESUMEFLAG is DERIVED from CONTPTR instead of being
                ; a constant 1, and that is what makes the $0000-link exit's
                ; "re-enter FRESH" sentinel cost ZERO bytes -- `ld a,h / or l` is
                ; the same two bytes `ld a,1` was, and RESUMEFLAG only has to be
                ; NON-ZERO. CONTPTR = 0 -> RESUMEFLAG = 0 -> rp_lp enters the line
                ; FRESH (and CONTLINE is the $0000 marker, so it stops again,
                ; silently). Any real pointer -> resume mid-line, as before.
                ; ⚠️ `ld a,1` here instead is the whole difference between that and
                ; a CONT that resumes MID-LINE AT ADDRESS 0 (falsification F6).
                ld      a,h
                or      l
                ld      (RESUMEFLAG),a      ; resume mid-line at CONTPTR (0 = fresh)
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
                jp      rp_lp               ; re-enter the run loop
ex_cont_no:
                ld      a,$C9               ; "can't continue" landmark (distinct byte)
                ld      (ERRMARK),a
                ; 🔴 THIS ARM PRINTED ITS MESSAGE AND LEFT `ERR` AT 0, AND NOTHING
                ; HAD EVER LOOKED. Found by D-DELETE's `dlt-cont`, whose reference
                ; answer is ` 0  17 ` -- and it is NOT DELETE's defect: `dlt-contbare`
                ; is a bare `CONT` on a fresh machine with no DELETE anywhere, refs
                ; 17, zerobas 0. err_msgtab already maps ERR 17 -> err_cont
                ; (basic/interp.asm), so the code and the string were always the
                ; pair; only the store was missing.
                ; ⚠️ ERRFLG, NOT raise_error, AND THAT IS DELIBERATE. Like
                ; dl_overflow's arm in this same file, the refusal is raised by the
                ; EDITOR/prompt rather than by a running program, so it reports and
                ; returns to the REPL; routing it through raise_error's trap branch
                ; would jump into a finished program from the prompt. PRINT ERR is
                ; the only observer either way, and it now reads what both
                ; references read.
                ld      a,17                ; ERR 17: can't continue
                ld      (ERRFLG),a
                ld      hl,err_subhosted    ; D-MSGMIGRATE: em_cont, keyed on the
                                            ; ERRFLG store two lines up. ⚠️ THAT STORE
                                            ; IS NOW LOAD-BEARING FOR THE TEXT, not just
                                            ; for PRINT ERR -- change the 17 and this
                                            ; prints `Unprintable error`. Gate row
                                            ; `cont-bare`; knife K2 cuts exactly this.
                jr      print_msg           ; D-MSGENC: encoded body + emitted CRLF

; --- find_line_bc: locate a stored line by number ----------------------------
; in: BC = line number. out: CF set + HL = the line's link-field address if
; found; CF clear otherwise. Clobbers A, DE, HL.
find_line_bc:
                ld      hl,(TXTTAB)  ; D-BASICROM: the program START is TXTTAB (a cartridge program sits at TEXT+1)
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
; 📌 store_line's BODY is a PIN REFILL in basic/files.asm (OPEN's mode dispatch)
; since S10.E (2026-10-19): it refills bytes S10.E freed in front of $6CF3.
; 🎯 err_mem IS NOW AN ALIAS, NOT A STRING. It was the lowercase twin of arrays'
; capitalised err_mem_arr ("o" vs "O" + MSGESC_UTOF + "memory"); D-MSGEXACT made
; both the reference's `Out of memory`, so they became byte-identical and this
; page-1 copy is deleted (-9 B of page 1). err_mem_arr lives in arrays.asm's LOW
; region, which still satisfies the constraint that mattered here: the message
; STRING must stay MAIN-resident even though sl_oom's own CODE moved sub-side,
; because interp.asm's err_msgtab takes its ADDRESS directly (`dw err_mem`) and
; that must resolve to a main-ROM address, never a sub-ROM one. err_stack (below)
; and cload.asm's err_prog_mem both `equ err_mem` and are unaffected.
err_mem         equ     err_mem_arr

; (le_call_op lives in basic/files.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)
; (moved OUT of the segment in front of $73AC by D-WSZERO S16, as part of an
; exact refill there: le_call_op went in, this went out -- page 1 both ways)
; --- arl_getbyte: ascii_read_lines' byte-source indirection (D2) ------------
; Jumps through the ARL_GETBYTE RAM vector to the CURRENT byte-source routine
; (fat_io_getbyte by default; cload.asm's cal_getbyte during a cassette ASCII
; load). Standard Z80 call-through-pointer idiom: `call arl_getbyte` pushes
; OUR caller's return address, then `jp (hl)` jumps to the target WITHOUT
; touching the stack, so the target's own `ret` pops that same address —
; reaching ascii_read_lines exactly as a direct `call fat_io_getbyte` would.
; Preserves nothing (neither source routine does); ascii_read_lines already
; reloads everything it needs from RAM after each call.
;   out: A = byte, CF clear; or CF set = no more data (source-defined "EOF").
; 🔁 DEMOTED BACK TO PAGE 1, 2026-09-08 (D-REBALANCE). It was PROMOTED
; into the low region earlier the same evening, when main page 1 had 3 B and the
; low region 14 B. D-INCSKIP and D-SKIPCOMMA then freed 113 B of page 1 and only
; 12 of low, so the SCARCE wall changed sides and the promotion now costs the
; wrong region. The two regions are one budget; which side a routine sits on is a
; reading of today's split, not a property of the routine.
; arl_getbyte — the indirect byte source ascii_read_lines reads through.
;   out: A = byte, CF clear; or CF set = no more data (source-defined "EOF").
; Preserves nothing (neither source routine does); ascii_read_lines already
; reloads everything it needs from RAM after each call.
; 💰 PROMOTED OUT OF basic/files.asm (main page 1) INTO THE LOW REGION,
; 2026-09-08, to fund `ATTR$`'s `ev_f` arm (D-ATTRFN). Same route as `upcase`
; above (D-PROMOTE): the two regions are one contiguous, freely inter-callable
; image, so these four bytes cost nothing here and buy four bytes of page 1.
; 🎯 It qualifies because nothing about it is position-dependent: entered only by
; `call`, left only by `jp (hl)` — an unconditional terminator — emits no data,
; and no `jr`/`djnz` crosses its boundary. `ascii_read_lines`, its only caller,
; reaches it absolutely. Sited ABOVE the overflow guard, which has to stay the
; last thing in this block or it does not guard the bytes after it.
; 📌 arl_getbyte's 4 B body is a PIN REFILL in basic/files.asm since D-FCHNUM
; (2026-10-17), ahead of oo_fail_syn.
; 📌 (relink's 7 B BODY is a PIN REFILL at the end of basic/strvar.asm since
; D-FLDDESC, 2026-10-17, in front of $6CF3: `ld c,LE_OP_RELINK` + the lineedit
; tenant call, entered only by `call`.)

; --- ex_delete: DELETE [<lo>][-[<hi>]] ---------------------------------------
; docs/spec-basic-delete.md, measured in docs/delete-msx1-characterization.md.
; HL enters on the DELETE token (the es_hit contract). The WHOLE verb -- the
; argument parse, the two validations and the delete walk -- lives in
; sub/lineedit.asm beside the TXTTAB memmove engine it drives; this is the
; marshalling head, and it is deliberately the third shim in this file rather
; than a fourth thing that knows about line storage.
;
; WHY THE PARSE IS SUB-SIDE (spec §3.1). The grammar is `[$0E lo] [$F2 [$0E hi]]`
; -- pure token bytes, no expression evaluation anywhere -- so the entire
; argument marshals as ONE POINTER. Parsing it here instead would cost ~88 B of
; main page 1 against this head's ~34; the tenant pays it out of sub page 1,
; which had 3339 B free at D-RETLN's HEAD. Measured both ways (spec §7 K6): the
; claim is not left as an estimate.
;
; ⚠️ NOTHING COMES BACK BUT A STATUS, AND THAT IS R-D8, NOT A SHORTCUT. DELETE
; ENDS the line and the program on BOTH paths -- a succeeding one via ENDFLAG
; below, a failing one via raise_error -- so the advanced cursor has no reader
; and is never marshalled back. `DELETE 20:B=9` leaves B at 0 with ERR 0 on both
; references (dlt-tail, against dlt-tailctl's 9), which is what says the ':' is
; ACCEPTED and then abandoned rather than rejected.
; 📌 (ex_delete's BODY is a PIN REFILL in basic/field.asm since D-FLDDESC,
; 2026-10-17, in front of the $72D4 pin; the header above is its contract. It is
; entered only through the statement table.)

; --- ex_renum: RENUM [<new>][,[<old>][,<inc>]] (D-EDITVERB) -------------------
; docs/spec-basic-editverb.md §3.2, measured in
; docs/editverb-msx1-characterization.md §2. HL enters on the RENUM token (the
; es_hit contract). The whole verb -- parse, both validations, the reference pass
; and the header pass -- lives in sub/lineedit.asm (le_renum), for the same
; reason DELETE's does: it drives the stored program text and marshals as one
; pointer. This is the marshalling head PLUS the one thing the tenant cannot do.
;
; 🔴 THE LOOP IS THE POINT. `Undefined line <n> in <m>` is emitted ONCE PER
; DANGLING REFERENCE (R-RN9 -- `1 ON 1 GOTO 77,88` prints two, both `in 1`), and
; rendering it needs print_string + list_num, which are main PAGE-1 resident and
; therefore unreachable from a page-1 tenant. So the tenant STOPS at each one,
; hands back the pair in RN_TGT/RN_LINE, and this head prints it and re-enters
; with LE_OP_RENUM_NEXT. The tenant's cursor lives in RN_PTR across the round
; trip, which is why that cell may not be an alias of the SL_* block.
;
; 🔴 AND IT IS NOT AN ERROR (R-RN10). ERR stays 0, ON ERROR does not trap it, and
; the renumbering HAPPENS ANYWAY -- `1 GOTO 77` becomes `10 GOTO 77`. That is why
; status 1 is a REPORT and only status >= 2 reaches raise_error.
ex_renum:
                ld      (RN_PTR),hl         ; the statement cursor, on the token
                ld      a,LE_OP_RENUM
exr_call:
                call    le_call_op          ; A = LE_STATUS, Z = ok
                jr      z,exr_done          ; 0 = the whole renumbering is done
                dec     a
                jr      nz,exr_raise        ; >= 2 is the ERR CODE ITSELF: 2 for
                                            ; R-RN14/R-RN15, 5 for R-RN11/12/13
                ld      hl,rn_undefined     ; 1 = report one dangling reference
                call    print_string
                ld      de,(RN_TGT)
                call    list_num            ; the target, bare unsigned decimal
                ld      hl,rn_in
                call    print_string
                ld      de,(RN_LINE)        ; R-RN8: the containing line's OLD
                call    list_num            ; number -- `in 1`, not `in 10`
                call    print_crlf
                ld      a,LE_OP_RENUM_NEXT
                jr      exr_call
exr_raise:
                ld      a,(LE_STATUS)
                jp      raise_error
exr_done:
                ; R-RN16: and then the run stops, exactly as DELETE and LIST do.
                ; ⚠️ CONTVALID IS DELIBERATELY NOT CLEARED AND vars_reset IS
                ; DELIBERATELY NOT RUN -- R-RN17, measured on both references with
                ; a program whose lines actually MOVE: `1 A=7/RUN/RENUM/PRINT A`
                ; reads 7, and `1 STOP/2 PRINT 5/RUN/RENUM/CONT` still prints 5.
                ; RENUM is not a program EDIT in the sense DELETE is: no byte
                ; changes length, so nothing the variables or the CONT point
                ; address has moved.
                jp      end_line_end

; The two halves of the report. Plain ASCII rather than the D-MSGENC pool: the
; pool encodes whole messages and this one has two NUMBERS spliced into it, so
; there is no message to look up -- and `Undefined line` is not a prefix of
; err_undefined's text in any form the decoder could share.
; rn_undefined -- MOVED to basic/islands.asm (D-ISLDATA2, 2026-10-03): pure data,
; read only by absolute `ld` from main; now in the font island.
; (rn_in = in_msg: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)

; --- ex_auto: AUTO [<start>][,<inc>] (D-EDITVERB) ----------------------------
; docs/spec-basic-editverb.md §3.3, measured in
; docs/editverb-msx1-characterization.md §3. The ARGUMENT is parsed sub-side
; (le_auto); the MODAL LOOP is here, because it drives read_line, dispatch_line,
; find_line_bc, list_num and CHPUT -- all main page 1, none of them reachable
; from a page-1 tenant. LIST's split with the halves reversed.
;
; 🎯 THE LOOP STORES NOTHING ITSELF. It writes the line number's own digits at
; the FRONT of LINEBUF, points read_line's cursor just past them, and hands the
; finished buffer to dispatch_line -- which sees an ordinary `<number> <body>`
; and takes the path a typed line already takes. No second parser, no second
; store, and every rule dispatch_line already enforces (the 65529 refusal, the
; crunch overflow, D-DOTGAPS's `.` write) applies here for free.
;
; 🔴 THE `*` IS SCREEN-ONLY. R-AU6: the prompt reads `10*` when a line 10 already
; exists and `10 ` when it does not -- but the STORED line is `10 REM X` either
; way, so the marker goes to CHPUT and the SPACE goes to the buffer. Putting the
; measured character into LINEBUF would store `10*REM X`, whose body crunches to
; something else entirely.
ex_auto:
                ld      (RN_PTR),hl         ; the statement cursor, on the token
                ld      a,LE_OP_AUTO
                call    le_call_op          ; A = LE_STATUS, Z = ok.
                                            ; 2 = R-AU9 trailing junk, 5 = R-AU5
                                            ; (increment 0, which is also what bare
                jp      nz,raise_error      ; `AUTO ,` reduces to)
                inc     a                   ; -> 1: read_line polls from here on
                ld      (RL_AUTO),a
exa_loop:
                ld      de,(AU_NUM)
                call    list_num            ; print the digits -- and leave them
                                            ; 0-terminated in NUMBUF, which is what
                                            ; makes the buffer copy below free
                ld      bc,(AU_NUM)
                call    find_line_bc        ; CF set = that line already exists
                ld      a,' '
                jr      nc,exa_mark
                ld      a,'*'               ; R-AU6
exa_mark:
                call    CHPUT               ; SCREEN ONLY (see the header)
                ld      hl,NUMBUF
                ld      de,LINEBUF
exa_copy:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                or      a
                jr      nz,exa_copy
                dec     de                  ; DE -> the terminator just written
                ld      a,' '               ; the ONE separator blank parse_lineno
                ld      (de),a              ; eats (D-LNBLANK R3)
                inc     de                  ; DE = where the typed body begins
                push    de
                ex      de,hl               ; HL = read_line's write cursor
                call    rl_loop             ; the second entry point: HL preset
                pop     de
                jr      c,exa_stop          ; R-AU8: Ctrl-STOP ends the session, and
                                            ; the half-typed line is DISCARDED
                ; R-AU7: an EMPTY entry stores NOTHING. ⚠️ That is NOT the same as
                ; storing an empty body -- dispatch_line would read that as the
                ; bare-line-number form and DELETE the line. The separating row is
                ; `au-emptykill`: Enter at a prompt whose line EXISTS leaves it
                ; standing on both references. Round 3's case pressed Enter at a
                ; prompt whose line did not exist, where skip and delete agree.
                ld      a,l
                cp      e
                jr      nz,exa_store
                ld      a,h
                cp      d
                jr      z,exa_next
exa_store:
                call    dispatch_line       ; store / replace, exactly as if typed
exa_next:
                ld      hl,(AU_NUM)
                ld      de,(AU_INC)
                add     hl,de
                jr      c,exa_stop          ; a 16-bit wrap ends the session
                ld      a,h                 ; R-AU11: and so does passing the same
                cp      high (LINENO_CEIL+1)    ; 65529 ceiling a typed line obeys --
                jr      c,exa_ok            ; `AUTO 65525,10` prompts once and stops
                ld      a,l                 ; (LINENO_CEIL+1 is $FFFA, so H can never
                cp      low (LINENO_CEIL+1) ; be ABOVE its high byte and the two-step
                jr      nc,exa_stop         ; compare is exact)
exa_ok:
                ld      (AU_NUM),hl
                jr      exa_loop
exa_stop:
                xor     a
                ld      (RL_AUTO),a         ; the prompt blocks again
                jp      end_line_end        ; R-AU9: AUTO ends the line and the run

; --- gosub_push: push a bounds-checked GOSUB return frame (repack golf) -------
; D-CTLPOOL: the frame is [CURLINE:2][resume-ptr:2][prevFSP:2][gdelta:1] -- 7 B as
; the reference's (sysvars.inc GOSUB_FRAME: the previous GOSUB frame is prevFSP +
; gdelta; it was an 8-byte [..][prevGSP:2][prevFSP:2] until 2026-10-17),
; taken from the control pool rather than a fixed array; resume = the token
; position to run when RETURN pops it. prevGSP chains the GOSUB frames (they are
; no longer contiguous -- FOR frames interleave with them), and prevFSP is
; D-FORRET's field under a new name: FSP is the FOR run's FLOOR, so restoring it
; discards every FOR opened since this GOSUB (row lnrt-forret). Factored out of ex_gosub / eon_gosub (which each used
; to inline this) so the interrupt-trap dispatcher can reuse it as its GOSUB-into-
; handler branch (docs/spec-basic-interrupt-traps.md §2.1/§10.1).
;   IN:  HL = resume token pointer; CURLINE = the line to resume in.
;   OUT: CF clear = pushed, GSP advanced by GOSUB_FRAME.  CF set = stack full (nothing
;        pushed).
;        Preserves BC (the target line number). Clobbers A, DE, HL.
gosub_push:
                push    bc                  ; guard the caller's target line number
                push    hl                  ; save resume ptr
                ld      hl,GOSUB_FRAME
                call    ctl_alloc           ; 🎯 THE ONE CHECK THAT REPLACED THREE:
                jr      c,gp_full           ; "collided with the variable area"
                ex      de,hl               ; DE = the frame base = the write cursor
                ld      hl,(CURLINE)
                call    ctl_put             ; [0..1] the line to resume in
                pop     hl                  ; HL = resume ptr
                call    ctl_put             ; [2..3] where in it
                ld      hl,(FSP)
                call    ctl_put             ; [4..5] prevFSP -- D-FORRET's field
                ex      de,hl               ; HL = the cursor, DE = FSP
                push    hl
                ld      hl,(GSP)
                or      a
                sbc     hl,de               ; GSP - FSP: 0, or 3 under a trap record
                ld      a,l
                pop     hl
                ld      (hl),a              ; [6] gdelta -- the frame chain
                ; 🎯 GSP AND FSP BOTH BECOME THE FRAME'S BASE, and the second one
                ; is what D-CTLCROSS needs: FSP is the FOR run's FLOOR, so every
                ; FOR frame opened BEFORE this GOSUB is now below it and invisible
                ; to a NEXT inside the subroutine. Both references answer
                ; `NEXT without FOR` there (spec-basic-trapsvc.md §12) and three
                ; separate arrays could not express it.
                ld      hl,(CSP)
                ld      (GSP),hl
                ld      (FSP),hl
                pop     bc                  ; restore target line number
                or      a                   ; CF = 0 -> success
                ret
gp_full:
                pop     hl                  ; discard resume ptr
                pop     bc                  ; discard target
                scf                         ; CF = 1 -> pool full
                ret
; ctl_put / ctl_get: store/load HL at (DE), DE += 2. Four call sites each in the
; two routines below -- open-coding them costs 21 bytes of main page 1 apiece,
; which this region does not have (`make basic-reloc` reports the wall).
    IF BASICINT_PINS
                                            ; (ctl_put lives in basic/fat.asm in the
                                            ; shipping build: S10.C's $6CF3 refill)
    ELSE
ctl_put:
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                ret
    ENDIF
; (ctl_get lives in basic/expr.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)
; gosub_stk_over: shared control-stack-overflow tail (ex_gosub + eon_gosub).
gosub_stk_over:
                ; 🎯 D-GOSUBOOM (2026-10-16): THE REFERENCE EMPTIES ITS STACK ON THIS
                ; OVERFLOW, so the pool goes too. Measured (scratchpad/gosubedge_probe.py):
                ; in the handler of a trapped GOSUB overflow the VG-8020's FRE(0) reads
                ; nearly all memory and a RETURN is `RETURN without GOSUB`; a plain
                ; trapped ERROR inside ONE GOSUB keeps its frame on both machines. Here
                ; the frames stood, the handler's RETURN went back into the recursion
                ; and the program looped for ever -- and CTL_FRAME_MARGIN had to keep
                ; 768 B clear so expressions could still run under them (D-STACKFLOOR).
                ; ctl_reset empties the pool as RUN / CLEAR do (every GOSUB / FOR / DEF
                ; FN frame and trap record); the word at SAVSTK -- run_prog's return,
                ; just above this statement's own stack -- is untouched, so the trap
                ; branch and the abort still unwind to it, and the run loop re-bases
                ; SP on the new frontier at the handler's first line (rp_lp).
                call    ctl_reset
                xor     a
                ld      (TRAPSVC),a         ; no trap in service: its record went too
                ld      a,$CE               ; control-stack overflow landmark
err7_mark:                                  ; D-TAILMERGE: A = the landmark; the
                                            ; out-of-memory tail above joins here
                ld      (ERRMARK),a
                ld      a,7                 ; ERR 7: out of memory (error-handling S2a)
                jp      raise_error
; --- ex_gosub: GOSUB <line> (repack: via gosub_push) -------------------------
ex_gosub:
                rst    $10                ; past the GOSUB token
                call    req_lineno          ; D-NGRAM10: $0E,<lineno LE> expected --
                                            ; BC = target, HL = just past the line
                                            ; number -- NOT yet the resume point
                ; D-FLOWTAIL: the resume point is the end of the STATEMENT, not
                ; the byte after the line number. `GOSUB 100 ZZ` is accepted on
                ; both references and the ZZ never runs; here RETURN came back
                ; onto it and raised ERR 2. Sited at THIS verb and at eon_gosub
                ; rather than at the shared `goto_take_bc` below, whose own header
                ; says a change there serves GOTO too -- and `GOTO 100 ZZ` AGREES
                ; today, because GOTO never comes back to its tail
                ; [[a-shared-tail-is-not-a-decision]].
                call    skip_stmt_tail      ; HL -> ':' or EOL; BC (the target) kept
                call    gosub_push          ; push frame; BC=target kept; CF set = full
                jr      c,gosub_stk_over
                jp      goto_take_bc        ; BC = target; arm GOTOTGT/GOTOFLAG

; --- ex_return: RETURN -------------------------------------------------------
; Pop the top GOSUB frame and resume at its saved (CURLINE, resume-ptr) via the
; RUN loop's mid-line resume path. (HL enters on the RETURN token.)
ex_return:
                ; interrupt-trap re-enable (T1): if any trap is servicing and THIS
                ; RETURN's frame is the trap's own (GSP match), auto-resume it to ON
                ; before the normal pop (spec-traps-t1-stop-reslice.md §8). The gate
                ; is one RAM load on every RETURN in the common (no-trap) case.
                push    hl                  ; D-RETLN: the token cursor, across BOTH
                                            ; the trap check and the empty-stack
                                            ; check below (each needs HL).
                                            ; 🔴 THE PUSH MUST PRECEDE trap_return_
                                            ; check, AND PUTTING IT AFTER SHIPPED A
                                            ; REGRESSION. That routine destroys HL
                                            ; unconditionally (basic/traps.asm: `ld
                                            ; l,a / ld h,0 / add hl,hl ...`), which
                                            ; was FREE before this slice because
                                            ; ex_return's next act was `ld hl,(GSP)`
                                            ; -- HL was dead across it. Making HL
                                            ; live is exactly the clobber contract a
                                            ; refactor inherits without being told.
                                            ; Caught by stop-trap-acceptance
                                            ; (C2_press_in_handler_latches), NOT by
                                            ; this slice's own 28-row battery: no
                                            ; lnrt row RETURNs out of a servicing
                                            ; interrupt trap, so TRAPSVC is 0 in
                                            ; every one of them and the clobber
                                            ; could not fire.
                ld      a,(TRAPSVC)
                or      a
                call    nz,trap_return_check
                                            ; ⚠️ The
                                            ; ex_ret_under arm leaves the pushed HL on
                                            ; the stack ON PURPOSE -- raise_error's
                                            ; two exits BOTH reset SP from SAVSTK
                                            ; (the trap arm's `ld sp,(SAVSTK)`,
                                            ; basic/interp.asm; the abort arm's
                                            ; fre_abort_low as its first act), so a
                                            ; `pop hl` there would be a byte for
                                            ; nothing. The row `lnrt-leak` -- 200
                                            ; RETURN-without-GOSUBs in one program --
                                            ; is what proves it, not this comment.
                ld      hl,(GSP)            ; empty stack -> RETURN without GOSUB
                ld      de,(CTLTOP)         ; D-RETLN R-T1: THIS CHECK COMES FIRST,
                or      a                   ; before the argument is parsed OR
                sbc     hl,de               ; resolved. Measured both references:
                jr      z,ex_ret_under      ; `RETURN B` with an empty stack is
                                            ; ERR 3, not ERR 2 (lnrt-nogosbad), and
                                            ; `RETURN 99` is ERR 3, not ERR 8
                                            ; (lnrt-nogosund). lnrt-nogos alone
                                            ; cannot tell the two orders apart.
                pop     hl
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,ret_frame_bare
                                            ; after it does NOT run (lnrt-bcolon)
                ; D-RETLN R-T2/R-T3/R-T4 (docs/spec-basic-retln.md §2): pop the
                ; frame and hand the cursor to GOTO's own parser -- $0E branches,
                ; anything else is ex_goto_at's own `jp nz,stmt_error` (ERR 2).
                ; POP FIRST IS MEASURED, NOT CHOSEN FOR CHEAPNESS: both failure
                ; modes pop before they raise, and the rows that say so read the
                ; STACK rather than the outcome -- a handler's own bare RETURN
                ; reports ERR 3 after `RETURN 99` (lnrt-undefp) AND after
                ; `RETURN B` (lnrt-varp). Neither path writes CURLINE, which is
                ; the other half: both references file the error against the
                ; RETURN's OWN line, not the caller's (lnrt-erlund/-erlvar, ERL=40).
                ; That is what rules out the obvious shape -- reusing the bare tail
                ; below, whose `ld (CURLINE),de` would file it against the caller.
                push    hl
                call    ret_frame           ; GSP -= 6; the frame's contents are dead
                pop     hl                  ; on this path (BC is the branch target)
                jp      ex_goto_at          ; its own skip_spaces is a no-op here --
                                            ; HL is already past the blanks
ret_frame_bare:
                call    ret_frame
                ld      (CURLINE),de
                ld      (RESUMEPTR),bc
; set_resumeflag_ret: shared tail (error-handling S2b space fix) -- ex_resume's
; res_setptr (basic/interp.asm, repack-only) jumps in here after its own
; `ld (RESUMEPTR),hl`, reusing the RESUMEFLAG:=1 + ret verbatim. A zero-cost
; label: RETURN's own bytes/behaviour here are completely unchanged, and this
; label costs nothing: RETURN's own bytes here are unchanged.
set_resumeflag_ret:
                ld      a,1
                ld      (RESUMEFLAG),a
                ret
ex_ret_under:
                ; D-FORRET: there is no GOSUB frame, so the reference's walk runs the
                ; whole stack and discards EVERY open FOR before it gives up and
                ; raises. Row lnrt-forret is this arm and nothing else: ` 102  0  1 `
                ; on both references against ` 103  0  4 ` here, and the loop that
                ; kept running IS the frame this clears.
                ; D-CTLPOOL: the FOR run is [CSP,FSP), so dropping the frontier
                ; to the floor discards every open FOR in one store.
                ld      hl,(FSP)
                ld      (CSP),hl
                ld      a,$CD               ; "return without gosub" landmark
                ld      (ERRMARK),a
                ld      a,3                 ; ERR 3: return without gosub (error-handling S2a)
                jp      raise_error
; ret_frame: pop the top GOSUB frame. out: DE = its saved CURLINE, BC = its resume
; pointer, GSP -= GOSUB_FRAME, HL = the new GSP, and FSP is truncated back to the
; frame's recorded depth. The caller has ALREADY established that the
; stack is non-empty (R-T1). Was inline in ex_return until D-RETLN; it is a
; subroutine now because the two arms want different halves of it -- the bare arm
; needs the contents, the `RETURN <line>` arm needs only the GSP decrement and
; must NOT let the contents reach CURLINE.
; 📌 ret_frame's BODY is a PIN REFILL in basic/files.asm (beside fch_select) since
; S10.E (2026-10-19): it refills bytes the channel switch freed in front of $72D4.
; Its two notes, which belong to the body:
;   * D-FORRET, unchanged in meaning: restoring the FOR run's floor (the
;     `ld (FSP),hl` of prevFSP) is what discards the frames opened since this
;     GOSUB. `RETURN <line>` discards the same ones as a bare RETURN (row
;     lnrt-forgline, measured on both references), which is why BOTH arms pop.
;   * 🎯 ONE STORE FREES THE WHOLE SUBTREE. DE has walked to base+GOSUB_FRAME
;     exactly, so `ld (CSP),de` drops the frame, every FOR opened since it, AND a
;     trap service record if this RETURN is a handler's -- all of them sit at
;     lower addresses than DE.

; --- for_name: parse a FOR/NEXT loop variable into the frame key -------------
; D-FORVAR (docs/spec-basic-forvar.md §4.3), shared by ex_for and ex_next.
; in:  HL = cursor at the name's first letter (the caller has run is_letter).
; out: FOR_CUR[0..2] = the frame's KEY; A = the resolved type; BC = the key
;      (var_name_key's, untouched by for_key -- ex_for hands A and BC straight to
;      var_alloc_or_find, D-LETNEWFIRST); HL advanced past the whole name AND its
;      type suffix.
; Clobbers A, BC, DE, HL (var_name_key's own contract).
;
; 🔴 THE KEY IS [name1][name0][type], NOT [name0][name1][type], AND THE ORDER IS
; LOAD-BEARING RATHER THAN ARBITRARY. `LD (nn),BC` writes C first, and
; var_name_key returns B = name0 / C = name1 -- so this IS the layout, and
; for_get/for_set_typed read it straight back with `ld bc,(FOR_CUR)`. Getting a byte
; order for free is worth more than a tidier one for 4 bytes.
; ⚠️ Which means name0 lives at FOR_CUR+1, and every reader below says +1
; DELIBERATELY. The first draft of this slice put the bare-NEXT sentinel on
; FOR_CUR+0 and the gate caught it in three rows: name1 is 0 for any
; SINGLE-CHARACTER name, so `NEXT A` read as a bare NEXT and matched the top
; frame whatever its name. Every row whose top frame happened to BE the right one
; passed regardless -- only n.xtype, n.prefix and n.strnx could see it.
;
; 🎯 FOR_CUR IS ALSO NEXT'S KEY, AND THAT COSTS NO RAM. FOR_CUR is scratch that
; only ex_for and nx_have write, and nx_have writes it AFTER the match -- so
; ex_next parks its parsed key here and nx_scan compares each frame against it
; in place; the ldir that follows a match rewrites the same three bytes.
;
; D-NXARY: for_key is the second entry point, and it costs NOTHING because
; for_name falls into it. ex_next no longer parses with var_name_key -- it uses
; tgt_parse, which resolves a subscript too -- but the frame-key store is the
; same three fields either way, so the two verbs share the tail instead of the
; head. ⚠️ ex_for must NOT switch to tgt_parse: spec-basic-nxary.md §5.2.
for_name:
                call    var_name_key        ; BC = key, HL past name + suffix,
for_key:                                    ; (VARTYPE) = the resolved type (F3/S3b:
                ld      (FOR_CUR),bc        ; the suffix, or the DEFtbl default for
                ld      a,(VARTYPE)         ; name0 when there is none)
                ld      (FOR_CUR+2),a
                ret

; --- for_set_at: FOR's start value -> the loop variable's ENTRY --------------
; in:  HL = the entry ex_for created-or-found BEFORE the start expression
;      (D-LETNEWFIRST), the value live as eval left it, FOR_CUR[2] = the type.
; A `%` loop variable keeps eval's int16 tail (FACTYP forced to 2): that is what
; `FOR A%=1.7 TO 3` starting at 2 on both references rests on (row intinit) --
; the int coercion truncates, and would give 1. Any other type takes the value
; whole (`FOR A=.5` starts at .5). This is the rule vars.asm's `for_set` carried
; until D-LETNEWFIRST (2026-10-19), when FOR's store stopped looking the variable
; up after the start expression; it FALLS INTO var_store_at.
; 🧮 The VG-8020's `FOR I=FRE(0) TO ...` with I new reads 11 B less than here did
; (scratchpad/letnew_run.out): it has made I's 11 B double before the start
; expression runs. ex_for's header (basic/fat.asm, and its ELSE twin in this file)
; has the order; ex_let's (basic/interp.asm) has the pointer-validity argument.
for_set_at:
                ld      a,(FOR_CUR+2)
                cp      2
                call    z,set_factyp2       ; a `%` loop keeps eval's int16 tail;
                                            ; set_factyp2 touches A and FACTYP only
; --- var_store_at: HL = a scalar's ENTRY -> coerce the live RHS into it ------
; in:  HL = the entry ([name0][name1][type][value]), DE valid iff (FACTYP) == 2,
;      else FAC/FACTYP hold the RHS's own float value -- var_store_fac's RHS
;      contract exactly.
; out: the value field holds the RHS coerced into the ENTRY's own type, by
;      var_store_fac's rules (§11.2): int TRUNCATES in the strict int16 domain
;      (fac_to_int_strict), single ROUNDS to 6 digits, a double already in FAC is
;      written as it stands (D-FORFAST) and anything else is widened and packed.
;      A coercion-time Overflow sets FPERR and writes NOTHING -- the caller's
;      fp_stmt_done raises it. Clobbers A, B, C, D, E, H, L.
; 🧮 D-LETNEWFIRST (2026-10-19): var_store_fac's store with its lookup taken out.
; LET and FOR now find-or-create the target BEFORE the right side and hand the
; entry here, so the existing-target path makes one lookup, as it always did, and
; skips everything var_store_fac spends carrying the KEY and the TYPE across the
; coercion (the key push, the two VS_TARGET_TYPE reloads, the VS_INT_VAL round
; trip). The type comes from the entry's own type byte, which is also why LET no
; longer latches (VARTYPE) across eval. var_store_fac stays for its keyed callers
; (NEXT, READ / INPUT targets, an FN call's formals).
var_store_at:
                inc     hl
                inc     hl
                ld      a,(hl)              ; A = the entry's own type (2/4/8)
                inc     hl                  ; HL = its value field
                push    hl                  ; [value] across the coercion
                cp      2
                jr      z,vsa_int
                cp      4
                jr      z,vsa_single
                ld      a,(FACTYP)          ; 🐌 D-FORFAST: a double already in FAC is
                cp      8                   ; already packed and rounded
                jr      z,vsa_dbl
                call    arga_widen          ; D-ARGAWIDEN
                call    round_and_finalize  ; exact widen + pack as double
vsa_dbl:
                ld      a,8                 ; the byte count
                jr      vsa_copy
vsa_single:
                call    arga_widen          ; D-ARGAWIDEN
                call    round_single_and_pack ; 6-digit half-up round + pack
                ld      a,4
vsa_copy:
                pop     de                  ; DE = the value field
                ld      c,a                 ; C = the byte count
                ld      a,(FPERR)
                or      a
                ret     nz                  ; coercion Overflow -> nothing written
                ld      b,a                 ; B = 0
                ld      hl,FAC
                ldir                        ; FAC -> value field, verbatim
                ret
vsa_int:
                call    fac_to_int_strict   ; DE = the value (truncated, strict int16);
                                            ; FPERR on overflow
                pop     hl                  ; HL = the value field
                ld      a,(FPERR)
                or      a
                ret     nz                  ; Overflow -> nothing written
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret

; --- slot_store / slot_load: a FOR frame's typed limit/step slot (D-FORFLOAT) --
; A slot is [FACTYP][8]: an int16 in its first two bytes, or FAC's eight. Its
; job is to hand NEXT the value exactly as the factor that FOR evaluated left it,
; so combine_add / combine_cmp see the same operand an expression would.
; slot_store: HL = slot, the value live (FACTYP + DE or FAC). Clobbers A,BC,DE,HL.
; 🐌 D-FORFAST (2026-10-20): A NON-`%` LOOP'S EXACT-INT16 LIMIT/STEP IS KEPT AS AN
; INT16 SLOT -- an int16 as eval left it, and a single/double that holds an exact
; int16 (`TO N` with N = 300) converted to one (nx_pki). Both slots int16 is what
; sends NEXT down its int path (nx_fast, below); the first NEXT that cannot take
; it WIDENS the int16 slots for good (nx_demote) into exactly the packed double
; this routine wrote before -- the widen-once of the first D-FORFAST step, moved
; from FOR to that NEXT, so the BCD path still never widens per pass. Anything
; else (a fraction, past int16, a `%` loop's slots) is stored as it stands.
slot_store:
                ld      a,(FOR_CUR+2)
                cp      2
                jr      z,sst_go            ; a `%` loop: slots stay as given
                ld      a,(FACTYP)
                ld      b,a                 ; B = the type = the byte count (4 / 8)
                and     3                   ; 2 = an int16 (kept); 3 = a string --
                jr      nz,sst_go           ; neither is a float to test
                push    hl
                ld      hl,FAC
                call    nx_pki              ; an exact int16 in a single/double?
                pop     hl
                jr      c,sst_go            ; no: stored as it stands
                ld      a,2                 ; yes: an int16 slot, DE = the value
                jr      sst_typ
sst_go:
                ld      a,(FACTYP)
sst_typ:
                ld      (hl),a
                inc     hl
                cp      2
                jr      nz,sst_fac
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ret
sst_fac:
                ex      de,hl
                ld      hl,FAC
                ld      bc,8
                ldir
                ret
; slot_load: HL = slot -> FACTYP, and DE (int16) or FAC. Out: A = the byte whose
; bit 7 is the value's SIGN -- an int16's high byte, a BCD value's lead byte
; (sign + exponent). Clobbers A,BC,DE,HL.
slot_load:
                ld      a,(hl)
                ld      (FACTYP),a
                inc     hl
                cp      2
                jr      nz,sld_fac
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      a,d
                ret
sld_fac:
                ld      de,FAC
                ld      a,(hl)
                ld      bc,8
                ldir
                ret

; --- ex_for: FOR <var> = <init> TO <limit> [STEP <step>] ---------------------
; Create-or-find the loop variable, assign init to it, then push a frame
; [name1][name0][type][limit slot:9][step slot:9][CURLINE:2][resume-ptr:2] (25 B,
; the reference's size -- D-FORFLOAT, sysvars.inc FOR_FRAME) and fall through to
; run the loop body (the statements following FOR). NEXT consults the top frame.
;
; D-FORVAR (docs/spec-basic-forvar.md, 30 of 32 measured rows, BOTH references
; agreeing on all 32): a FOR loop variable is an ordinary scalar variable
; REFERENCE -- any name (2 significant chars), any type suffix, the DEFtbl
; default when there is none -- exactly what LET and READ and INPUT accept. This
; used to consume ONE upcased letter into a 1-byte frame field and store through
; var_get/var_set, the single-letter int16 shim, so `FOR AB=`, `FOR A1=`,
; `FOR A%=` and `FOR INDEX=` were all Syntax error while both references ran the
; loop. It is exactly what exr_lp did before D-READVAR, in the verb that slice
; never re-checked.
;
; 🎯 AND THE TYPE IS IN THE FRAME BECAUSE THE REFERENCES PUT IT IN THE MATCH.
; `FOR A%=1 TO 3` / `NEXT A` is NEXT without FOR on both machines (row n.xtype),
; so the loop variable's identity is (name0, name1, type) and nx_scan compares
; all three. One field then serves both the match and the store: var_find_typed
; keys on exactly that triple.
;
; 🧮 D-LETNEWFIRST (2026-10-19): THE VARIABLE EXISTS BEFORE THE START EXPRESSION
; RUNS. The VG-8020's `FOR I=FRE(0) TO ...` with I new reads 11 B less than zerobas
; did -- I's whole double entry (scratchpad/letnew_run.out) -- so the lookup that
; for_set made after inc_eval moved in front of it, and the store goes through the
; entry (for_set_at). Still ONE lookup; `FOR A$=` is refused before it, so a string
; name is never created here (whether the reference creates A$ before its Type
; mismatch is unmeasured).
; 🔴 `FOR A(1)=` STAYS A SYNTAX ERROR (row f.ary, both references). var_name_key
; walks a name and a suffix and never a subscript, so it leaves HL on the `(`
; and the EQ_TOKEN test below rejects it -- this is a NAME residual, not an
; array one, and tgt_parse (which resolves subscripts) is the wrong tool.
    IF BASICINT_PINS
                                            ; (ex_for lives in basic/fat.asm in the
                                            ; shipping build: with cont_record and
                                            ; ctl_put it REFILLS the 128 B S10.C freed
                                            ; ahead of the pinned $6CF3, 2026-10-15)
    ELSE
ex_for:
                inc     hl                  ; past the FOR token
                call    req_letter          ; D-NGRAM: FOR needs a loop variable
                call    for_name            ; FOR_CUR[0..2] = the key; A = the type
                cp      DEFTBL_STR          ; `FOR A$=` -- and `DEFSTR A` / `FOR AB=` --
                jp      z,type_mismatch_error ; are ERR 13, not ERR 2 (rows f.str and
                                            ; f.defstr, both references). The test is on
                                            ; the RESOLVED type, not on the `$` char,
                                            ; because f.defstr says the rule is.
                push    hl                  ; [cursor]
                call    var_alloc_or_find   ; D-LETNEWFIRST: A = the type, BC = the key
                                            ; (for_name's out) -> HL = the variable's
                                            ; entry, created zero-valued if new, BEFORE
                                            ; the start expression -- FOR's ONE lookup
                jp      nc,fp_runtime_error ; Out of memory, FPERR already set
                ex      (sp),hl             ; HL = cursor, [entry] across '=' + eval
                call    skip_eq             ; '=' -> $EF
                jp      nz,stmt_error
                call    inc_eval            ; DE = initial value, HL advanced
                ex      (sp),hl             ; HL = entry, [cursor]
                call    for_set_at          ; var := initial value, through the entry
                pop     hl
                call    skip_spaces
                cp      TO_TOKEN           ; TO -> $D9
                jp      nz,stmt_error
                call    inc_eval            ; the limit, as a factor leaves it
                push    hl
                ld      hl,FOR_LIM
                call    slot_store          ; D-FORFLOAT: typed, not an int16 tail
                pop     hl
                call    set_factyp2         ; the default STEP below is an int16 1
                call    skip_spaces
                ; D-NXARY: the default is loaded FIRST and eval overwrites it, so the
                ; two arms stop needing a join (-2 B). `ld de,nn` touches no flag, so
                ; the CP below still reads skip_spaces' char. Guarded in both
                ; directions by rows that already exist: f.step (forvar, `STEP -3` ->
                ; `-2 `) and m.step (nxlist, a negative step inside a list) take the
                ; STEP arm, every other loop row takes the default.
                ld      de,1                ; default step = +1
                cp      STEP_TOKEN         ; STEP -> $DC (optional)
                jr      nz,ef_havestep
                call    inc_eval            ; DE = step
ef_havestep:
                push    hl
                ld      hl,FOR_STEP
                call    slot_store          ; the step, typed
                pop     hl
                ld      (FOR_BODY),hl       ; the resume ptr (loop body)
                push    hl                  ; D-NXARY: and it rides the stack to the
                                            ; tail below instead of being re-loaded --
                                            ; ldir does not touch the stack (-1 B)
                ld      de,(CURLINE)
                ld      (FOR_LINE),de       ; CURLINE
                ; D-CTLPOOL: the FOR_STK_END bound test is gone with the array.
                ; ⚠️ FSP IS NOT TOUCHED HERE, and that is the invariant the whole
                ; NEXT walk rests on: the FOR run is [CSP, FSP), so lowering the
                ; frontier IS the push and the run stays contiguous -- nothing but
                ; a FOR frame is ever pushed without also moving FSP.
                ; ⚠️ Row a.dep8 (8 nested loops) is still the row that reaches the
                ; full-pool arm, and K-NA4 is still its knife.
                ld      hl,FOR_FRAME
                call    ctl_alloc
                jp      c,ef_over           ; collided with the variable area
                ex      de,hl               ; DE = the frame base (ldir destination)
                ld      hl,FOR_CUR          ; push the FOR_FRAME-byte frame
                ld      bc,FOR_FRAME
                ldir
                jp      pop_exec            ; HL = loop body -> run it
    ENDIF
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to gosub_stk_over,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
ef_over         equ     gosub_stk_over

; --- ctl_reloc: MOVED to basic/cload.asm (after autoexec_run), 2026-10-19 -------
; 📌 A PIN REFILL: its 42 B, with fch_modes_ptr's 9, take back the 51 B that
; AUTOEXEC.BAS's probe leaving for disk.rom, NAME's fat_mount / fat_find shims
; and FCH_MODE's dead stores freed in front of the $6CF3 pin. Its header and
; every note travelled with it; still page 1, still a TAIL jump from ctl_alloc.

; --- ex_next: NEXT [<var>] ---------------------------------------------------
; Step the loop variable of the matching FOR frame, test against the limit, and
; either resume at the frame's body (loop continues) or pop the frame and run on
; (loop ends). A named NEXT closes any inner frames above the matching one.
;
; D-FORVAR: the name parse is for_name's, shared with ex_for, and the match is a
; THREE-byte compare against FOR_CUR[0..2] -- name0, name1 AND the resolved type.
;
; D-NXLIST (docs/spec-basic-nxlist.md, 25 of 28 measured rows, BOTH references
; agreeing on all 28): NEXT takes a comma-separated LIST, and `NEXT B,A` is
; exactly `NEXT B : NEXT A`. nx_end reads the `,` and re-enters at nx_comma; the
; loop-CONTINUES exit (nx_again) resumes at the frame's own body and never sees
; it, which row m.count measures as ` 6 ` inner-body executions.
; 🎯 THE LIST STATE IS THE SENTINEL'S VALUE, NOT A FLAG AND NOT A RAM CELL.
; nx_scan already treats FOR_CUR+1 = 0 as "match the top frame" and any other
; non-letter as "match nothing", so ex_next parks 0 and nx_comma parks 1 -- and
; that one byte is the whole of `NEXT B,` being NEXT without FOR (m.trail) while
; a bare `NEXT` takes the top frame (c.for).
;
; 🎯 A `$` NEXT NAME IS NOT REJECTED HERE, AND THAT IS A MEASUREMENT.
; `FOR A=1 TO 3` / `NEXT A$` is NEXT without FOR on both references (row
; n.strnx), NOT Type mismatch -- so the symmetry with ex_for's own guard would
; answer the wrong error. var_name_key resolves a `$` name's type to DEFTBL_STR
; (D-FORVAR spec §4.2), a code ex_for refuses to put in a frame, so such a key
; matches nothing, walks the stack out and raises ERR 1 with no guard and no
; bytes spent here at all.
ex_next:
                xor     a                   ; 0 = "a bare NEXT here matches the TOP
                jr      nx_head             ; frame" -- the D-FORVAR sentinel
nx_comma:
                ; D-NXLIST: reached ONLY from nx_end, with HL on the `,` of a list.
                ; 🔴 1 = "a bare NEXT here matches NOTHING". A trailing comma is NOT a
                ; bare NEXT: `FOR A / FOR B / NEXT B,` is NEXT without FOR on both
                ; references (row m.trail) even though an OUTER frame is standing and a
                ; bare NEXT would have closed it. 1 is not 0 and is not a letter, so
                ; nx_scan's 3-byte compare walks the whole stack out and nx_nofor
                ; raises ERR 1 -- the measured answer, for TWO bytes and no guard.
                ; ⚠️ m.trail1 (`FOR B / NEXT B,`) cannot say this: its stack is empty by
                ; then, so a bare NEXT misses there too and agrees for the wrong reason.
                ld      a,1
nx_head:
                ld      (FOR_CUR+1),a       ; park the sentinel; for_name overwrites it
                rst    $10                ; past the NEXT token (or past the `,`)
                call    is_letter
                jr      nc,nx_notletter     ; no variable -- the parked sentinel stands
                ; D-NXARY (docs/spec-basic-nxary.md, 21 rows, BOTH references
                ; agreeing on all 21): a NEXT operand is an ordinary variable
                ; REFERENCE, subscript and all. `NEXT A(1)` is NEXT without FOR but
                ; `NEXT A(99)` is Subscript out of range, so the subscript is
                ; EVALUATED -- and row a.autodim (trap the error, then DIM) reads
                ; Redimensioned array on both references, so the resolve also
                ; AUTO-DIMS. That is exactly tgt_parse's ary_op0_resolve op=0, and
                ; ex_read has reached it from page 1 since D-ARYLV.
                ; ⚠️ THIS COMMENT SAID "its SEVENTH call site" AND THAT WAS WRONG --
                ; D-TGTSPC walked it: EIGHT `call tgt_parse` from NINE statement
                ; surfaces, and the seven was a hand list that forgot to count this
                ; site ([[a-hand-listed-denominator-is-a-scope-claim]]). The table is
                ; in tgt_parse's own header (basic/vars.asm).
                call    var_str_type        ; A = mode (0 num / 1 str); HL NOT advanced.
                                            ; The $ arm must pick the STRING array --
                                            ; a.stroob, and a.str agrees WITHOUT it
                call    tgt_parse_req      ; BC=key, (VARTYPE)=type, (TGT_ADDR)=elem
                                           ; Subscript out of range -- a.oob/a.rank
                call    for_key             ; FOR_CUR[0..2] = (BC, VARTYPE)
                ; ⚠️ AND THAT SENTENCE IS ONLY TRUE ON THE SCALAR PATH. On the array
                ; path BC and (VARTYPE) are whatever ary_op0_resolve left behind, so
                ; the key stored here is not the name's -- it does not matter, because
                ; the store below makes it unmatchable either way, and it is cheaper
                ; to call for_key unconditionally than to branch around it. K-NA2
                ; found this: with the element test cut, `NEXT A$(1)` MATCHES a
                ; `FOR A` frame, which the "its type is DEFTBL_STR" reasoning says is
                ; impossible. The type is not DEFTBL_STR by then.
                ; 🎯 AN ELEMENT MATCHES NO FRAME, AND THE TEST'S OWN ANSWER IS THE
                ; KEY THAT SAYS SO. (TGT_ADDR) is 0 for a scalar and an array element
                ; lives in RAM above $8000, so the high byte is 0 iff scalar -- and
                ; when it is not, it is >= $80, which no is_letter-gated name0 can be.
                ; Same trick as D-FORVAR's DEFTBL_STR and D-NXLIST's list sentinel:
                ; make the key unmatchable and ERR 1 falls out with no error path.
                ld      a,(TGT_ADDR+1)
                or      a
                jr      z,nx_find           ; a scalar keeps its real key
                ld      (FOR_CUR+1),a
                jr      nx_find
; (nx_nofor sits HERE, ahead of nx_find, since D-FORFAST: nx_have's path gate put
; its old site past nx_bound's `jr z` reach, and a `jp z` there would cost every
; NEXT 3 T. Entered only by that `jr`; nothing falls into it.)
nx_nofor:
                pop     hl                  ; discard the saved cursor
                ld      a,$CB               ; "next without for" landmark
                ld      (ERRMARK),a
                ld      a,1                 ; ERR 1: next without for (error-handling S2a)
                jp      raise_error
nx_notletter:
                ; `NEXT 1` is ERR 2 on the reference, not "next without for" -- only a
                ; statement TERMINATOR is a variable-less NEXT. D-NXLIST: this one test
                ; now serves both entries, and the parked sentinel decides what a
                ; terminator MEANS -- `NEXT` takes the top frame, `NEXT B,` matches
                ; nothing. `NEXT B,1` lands on the same ERR 2 as `NEXT 1` (rows n.num
                ; and m.trailnum, both references), which is why this is a shared test
                ; and not a guard in nx_comma.
                or      a
                jr      z,nx_find
                cp      COLON
                jp      nz,stmt_error
                                            ; falls through to nx_find
nx_find:
                push    hl                  ; save the post-NEXT cursor
                ld      hl,(CSP)            ; the NEWEST frame -- the run's top
                jr      nx_bound
nx_miss:
                pop     hl                  ; the frame just rejected
                ld      de,FOR_FRAME
                add     hl,de               ; close it: on to the next-older frame
                ld      (CSP),hl            ; (a named NEXT closes inner frames as
                                            ;  it walks, exactly as before)
nx_bound:
                ; D-NXLIST §4.3: ONE frame-stack bound test, entered from nx_find ("is
                ; the stack empty?") and from nx_miss ("did the walk run out?"). Both
                ; arrive with HL = FSP and both answer NEXT without FOR at zero, so the
                ; test was written twice. The subtraction that answers it also CONTINUES
                ; into the frame-base computation, which is why nx_scan no longer
                ; reloads (FSP).
                ; ⚠️ No cut can separate the two entries any more, so the ROWS do:
                ; n.nofor / n.barenofor take nx_find's (a NEXT with no FOR at all --
                ; a program no D-FORVAR row contains) and m.wrong / m.typex take
                ; nx_miss's.
                ; D-CTLPOOL: the run is [CSP, FSP) and HL walks it from the top.
                ; It is exhausted when HL reaches the FLOOR -- which is the base of
                ; the innermost live GOSUB frame, NOT the base of an array. 🎯 That
                ; is what makes a NEXT stop at a GOSUB frame instead of matching
                ; past it: D-CTLCROSS (spec-basic-trapsvc.md §12), `NEXT without
                ; FOR` on both references, and it costs nothing here -- the same
                ; comparison that used to ask "is the array empty?".
                ld      de,(FSP)
                ld      a,h
                cp      d
                jr      nz,nx_scan
                ld      a,l
                cp      e
                jr      z,nx_nofor          ; reached the floor -> no frame left
nx_scan:
                ld      a,(FOR_CUR+1)       ; name0 (for_name's header: +1, not +0)
                or      a
                jr      z,nx_have           ; bare NEXT accepts the top frame
                push    hl
                ld      de,FOR_CUR
                ld      b,3                 ; name0, name1 AND the TYPE -- row n.xtype:
nx_cmp:                                     ; `FOR A%` / `NEXT A` is NEXT without FOR on
                ld      a,(de)              ; both references, so the type is part of the
                cp      (hl)                ; identity and not just of the store.
                inc     hl                  ; INC touches no flag, so the CP result
                inc     de                  ; survives to the JR below.
                jr      nz,nx_miss
                djnz    nx_cmp
                pop     hl                  ; matched -- falls through to nx_have
nx_have:
                push    hl                  ; save the frame base (for pop / keep)
                ld      de,FOR_CUR          ; work on a copy of the frame
                ld      bc,FOR_FRAME
                ldir
                ; 🐌 D-FORFAST: WHICH PATH. A `%` loop goes straight to the general
                ; path (its int16 slots ARE its arithmetic, unchanged). A float loop
                ; whose two slots are int16 tries nx_fast; one with exactly one int16
                ; slot (`FOR A=1 TO 9 STEP .5`) widens it for good first.
                ld      a,(FOR_CUR+2)
                cp      2
                jr      z,nx_slow           ; a `%` loop
                ld      a,(FOR_LIM)
                cp      2
                ld      a,(FOR_STEP)        ; (ld: the flags are the limit's)
                jr      nz,nx_lnoint
                cp      2
                jr      z,nx_fast           ; both int16: the int path
                call    nx_demote           ; int16 limit, BCD step
                jr      nx_slow
nx_lnoint:
                cp      2
                call    z,nx_demote         ; BCD limit, int16 step
nx_slow:
                ; D-FORFLOAT: `var := var + step`, then `var : limit`, BOTH through the
                ; evaluator's own operators and its LHS-frame protocol (push_lhs_frame
                ; with DE = the lhs, then the rhs as a factor leaves it). Each has
                ; an int16 fast path that PROMOTES to BCD on overflow and a BCD path
                ; for anything fractional or past int16 -- so `STEP .25`, `FOR A=
                ; 56700 TO 56702`, `FOR A=1 TO 32767 STEP 16384` (A ends at 32769) and
                ; a body that makes the variable fractional are all the reference's
                ; (scratchpad/forfloat_probe.py). The int16 `add hl,de` this replaced
                ; wrapped every one of them, and four never ended.
                call    for_get             ; the variable, at its OWN type
                call    push_lhs_frame      ; (DE = an int16 variable's value)
                ld      hl,FOR_STEP
                call    slot_load           ; the step as the rhs; A = its sign byte
                ld      (FOR_SIGN),a
                call    combine_add         ; var + step
                call    for_set_typed       ; stored, and left in FAC/DE as stored
                call    check_expr_errors   ; a `%` loop's Overflow is ERR 6 HERE, on
                                            ; the NEXT line (row edgeint) -- not at the
                                            ; body's first statement, which is where
                                            ; D-STMTPEND's boundary would report it
                call    push_lhs_frame
                ld      hl,FOR_LIM
                call    slot_load
                call    combine_cmp         ; A = 1 <, 2 =, 4 >
                ; D-NXLIST §4.4: the two directions differ ONLY in which verdict ends
                ; the loop. Row m.step (`FOR A=3 TO 1 STEP -1` inside a list) guards
                ; the negative arm in THIS battery.
                ld      b,a
nx_cmpd:                                    ; (nx_fast joins here: B = its verdict)
                ld      a,(FOR_SIGN)
                rla                         ; CF = the step is negative
                ld      a,4                 ; step >= 0: end when value > limit
                jr      nc,nx_dir
                ld      a,1                 ; step <  0: end when value < limit
nx_dir:
                cp      b
                jr      z,nx_end
nx_again:
                pop     hl                  ; frame stays on the stack
                ld      hl,(FOR_LINE)       ; resume at the loop body
                ld      (CURLINE),hl
                ld      hl,(FOR_BODY)
                ld      (RESUMEPTR),hl
                ld      a,1
                ld      (RESUMEFLAG),a
                pop     bc                  ; discard the post-NEXT cursor
                ret
nx_end:
                pop     hl                  ; frame base -> pop the frame
                ld      de,FOR_FRAME        ; D-CTLPOOL: the pool descends, so
                add     hl,de               ; freeing it means raising the frontier
                ld      (CSP),hl
                pop     hl                  ; restore the post-NEXT cursor
                ; D-NXLIST: `NEXT B,A` is `NEXT B : NEXT A`, and THIS is the only path
                ; that may read the comma. The loop-CONTINUES exit (nx_again) resumes at
                ; the frame's own body and never reaches the terminator, which is what
                ; makes the rest of the list invisible while the inner loop runs -- row
                ; m.count reads 3x2 = ` 6 ` inner-body executions and is the only row
                ; that can see a comma test placed one fork too early.
                ; `call skip_spaces` is here for `NEXT B , A` (row m.space).
                call    skip_comma
                jp      z,nx_comma
                jp      exec_stmt           ; run on past NEXT

; --- nx_fast: NEXT of a float loop whose limit and step are int16 (D-FORFAST) --
; 🐌 TIER 5. Since D-FORFLOAT a single/double loop variable went through a BCD
; add, a BCD compare and two variable lookups every pass: an empty `FOR I=1 TO
; 300:NEXT` was 100 TIME ticks against the VG-8020's 24. When the limit and the
; step are exact int16 (slot_store) and the variable's OWN BYTES say it holds an
; exact int16 now, `var + step` and `var : limit` are int16 arithmetic with the
; same answers the BCD path gives -- an exact sum, packed canonically -- so this
; does them on int16s with ONE lookup and writes the packed sum in place.
; 🎯 THE PROOF IS THE VARIABLE ITSELF, NOT A COPY OF IT. The item proposed keeping
; the last stored value in the frame and comparing; reading the variable's packed
; bytes (nx_pki) needs no frame byte at all, and a body that writes an INTEGER
; (`A=A+1`, `A=5`) stays on this path. A body that writes a fraction or a value
; past int16 (row x.body), and a sum that overflows int16 (row x.edge, A = 32769),
; leave through nx_fbail: the slots are widened for good (nx_demote) and the
; general path runs this NEXT from the start -- nothing was written yet.
; The frame is unchanged in size: an int16 slot is [2][lo][hi] + 6 unused bytes,
; the same 9 B a `%` loop's slots always were.
nx_fast:
                ld      bc,(FOR_CUR)
                ld      a,(FOR_CUR+2)
                call    var_find_typed      ; HL = the entry (FOR created it)
                jr      nc,nx_fslow         ; (not found: let the general path say so)
                inc     hl
                inc     hl
                ld      b,(hl)              ; B = the entry's type = its byte count
                inc     hl                  ; HL = its value field
                push    hl                  ; [value field]
                call    nx_pki              ; NC: DE = the variable, an exact int16
                jr      c,nx_fbail
                ld      hl,(FOR_STEP+1)
                ld      a,h
                ld      (FOR_SIGN),a        ; the step's sign byte, as slot_load gives it
                adc     hl,de               ; CF = 0 from nx_pki; P/V = int16 overflow
                jp      pe,nx_fbail         ; x.edge: the BCD path promotes past 32767
                pop     de                  ; DE = the value field
                push    hl                  ; [the new value]
                call    nx_pack             ; written in place, the BCD path's bytes
                pop     hl
                ld      de,(FOR_LIM+1)
                call    cmp16_bits          ; A = 1 <, 2 =, 4 > -- combine_cmp's code
                ld      b,a
                call    set_factyp2         ; as combine_cmp leaves FACTYP
                jr      nx_cmpd
nx_fbail:
                pop     hl                  ; drop [value field]
nx_fslow:
                call    nx_demote
                jp      nx_slow

; --- nx_demote: widen a float loop's int16 slots for good -----------------------
; FOR_CUR's int16 slot(s) become the packed double slot_store wrote before
; D-FORFAST's second step (arga_widen + round_and_finalize, type 8), and both
; slots are written back into the frame in the pool, so the BCD path never widens
; per pass. In: the frame base is the word under our return address (nx_have's
; push). Clobbers A, BC, DE, HL.
nx_demote:
                ld      hl,FOR_LIM
                call    nxd_slot
                ld      hl,FOR_STEP
                call    nxd_slot
                pop     bc                  ; our return address
                pop     hl                  ; HL = the frame base
                push    hl
                push    bc
                ld      de,FOR_LIM - FOR_CUR
                add     hl,de
                ex      de,hl               ; DE = the frame's limit slot
                ld      hl,FOR_LIM
                ld      bc,FOR_LINE - FOR_LIM ; both slots, 18 B
                ldir
                ret
nxd_slot:
                ld      a,(hl)
                cp      2
                ret     nz                  ; already BCD (or not a number)
                push    hl
                call    slot_load           ; FACTYP = 2, DE = the int16
                call    arga_widen          ; -> a packed double, FACTYP = 8
                call    round_and_finalize
                pop     hl
                jp      sst_go              ; [8][FAC] into the slot

; --- nx_pki: HL = a packed single/double, B = its byte count (4 / 8) ----------
; -> NC and DE = its value iff it is an EXACT int16 in -32767..32767 (and every
; digit past the point zero, to the last byte); CF otherwise. Read straight off
; the packed bytes -- [sign + exponent $40 + digits][BCD pairs] -- so no unpack
; into a 15-digit array. -32768 answers CF (the general path handles it).
; Clobbers A, BC, DE, HL.
nx_pki:
                ld      a,(hl)
                ex      de,hl               ; DE -> the lead byte
                ld      hl,0                ; the magnitude
                dec     b                   ; B = the mantissa bytes left to check
                push    af                  ; [lead] -- its bit 7 is the sign
                or      a
                jr      z,npi_tail          ; zero: every mantissa byte must be 0
                and     $7F
                sub     $41                 ; A = digits before the point - 1
                cp      5
                jr      nc,npi_no           ; |x| < 1 or >= 100000
                ld      c,a                 ; C = digits still to take - 1
                cp      4
                jr      nz,npi_byte
                inc     de                  ; five digits: the first must be <= 3, so
                ld      a,(de)              ; the magnitude stays below 40000 and
                dec     de                  ; never wraps 16 bits
                cp      $40
                jr      nc,npi_no
npi_byte:
                inc     de
                dec     b
                ld      a,(de)
                rrca
                rrca
                rrca
                rrca
                call    npi_x10             ; the high digit
                dec     c
                jp      m,npi_lowz          ; that was the last: the low one must be 0
                ld      a,(de)
                call    npi_x10             ; the low digit
                dec     c
                jp      p,npi_byte
                jr      npi_tail
npi_lowz:
                ld      a,(de)
                and     $0F
                jr      nz,npi_no
npi_tail:
                inc     b
                dec     b
                jr      z,npi_end
npi_tlp:
                inc     de
                ld      a,(de)
                or      a
                jr      nz,npi_no
                djnz    npi_tlp
npi_end:
                bit     7,h
                jr      nz,npi_no           ; 32768..39999: not an int16
                ex      de,hl               ; DE = the magnitude
                pop     af
                rla                         ; CF = the sign
                call    c,neg_de
                or      a                   ; NC: exact
                ret
npi_no:
                pop     af
                scf
                ret
; HL = HL * 10 + (A & 15). Keeps BC, DE.
npi_x10:
                and     $0F
                push    de
                ld      d,h
                ld      e,l
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,a
                ld      d,0
                add     hl,de
                pop     de
                ret

; --- nx_pack: HL = an int16, DE -> a variable's value field -------------------
; Writes [lead][3 BCD pairs] -- what round_and_finalize / round_single_and_pack
; pack for the same exact value, single or double alike (an int16 has at most
; five digits; a double's last four bytes are already 0, nx_pki said so).
; Clobbers A, BC, DE, HL.
nx_pack:
                ld      a,h
                or      l
                jr      z,npk_zero
                push    de                  ; [dest]
                ld      a,h
                and     $80
                push    af                  ; [sign]
                jr      z,npk_pos
                ex      de,hl
                call    neg_de_hl           ; HL = |value| (32768 stays 32768)
npk_pos:
                ld      de,-10000
                call    npk_sub
                ld      c,a                 ; C = d4
                ld      de,-1000
                call    npk_sub
                add     a,a
                add     a,a
                add     a,a
                add     a,a
                ld      b,a
                ld      de,-100
                call    npk_sub
                or      b
                ld      b,a                 ; B = d3 d2
                ld      de,-10
                call    npk_sub
                add     a,a
                add     a,a
                add     a,a
                add     a,a
                or      l                   ; A = d1 d0
                ld      e,$46               ; $40 + six nibbles: 0 d4 d3 d2 d1 d0
npk_byte:
                inc     c
                dec     c
                jr      nz,npk_nib
                ld      c,b                 ; a zero byte in front: shift by a byte
                ld      b,a
                xor     a
                dec     e
                dec     e
                jr      npk_byte
npk_nib:
                ld      d,a
                ld      a,c
                cp      $10
                ld      a,d
                jr      nc,npk_put          ; the leading digit is in the high nibble
                ld      d,4                 ; else shift by a nibble
npk_shl:
                add     a,a
                rl      b
                rl      c
                dec     d
                jr      nz,npk_shl
                dec     e
npk_put:
                ld      d,a                 ; D = the third pair
                pop     af                  ; A = the sign
                or      e                   ; the lead byte
                pop     hl                  ; HL = dest
                ld      (hl),a
                inc     hl
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (hl),d
                ret
npk_zero:
                ex      de,hl               ; A = 0: the canonical zero, all four bytes
                ld      b,4
npkz_lp:
                ld      (hl),a
                inc     hl
                djnz    npkz_lp
                ret
; A = how many times -DE fits in HL (one decimal digit); HL reduced. Keeps BC.
npk_sub:
                ld      a,-1
npks_lp:
                inc     a
                add     hl,de
                jr      c,npks_lp
                sbc     hl,de               ; CF = 0 here: undo the last add
                ret

err_stack       equ     err_mem             ; share sl_oom's "out of memory" (D-2
                                            ; self-funding — the string bytes are
                                            ; identical). Saves 15 B in the page-1
                                            ; budget for the run-mode " in <line>"
                                            ; suffix (docs/spec-basic-error-handling.md S1 D-2).
; D-MSGMIGRATE: err_noret / err_nofor are sub-ROM-hosted (em_noret, em_nofor;
; ERRFLG 3 / 1). Both were reached ONLY through err_msgtab, so the migration is
; two table operands. They were also two of MSGESC_WITHOUT's three users -- the
; third, err_resume_noerr, migrated too, which is what killed that phrase.

; --- ex_read: READ <var> [, <var> ...] ---------------------------------------
; Fill each variable from the next DATA item. DATA items are stored as verbatim
; ASCII (oracle), so read_one_value parses ASCII from the program text.
;
; D-READVAR (docs/spec-basic-readvar.md, 22 of 24 measured rows): a READ target is
; an ordinary VARIABLE REFERENCE -- any name, any type suffix, the DEFtbl default
; when there is none -- exactly what LET and INPUT accept. This used to consume ONE
; letter into READVAR and store through var_get/var_set, the single-letter int16
; shim, so `READ AB` / `READ A%` / `READ A$` were all Syntax error while both
; references read the item. The shape below IS ex_input's (basic/input.asm
; inpc_vloop/inpc_vstr/inpc_after), routine for routine; the twin is the RIGHT
; shape rather than a convenient one, because ex_input already carries the sub/main
; split this needs -- STRSCR is filled where the bytes are and wrapped where
; strscr_desc lives.
;
; 🎯 var_str_type ALREADY RETURNS THE ITEM MODE. It answers 1 for a string target
; and 0 for a numeric one, which is RDV_MODE's encoding, so the branch is stored
; once and re-read after the DATA read instead of being decided twice.
;
; D-ARYLV (docs/spec-basic-arylv.md, 18 more measured rows): and an ARRAY ELEMENT
; is a target too -- any rank, any expression per subscript, at any position in
; the list. The three tgt_* helpers (basic/vars.asm) are shared verbatim with
; input.asm's three sites; this one differs only in reading its value from a DATA
; item instead of a console field, which is why the SHARED thing is the target
; parse and the two stores, and not a single "READ/INPUT" head.
ex_read:
                inc     hl                  ; past the READ token
exr_lp:
                call    req_letter          ; D-NGRAM: READ needs a variable
                call    var_str_type        ; A = 1 iff the name carries a '$' (or its
                ld      (RDV_MODE),a        ; DEFtbl default is a string) -- and that
                                            ; is exactly the DATA-item read mode
                call    tgt_parse_req      ; D-ARYLV: BC = key, HL past the whole
                                            ; reference, (TGT_ADDR) = element address or
                                            ; 0; (VARTYPE) = the resolved type (F3).
                                            ; A already holds the mode tgt_parse wants.
                                           ; a bad subscript aborts with the ARRAY
                                            ; engine's own error (`READ A(9)` on
                                            ; `DIM A(3)` is Subscript out of range on
                                            ; both references, NOT Syntax error --
                                            ; routing this to stmt_error would answer
                                            ; what the tree said BEFORE the fix, so the
                                            ; row would read as untouched, spec §5.3)
                push    bc                  ; [stack: key]
                push    hl                  ; [stack: key, exec cursor]
                call    read_one_value      ; A = status; STRSCR = the item
                dec     a
                jr      nz,exr_bad          ; 0 -> out of data
                pop     hl                  ; exec cursor
                pop     bc                  ; key
                push    hl                  ; guard the cursor across the store
                ld      a,(RDV_MODE)
                or      a
                jr      nz,exr_str
                push    bc                  ; the key (inp_num clobbers BC)
                call    inp_num             ; D-READFLT: VAL's parse of the item --
                pop     bc                  ; `1.5`, `2E3`, `&H10`, `&B101`, 40000;
                jr      c,exr_nan           ; only blanks may follow the number
                call    inp_store           ; int16 or float -> the target, coerced
                                            ; (D-ARYLV: a scalar or the resolved ELEMENT)
                jr      exr_chk             ; `99999` into A% is Overflow: the check below
exr_str:
                call    tgt_store_ref       ; D-READREF: var$[key] -> the DATA text itself
                                            ; (was tgt_store_str -- D-ARYLV: var$[key] = the DATA item's bytes,
                                            ; or the resolved element (op=3 COPY_STR)
exr_chk:
                pop     hl
                ; The same arrays slice-4c (§7.3) hazard ex_input guards: a
                ; scalar-CHAIN OOM in str_set_key sets FPERR without aborting on
                ; its own, and would otherwise be cleared at the next exec_stmt.
                ; ⚠️ D-STMTPEND: the boundary now REPORTS a live code rather than
                ; clearing it, so this check decides WHERE the abort lands, not
                ; whether there is one (spec-basic-stmtpend.md §6.3).
                ; Both guard words are already popped, so this is the SP-clean
                ; site variant (TMISMATCH is always 0 -- READ never sets it).
                ; D-READFLT: the numeric store joins here, for its Overflow.
                call    check_expr_errors
exr_after:
                call    skip_comma          ; more variables to fill?
                jr      z,exr_more
                jp      exec_stmt           ; READ statement done
exr_more:
                inc     hl
                jr      exr_lp
exr_nan:                                    ; D-READFLT: the item is not a number.
                ld      c,a                 ; C = inp_num's A: VAL's code, or 0
                ld      hl,(RDV_VAL)        ; Leave it UNREAD, as the VG-8020 does: a
                ld      (DATAPTR),hl        ; second READ refuses it again (`again`
                                            ; row).
                ; 🔴 D-READERL: AND ITS LINE. This said "a refused item is never
                ; consumed, so DATALINE cannot be wrong for it" -- false: the
                ; tenant's seek for the NEXT item had already moved DATALINE on
                ; (to the program's end, traced: scratchpad/readerl_trace.out), so
                ; the next READ after this one followed a dead link. The tenant
                ; keeps the item's own line in RDV_LINE.
                ld      hl,(RDV_LINE)
                ld      (DATALINE),hl       ; HL stays the item's line for exr_syn
                ld      a,1
                ld      (DATASTATE),a
                ld      a,c
                cp      5                   ; VAL's code 5: `1E99` -> Overflow (6)
                jr      nz,exr_syn          ; `12X`, `"5"`, `HELLO` -> ERR 2 on both
                ld      a,6
                jp      raise_error
; exr_syn -- D-READERL (2026-10-10): a DATA item that is not a number is a Syntax
; error IN THE DATA LINE on the VG-8020 -- ERL, `Syntax error in 20`, and `LIST .`
; all name it, from a program and from the prompt alike (`READ A` typed: `Syntax
; error in 20`, ERL 20) -- while RESUME NEXT still goes on after the READ
; (scratchpad/readerl_run.out). So ERL and `.` come from the item's line (HL, from
; RDV_LINE above) and NOT from record_errline, and the
; raise enters at rerr_msg, past it -- the trap capture (CURLINE / SAVTXT, the
; resume point) is untouched. A pending numeric fault still outranks it, as in
; stmt_error; check_fperr_only returns only with FPERR already 0.
exr_syn:
                call    check_fperr_only    ; keeps HL: the DATA line's link field ...
                inc     hl
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; ... DE = its line number
                ld      (ERRLIN),de
                ld      (DOT),de
                ld      a,2                 ; Syntax error
                ld      (ERRFLG),a
                jp      rerr_msg
exr_bad:
                pop     hl                  ; discard the exec cursor and the key
                pop     hl                  ; (balance the stack)
                ld      a,$CA               ; "out of data" landmark
                ld      (ERRMARK),a
                ld      a,4                 ; ERR 4: out of data (error-handling S2a)
                jp      raise_error
; D-MSGMIGRATE: err_data is sub-ROM-hosted (em_data, ERRFLG 4). MSGESC_UTOF
; survived that move with three low-region users (err_subscript, err_mem_arr,
; err_out_of_str) -- until DT-6 (space plan B-9, 2026-10-05) retired every phrase escape; those three
; are plain text now.

; --- ex_restore: RESTORE [<line>] --------------------------------------------
; Reset the DATA cursor to the program start, or to a given line. The optional
; line arrives as the $0E line-number reference (branch_lineno tokenises it).
ex_restore:
                rst    $10                ; past the RESTORE token
                cp      LINENO_TOKEN        ; $0E,<lineno LE> -> restore to a line. NOT $0D:
                                            ; the VG-8020 raises 8 for a RESTORE pointer
                                            ; (D-BASICROM gate, case lptr's first run)
                jr      z,ers_line
                ; D-DATACOLON: this arm used to be an unconditional `ret` under
                ; "nothing else on a bare RESTORE word" -- and the dispatcher
                ; enters handlers by push/ret, so that `ret` ended the whole
                ; LINE: `RESTORE:C=9` left C unset (refs 9, here 0), and
                ; `READ A:RESTORE:READ B` never read B (refs 2, here 1). The
                ; bare arm now falls back into the statement loop; junk after
                ; the word (`RESTORE X`) is RESTORE-to-nothing on both
                ; references -- ERR 8, not ERR 2 and not silence -- so it takes
                ; the line path with BC=0 and fails the lookup there.
                or      a
                jr      z,ers_bare          ; end of line
                cp      COLON
                jr      z,ers_bare          ; ':' -> the next statement runs
                ld      bc,0                ; junk -> RESTORE to line 0: undefined
                push    hl                  ; (unless a line 0 exists, as on the
                jr      ers_find            ; references)
ers_bare:
                push    hl                  ; keep the exec cursor -- the old code
                ld      hl,(TXTTAB)          ; clobbered HL because it never came back
                ; 🎯 D-CARVE3: canonical RESTORE tail -- pin the line, clear the
                ; DATA state, resume. Both RESTORE arms end this way.
restore_done:
                ld      (RESTORE_LINE),hl
                xor     a
                ld      (DATASTATE),a
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt
ers_line:
                call    lref_bc             ; BC = the target line ($0E only reaches here)
                push    hl
ers_find:
                call    find_line_bc        ; CF set + HL = line link-field
                jr      nc,ers_undef
                jr      restore_done        ; D-CARVE3 (-8 B, main page 1)
ers_undef:
                pop     hl                  ; balance the stack
                jp      ex_goto_undef       ; reuse "undefined line"

; --- READ/DATA value engine (read_one_value / data_seek / data_parse_int) ---
; Carved out to a PAGE-0 sub-ROM tenant to fund graphics G7
; (docs/spec-eviction-g7-space.md). The body itself is basic/readdata-body.inc.
; Resident stub: CALSLT the tenant, then rebuild the (A, DE) contract from the
; RDV_ST/RDV_VAL cells -- registers cannot ride back through subrom_call.
; in:  (RDV_MODE) 0 = numeric / 1 = string (the caller sets it).
; out: A = 0 out of data / 1 item read / 2 the item is not a number (D-READVAR);
;      DE = the value in numeric mode, STRSCR = [len][bytes] in string mode.
; 📌 read_one_value's body is a PIN REFILL in basic/files.asm (beside fch_select)
; since S10.E (2026-10-19): it refills bytes the channel switch freed in front of
; $72D4. (Its `ld a,0`, not `xor a`, keeps subrom_call's CF: defensive -- no
; tenant -> out of data.)

; --- ex_on: ON <expr> GOTO/GOSUB <line>[,<line>...] -------------------------
; Evaluates expr (1-based index N). Finds the Nth branch target in the
; comma-separated $0E list and branches (GOTO) or calls (GOSUB) to it.
; N=0 or N > count of targets falls through to the next statement.
; Source: public MSX-BASIC language reference (ON…GOTO/GOSUB semantics).
ex_on:
                rst    $10                ; past ON_TOKEN
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
ex_on_expr:                                 ; ON <expr> GOTO/GOSUB -- the ordinary form
                call    eval                ; DE = N (1-based index), HL past expression
                call    get_byte_arg        ; D-F2-2 stage B: ON's selector is a byte 0..255
                                            ; (>int16 ERR 6, 256.. ERR 5); DE=N, D=0 for
                                            ; eon_seek_nth. ON 0 = valid no-branch (falls thru).
                call    skip_spaces
                cp      GOTO_TOKEN
                jr      z,eon_goto
                cp      GOSUB_TOKEN
                jr      z,eon_gosub
                jp      stmt_error

eon_goto:
                inc     hl                  ; past GOTO token
                call    eon_seek_nth        ; BC = line number, HL past list; CF set if found
                jr      nc,eon_notfound     ; D-ONLIST: 0 B, the same instruction
                jr      goto_take_bc        ; BC = target; arm GOTOTGT/GOTOFLAG
                                            ; (both `jr`: 3 B carved for D-UPSTR here
                                            ; and at eon_gosub's copy below)

; eon_gosub (repack: via gosub_push, sharing gosub_stk_over)
eon_notfound:                               ; D-ONLIST: eon_seek_nth found no Nth
                                            ; entry. Z = the list legitimately ran
                                            ; out; NZ = the sought position held
                                            ; something that is not a lineno.
                                            ; 🔴 THE RAISE LIVES HERE, NOT INSIDE
                                            ; eon_seek_nth, AND THAT IS THE POINT:
                                            ; the abort chain PRINTS AND RETURNS
                                            ; without resetting SP, so it is only
                                            ; correct at the statement handler's
                                            ; own depth. eon_seek_nth is one
                                            ; `call` deeper, and a `jp
                                            ; stmt_error` from in there would land
                                            ; control back inside eon_seek_nth's
                                            ; caller instead of the run loop --
                                            ; the LOCATE/WIDTH failure shape.
                jp      nz,stmt_error       ; malformed -> ERR 2 (trappable)
                jp      exec_stmt           ; legal -> fall through, as before
eon_gosub:
                inc     hl                  ; past GOSUB token
                call    eon_seek_nth        ; BC = line number, HL past list; CF set if found
                jr      nc,eon_notfound     ; D-ONLIST: 0 B, the same instruction
                call    skip_stmt_tail      ; D-FLOWTAIL: resume after the STATEMENT --
                                            ; `ON 1 GOSUB 100 ZZ` diverged exactly as
                                            ; the plain GOSUB above did
                call    gosub_push          ; push [CURLINE][resume=HL]; BC kept; CF=full
                jp      c,gosub_stk_over    ; jp (not jr): gosub_stk_over is far back
; --- goto_take_bc: BC names the target line -- find it and ARM the jump ------
; (D-NGRAM5.) The identical 15 B run stood at THREE sites: `ex_gosub`, `eon_goto`
; and this one. The other two now `jp` here; this site keeps the code and simply
; LABELS it, so the third jump costs nothing: -24 B of page 1.
;   in:  BC = the target line number, any pushed frame already made.
;   out: GOTOTGT/GOTOFLAG armed, returns to the statement driver. Does NOT return
;        when the line does not exist -- ex_goto_undef owns that exit.
; ⚠️ THIS IS NOW A SHARED TAIL, AND A SHARED TAIL IS A LABEL, NOT A DECISION: a
; change sited here serves ALL THREE verbs (GOSUB, ON..GOTO, ON..GOSUB). Anything
; that should apply to only one of them belongs at that site, above the jump.
; 🔴 AND IT WAS THE SAME ROUTINE TWICE. `goto_resolve` (basic/interp.asm) is this
; code instruction for instruction -- `find_line_bc`, the undefined-line exit, the
; GOTOTGT/GOTOFLAG arm, `ret` -- differing only in `jr nc` where reach allowed it.
; Two labels, one behaviour, 15 B and 14 B, and D-NGRAM5 had already carved THIS
; site once without anyone noticing the other copy.
; 🎯 FOUND BY COUNTING `ret`s, NOT BY LOOKING FOR DUPLICATES: D-JUMPLOOP lists every
; `ret` that leaves `exec`, and both ends appeared in it three lines apart in shape.
; A dup-span sweep could not see it -- the bodies differ in one opcode.
goto_take_bc:
                jp      goto_resolve

; --- skipsp_test / diskslot_test: two parser/disk idioms, at 25 sites -------
; `call skip_spaces`+`or a` stood at SEVENTEEN sites and
; `ld a,(DISKSLOT_OK)`+`or a` at EIGHT, 4 B each. Both are flag-transparent by
; construction -- the `or a` IS the result and `ret` writes no flag -- so every
; site branches on exactly what it did before, with A unchanged too.
; 🔴 SITED AFTER AN UNCONDITIONAL `jp`, and that is not decoration. A helper
; spliced where the instruction above can FALL INTO it is a silent disaster:
; errmark_expr was put immediately before `raise_error_hl`, which `rerr_msg`
; falls through into, and every untrapped error then ran the helper and `ret`ed
; instead of aborting. It cost a whole battery to find.
; ⚠️ 17 T per call, on parse and disk-entry paths only: not one of the 25 is in
; expr.asm or float-arith.asm, which is where the TIER 4 speed item lives.
    IF BASICINT_PINS
                                            ; (diskslot_test lives in basic/files.asm in
                                            ; the shipping build: S10.C's $73AC refill)
    ELSE
diskslot_test:
                ld      a,(DISKSLOT_OK)
                or      a
                ret
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
                call    is_lref             ; $0E / $0D expected (D-BASICROM)
                jr      nz,esn_notlineno    ; D-ONLIST: NOT simply "list shorter
                                            ; than N" -- that comment was true for
                                            ; one of this jump's two entry
                                            ; conditions and false for the other
                call    lref_bc             ; BC = this entry's line number, HL past it
                dec     de
                ld      a,d
                or      e
                jr      z,esn_found         ; DE == 0 -> this was the Nth entry
                ; still counting: expect a comma before the next entry
                call    skip_comma
                jr      nz,esn_nocf         ; no comma -> list shorter than N
                inc     hl                  ; past comma
                jr      esn_p1
; Phase 2: Nth entry found (BC = line number). Scan past any remaining entries.
esn_found:
                push    bc                  ; guard the found line number
esn_p2:
                call    skip_comma
                jr      nz,esn_ok           ; no more commas -> HL past the list
                rst    $10                ; past comma
                call    is_lref
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
                call    is_lref
                jr      nz,esn_nocf         ; no entries at all
                inc     hl
                inc     hl
                inc     hl                  ; skip first $0E,lo,hi
esn_scan_lp:
                call    skip_comma
                jr      nz,esn_nocf         ; no more commas -> done
                rst    $10                ; past comma
                call    is_lref
                jr      nz,esn_nocf
                inc     hl
                inc     hl
                inc     hl                  ; skip $0E,lo,hi
                jr      esn_scan_lp
; --- D-ONLIST (docs/spec-basic-onlist.md): the Nth position, and ONLY it -----
; `ON 1 GOTO` is Syntax error on both references and `ON 5 GOTO` is SILENT --
; and in this routine those are the SAME INSTRUCTION, esn_p1's `cp
; LINENO_TOKEN` on its first iteration. So the reference is not validating the
; target list at all:
;
;   🎯 IT DEMANDS A LINE NUMBER ONLY AT THE POSITION IT IS ABOUT TO USE.
;      Syntax error iff the Nth position is REACHED and what is there is not a
;      lineno. N=0 never looks; a list that ends before position N never looks.
;
; Measured over 15 rows x 3 machines, references unanimous. The rows that pin it
; are `ON 2 GOTO 40,` (ERR 2 -- the consumed comma COMMITS the reference to
; position 2) against `ON 5 GOTO 40,` (SILENT -- the same comma commits nothing,
; because position 5 is unreachable).
;
; 🔴 AND THE WIDE RULE WOULD HAVE SHIPPED THREE REGRESSIONS. The draft this
; replaces raised at every malformed-looking site -- esn_scan's `no entries at
; all`, and esn_ok's two "malformed: stop here" jumps. All three are measured
; SILENT on both references, and zerobas was ALREADY RIGHT at each: `ON 0 GOTO`,
; `ON 1 GOTO 40,` and `ON 1 GOTO 40,X` complete on all three machines. Reading
; the jump sites said four of seven were errors; the machines say ONE.
;
; DE has not yet been decremented for the entry esn_p1 was about to read, so
; DE==1 is exactly "this is the one being sought". DE is dead on both exits.
esn_notlineno:
                dec     de
                ld      a,d
                or      e
                jr      nz,esn_nocf         ; still counting -> the list simply
                                            ; ENDS before position N: LEGAL, and
                                            ; the caller falls through silently
; 🔴 esn_bad IS A LABEL, NOT A REUSABLE RAISER, and its own knives are why it
; says so. K-OL3/K-OL4 pointed two OTHER sites at esn_notlineno above and moved
; the wrong row / no row at all: that entry runs `dec de` on a DE that is
; already 0 there, wraps to $FFFF, and lands back on the LEGAL exit. The
; discriminator is coupled to esn_p1's state and to nothing else. Anything that
; wants this verdict from another site must jump HERE, past the test.
esn_bad:
                or      $FF                 ; sought position, no lineno -> CF
                ret                         ; clear + NZ = malformed (eon_notfound)
esn_nocf:
                xor     a                   ; CF clear + Z = a legal not-found.
                ret                         ; (was `or a`; same 1 byte, and now
                                            ; the Z flag carries the verdict)

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
ex_on_error:
                rst    $10                ; past ERROR_TOKEN
                cp      GOTO_TOKEN          ; syntax: ON ERROR *GOTO* <line>
                jp      nz,stmt_error
                rst    $10                ; past GOTO_TOKEN
                ; --- D-ONERRGO: THE OPERAND STAGE HAS THREE OUTCOMES, MEASURED
                ; --- ON BOTH REFERENCES (docs/spec-basic-onerrgo.md).
                ; This used to be a bare `call req_lineno`, i.e. ONE outcome for
                ; every non-`$0E` byte: trapped ERR 2. The references split it:
                ;   * NO operand (end of line, or `:`) is not an error at all --
                ;     it is EXACTLY `ON ERROR GOTO 0`. Measured three ways: it
                ;     DISARMS (h.bare == h.off, `Illegal function call in 40`),
                ;     it RE-RAISES inside an active handler (i.bare == i.zero),
                ;     and the statement after it on the same line still runs
                ;     (j.colonrun -> `[B= 7 ]`). So it routes to oe_disable and
                ;     inherits D-ONERR0's re-raise -- which is why that had to be
                ;     measured and not assumed.
                ;   * an operand that IS present but is not a line number raises
                ;     `Syntax error` UNTRAPPED (oe_badop below).
                ;   * a line number keeps the old path, undefined-line included
                ;     (a.undef traps ERR 8 on all three sides, unchanged).
                ; 🔴 THE FIRST DRAFT OF THIS FIX HAD ONLY THE cp LINENO_TOKEN TEST
                ; and would have made `ON ERROR GOTO` an untrapped Syntax error --
                ; a NEW divergence, in a row the old code got right by accident.
                ; [[two-rules-that-coincide-on-every-row-you-have]]
                or      a
                jr      z,oe_disable        ; `ON ERROR GOTO` <eol>  == GOTO 0
                cp      COLON
                jr      z,oe_disable        ; `ON ERROR GOTO :`      == GOTO 0
                call    is_lref
                jr      nz,oe_badop         ; present, not a line number (D-SCRBAUD
                                            ; carve: jr range, per jr_mapper.py)
                call    req_lineno          ; D-NGRAM10: $0E,lo,hi expected (GOTO's
                                            ; own operand shape) -- BC = the line,
                                            ; HL past the $0E operand
                ld      a,b
                or      c
                jr      z,oe_disable        ; GOTO 0 -> disable
                push    hl                  ; [cursor] guard across find_line_bc (which
                                            ; clobbers HL, returning the match in it)
                call    find_line_bc        ; CF set + HL = link addr if found
                jp     nc,oe_undef
                ld      (ONELIN),hl         ; ONELIN := the handler line's LINK address
                                            ; (find_line_bc's return convention -- exactly
                                            ; what raise_error's trap / rp_goto expect)
                pop     hl                  ; HL = cursor again (ON ERROR GOTO does not
                                            ; redirect flow -- continue the same line)
                jp      exec_stmt
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to ers_undef,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
oe_undef        equ     ers_undef
; --- oe_badop: the operand is PRESENT and is not a line number ---------------
; `ON ERROR GOTO A` / `ON ERROR GOTO "X"` -> `Syntax error in <line>`, UNTRAPPED,
; with ERR/ERL set to 2 / the erroring line (measured: e.errl reads `[ 2  30 ]`
; on both references, against an e.ctl of `[ 5  20 ]` for an ordinary abort --
; which is why record_errline is called and not skipped).
;
; 🎯 "UNTRAPPED" IS EXPRESSIBLE AND ALREADY WAS. TODO.md filed this as needing
; "a raise that skips the trap check, which is not what stmt_error does" -- but
; raise_error's own tail is already split: raise_error_hl makes the trap
; decision and ra_abort is the abort body BELOW it. Entering at ra_abort with
; the message in HL is the untrapped raise, and it is the same four steps
; raise_error_forced (ERR 22) has always used.
oe_badop:
                ld      a,2
                ld      (ERRFLG),a
                call    record_errline      ; ERRLIN := this line (ERL reads 30)
                ld      hl,err_syntax       ; err_msgtab entry 2, low-region pool
                jp      ra_abort            ; PAST raise_error_hl -> never traps

oe_disable:
                ld      de,0                ; (DE, not HL -- HL still holds the cursor
                ld      (ONELIN),de         ; to continue the line with)
                ; --- D-ONERR0: INSIDE AN ACTIVE HANDLER, THIS RE-RAISES ---------
                ; docs/spec-basic-onerr0.md; measured on both references, 23 rows,
                ; docs/onerr0-msx1-characterization.md. `ON ERROR GOTO 0` executed
                ; while ONEFLG is set does NOT merely disarm and run on: it puts
                ; the erroring statement's context back and re-raises the error
                ; that entered the handler, untrapped (ONELIN is 0 by the two
                ; instructions above, so raise_error_hl can only abort).
                ; 🎯 THE TEST IS ON `GOTO 0` AND NOT ON `ON ERROR`, and that is
                ; MEASURED, not assumed: `ON ERROR GOTO <n>` inside a handler
                ; RE-ARMS and runs on, identically on all three sides
                ; (characterization row `r.rearm`). Disarming is special.
                ld      a,(ONEFLG)
                or      a
                jr      nz,oe_reraise
                ; ONEFLG was ALREADY 0 on this arm, so the store that used to
                ; stand here was writing 0 over 0. Deleting it is a 3-byte carve
                ; the re-raise test pays for itself with, and it is only visible
                ; once the two states are split (the old single path had to
                ; clear the flag because it served both).
                jp      exec_stmt
oe_reraise:
                ; res_ctx (basic/interp.asm) is RESUME's own leave-the-handler
                ; restore: ONEFLG:=0, CURLINE:=the erroring statement's line,
                ; HL:=its text pointer. The re-raise wants exactly that context
                ; and then an ABORT instead of a resume -- so SAVTXT gets the
                ; pointer (ra_abort hands it to cont_record, and a CONT after
                ; the re-raise re-raises at the ERRORING statement: row `k.cont`)
                ; and rerr_msg raises ERRFLG's code without re-recording ERRLIN.
                ; 🔴 NOT "disarm, then RESUME". That design is 14 bytes cheaper
                ; -- it would get CURLINE, SAVTXT and even DIRECTF back for free
                ; by handing the statement to the run loop -- and row `r.reexec`
                ; REFUTES it: `PRINT"[X]";ASC("")` prints `[X]` ONCE on both
                ; references, so the reference does not re-execute the statement
                ; it re-raises from. The row exists only because the cheap design
                ; was drafted first (spec §4.1).
                call    res_ctx
                ld      (SAVTXT),hl
                ; D-LOCARG: and the MODE too, derived from the CURLINE res_ctx
                ; just restored. rerr_msg does not pass rp_exec, so without this
                ; the report carries the RE-RAISING statement's mode and the
                ; " in <line>" suffix is wrong in one direction or the other --
                ; see derive_directf's header for the two rows and why a constant
                ; cannot serve. Clobbers A only; HL is already spent.
                call    derive_directf
                jp      rerr_msg

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
                call    req_gosub           ; D-NGRAM18
                                            ; raises, and raise_error resets SP)
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
; D-DUPSPAN: an ALIAS, not a second copy -- byte-identical to play.asm's
; pl_syntax, which is the family's canonical tail because its four callers
; are the only ones close enough to reach it with `jr`. The NAME and every
; call site survive; un-alias here for a distinct face and nothing moves.
trap_syntax     equ     pl_syntax   ; ERR 2 (malformed trap statement)

; --- onoff_decode: MOVED to basic/files.asm (where fch_modes_ptr was), 2026-10-19
; 📌 A PIN REFILL: its 24 B take back what fch_modes_ptr's move and FCH_MODE's
; dead stores / re-reads freed in front of the $72D4 pin. Header and contract
; travelled with it.

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
                call    is_lref             ; $0E / $0D (D-BASICROM)
                jr      z,tll_have
                or      a                   ; not a line ref -> CF = 0
                ret
tll_have:
                call    lref_bc             ; BC = the handler line, HL past it
                push    hl                  ; guard cursor across find_line_bc
                call    find_line_bc        ; CF set + HL = link addr if found
                jp     nc,tll_undef
                ex      de,hl               ; DE = handler LINK
                pop     hl                  ; HL = cursor
                scf
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to ers_undef,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
tll_undef       equ     ers_undef

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
; (iv_seq, the spelling above's `ld de,iv_seq` reads, lives in basic/graphics.asm
; since D-WSZERO S14g-d: it refills bytes freed in front of the $6CF3 pin)

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
                call    trap_pend   ; make check_traps look once more
ei_done:
                jp      pop_exec            ; continue the line (`INTERVAL ON:...`)

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
                call    skip_eq             ; D-SKIPEQ: skip_spaces + cp EQ_TOKEN
                jp      nz,trap_syntax      ; `ON INTERVAL GOSUB 800` -> ERR 2
                inc     hl
                call    eval_addr           ; DE = n (checked address domain)
                call    check_fperr_only    ; outside -32768..65535 -> Overflow (ERR 6)
                ld      a,d
                or      e
                jp      z,eoi_err5          ; ON INTERVAL=0 -> Illegal function call
                ld      (ZINTVAL),de        ; the period...
                ld      (ZINTCNT),de        ; ...and RELOAD the live counter: arming
                                            ; restarts the period (§1.4 P2, measured --
                                            ; re-arming mid-run moves the next fire)
                call    req_gosub           ; D-NGRAM18
                call    skip_spaces
                ld      de,ZTRAP+ZTI_INTERVAL*ZTRAP_ENTSZ+1
                push    de                  ; eos_line pops it as the store target
                jp      eos_line            ; shared tail: optional line ref, else CLEAR
                                            ; the slot (§1.6 -- the reference accepts a
                                            ; bare `ON INTERVAL=n GOSUB` and disarms)
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
; (eoi_err5 = gb_illegal: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)
    ENDIF

; --- ex_ff_stmt: the `$FF <selector>` STATEMENT fork -------------------------
; A statement that starts with a two-byte function token. MID$ ($FF $83) is the
; string-assignment form; STRIG ($FF $A3) is the T2 arming statement (this is the
; site that used to be the blanket ERR 2 of the input-devices D-I-5 handoff).
; Anything else falls into ex_mid_stmt's Syntax error. ⚠️ ex_mid_stmt is entered
; ON the selector byte: this fork has already done the `inc hl` and fetched it,
; so the byte is not re-fetched. It used to have a `ex_mid_sel` post-`inc hl`
; label for that; D-SEEDPROSE deleted the head instead (1 B, page-0 LOW).
ex_ff_stmt:
                inc     hl                  ; -> the selector byte
                ld      a,(hl)
                cp      STRIG_TOKEN         ; STRIG(n) ON|OFF|STOP  (traps T2)
                jr      z,ex_strig_stmt     ; (entered with HL on the selector)
    IF TRAPS_T5
                call    iv_match            ; INTERVAL ON|OFF|STOP  (traps T5)
                jr      c,ex_interval       ; CF=0 leaves HL on the selector, so
    ENDIF                                   ; ex_mid_stmt's Syntax error is unchanged
                jp      ex_mid_stmt

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
;
; 💰 D-ONTRAPMERGE (2026-09-30): THIS LOOP IS ALSO ON KEY GOSUB's. The two were
; byte-for-byte the same 46 B but for the slot limit (5 / 10) and the trap index
; (ZTI_STRIG0+C / ZTI_KEY1+9-C, the reversed KEY band). The limit rides in B --
; which the loop already guards across trap_line_link -- and the index arm tells
; the two apart by B's bit 3 (5 = %0101, 10 = %1010). ex_on_key sets B = 10 and
; jumps in at eon_trap_in. The T3 spec's "duplicate, specialise" verdict priced
; the constants as RAM PARAMETERS (76 B); in a register they cost 8.
ex_on_strig:
                ld      bc,5*256+0          ; B = slot limit, C = slot index 0..4
eon_trap_in:                                ; ex_on_key joins with B = 10
                inc     hl                  ; past the STRIG selector byte / KEY token
                call    req_gosub           ; D-NGRAM18
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
    IF TRAPS_T3
                bit     3,b                 ; B = 10: ON KEY -- the REVERSED band
                jr      z,eostr_idx
                neg
                add     a,ZTI_KEY1+9-ZTI_STRIG0 ; + ZTI_STRIG0 below = ZTI_KEY1+9-C
eostr_idx:
    ENDIF
                add     a,ZTI_STRIG0
                call    ztrap_entry         ; HL = &ZTRAP[3+C] (the state byte)
                pop     de
                inc     hl                  ; -> the handler field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                pop     hl                  ; HL = cursor
                inc     c
                call    skip_comma          ; another slot?
                jp      nz,exec_stmt        ; no -> statement done, continue the line
                inc     hl                  ; consume the comma
                ld      a,c
                cp      b                   ; slots 0..B-1 only
                jp      nc,trap_syntax      ; a 6th STRIG slot -> trappable ERR 2
                                            ; (D-T2-4); an 11th KEY slot -> ERR 2
                                            ; (§1.4 K15), as the reference raises
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
                call    inc_skip_paren     ; past the STRIG selector byte
                jp      nz,trap_syntax
                call    inc_eval            ; DE = n; HL past the expression
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
                rst    $10     
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
                jp      pop_exec            ; continue the line -- a bare `ret` here would
                                            ; SWALLOW the rest of it (the T1 es_set lesson)
; D-DUPSPAN: an ALIAS, not a second copy -- the two instructions were
; byte-identical to interp.asm's gb_illegal, on gfx_absent's own precedent.
; The NAME and every call site survive; un-alias here to give this site a
; distinct face and nothing else moves.
; (strig_illegal = gb_illegal: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)

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
; 🔴 EXCEPT THE ON ... GOSUB LOOP, SINCE D-ONTRAPMERGE (2026-09-30): its only
; differences were two constants, and a REGISTER carries them for 8 B where RAM
; cost 76 -- so ex_on_key is now a 6-byte entry into ex_on_strig's loop (-44 B).
; The verdict above stands for the other parsers and for RAM parameters.
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
                ld      bc,10*256+0         ; B = slot limit, C = slot index 0..9
                jp      eon_trap_in         ; D-ONTRAPMERGE: STRIG's loop, whose
                                            ; index arm reverses the band for B = 10
                                            ; (it lived in basic/field.asm as a pin
                                            ; refill 2026-10-15..16; D-BASICINT2's
                                            ; layout sent it home)

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
                call    inc_eval            ; DE = n; HL past the expression
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
                rst    $10     
                call    onoff_decode        ; KEY(n) ON|OFF|STOP (STOP == OFF, D-T3-6);
                                            ; DE (the entry pointer) survives
                jp      nc,trap_syntax      ; bare `KEY(n)` / junk -> trappable ERR 2
                ld      b,a
key_set:
                inc     hl                  ; consume the ON/OFF/STOP sub-keyword
                push    hl                  ; guard the exec-continue cursor
                ex      de,hl               ; HL = the entry pointer
                ld      a,b
                jp      trap_state_done     ; D-CARVE2 (-4 B, main page 1)
    ENDIF
