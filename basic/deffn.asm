; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; deffn.asm — DEF FN<name>[(<formals>)]=<body> (statement) and FN<name>[(<args>)]
; (expression function). The last MSX1 reserved word (`make kwsweep`: MISSING=1,
; and it was `deffn`).
;
; EVERY RULE BELOW WAS MEASURED, on a Philips VG-8020 and a National CF-3300,
; both agreeing on every scored row: docs/deffn-design-2026-08-22.md (82 rows,
; probes/basic/basic_probe_deffn.py, `make deffn-acceptance`). The three that
; shape this file:
;
;   1. THE FORMAL IS A SHADOW CELL, not the program's variable. `X=5 :
;      P=VARPTR(X) : DEF FNA(X)=PEEK(P)` reads 5 while the body runs
;      (o.realcell), and `VARPTR(X)-P` inside the body is 30327, not 0
;      (o.sameaddr). So the variable table is NEVER written -- which is also
;      why the ERROR path needs no unwinding at all (o.errrestore, o.strnumx:
;      `X` is still 5 after a body that faulted).
;   2. ...BUT THE SHADOW BLOCK **IS** SAVED AND RESTORED. z.addr2/z.addr2i read
;      the SAME address one nesting level deeper, so the reference reuses one
;      fixed block; o.nestsame (`DEF FNA(X)=X : DEF FNB(X)=FNA(X+1)+X` ->
;      FNB(3) = 7, not 8) then only holds if the outer frame comes BACK.
;      🔴 §1 of the design doc headlined "nothing is saved, nothing is restored"
;      and that sentence is true of the VARIABLE TABLE ONLY -- one scope too
;      wide, the memory index carried the wide form, and the mutation battery
;      had no mutant for it until the RAM-hunt round added one. fn_enter /
;      fn_leave below are that correction written as code.
;   3. `DEF FN` DOES NOT PARSE ITS BODY, OR ITS PARAMETER LIST. `DEF FNA(X)=X+*2`
;      is OK (o.lazybody), so is a missing `=` (o.noeq), and `DEF FNA(B(1))=...`
;      is OK at the DEF and ERR 2 at the CALL (o.aryformal). The only DEF-time
;      check is that a letter follows `FN`. So the statement is a SCAN -- name,
;      record a text pointer, skip to the end of the statement -- and all the
;      parsing happens per call, against the two lists walked together.
;
; The definition lives in the ORDINARY VARIABLE CHAIN under a key with bit 7 of
; name0 set. Two measured rows say that is where it belongs: `CLEAR` erases a
; definition (o.clearwipe3 -> Undefined user function), and `A` and `FNA` coexist
; (o.namespace -> `9 3`). A bit-7 name0 is a key no ordinary name can produce, so
; it needs no new table -- and the entry's own value field is exactly a text
; pointer. That pointer is safe because DEF FN in DIRECT mode is refused (ERR 12,
; d.defonly / d.sameline): a direct-mode definition would point into the line
; buffer the next command overwrites.
;
; ⚠️ THE SHADOW LOOKUP IS NOT IN THIS FILE, AND THAT IS WHERE THE BUDGET WENT.
; It sits at the top of sub/arrays.asm's scv_find, in the sub-ROM, where ALL FOUR
; accessors reach it at once (var_find_typed / var_alloc_or_find via ARY_OP 4/5,
; and -- since slice-4c unified string scalars into the same chain at type=1 --
; str_get_key / str_set_key too). Four `call fn_shadow` preludes in basic/vars.asm
; would have been ~64 B of a main ROM with 100 free; there it is ~40 B of a sub
; page 0 with 3 KB free, on a CALSLT every scalar reference already pays.
;
; Clean-room: original code. DEF FN / FN *semantics* are this project's own
; black-box measurements of the two reference machines (docs/deffn-scout-
; 2026-08-22.md, docs/deffn-design-2026-08-22.md) plus the public MSX-BASIC
; language reference; the token is oracle-locked from the reference's own crunch.
; No disassembly.

; ===========================================================================
; The statement
; ===========================================================================

; --- ex_deffn: DEF FN<name>[(<formals>)][=]<body> ---------------------------
; HL -> the FN token (basic/usr.asm's ex_def has stepped over DEF and skipped
; spaces). Records a text pointer under the bit-7 key and skips the rest of the
; statement; continues the line.
ex_deffn:
                ; 🎯 DIRECT MODE IS `Illegal direct`, ERR 12, AND TWO CONTROLS
                ; PIN IT TO `DEF FN` RATHER THAN TO `DEF` OR TO DIRECT MODE AT
                ; LARGE: `DEF USR=&HC000` and a bare `A=1` typed at the prompt
                ; are both OK on both references (d.defusr / d.let). ERR 12's
                ; message already ships (err_msgtab entry 12, sub-hosted) and
                ; was reachable only through `ERROR 12` until now.
                ld      a,(DIRECTF)         ; DERIVED at rp_exec, valid here
                or      a
                jr      z,exdf_run
                ld      a,12                ; Illegal direct
                jp      raise_error
exdf_run:
                inc     hl                  ; past the FN token
                call    req_letter          ; D-NGRAM: the ONE thing a DEF validates
                                            ; at the DEF -- `DEF FN1(X)` / `DEF FN(X`
                                            ; -> ERR 2 (o.badname / o.twofault)
                call    var_name_key        ; BC = key, HL past the name + suffix
                ld      a,(VARTYPE)         ; FNA / FNA% / FNA! / FNA$ are four
                                            ; distinct functions, exactly as the
                                            ; four spellings of a variable are
                                            ; four distinct scalars
                push    hl                  ; [defptr] -- the body starts HERE
                set     7,b                 ; the FN namespace
                call    var_alloc_or_find   ; HL = the entry (created if new)
                pop     de                  ; DE = the text pointer to record
                ; ⚠️ `jp nc` AND NOT `ret nc`, WHICH IS 2 B AND ONE STATEMENT'S
                ; WORTH OF ATTRIBUTION. A statement handler is entered by `jp`,
                ; so a bare `ret` unwinds to the run loop exactly as an
                ; end-of-line does and the pending Out of memory is then read at
                ; the NEXT line's statement boundary -- reported, but against
                ; the wrong line. ex_let's own store does it this way
                ; (`jp nz,fp_runtime_error`), and fp_runtime_error reloads FPERR
                ; itself, so no `ld a,(FPERR)` is needed here.
                jp      nc,fp_runtime_error ; out of memory: FPERR already set
                inc     hl
                inc     hl
                inc     hl                  ; HL -> the value field
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ex      de,hl               ; HL = the definition text again
                ; ⚠️ THE SKIP IS TOKEN-AWARE AND THAT IS MEASURED BOTH WAYS.
                ; `DEF FNA$(X$)=X$+":Q"` returns `a:Q` (o.quotedcolon), so a ':'
                ; inside a string literal does NOT end the definition -- while
                ; `DEF FNA(X)=X+1:B=9` really does go on to run `B=9`
                ; (o.stmtcolon). tok_skip is the routine that knows both, and
                ; tok_skip_to (basic/interp.asm) is if_skip_to_else with its
                ; terminator in C rather than baked in.
                ld      c,COLON
                call    tok_skip_to
                jp      exec_stmt

; ===========================================================================
; The call
; ===========================================================================

; --- ev_fn: the NUMERIC factor entry (basic/expr.asm ev_f, IX = cursor) -----
; ⚠️ THE PRE-CHECK IS NOT DECORATION. A `$` function reaching a numeric factor
; is Type mismatch, and without it the body would be evaluated as a string and
; the factor would hand back whatever FAC happened to hold -- this tree's own
; silent-wrong-answer class. var_str_type answers it from the NAME alone and
; advances nothing.
ev_fn:
                push    ix
                pop     hl
                call    inc_skip
                call    var_str_type        ; is the FN's own name a string name?
                or      a
                jp      nz,ev_f_tmm         ; deferred FPERR=10 -- the same shape
                                            ; a string VARIABLE in a numeric
                                            ; factor already takes (ev_f_var's
                                            ; check_vartype_num)
                call    fn_call             ; IX = cursor in, HL = cursor out
                push    hl
                pop     ix
                ret

; --- str_ev_fn: the STRING operand entry (basic/strvar.asm str_eval_one) ----
; HL -> the FN token. A numeric FN here is NOT an error: str_eval_one is offered
; the operand first and DECLINES what it cannot type, exactly as str_eval_paren
; does for `(A+1)` -- the caller then takes the numeric path it would have taken
; anyway. So this restores HL and returns CF clear.
str_ev_fn:
                push    hl
                call    inc_skip
                call    var_str_type
                or      a
                pop     hl
                jp      z,str_eval_no       ; numeric FN -> hand the operand back
                push    hl
                pop     ix
                call    fn_call
                jp      str_eval_ok         ; VALTYP=1 + CF set

; --- fn_call: evaluate FN<name>[(<args>)] ----------------------------------
; in:  IX -> the FN token.
; out: HL past the call; the result in FAC/FACTYP/DE (numeric) or STRPTR
;      (string). Clobbers everything.
;
; THE CALL ORDER IS MEASURED (design §4): name -> ERR 18 -> walk the two lists
; together -> ERR 2 on a shape mismatch -> ERR 5 past the ceiling -> bind ->
; evaluate. An undefined name beats every other fault: `FNZ(1,2)` -- undefined
; AND unmatched -- is ERR 18, not ERR 2 (o.undefarg).
fn_call:
                ; --- fn_enter: save the outer frame ------------------------
                ; ⚠️ ONLY THE LIVE PART, AND THAT IS A STACK DECISION RATHER
                ; THAN A BYTE ONE. A fixed 102-byte save is 3 bytes shorter to
                ; write and would burn the whole block on EVERY call, including
                ; the overwhelmingly common non-nested one -- and this machine's
                ; Z80 stack is a few hundred bytes (tests/msxtest.py's band, and
                ; the runaway sweep's measured base of $F380 with a deepest
                ; ordinary excursion of 90 B). At top level the live part is
                ; ZERO, so a plain `FNA(2)` costs 5 bytes of stack, not 102.
                ; D-FNPOOL (docs/spec-basic-fnpool.md, ruled by Joost 2026-09-11):
                ; the frame comes from the CONTROL POOL now, not from below `SP`,
                ; so a nested call's saved formals are ADDRESSABLE and the GC walks
                ; them. `SP` is not touched at all any more -- which is also what
                ; lets the stack's base move (D-SPMERGE): this routine's `cp high
                ; FN_STK_FLOOR` was an ABSOLUTE $F2 against `SP`, and it would have
                ; answered ERR 7 to every FN call the moment the base relocated.
                ; The body is a page-0 tenant op because main page 1 had ONE byte
                ; free; ERR 7 now comes from the pool's own collision.
                push    ix                  ; IX is the caller's cursor; the
                ld      l,FNF_SAVE          ; dispatch loads IX and CALSLT clobbers it
                call    deffn_subcall
                pop     ix
                jp      c,subrom_absent_error
                ld      a,(FN_FST)
                or      a
                jp      nz,gosub_stk_over   ; the pool is full -> ERR 7, as before --
                                            ; D-SPMERGE's carve: `fn_deep` was a bare
                                            ; `jp gosub_stk_over` with this as its one
                                            ; caller, so the label and its 3 bytes go

; ===========================================================================
; D-DEFFNEV: THE PARSE IS A SUB PAGE-0 TENANT, AND WHAT IS LEFT HERE IS A
; FOUR-REQUEST SERVICER.
;
; The measurement that forced it: the verb costs 450 B of a main ROM with 222
; free (docs/deffn-impl-2026-08-22.md §1, docs/spec-basic-dupspan2.md §3), and
; everything between the frame save and the frame restore is TOKEN WALKING over
; page-3 RAM -- name resolve, the two lists walked together, the delimiter
; agreement, the shadow-slot open and its ceiling. None of it touches `eval`,
; so all of it is page-0-tenant legal (tools/carve_scout.py --entries
; skip_spaces,is_letter,var_name_key,var_str_type,if_skip_to_else: CLEAN), and
; sub page 0 has 3 KB.
;
; ⚠️ A CALSLT IS NOT RESUMABLE, so this is not a co-routine in the CIRCLE sense
; (docs/spec-circle-coroutine-space.md): the tenant re-enters at its top every
; bounce and recovers its phase from L, which carries BOTH directions -- the
; tenant's request on the way out (in A, subrom_call's result), and the
; servicer's answer on the way back (in L, passed through CALSLT). One byte,
; because the two alphabets are disjoint.
;
;   tenant -> main   1  evaluate the expression at FN_PTR; say what you got
;                    2  store the value into (FN_KEY, FN_TYP)
;                    3  snapshot the string result off the frame, then LEAVE
;                    4  load (FN_KEY, FN_TYP) back into FAC, then LEAVE
;                    0  raise FN_TYP
;   main -> tenant  $81 a NUMERIC value (FAC/FACTYP/DE)
;                   $82 a STRING value (STRPTR)
;                   $83 stored
;
; 🎯 THERE IS NO BARE "LEAVE" REQUEST, AND THAT IS THE SAME RULE AS THE
; INT-RESULT ONE BELOW READ FROM THE OTHER END. Both terminal requests do their
; own work AND leave, because a bounce after either would be a bounce that
; carries nothing: the string case has already been snapshotted and the numeric
; case is sitting in DE. Two arms of the dispatch and eight bytes of tail, for a
; round trip whose only content was "yes, now".
;
; 🎯 ONE EVALUATE REQUEST SERVES BOTH THE ACTUALS AND THE BODY, and that is
; what makes the servicer small: main never decides WHICH expression it is
; looking at, only what came back. `str_eval` is offered first and allowed to
; DECLINE (D-STRPAREN's contract), so the answer is `$82` or `$81` and every
; type rule -- a string actual in a numeric formal, a numeric body in a `$`
; function, both directions of ERR 13 -- is the tenant's, where it is free.
;
; 🔴 THE LAST BOUNCE MAY NOT BE FOLLOWED BY ANOTHER. An INT-typed factor returns
; its value in DE (FACTYP=2; FAC is not written), and a CALSLT clobbers DE --
; so "load the result" and "leave" MUST be the same request. Splitting them
; would hand every `DEFINT` function a leftover register, which is the exact
; shape of the defect the 69-row battery found in the draft's own fn_leave
; (docs/deffn-impl-2026-08-22.md §4.2, six rows, one identical -3392).
; ===========================================================================
                push    ix
                pop     hl
                inc     hl                  ; past the FN token
                ld      (FN_PTR),hl
                ; 🎯 THE PHASE TRAVELS IN **L**, NOT IN A RAM CELL, AND THAT IS
                ; WHAT DELETED FN_REQ. CALSLT passes the main register set
                ; through to the tenant (C-BIOS's own calslt is `ex af,af'/exx`
                ; at entry and `exx` again just before it jumps to the target),
                ; and subrom_call touches nothing but A/DE/IY on the way in. The
                ; cell existed because "a CALSLT is not resumable, so the phase
                ; lives in RAM" -- true of the tenant's state, false of the
                ; SERVICER's, which is ordinary main-ROM code holding an
                ; ordinary register across a `call`. -7 B, at three sites.
                ; ⚠️ AND NESTING IS WHY THIS IS SAFE RATHER THAN LUCKY: an inner
                ; fn_call runs entirely inside the outer one's `call eval`, and
                ; the outer sets L again at fn_ev_x AFTER that call returns. The
                ; phase never has to survive anything.
                ld      l,0                 ; phase 0: nothing has been asked yet
