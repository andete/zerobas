; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; missing.asm — LOCATE / SWAP / TRON / TROFF / MOTOR, the MISSING class.
; ===========================================================================
; The five MSX1 reserved words that this BASIC did not have at all: the
; tokeniser did not crunch them and exec_stmt had nowhere to send them, so each
; one was a Syntax error on a line the reference runs. They are collected here
; rather than scattered into screen.asm / vars.asm / program.asm because they
; land as ONE slice against ONE gate, and because a slice you can delete in one
; piece is a slice you can falsify.
;
; Normative surface, all VG-8020-measured, none assumed:
;   docs/spec-basic-missing-class.md          (signed off S-MC-1..6)
;   docs/missing-vg8020-characterization.md   (175 cases + the locrow battery)
;
; ⚠️ REPACK-ONLY, deliberately (S-MC-5). The whole file is behind one
; (The retired lean 16 KB cart assembled NOTHING from this file, so its five words
; did not exist there at all -- knowingly: that build was byte-full and its kwtable
; was inline in page 1, where the
; kwtable is a sub.rom tenant with ~8 KB free.
; ===========================================================================


; --- ex_motor: MOTOR | MOTOR ON | MOTOR OFF ---------------------------------
; Exactly three forms, and everything else is a Syntax error (measured, spec
; §3.5): MOTOR 1, MOTOR 0, MOTOR "ON", MOTOR A, MOTOR ON,OFF, MOTOR ON, -- and,
; unlike every other ON/OFF statement in this tree, **MOTOR STOP**. That last
; one is why onoff_decode returns "which sub-keyword" instead of "is this
; allowed": the 2-way policy is the caller's single `cp ZTS_STOP`, not a second
; flavour of the shared decoder (see its header in program.asm).
;
; The body is a BIOS call. tape/tape.asm implements STMOTR ($00F3) with the MSX
; convention -- A=0 stop, A=$FF toggle, otherwise start -- and tape/tape.asm is
; a dependency of the merged repack ROM, so the entry is present on the target
; machine. ZTS_OFF/ZTS_ON are literally 0/1 (sysvars.inc), so onoff_decode's
; answer IS the STMOTR argument with no mapping step.
ex_motor:
                inc     hl                  ; past the MOTOR token
                call    skip_spaces         ; returns A = (HL)
                call    onoff_decode
                jr      c,mot_onoff
                ; Not ON/OFF/STOP. A bare MOTOR is the TOGGLE form, but only at a
                ; statement boundary -- `MOTOR 1` and `MOTOR A` must NOT silently
                ; toggle and swallow their argument. onoff_decode hands the
                ; original token back in A on the CF=0 path precisely so this
                ; test can be made without re-reading (HL).
                or      a
                jr      z,mot_toggle        ; end of line
                cp      COLON
                jp      nz,trap_syntax      ; MOTOR <anything else> -> ERR 2
mot_toggle:
                ld      a,$FF               ; STMOTR: toggle
                jr      mot_go
mot_onoff:
                cp      ZTS_STOP
                jp      z,trap_syntax       ; MOTOR STOP -> ERR 2 (MEASURED -- do not
                                            ; "harmonise" this with SPRITE/KEY/STRIG,
                                            ; which all accept STOP)
                inc     hl                  ; consume the ON/OFF sub-keyword
mot_go:
                push    hl                  ; guard the cursor across the BIOS call
                call    STMOTR
                pop     hl
                jp      exec_stmt           ; continue the line (a bare `ret` would
                                            ; swallow the rest of it -- the T1 lesson)

; --- err_missing_operand: the ERR 24 message --------------------------------
; The err_msgtab in interp.asm stopped at code 23, so ERR 24 printed
; "unprintable error" -- on all THREE of its sites, two of which
; (graphics.asm g8_missing, time.asm tm_err24) predate this slice and had been
; raising a code with no message. LOCATE is what surfaced it: bare `LOCATE`
; reads `Missing operand` on the reference. House-style lowercase, like
; "syntax error" and "type mismatch" (D-2: reference wording is not copied).
; The string is HERE, not next to its table, because 17 bytes inserted there
; push page 1's dense forward `jr`s out of reach.
err_missing_operand:                        ; D-MSGENC: no phrase hit, 18 B -> 16 B.
                db      "missing operand",0 ; Shrinking here only IMPROVES the `jr`

; err_linebuf_overflow (the ERR 25 message, D-LINEMAX R-2) is NOT here, despite
; this file being the precedent for exactly this constraint. It did not fit: page
; 1 had 10 free bytes against a 42-byte need, so it lives in the LOW-REGION STRING
; POOL (basic/main.asm, before __MEAS_LOW_END) instead.
;
; ⚠️ ITS WORDING IS THE REFERENCE'S, not house-style lowercase. Every other message
; in this tree is deliberately our own (D-2), but `Line buffer overflow` was read
; VERBATIM off the reference's screen by the `tokx` battery and the gate compares
; the two machines' screens row for row -- so the measured string IS the spec.

; --- ex_locate: LOCATE [col][,[row][,cursor]] -------------------------------
; Modelled on ex_color (basic/screen.asm), the tree's other three-optional-
; comma-separated-argument statement, with four differences that are all
; measured (spec §3.2, characterization §3.2/§3.3):
;
;   * an OMITTED argument KEEPS the current value, so there is nothing to write
;     for one -- ex_color's bare form re-applies, LOCATE's simply does not move
;     that axis. `LOCATE 0` is a VALUE, not an omission.
;   * a bare `LOCATE` is **`Missing operand` (ERR 24)**, not a no-op and not a
;     Syntax error. So are `LOCATE ,`, `LOCATE ,,` and the trailing-comma form
;     `LOCATE 5,3,`. That is a distinct error and has to be raised as one.
;   * each argument goes through eval + get_byte_arg, which is ALREADY the
;     measured two-stage domain rule -- `Overflow` beyond int16, `Illegal
;     function call` outside 0..255 within it -- on all three arguments.
;   * ⚠️ PARSE ALL THREE, THEN APPLY -- which is the OPPOSITE of what the spec
;     directed, and the spec was wrong. §4 said "apply as you parse, do not
;     batch", inferring it from the one measured row `LOCATE 1,1,1,1`: that
;     moves the cursor to (1,1) and prints `Syntax error` THERE, so a rejected
;     argument plainly does not undo the accepted ones.
;
;     But that row only constrains a FOURTH argument, found after three valid
;     ones. It says nothing about a DOMAIN error inside the first three, and the
;     apply-as-you-parse build got that half wrong. Measured on the reference,
;     screen-dumped, after the gate flagged it:
;
;       CLS:LOCATE -1,0   message at row 0  (cursor never moved)
;       CLS:LOCATE 5,-1   message at row 0  <-- col 5 was NOT applied
;       CLS:LOCATE 0,-1   message at row 0  <-- col 0 was NOT applied
;
;     Apply-as-you-parse put the cursor at column 5 first, so the abort printed
;     from there and the gate read `ZB`-overwritten fragments. Both measurements
;     fit one model and only one: parse and domain-check up to three arguments,
;     APPLY them, and only then reject a fourth. Batching is the faithful one,
;     and it is also what makes an omitted axis free (see the seeding below).
;
; O-3 DEVIATION: the third argument is accepted, domain-checked (0..255 -- it is
; NOT restricted to 0/1, measured) and then IGNORED. Nothing in this tree reads
; CSRSW or any equivalent, so there is no mechanism for it to drive and storing
; it would be a write nobody reads. Recorded in the spec as a deviation.
ex_locate:
                inc     hl                  ; past the LOCATE token
                ; SEED FROM THE CURRENT POSITION. An omitted axis KEEPS its value
                ; (measured), and seeding makes that fall out with no present-flag
                ; per argument: an omitted axis is simply re-applied unchanged.
                ld      a,(CSRX)
                dec     a                   ; CSRX/CSRY are 1-BASED
                ld      (LOC_COL),a
                ld      a,(CSRY)
                dec     a
                ld      (LOC_ROW),a
                call    loc_next
                jr      nc,loc_row          ; `LOCATE ,row` -- column omitted
                ld      (LOC_COL),a
                call    loc_more
                jr      nc,loc_apply
loc_row:
                call    loc_next
                jr      nc,loc_cur          ; `LOCATE col,,cursor` -- row omitted
                ld      (LOC_ROW),a
                call    loc_more
                jr      nc,loc_apply
loc_cur:
                call    loc_next            ; the cursor argument: parsed and
                                            ; domain-checked, then dropped (O-3)
                call    loc_more
                jr      nc,loc_apply
                ; A FOURTH argument. Apply the first three FIRST, then reject --
                ; measured: `LOCATE 1,1,1,1` moves the cursor to (1,1) and prints
                ; `Syntax error` THERE.
                call    loc_apply_pos
                jp      stmt_error
loc_apply:
                call    loc_apply_pos
                jp      exec_stmt

; loc_apply_pos: write the parsed position, each axis clamped to the screen.
; Clamping is SEPARATE from the domain check: 0..255 is accepted (loc_next), and
; only then squeezed onto the console.
loc_apply_pos:
                ; column -> clamp to the CURRENT WIDTH, not a fixed 40. Measured:
                ; WIDTH 40 -> 40/41/255 all land at col 39; WIDTH 32 -> 32/39 both
                ; land at col 31. LINLEN is the live width.
                ld      a,(LOC_COL)
                ld      b,a
                ld      a,(LINLEN)
                dec     a                   ; A = the last usable column
                cp      b
                jr      nc,loc_col_set      ; wanted <= last -> keep it
                ld      b,a                 ; else clamp to the last column
loc_col_set:
                ld      a,b
                inc     a                   ; CSRX is 1-BASED
                ld      (CSRX),a
                ; row -> clamp to the console's bottom row (sysvars.inc
                ; CON_LASTROW; NOT CRTCNT, which measures 24 on both machines)
                ld      a,(LOC_ROW)
                cp      CON_LASTROW+1
                jr      c,loc_row_set
                ld      a,CON_LASTROW
