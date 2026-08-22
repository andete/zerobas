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
                call    skip_spaces
                call    is_letter           ; the ONE thing a DEF validates
                jp      nc,stmt_error       ; `DEF FN1(X)` / `DEF FN(X` -> ERR 2
                                            ; at the DEF (o.badname / o.twofault)
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
                inc     hl
                call    skip_spaces
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
                inc     hl
                call    skip_spaces
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
                ld      a,(FN_FEND)
                sub     low FN_PAREA
                add     a,FN_CELLS          ; + FN_FEND/FN_SLOTP/FN_RTYPE, which
                ld      c,a                 ; sit BELOW the area so ONE contiguous
                ld      b,0                 ; copy from FN_BASE carries both
                ld      hl,0
                add     hl,sp
                or      a
                sbc     hl,bc               ; HL = the reserved block
                ld      a,h
                cp      high FN_STK_FLOOR
                jp      c,fn_deep           ; ERR 7 -- `DEF FNA(X)=FNA(X)` is Out
                                            ; of memory on both references
                                            ; (b.recurse), and a floor is the
                                            ; only thing between that answer and
                                            ; a wrecked stack
                ld      sp,hl
                ex      de,hl               ; DE -> the reserved block
                ld      hl,FN_BASE
                push    bc                  ; [size] -- pushed BELOW the block so
                                            ; fn_leave meets it first
                ldir
                ; --- resolve the name --------------------------------------
                push    ix
                pop     hl
                inc     hl                  ; past the FN token
                call    skip_spaces
                call    var_name_key        ; BC = key, HL past the name + suffix
                ld      a,(VARTYPE)
                ld      (FN_RTYPE),a        ; the FN's own type IS its result
                                            ; type (o.fnpct 2 vs o.fnbang 2.5,
                                            ; o.defint 2 vs its control 2.5)
                set     7,b
                push    hl                  ; [ccur]
                call    var_find_typed
                jp      nc,fn_undef         ; ERR 18, and it outranks everything
                inc     hl
                inc     hl
                inc     hl                  ; HL -> the recorded text pointer
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the definition cursor
                pop     hl                  ; HL = the call cursor
                ld      a,low FN_PAREA
                ld      (FN_SLOTP),a        ; the first formal takes slot 0
                ; ⚠️ FN_FEND IS **NOT** RESET HERE, AND THAT IS o.nestsame's
                ; WHOLE POINT. The actuals are evaluated in the CALLER's scope
                ; (o.actualfirst: `X=5 : DEF FNA(X)=X*10` called as `FNA(X+1)`
                ; is 60), so the outer frame has to stay visible until the last
                ; one has been evaluated. fn_slot grows FN_FEND to cover the new
                ; slots without ever shrinking it, and the exact frame is set
                ; once the list closes.
                ld      a,(de)
                cp      '('
                jr      nz,fn_body          ; `DEF FNA=7` consumes NO parentheses
                                            ; at the call either -- `FNA(1)` is
                                            ; `7 1`, two PRINT items (o.argnoarg)
                call    skip_spaces
                cp      '('
                jp      nz,stmt_error       ; a list in the DEF and none at the
                                            ; call is ERR 2 (o.barecall)
                inc     hl
                inc     de
fn_bindlp:
                ex      de,hl               ; HL = the definition cursor
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error
                call    var_name_key        ; BC = the formal's key
                ld      a,(VARTYPE)
                ex      de,hl               ; HL = call cursor, DE = def cursor
                call    fn_bind_one
                ; --- the two delimiters must AGREE -------------------------
                ; This is the whole of the arity rule, and it is why ERR 2 comes
                ; out of `FNA(1,2)` on a one-formal FN (o.toomany), `FNA(1)` on a
                ; two-formal one (o.toofew), AND `DEF FNA(B(1))=...` (o.aryformal
                ; -- the definition's next character is `(`, the call's is `)`).
                ex      de,hl
                call    skip_spaces
                ex      de,hl
                ld      c,a                 ; C = the definition's delimiter
                call    skip_spaces
                cp      c
                jp      nz,stmt_error
                inc     hl
                inc     de
                cp      ','
                jp      z,fn_bindlp
                cp      ')'
                jp      nz,stmt_error
