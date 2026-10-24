; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; pgmedit.asm -- zerobas-sub2 PAGE 0: the STATEMENT halves of the program-editing
; verbs DELETE, RENUM and AUTO (D-P0CB, docs/spec-sub2-p0cb.md §5). Moved out of
; main page 1 on 2026-10-24: ex_delete's marshalling head (basic/field.asm, a pin
; refill in front of $72D4), ex_renum whole -- its report loop included -- and
; ex_auto's argument head (basic/program.asm).
;
; The verbs' ENGINES did not move and were never main's: the parse, the
; validations, the delete walk, the renumbering passes and AUTO's argument parse
; are the sub ROM's lineedit tenant (sub/lineedit.asm le_delrange / le_renum /
; le_renum_next / le_auto), reached through main's le_call_op exactly as before
; -- now a p0cb call, so that tenant runs one CALSLT deeper (below).
;
; WHAT STAYS IN MAIN, and is reached through p0cb:
;   le_call_op       the lineedit tenant's call (LIST and the line store use it)
;   print_string / list_num / print_crlf   RENUM's report (shared everywhere)
;   rn_undefined / in_msg   DATA in main's page-0 islands, read by print_string
;                    while p0cb has main's page 0 mapped -- this ROM's page 0
;                    could not hold them (it is switched OUT during the call)
; and as CONTINUATIONS (returned in DE, never p0cb'd):
;   end_line_end     DELETE and RENUM end the line and the run (R-D8, R-RN16)
;   exa_loop         AUTO's modal loop: it blocks on the keyboard (rl_loop) and
;                    stores every line it reads (dispatch_line), so it runs in
;                    main at the statement's own SP, OFF this tenant's CALSLT
;                    frame (the D-BLOADSTK rule: nothing long runs nested here)
;
; Entered through trap_tenant (sub2/trapstmt.asm) -> file_tenant -> ls_tenant ->
; scr_tenant (sub2/scrstmt.asm), which forwards every token but KEY here. Main's
; three entry labels share ex_open's ONE byte, `ld c,a` in front of ex_sub2
; (basic/program.asm): exec_stmt hands a handler A = its token
; (tests/test_stmt_dispatch.py asserts it).
;   in   HL = the cursor ON the statement token (exec_stmt's contract)
;        A = C = the token
;   out  DE = the main continuation (above); HL is not read by either
; A raise reached through p0cb never returns (raise_error resets SP and runs
; main's error path with main's page 0 mapped), exactly as the `jp raise_error`
; it replaces never returned. fs_raise (A = the ERR code) and ls_end_line (the
; end_line_end continuation) are sub2/filestmt.asm's / sub2/loadsave.asm's.
;
; 📏 STACK, counted from the statement's SP (S, ex_sub2's entry). This tenant runs
; at S-14 (scrstmt.asm's header: ex_sub2's call, sr_slot's push iy, C-BIOS's
; CALSLT frame of 10) and a p0cb adds 6 (its call, the old $A8, clprim's call),
; so a main routine p0cb'd from here is ENTERED at S-20, where main's ex_* entered
; it at S-2 (its own `call`): 18 B deeper. le_call_op then runs the lineedit
; tenant 16 B below its entry (sc_inl1's call, sc_call's `call subrom_call`,
; sr_slot's push iy, the CALSLT frame). So:
;   DELETE / RENUM / AUTO's parse   the lineedit tenant at S-36, was S-18: 18 B
;                    deeper, for the length of one tenant call (RENUM: one call
;                    per report round trip, the passes inside it)
;   RENUM's report   print_string / list_num / print_crlf entered at S-20, was
;                    S-2: 18 B deeper
;   AUTO's loop      exa_loop at S, as before (a continuation, after ex_sub2's
;                    `push de / ret`): read_line and dispatch_line at their old depth
; RENUM's whole verb runs nested here, report loop included: it ends the run
; (R-RN16), a tape loader has no reason to run it, and its loop is bounded by the
; program's dangling references -- it waits on nothing.
; ⏱ INTERRUPTS: the tenant enters under sr_slot's DI; the first nested
; le_call_op comes back through sr_slot's `ei`, so the report prints and the
; tenant returns with interrupts ON (an interrupt here takes this ROM's $0038 ->
; SUB_INT_RAM, D-SUB2EI) -- the same state main's ex_* reached after the call.
;
; The code is otherwise main's, statement for statement: the same LE_OP order,
; the same status decoding, CONTVALID cleared on a succeeding DELETE only, and
; the same end-of-run continuation. The history behind each rule is in git
; (basic/program.asm and basic/field.asm before this move); the measured rule
; each one encodes is kept below.

; --- the dispatch -------------------------------------------------------------
pe_tenant:                                  ; A = C = the token (scr_tenant's tail)
                cp      DELETE_TOKEN
                jr      z,pe_delete
                cp      AUTO_TOKEN
                jr      z,pe_auto
                ; FALL THROUGH: RENUM_TOKEN is the only other token main sends here

; ===========================================================================
; RENUM [<new>][,[<old>][,<inc>]]   (main's ex_renum, D-EDITVERB)
; ===========================================================================
; docs/spec-basic-editverb.md §3.2, measured in
; docs/editverb-msx1-characterization.md §2. The whole verb -- parse, both
; validations, the reference pass and the header pass -- is the lineedit tenant's
; (le_renum); this is the marshalling head PLUS the one thing the tenant cannot
; do: print.
; 🔴 THE LOOP IS THE POINT. `Undefined line <n> in <m>` is emitted ONCE PER
; DANGLING REFERENCE (R-RN9 -- `1 ON 1 GOTO 77,88` prints two, both `in 1`), and
; rendering it needs print_string + list_num, main page-1 code a page-1 tenant
; cannot reach. So the tenant STOPS at each one, hands back the pair in
; RN_TGT / RN_LINE, and this head prints it and re-enters with LE_OP_RENUM_NEXT.
; The tenant's cursor lives in RN_PTR across the round trip, which is why that
; cell may not be an alias of the SL_* block.
; 🔴 AND IT IS NOT AN ERROR (R-RN10). ERR stays 0, ON ERROR does not trap it, and
; the renumbering HAPPENS ANYWAY -- `1 GOTO 77` becomes `10 GOTO 77`. That is why
; status 1 is a REPORT and only status >= 2 reaches raise_error.
pe_renum:
                ld      (RN_PTR),hl         ; the statement cursor, on the token
                ld      a,LE_OP_RENUM
per_call:
                ld      ix,p0_le_call_op
                call    p0cb                ; A = LE_STATUS, Z = ok
                ; R-RN16: done -> the run stops, exactly as DELETE and LIST do.
                ; ⚠️ CONTVALID IS DELIBERATELY NOT CLEARED AND vars_reset IS
                ; DELIBERATELY NOT RUN -- R-RN17, measured on both references with
                ; a program whose lines actually MOVE: `1 A=7/RUN/RENUM/PRINT A`
                ; reads 7, and `1 STOP/2 PRINT 5/RUN/RENUM/CONT` still prints 5.
                ; RENUM is not a program EDIT in the sense DELETE is: no byte
                ; changes length, so nothing the variables or the CONT point
                ; address has moved.
                jp      z,ls_end_line       ; 0 = the whole renumbering is done
                dec     a
                jr      nz,per_raise        ; >= 2 is the ERR CODE ITSELF: 2 for
                                            ; R-RN14/R-RN15, 5 for R-RN11/12/13
                ld      hl,p0_rn_undefined  ; 1 = report one dangling reference
                ld      ix,p0_print_string
                call    p0cb
                ld      de,(RN_TGT)
                ld      ix,p0_list_num
                call    p0cb                ; the target, bare unsigned decimal
                ld      hl,p0_rn_in
                ld      ix,p0_print_string
                call    p0cb
                ld      de,(RN_LINE)        ; R-RN8: the containing line's OLD
                ld      ix,p0_list_num
                call    p0cb                ; number -- `in 1`, not `in 10`
                ld      ix,p0_print_crlf
                call    p0cb
                ld      a,LE_OP_RENUM_NEXT
                jr      per_call
per_raise:
                ld      a,(LE_STATUS)
                jp      fs_raise            ; raises; never returns

; ===========================================================================
; DELETE [<lo>][-[<hi>]]   (main's ex_delete, D-DELETE)
; ===========================================================================
; docs/spec-basic-delete.md, measured in docs/delete-msx1-characterization.md.
; The WHOLE verb -- the argument parse, the two validations and the delete walk
; -- is the lineedit tenant's (le_delrange), beside the TXTTAB memmove engine it
; drives: the grammar is `[$0E lo] [$F2 [$0E hi]]`, pure token bytes, so the
; argument marshals as ONE POINTER (spec §3.1, measured both ways, §7 K6).
; ⚠️ NOTHING COMES BACK BUT A STATUS, AND THAT IS R-D8, NOT A SHORTCUT. DELETE
; ENDS the line and the program on BOTH paths -- a succeeding one via ENDFLAG, a
; failing one via raise_error -- so the advanced cursor has no reader and is never
; marshalled back. `DELETE 20:B=9` leaves B at 0 with ERR 0 on both references
; (dlt-tail, against dlt-tailctl's 9): the ':' is ACCEPTED and then abandoned.
pe_delete:
                ld      (SL_DELPTR),hl      ; the statement cursor, on the token
                ld      a,LE_OP_DELRANGE
                ; LE_STATUS carries the ERR CODE ITSELF for this op (basic/
                ; sysvars.inc): 0 = ok, 2 = R-D6 trailing junk, 5 = R-D2 (the high
                ; end names no stored line) or R-D4 (lo > hi).
                ld      ix,p0_le_call_op
                call    p0cb                ; A = LE_STATUS, Z = ok
                jp      nz,fs_raise         ; A = the ERR code; never returns
                ; R-D7: a SUCCEEDING delete is a program EDIT. The tenant has
                ; already run relink + vars_reset (its own tail, exactly as
                ; store_line's op does); CONTVALID is the resident half, cleared
                ; HERE and only here -- a FAILING delete must leave the CONT point
                ; alone (dlt-contbad: its CONT still resumes, reading 5).
                ld      (CONTVALID),a       ; A = 0 (the Z above)
                ; R-D8: and then the run stops. Same mechanism as END -- the run
                ; loop tests ENDFLAG immediately after `exec` returns and BEFORE it
                ; dereferences CURLINE, which matters here: the text this
                ; statement just memmoved is where CURLINE points.
                jp      ls_end_line         ; main's `jp end_line_end`

; ===========================================================================
; AUTO [<start>][,<inc>]   (main's ex_auto head, D-EDITVERB)
; ===========================================================================
; docs/spec-basic-editverb.md §3.3. The ARGUMENT is parsed by the lineedit tenant
; (le_auto, into AU_NUM / AU_INC); the MODAL LOOP is main's exa_loop
; (basic/program.asm), this tenant's continuation -- see the header for why it
; does not run here.
pe_auto:
                ld      (RN_PTR),hl         ; the statement cursor, on the token
                ld      a,LE_OP_AUTO
                ld      ix,p0_le_call_op
                call    p0cb                ; A = LE_STATUS, Z = ok.
                                            ; 2 = R-AU9 trailing junk, 5 = R-AU5
                                            ; (increment 0, which is also what bare
                jp      nz,fs_raise         ; `AUTO ,` reduces to)
                inc     a                   ; -> 1: read_line polls from here on
                ld      (RL_AUTO),a
                ld      de,p0_exa_loop      ; the loop, in main (a continuation)
                ret