loc_row_set:
                inc     a                   ; CSRY is 1-BASED
                ld      (CSRY),a
                ret

; loc_next: parse ONE argument position.
;   out: CF=1 -> A = the argument's byte value
;        CF=0 -> the argument was OMITTED and its comma has been consumed
;   Aborts directly on `Missing operand`, `Type mismatch` and either domain
;   error. HL advances.
; ⚠️ IT PARKS ITS OWN RETURN ADDRESS, and that is not a trick -- it is what makes
; the error paths correct. The abort chain (raise_error -> fre_abort_low, and
; type_mismatch_error) PRINTS AND THEN RETURNS, and it is built to return into
; the run loop: the stack has to look exactly as it did when exec_stmt jumped to
; this handler. A helper `call`ed from the handler is one frame deeper, so every
; abort inside it landed back INSIDE LOCATE, which carried on parsing and errored
; a second time. That is not a theory -- it is what the gate printed:
;
;   LOCATE          zb: missing operand / missing operand
;   LOCATE "5",3    zb: type mismatch / missing operand
;   LOCATE 0,-1     zb: Illegal function call, then overwritten by the prompt
;
; So the return address goes to LOC_RET for the duration and eval /
; get_byte_arg / raise_error all run at the handler's own depth, which is
; exactly how ex_width calls the same get_byte_arg.
loc_next:
                pop     de
                ld      (LOC_RET),de        ; park it: run at the HANDLER's stack depth
                call    skip_spaces         ; returns A = (HL)
                or      a
                jr      z,loc_missing       ; end of line at an argument position
                cp      COLON
                jr      z,loc_missing       ; `LOCATE :` / `LOCATE 5,3,:`
                cp      ','
                jr      z,loc_omit
                call    eval
                ld      a,(TMISMATCH)       ; `LOCATE "5",3` -> Type mismatch (measured)
                or      a
                jp      nz,type_mismatch_error
                ; --- the two-stage domain check, INLINE and not `call get_byte_arg` --
                ; ⚠️ get_byte_arg implements exactly this rule and CANNOT BE CALLED
                ; here, for a reason that turned out to be a live bug in the tree
                ; rather than a nicety. Its reject is `jp raise_error`, and the
                ; abort chain PRINTS AND RETURNS -- consuming the caller's own
                ; `call get_byte_arg` frame and landing back INSIDE the caller,
                ; just past the call, with A = the error code. Its existing
                ; caller ex_width therefore does `ld (LINLEN),a` with A=5 and
                ; re-inits the screen: `WIDTH 300` on this build prints nothing
                ; and CORRUPTS THE DISPLAY. Measured as the control while
                ; debugging LOCATE, recorded in TODO.md, not fixed here.
                ;
                ; Inline, at the handler's own depth (loc_next parked its frame),
                ; the same two `jp`s abort correctly: they return to the run loop.
                push    hl                  ; fac_to_int_strict clobbers HL
                call    fac_to_int_strict   ; DE = int16; FPERR set if |x| > 32767
                pop     hl
                ld      a,(FPERR)
                or      a
                jp      nz,fp_runtime_error ; stage 1: beyond int16 -> Overflow (ERR 6)
                ld      a,d
                or      a
                jr      nz,loc_illegal      ; stage 2: outside 0..255 -> ERR 5
                ld      a,e                 ; A = the accepted byte
                scf
                jr      loc_ret