fn_body:
                ld      a,(FN_SLOTP)
                ld      (FN_FEND),a         ; the live frame is EXACTLY this
                                            ; call's own formals -- which is why
                                            ; `DEF FNB(Y)=X` called from inside
                                            ; FNA(X) reads the GLOBAL X
                                            ; (o.dynscope -> 5, not 2)
                ex      de,hl               ; HL = def cursor, DE = call cursor
                push    de                  ; [ccur]
                call    skip_spaces
                cp      EQ_TOKEN            ; `=` crunches to $EF; a definition
                jr      nz,fnb_noeq         ; without one is legal (o.noeq) and
                inc     hl                  ; simply evaluates from here
fnb_noeq:
                ld      a,(FN_RTYPE)
                cp      DEFTBL_STR
                jr      z,fnb_str
                call    eval                ; the body, in the callee's own scope
                ; 🎯 THE RESULT COERCION RIDES THE VARIABLE STORE RATHER THAN
                ; DUPLICATING THE CODEC. By now the formals have been read and
                ; slot 0 is dead, so the value goes through var_store_fac /
                ; var_load_fac on a scratch slot keyed $FFFF -- a key no formal
                ; can carry, since a formal's name0 is always a letter. That is
                ; the int-truncate / single-round / double-widen ladder spec
                ; §11.2 already owns, and it is what makes `DEF FNA%(X)=X/2`
                ; answer 2 where its `!` twin answers 2.5.
                ld      hl,FN_PAREA
                ld      (hl),$FF
                inc     hl
                ld      (hl),$FF
                inc     hl
                ld      a,(FN_RTYPE)
                ld      (hl),a
                ld      hl,FN_FEND
                ld      (hl),low FN_PAREA + FN_SLOTSZ
                ld      bc,$FFFF
                call    var_store_fac       ; A = FN_RTYPE still
                ld      bc,$FFFF
                ld      a,(FN_RTYPE)
                call    var_load_fac        ; FAC/FACTYP/DE = the coerced result
                pop     hl                  ; [ccur]
                jr      fn_leave
fnb_str:
                call    str_eval
                jp      nc,fn_typemm        ; a `$` function whose body is not a
                                            ; string is ERR 13
                ; ⚠️ SNAPSHOT BEFORE THE FRAME GOES BACK. `DEF FNA$(X$)=X$` would
                ; otherwise return STRPTR pointing INTO the shadow slot, which
                ; fn_leave is about to overwrite with the outer frame. The
                ; measured rows all concatenate (b.str, o.quotedcolon, o.defstr)
                ; and so all happen to land in a temp already -- which is exactly
                ; the kind of accident this project does not leave standing.
                call    str_snapshot_to_temp    ; reads STRPTR itself
                ld      (STRPTR),hl
                pop     hl                  ; [ccur]
; 🔴 DE IS THE RESULT AND THE RESTORE IS AN `ldir`, WHICH IS THE WHOLE REASON
; THIS IS FOUR INSTRUCTIONS LONGER THAN IT LOOKS. An int-typed factor returns
; its value in DE (FACTYP=2; FAC is not written), so the draft's `ldir` +
; `pop de` handed every INT-typed FN back a leftover stack address -- `-3392`
; on six rows, identically, whatever their body computed. A float result lives
; in FAC, which is RAM, so it survived: the bug was visible ONLY through
; `DEFINT A-Z` or a `%` on the function's own name, and it read as a plausible
; number rather than as damage.
fn_leave:
                pop     bc                  ; [size]; SP now = the block base
                push    de                  ; [result] -- ldir needs DE
                push    hl                  ; [cursor]
                ld      hl,4
                add     hl,sp               ; HL -> the saved block
                ld      de,FN_BASE
                ldir                        ; HL ends one past the block...
                pop     de                  ; DE = the cursor
                pop     bc                  ; BC = the result
                ld      sp,hl               ; ...which IS the pre-call SP
                ex      de,hl               ; HL = the cursor
                ld      d,b
                ld      e,c                 ; DE = the result, intact
                ret

; --- fn_bind_one: evaluate ONE actual and bind it to ONE formal -------------
; in:  A = the formal's resolved type, BC = its key, HL = the call cursor,
;      DE = the definition cursor.
; out: HL past the actual, DE unchanged. Clobbers A, BC.
;
; 🎯 str_eval IS TRIED FIRST FOR BOTH KINDS OF FORMAL, AND THAT ONE PROBE GIVES
; BOTH DIRECTIONS OF ERR 13 FOR FREE: a string actual handed to a numeric formal
; (`FNA("hi")` -> o.strnum) and a numeric actual handed to a string one
; (`FNA$(1)` -> o.numstr). It is the same offer-then-decline str_eval_paren was
; built for, so a numeric actual costs one refused call and nothing else.
fn_bind_one:
                push    de                  ; [dcur]
                push    bc                  ; [fkey]
                push    af                  ; [ftype]
                call    str_eval            ; CF set -> the actual IS a string
                jr      c,fnb1_str
                pop     af
                cp      DEFTBL_STR
                jp      z,fn_typemm         ; string formal, numeric actual
                push    af
                call    eval                ; HL advanced; FAC/FACTYP = the value
                pop     af
                pop     bc
                push    hl                  ; [ccur]
                call    fn_slot             ; write the slot header; A survives
                call    var_store_fac       ; coerce the live value INTO the slot
                                            ; -- the shadow lookup in sub/
                                            ; arrays.asm is what routes it there
                jr      fnb1_done