fn_lp:
                ; 🔴 DE IS THE EVALUATED INT AND A CALSLT CLOBBERS IT. An
                ; INT-typed value lives in DE with FAC UNWRITTEN (var_store_fac's
                ; own header: "DE, valid iff the CURRENT (FACTYP)==2"), and
                ; request 1 -> request 2 puts a whole tenant bounce between the
                ; `call eval` that produced it and the `call var_store_fac` that
                ; reads it. That is the SAME defect the 69-row battery found in
                ; the draft's fn_leave, one bounce further out -- and 2 B here is
                ; the entire fix, because the resident half's stack is the one
                ; thing a tenant re-entry cannot disturb.
                ; ⚠️ AND THE ALTERNATIVE -- THE TENANT DOING push de/pop de
                ; AROUND ITSELF -- WOULD HAVE MEASURED GREEN HERE AND BEEN A
                ; CLAIM ABOUT ONE BIOS. C-BIOS's own calslt happens to hand the
                ; callee's DE back (`ex af,af'/exx` in, the mirrored pair out),
                ; so the battery could not tell the two fixes apart; but
                ; subrom_call's header documents the opposite ("CALSLT clobbers
                ; all registers"), it restores DE only on the way IN, and every
                ; other tenant in this tree marshals through RAM. 2 B in the
                ; RESIDENT half is a claim about the protocol.
                ; 🔬 KNIFE K-DE1 CUTS -- scratchpad/deffn_de_knife.py deletes
                ; these two bytes and deffn-strict goes 0 -> 31 of 69 rows
                ; divergent. WIDER than predicted: an integer LITERAL actual is
                ; FACTYP=2 as much as a DEFINT one is, so `FNA(2)` is in the
                ; class too. And every wrong answer is a plausible NUMBER --
                ; 22529, 45058, 11264 -- not damage.
                push    de
                call    deffn_subcall       ; A = the tenant's request
                pop     de                  ; (a `pop` does not touch CF)
                jp      c,subrom_absent_error
                dec     a
                jr      z,fn_ev             ; 1 evaluate
                dec     a
                jr      z,fn_st             ; 2 store
                dec     a
                jr      z,fn_sn             ; 3 snapshot, then leave
                dec     a
                jr      z,fn_ld             ; 4 load, then leave
                ld      a,(FN_TYP)          ; 0 raise -- ERR 18 / 13 / 5, all of
                jp      raise_error         ; them the tenant's own disposition
; --- request 1: evaluate the expression at FN_PTR --------------------------
fn_ev:
                ld      hl,(FN_PTR)
                call    str_eval            ; offered first, allowed to decline
                ld      a,$82
                jr      c,fn_ev_x
                call    eval
                ld      a,$81
fn_ev_x:
                ld      (FN_PTR),hl
                ld      l,a                 ; the answer, straight into the phase
                jr      fn_lp
; --- request 2: bind the value into the shadow slot the tenant just opened -
fn_st:
                ld      bc,(FN_KEY)
                ld      a,(FN_TYP)
                cp      DEFTBL_STR
                jr      z,fn_st_s
                call    var_store_fac       ; coerces INTO the slot -- the shadow
                jr      fn_st_x             ; lookup in sub/arrays.asm routes it
fn_st_s:
                ld      de,(STRPTR)
                ld      a,1                 ; the `$` unifier type (slice-4c)
                call    str_set_key
fn_st_x:
                ld      l,$83
                jr      fn_lp
; --- request 3: a string result must leave the frame before the frame does -
; ⚠️ `DEF FNA$(X$)=X$` would otherwise return STRPTR pointing INTO the shadow
; slot that fn_leave is about to overwrite with the outer frame. Every measured
; row happens to concatenate and so lands in a temp anyway -- which is exactly
; the kind of accident this project does not leave standing.
fn_sn:
                call    str_snapshot_to_temp    ; reads STRPTR itself
                ld      (STRPTR),hl
                jr      fn_fin
; --- request 4: coerce the result to the FN's own type, THEN leave ---------
; The coercion rides the variable store rather than duplicating the codec: by
; now the formals have been read and slot 0 is dead, so the tenant re-keys it
; $FFFF -- a key no formal can carry, since a formal's name0 is always a letter
; -- and this is the int-truncate / single-round / double-widen ladder spec
; §11.2 already owns. It is what makes `DEF FNA%(X)=X/2` answer 2 where its `!`
; twin answers 2.5.
fn_ld:
                ld      bc,(FN_KEY)
                ld      a,(FN_TYP)
                call    var_load_fac        ; FAC/FACTYP/DE = the coerced result
fn_fin:
                ld      hl,(FN_PTR)         ; the cursor past the whole call

; 🔴 DE IS THE RESULT AND THE RESTORE IS AN `ldir`, WHICH IS THE WHOLE REASON
; THIS IS FOUR INSTRUCTIONS LONGER THAN IT LOOKS. An int-typed factor returns
; its value in DE (FACTYP=2; FAC is not written), so the draft's `ldir` +
; `pop de` handed every INT-typed FN back a leftover stack address -- `-3392`
; on six rows, identically, whatever their body computed. A float result lives
; in FAC, which is RAM, so it survived: the bug was visible ONLY through
; `DEFINT A-Z` or a `%` on the function's own name, and it read as a plausible
; number rather than as damage.
fn_leave:
                ; D-FNPOOL: the frame is in the pool, so nothing on the Z80 stack
                ; belongs to it -- `fn_call`'s own return address is still exactly
                ; where it was, and this `ret` uses it. DE (the result) and HL (the
                ; cursor) are this routine's contract and CALSLT clobbers both.
                push    de                  ; [result]
                push    hl                  ; [cursor]
                ld      l,FNF_RESTORE
                call    deffn_subcall       ; absent cannot happen here: the SAVE
                pop     hl                  ; already errored if it were
                pop     de
                ret

; --- the one error tail left --------------------------------------------
; 🎯 ERR 18, ERR 13 AND ERR 5 ARE GONE FROM THIS FILE, AND NOT BECAUSE THEY
; STOPPED BEING RAISED. Every one of them is a disposition the TENANT decides --
; the name was not found, the actual's type did not match the formal's, the
; tenth formal was reached -- so each is now a code in FN_TYP that the servicer's
; own `ld a,(FN_TYP) / jp raise_error` raises. Three tails, thirteen bytes, and
; `make deadcode` is what would have caught them had they been left behind.
; ⚠️ ERR 7 STAYS, and since D-FNPOOL it is the POOL's disposition, not a
; hand-rolled floor's: `ctl_alloc`'s own collision with `CTLLIM` is what refuses
; `DEF FNA(X)=FNA(X)`, which is Out of memory on both references (b.recurse).
; The `fn_deep` label that used to sit here was a bare `jp gosub_stk_over` with
; exactly one caller, so D-SPMERGE's carve spent it: the caller jumps straight
; to `gosub_stk_over` and these three bytes fund the stack base's relocation.