loc_illegal:
                ld      a,5
                jp      raise_error         ; Illegal function call
loc_omit:
                inc     hl                  ; consume the comma
                or      a                   ; A is ',' -> CF = 0
loc_ret:
                ; Return to the parked address, preserving BOTH the cursor in HL
                ; and the CF/A the caller reads. push/ld/ex (sp),hl touch no
                ; flags, so the `scf` above survives to the caller.
                push    hl                  ; [cursor]
                ld      hl,(LOC_RET)
                ex      (sp),hl             ; stack = the parked address, HL = cursor
                ret
loc_missing:
                ld      a,24
                jp      raise_error         ; Missing operand -- a DISTINCT error from
                                            ; Syntax error, and measured as such

; loc_more: is another argument coming? CF=1 -> yes (its comma is consumed).
loc_more:
                call    skip_spaces
                cp      ','
                jr      z,loc_more_yes
                or      a                   ; CF = 0: no more arguments
                ret
loc_more_yes:
                inc     hl
                scf
                ret

    IF SWAP_RESIDENT
; --- ex_swap: SWAP a,b -----------------------------------------------------
; The only statement in the language that writes TWO lvalues, and the measured
; surface is almost entirely about the ASYMMETRY between them (spec §3.3):
;
;   B=1:SWAP A,B   creates A            -- the FIRST operand may be created
;   A=1:SWAP A,B   Illegal function call -- the SECOND must already exist
;   SWAP A,Q(0)    accepted on an UNDIMENSIONED Q -- so the rule is specifically
;                  about SCALAR creation order, not about creation as such
;
; That falls out of choosing the right routine per side -- var_alloc_or_find for
; the first, var_find_typed (which never allocates) for the second -- rather
; than being coded as a rule. It is bug-for-bug behaviour to reproduce, not to
; fix: the reference's own cause is almost certainly that allocating the second
; can shift the variable table and invalidate the pointer already taken for the
; first. We reproduce the BEHAVIOUR, not the mechanism.
;
; TYPE RULE: EXACT EQUALITY, not numeric-vs-string. `%` != `!` != `#` all raise
; Type mismatch, as does `A%` against a bare (`!`) name. DEFINT participates by
; changing what a bare name MEANS, and then the same rule applies.
;
; ⚠️ STRINGS MOVE DESCRIPTORS, NOT BODIES -- measured: LEN follows the value
; across the swap and survives a later allocation, and an aliased body (B$=A$)
; is undisturbed. So the exchange is a fixed-width byte swap of the value field
; and THE STRING HEAP IS NEVER TOUCHED. The width is the type for 2/4/8 and 3
; for a string descriptor, which is the whole of the type-to-width mapping.
; ⚠️ BOTH OPERANDS MUST START WITH A LETTER, and the check lives HERE rather than
; in sw_operand, for two independent reasons (both measured 2026-07-28, when the
; first full `swaperr` run came back 211/214):
;
;   ref                     zb before this check
;   SWAP A,1    Syntax error   Illegal function call, PLUS trailing output
;   SWAP 1,A    Syntax error   type mismatch
;   SWAP A,LEN("x")  Syntax error   Illegal function call, PLUS trailing output
;
; (1) sw_operand fed a literal or a function token straight into var_name_key,
;     which happily manufactured a key from it -- so the operand "existed" or did
;     not by accident, and the error came out of whichever later test tripped
;     first instead of out of "that is not a variable".
; (2) THE DEPTH IS THE OTHER HALF. sw_operand is `call`ed, and the abort chain
;     PRINTS AND RETURNS without resetting SP (docs/spec-basic-cursor-cluster.md
;     §4.1, D-CUR-D) -- so an abort raised inside it consumes sw_operand's own
;     frame and lands back HERE, in ex_swap, which swaps on and prints more. That
;     is the trailing output in rows 1 and 3, and it is exactly why loc_next parks
;     its return address in LOC_RET. Testing at the handler's own depth costs 6 B
;     per operand and needs no parking at all: `jp stmt_error` unwinds correctly
;     from here, the same way this routine's existing missing-comma reject does.
; skip_spaces leaves A = the current character, so the guard is two instructions.
ex_swap:
                inc     hl                  ; past the SWAP token
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error       ; operand 1 is not a name -> Syntax error
                xor     a
                ld      (SW_MODE),a         ; operand 1: MAY be created
                call    sw_operand
                ld      de,(SW_ADDR)        ; park operand 1 -- operand 2's parse runs a
                ld      (SW_ADDR1),de       ; nested eval() and keeps nothing in registers
                ld      a,(SW_TYPE)
                ld      (SW_TYPE1),a
                call    skip_spaces
                cp      ','
                jp      nz,stmt_error       ; `SWAP` / `SWAP A` -> Syntax error
                inc     hl
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error       ; operand 2 is not a name -> Syntax error
                                            ; (see the header: this must be tested at
                                            ; THIS depth, not inside sw_operand)
                ld      a,1
                ld      (SW_MODE),a         ; operand 2: must already EXIST
                call    sw_operand
                ; a third operand: `SWAP A,B,C` is Illegal function call, but a bare
                ; trailing comma `SWAP A,B,` is Syntax error -- both measured, and they
                ; differ, so the comma alone cannot decide it.
                call    skip_spaces
                cp      ','
                jr      nz,sw_types
                inc     hl
                call    skip_spaces
                or      a
                jp      z,stmt_error        ; `SWAP A,B,` -> Syntax error
                cp      COLON
                jp      z,stmt_error
                jp      sw_illegal          ; `SWAP A,B,C` -> Illegal function call