fnb1_str:
                pop     af
                cp      DEFTBL_STR
                jp      nz,fn_typemm        ; numeric formal, string actual
                pop     bc
                push    hl                  ; [ccur]
                ld      a,1                 ; the `$` unifier type (slice-4c):
                                            ; string scalars key at type 1
                call    fn_slot
                ld      de,(STRPTR)
                call    str_set_key
fnb1_done:
                pop     hl                  ; [ccur]
                pop     de                  ; [dcur]
                ret

; --- fn_slot: open the next shadow slot for (BC = key, A = type) ------------
; out: A = type (unchanged), BC unchanged, HL clobbered. Raises ERR 5 past the
; ceiling.
;
; 🎯 THE CEILING IS A DIVISION, NOT A RULE. FN_PAREA_END is FN_PAREA + 9*11
; because 11 is a scalar entry and the window holds nine of them -- the same
; 100/11 that predicts the reference's own measured nine (o.p9 -> 1, o.p10/p11/
; p12/p16 -> ERR 5, all AT THE CALL, while `DEF` with ten formals is OK).
; Nothing here spells 9.
;
; ⚠️ FN_FEND GROWS, IT NEVER SHRINKS, and that is what keeps the OUTER frame
; visible to the actuals still to be evaluated (o.nestsame). The exact frame is
; set from FN_SLOTP once the list closes.
; 🔴 DE IS THE VALUE AND THIS ROUTINE MAY NOT TOUCH IT. The type is stashed on
; the STACK rather than in E, and that is a measured fix, not caution: the draft
; used `ld e,a` and every numeric formal bound to its own TYPE BYTE instead of
; its actual. `var_store_fac` takes the live RHS in DE whenever FACTYP is 2
; (fac_to_int_strict is `cp 2 / ret z` -- DE already holds it), so E carrying 8
; made `DEF FNA(X)=X+1 : FNA(2)` answer 9, `o.p3` answer 8 and `o.global`
; answer 11 -- 26 rows, every one of them a plausible-looking number.
fn_slot:
                push    af                  ; [type] -- NOT in E: see above
                ld      a,(FN_SLOTP)
                cp      low FN_PAREA_END
                jp      nc,fn_toomany       ; ERR 5 -- past the ninth formal
                ld      l,a
                ld      h,high FN_PAREA
                ld      (hl),b
                inc     hl
                ld      (hl),c
                inc     hl
                pop     af
                ld      (hl),a              ; the slot is a scalar entry, verbatim
                push    af
                ld      a,l
                add     a,FN_SLOTSZ-2       ; HL is at slot+2
                ld      (FN_SLOTP),a
                ld      hl,FN_FEND
                cp      (hl)
                jr      c,fnsl_x
                ld      (hl),a
fnsl_x:
                pop     af
                ret

; --- the error tails -------------------------------------------------------
; ⚠️ THREE OF THE FIVE ARE `jp`s TO SOMEBODY ELSE'S TAIL, WHICH IS D-DUPSPAN'S
; DOING: it collapsed thirteen byte-identical `ld a,N / jp raise_error` spans
; into `gb_illegal` (ERR 5) and `pl_syntax` (ERR 2) and left them as the tree's
; canonical ones. ERR 2 goes through stmt_error rather than pl_syntax because it
; must also clear PRDEST and honour a pending fault (D-STMTPEND).
fn_undef:                                   ; ERR 18 Undefined user function --
                                            ; the message already ships (errmsg
                                            ; tenant, em_undef_fn); before this
                                            ; verb NOTHING could reach it
                ld      a,18
                jp      raise_error
fn_typemm:                                  ; ERR 13 Type mismatch
                ld      a,13
                jp      raise_error
fn_toomany:
                jp      gb_illegal          ; ERR 5 Illegal function call
fn_deep:
                jp      gosub_stk_over      ; ERR 7 Out of memory