sw_types:
                ld      a,(SW_TYPE)
                ld      b,a
                ld      a,(SW_TYPE1)
                cp      b
                jp      nz,type_mismatch_error  ; EXACT type equality
                ; width: for 2/4/8 the width IS the type; only a string differs
                cp      1
                jr      nz,sw_width
                ld      a,3                 ; string: [len][ptr] descriptor
sw_width:
                ld      b,a
                push    hl                  ; guard the cursor across the exchange
                ld      hl,(SW_ADDR1)
                ld      de,(SW_ADDR)
sw_xloop:
                ld      a,(de)
                ld      c,(hl)
                ld      (hl),a
                ld      a,c
                ld      (de),a
                inc     hl
                inc     de
                djnz    sw_xloop
                pop     hl
                jp      exec_stmt

; sw_operand: resolve ONE operand at HL -> SW_ADDR (its VALUE address) and
; SW_TYPE. SW_MODE picks the scalar routine: 0 = var_alloc_or_find (may create),
; 1 = var_find_typed (never allocates -> Illegal function call when absent).
; An ARRAY element goes through ary_op0_resolve either way -- it auto-dims, which
; is exactly the measured `SWAP A,Q(0)` acceptance on an undimensioned Q, and it
; already maps subscript-out-of-range / illegal-function-call / syntax onto FPERR
; (measured: `SWAP A,Q(9)` on `DIM Q(2)` is Subscript out of range).
sw_operand:
                call    var_str_type        ; A = 1 iff the name has a `$` suffix
                ld      d,a                 ; (HL unmoved; D survives var_name_key --
                                            ; deftbl_lookup preserves BC/DE/HL)
                call    var_name_key        ; BC = key, HL past the name; (VARTYPE) =
                                            ; the resolved NUMERIC type
                ld      a,d
                or      a
                jr      nz,sw_typed         ; a `$` name is type 1, whatever VARTYPE says
                ld      a,(VARTYPE)
sw_typed:
                ld      (SW_TYPE),a
                ld      e,a                 ; E = type across the '(' peek
                ld      a,(hl)
                cp      '('
                jr      z,sw_array
                ; --- scalar: the entry's value field is entry+3 --------------
                push    hl
                pop     ix                  ; IX = the cursor; BOTH routines below
                                            ; GUARD IX across ary_engine_call
                ld      a,(SW_MODE)
                or      a
                ld      a,e                 ; A = type (both routines want it there)
                jr      nz,sw_must_exist
                call    var_alloc_or_find
                jp      nc,fp_runtime_error ; OOM -- FPERR already set by the engine
                jr      sw_value
sw_must_exist:
                call    var_find_typed
                jr      nc,sw_absent
sw_value:
                inc     hl
                inc     hl
                inc     hl                  ; HL = the value field (entry+3)
                ld      (SW_ADDR),hl
                push    ix
                pop     hl                  ; HL = the cursor again
                ret
sw_array:
                ld      a,e                 ; ary_op0_resolve wants the type in A,
                call    ary_op0_resolve     ; BC = key, HL = cursor at '('
                jp      nz,fp_runtime_error ; NZ: FPERR already mapped+set
                ld      (SW_ADDR),de        ; Z: DE = element addr, HL past ')'
                ret
sw_absent:
                ; the SECOND operand names a scalar that does not exist. Measured:
                ; `A=1:SWAP A,B` is Illegal function call, NOT an auto-created B.
                push    ix
                pop     hl                  ; restore the cursor for the abort
sw_illegal:
                ld      a,5
                jp      raise_error         ; Illegal function call
    ENDIF

; --- els_typecheck: D-MISS-1, the string-lvalue RHS type check --------------
; `A$=A` said `syntax error` where the reference says `Type mismatch`. The cause
; was localised and unglamorous: ex_let_str's only question was "is the RHS a
; string operand?", and everything else fell out of the parser. The numeric
; mirror (`A=A$`) was already right, because ex_let evaluates and then checks.
;
; ⚠️ THE FIX IS NOT "str_eval FAILED -> Type mismatch", AND THE MEASUREMENT SAYS
; SO. Four rows, taken before writing this (VG-8020 / zerobas-before):
;
;   A$=)     Syntax error      / syntax error
;   A$=      Missing operand   / syntax error
;   A$=+     Missing operand   / syntax error
;   A$=1/0   Division by zero  / syntax error      <-- the decisive one
;
; `A$=1/0` reports DIVISION BY ZERO, not Type mismatch. So the reference
; EVALUATES the right-hand side first and type-checks only a value it actually
; got -- the RHS's own error wins. Blanket Type-mismatch-on-failure would have
; matched the six d1 rows and been wrong on all four of these.
;
; So: evaluate as a numeric expression, let check_expr_errors abort on the RHS's
; own deferred error (FPERR div0/overflow/illegal/syntax, TMISMATCH), and only
; then call it a type mismatch.
;
; The last discriminator is "did the RHS parse as anything WELL-FORMED": `A$=`
; and `A$=+` have no operand at all, and must keep today's syntax error rather
; than acquire an invented Type mismatch. (The reference's `Missing operand` for
; those is a THIRD wording zerobas does not produce here -- not this slice's
; business, and unchanged by it.)
;
; ⚠️ "DID eval CONSUME ANY BYTES" IS THE WRONG TEST, and it was the first one
; written. `A$=+` reports Type mismatch under it: ev_f rejects the leading `+`
; without moving (a bare ERRMARK landmark, no FPERR), and then the BINARY-
; operator loop happily eats the `+` and asks for another factor -- so the
; cursor HAS advanced while nothing was parsed. Measured, not reasoned about
; after the fact: the row went from `syntax error` to `type mismatch`.
;
; What ev_f_err actually leaves is the $DD landmark in ERRMARK. That byte is
; normally set-only -- never cleared per statement -- so it cannot just be
; read. It CAN be cleared right here first: every path out of this routine
; raises an error, so no reader can observe the cleared value before the error
; that follows stamps its own landmark.
;
; ⚠️ Stack order is why check_expr_errors_popbc is NOT used: it pops the caller's
; saved word from UNDER its own return address. The saved word is dropped up
; front instead -- every path out of here errors, so it is dead either way --
; leaving the plain check_expr_errors with an ordinary frame.
;
; TWO ENTRIES, because the two string-lvalue forms carry DIFFERENT stack frames:
; the scalar path holds its saved dest key, the array-element path holds
; ary_snapshot_offset's [OFFSET] (which is why it uses its own elas_err /
; elas_abort_fp rather than the shared cepb_* routines -- vars.asm:647). Each
; entry discards its own one word and falls into the common tail.
elas_typecheck:                             ; Q$(0) = <non-string>
                pop     de                  ; discard [OFFSET], exactly as elas_err does
                jr      els_tc_common
els_typecheck:                              ; A$ = <non-string>
                pop     bc                  ; drop the dest key: every exit here errors
els_tc_common:
                xor     a
                ld      (ERRMARK),a         ; clear the landmark so it can be READ below
                call    eval                ; parse it as a NUMERIC expression
                call    check_expr_errors   ; the RHS's OWN error wins, and aborts
                ld      a,(ERRMARK)         ; ev_f_err's $DD -> no operand was parsed
                or      a
                jp      nz,stmt_error       ; -> syntax error, exactly as before
                jp      type_mismatch_error ; a real numeric RHS -> ERR 13

; --- ex_tron / ex_troff: TRON | TROFF ---------------------------------------
; A one-byte flag and one hook. Neither statement takes an argument -- `TRON 1`
; and `TROFF 1` are Syntax errors (measured), which falls out for free: the
; cursor is left ON the argument and exec_stmt's no-entry path rejects it.
ex_tron:
                ld      a,1
                jr      tr_set
ex_troff:
                xor     a
tr_set:
                ld      (TRACEFLAG),a
                inc     hl                  ; past the TRON/TROFF token
                jp      exec_stmt

; --- trace_line: emit `[<lineno>]` for the line about to run ----------------
; Called from run_program's FRESH-LINE-ENTRY point only (program.asm rp_lp); see
; the comment there for why a mid-line resume and a direct line never reach it.
;
; Format is measured (spec §3.4): '[' + the line number in DECIMAL, no padding,
; + ']', and **no newline of its own** -- so it appears inline at the cursor,
; which is what makes `PRINT "A";` followed by a traced line read as `A[30]`
; rather than putting the decoration on a line of its own.
;
; CURLINE is the line's LINK-field address, so the number is the 2-byte field at
; CURLINE+2 -- the same read print_in_lineno does for "break in <N>".
; ln_div_entry (list.asm) prints HL as a bare unsigned decimal; it clobbers
; A/BC/DE/HL and uses NUMBUF, which is safe here because NUMBUF is PRINT's
; format scratch and this runs BETWEEN statements, before any PRINT is live.
; pchar preserves every register, so only HL needs guarding.
trace_line:
                push    hl                  ; guard the token cursor
                ld      a,'['
                call    pchar
                ld      hl,(CURLINE)
                inc     hl
                inc     hl
                ld      e,(hl)              ; lineno LE -> DE
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = the line number
                call    ln_div_entry
                ld      a,']'
                call    pchar
                pop     hl
                ret


; ===========================================================================
; rerr_sparse2 — the SECOND sparse-code arm (D-NOTOPEN2)
; ===========================================================================
; in: A = ERRCODE. Reached only from rerr_sparse (basic/main.asm), which has
; already failed to match 52 and 59, which in turn is reached only when the code
; is past the dense err_msgtab (1..25). Falls through to rerr_unprintable exactly
; as rerr_sparse used to, so an unknown code is unchanged.
;
; WHY A SECOND ARM RATHER THAN THREE MORE LINES IN rerr_sparse: that routine and
; its two messages live in the page-0 LOW REGION, which had 23 B free; these three
; codes cost 72 B. Page 1 had 137 B after this slice's carve. The walls are
; co-mapped so a `jp` across them is ordinary and free ([[promotion-funds-low-
; region]] is the same trade in the other direction) -- so main.asm's low-region
; tail changed by ZERO bytes (`jp rerr_unprintable` -> `jp rerr_sparse2`) and all
; 72 B landed on the roomy wall.
;
; Sited at the END of the last include on purpose: inserting bytes mid-page-1
; lands between dense forward `jr`s and their targets and pasmo rejects it
; outright (see err_unprintable's note in basic/interp.asm).
;
; The three codes, all MEASURED on the CF-3300 (docs/spec-basic-gpfi-notopen-
; err59.md §2a), never guessed:
;   55  INPUT$ on any open channel that is not FOR INPUT, except RANDOM
;   58  GET/PUT on a DEVICE channel (LPT:/CRT:)
;   61  GET/PUT/FIELD on a disk channel that is open but not RANDOM, and
;       INPUT$ on a RANDOM channel
; ⚠️ FIELD on a device channel is ERR 5, not 58 -- it goes through err_msgtab
; like any dense code and needs nothing here.
rerr_sparse2:
                ld      hl,err_input_pastend
                cp      55
                jr      z,rsp2_go
                ld      hl,err_seq_only
                cp      58
                jr      z,rsp2_go
                ld      hl,err_bad_filemode
                cp      61
                jr      z,rsp2_go
                jp      rerr_unprintable    ; any other out-of-table code, unchanged
rsp2_go:
                jp      raise_error_hl      ; the SHARED trap decision -- so 55/58/61
                                            ; trap into an armed handler like 52/59
; D-MSGENC: only the third of these can use a phrase escape (MSGESC_FILE = "file ").
; The other two share no phrase with any existing message, so they are stored plain
; -- adding an escape for a phrase with ONE user costs more than it saves.
err_input_pastend:
                db      "input past end",0
err_seq_only:
                db      "sequential i/o only",0
err_bad_filemode:
                db      "bad ",MSGESC_FILE,"mode",0
