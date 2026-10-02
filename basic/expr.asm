; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; expr.asm — 16-bit integer expression evaluator.
;
; Evaluates an expression from the token/char stream. Grammar (small,
; precedence-climbing):
;
;   rel    := expr [ relop expr ]   (relop: < = > and compound <= >= <>)
;   expr   := term  { ('+' | '-') term }
;   term   := factor { '*' factor }
;   factor := const | letter(variable) | 'PEEK' '(' rel ')'
;           | 'VPEEK' '(' rel ')' | 'INP' '(' rel ')'
;           | 'VARPTR' '(' var ')' | 'BASE' '(' rel ')'
;           | '(' rel ')' | '-' factor
;
; A comparison yields -1 (true) or 0 (false). `eval` enters at `rel`; the bare
; arithmetic entry `ev_e` is still used where a relational makes no sense.
;
; The stream is the *crunched* token line (spec-tokens-statements.md §3/§4):
; constants arrive as their real MSX-BASIC tokens ($11+n digit, $0F+byte,
; $1C+word, $0C+word for &H) carrying a binary value; operators are tokens
; ('+' $F1, '-' $F2, '*' $F3); '(' ')' stay verbatim; PEEK is its two-byte
; function token ($FF $97); a variable is a single upcased letter. The evaluator
; *decodes* these tokens. All arithmetic is unsigned 16-bit, low-word on overflow.
;
; Clean-room: original code. POKE/PEEK *semantics* from the public MSX-BASIC
; language reference; the evaluator algorithm is our own. No disassembly.
;
; Cursor lives in IX throughout, which frees HL/DE/BC for arithmetic. The public
; wrapper converts to/from the caller's HL convention.

; --- inc_eval: `inc hl` then eval, as ONE call -----------------------------
; 💰 D-INCEVAL, the fourth instruction pair. `inc hl` / `call eval` — a handler
; stepping past its own token and evaluating what follows — stood at SEVENTEEN
; sites, 4 bytes each. This label is ONE byte and FALLS THROUGH into `eval`, so
; each site becomes a 3-byte `call inc_eval`: **-1 B per site**.
; 🟢 SAFE BECAUSE NOTHING FALLS INTO `eval` FROM ABOVE: it is the first code in
; expr.asm, and the file included before it (strvar.asm) ends in an unconditional
; `ret`. Both halves were checked before the byte went in — the include order is
; what makes the second half a question at all.
; 🎯 `call inc_eval` returns to the SITE, not here: the fall-through means eval's
; own `ret` unwinds to whoever called inc_eval, exactly as `call eval` did.
inc_eval:
                inc     hl

; --- eval: HL = cursor in -> DE = value, HL advanced past the expression -----
; Preserves the caller's IX. Clobbers A, BC, DE, HL.
eval:
                push    ix
                push    hl
                pop     ix                  ; IX = cursor
                call    set_factyp2
                                           ; §9.4: eval() sets FACTYP=2 (int) on entry
                call    ev_logic            ; lowest precedence layer
                push    ix
                pop     hl                  ; HL = cursor (advanced)
                pop     ix
                ret

; --- logical / bitwise layers (lowest precedence, left-assoc) --------------
; MSX-BASIC precedence below the relationals, MEASURED against the VG-8020 by
; probes/basic/basic_probe_logicops.py (every ordered pair, three lines each --
; the bare form plus BOTH explicit parenthesisations, verdict from which control
; the bare form matched):
;
;     NOT (unary)  >  AND  >  OR  >  XOR == EQV  >  IMP
;
; XOR and EQV are UNOBSERVABLE against each other -- they are mutually
; associative, so no operand triple can order them and the implementation is
; free to pick. All six are 16-bit bitwise; they also implement logical tests on
; the -1/0 results the relationals produce. Tokens: AND $F6, OR $F7, XOR $F8,
; EQV $F9, IMP $FA, NOT $E0.
;
; A TABLE-DRIVEN LAYER, which fits SIX levels into less space than the original
; hand-rolled THREE-level chain it replaced (that chain survived until 2026-07-29
; only because the retired lean 16 KB cart was byte-frozen and shipped no EQV/IMP).
; --- table-driven logical layer (repack build) -----------------------------
; `ev_and_lp`/`ev_or_lp`/`ev_xor_lp` were byte-for-byte uniform at 31 B each and
; differed only in a token compare and a 6-byte apply block (clone_scout: 5 x 31 B).
; Adding EQV and IMP as two more copies would have cost +68 B; one generic layer
; walking a precedence table costs LESS than the three copies it replaces.
;
; The level is a POINTER into logtab, carried in HL and pushed across recursion,
; so no index arithmetic is needed: the next-tighter level is simply the next
; 3-byte entry, and the $00 terminator is what drops through to unary NOT.
ev_logic:
                ld      hl,logtab           ; loosest level (IMP)
ev_lg:
                ld      a,(hl)
                or      a
                jr      z,ev_not            ; past the tightest layer -> NOT / relational
                push    hl
                call    ev_lg_next          ; DE = lhs, from the tighter level
                pop     hl
ev_lg_lp:
                call    ev_sp
                cp      (hl)                ; this level's operator token?
                ret     nz
                ; The level pointer must be SAVED BEFORE the conversion call:
                ; fac_to_int_strict_reset clobbers HL ("clobbers as
                ; fac_to_int_strict, +A", float-arith.asm). The hand-rolled
                ; layers got away without this because their level was implicit
                ; in the code position and HL was dead here -- carrying it in a
                ; register is exactly what makes the table-driven form need the
                ; guard. Missing it derails the interpreter into garbage on
                ; EVERY float operand (`2.7 AND 0`), while every integer operand
                ; keeps working: a green build that crashes the moment it runs.
                push    hl                  ; [level] -- MUST outlive the call
                ; spec §10.3 "strict int16 domain", exactly as the hand-rolled
                ; layers did it: convert the operand NOW and reset FACTYP=2 so a
                ; float does not leak into the rhs eval. No FAC save is needed --
                ; the conversion happens before the rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
                inc     ix
                push    de                  ; [lhs]
                call    ev_lg_next          ; DE = rhs
                call    fac_to_int_strict_reset
                pop     hl                  ; HL = lhs
                ex      (sp),hl             ; HL = level, (sp) = lhs
                push    hl                  ; [level]
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = this level's apply leaf
                pop     hl                  ; HL = level
                ex      (sp),hl             ; (sp) = level, HL = lhs
                call    lg_apply            ; DE = lhs OP rhs
                pop     hl                  ; HL = level
                jr      ev_lg_lp            ; left-assoc (MEASURED: IMP is the
                                            ; only level where that is observable)
ev_lg_next:
                inc     hl
                inc     hl
                inc     hl                  ; -> the next-tighter entry
                jr      ev_lg

; lg_apply: HL = lhs, DE = rhs, BC = apply leaf -> DE = result.
; The byte loop is shared; each leaf is the 2-3 byte ALU core that actually
; distinguishes the six operators. `ld e,d` slides the rhs high byte into E so
; every leaf can name its operand as `e` in both passes.
lg_apply:
                ld      a,l
                call    lg_go
                ld      l,a
                ld      a,h
                ld      e,d
                call    lg_go
                ld      h,a
                ex      de,hl               ; DE = result
                ret
lg_go:          push    bc
                ret                         ; jump to (BC); the leaf rets to us

lg_and:         and     e
                ret
lg_or:          or      e
                ret
lg_xor:         xor     e
                ret
lg_eqv:         xor     e
                cpl                         ; EQV = NOT (a XOR b)   [MEASURED]
                ret
lg_imp:         cpl
                or      e                   ; IMP = (NOT a) OR b    [MEASURED]
                ret

; The precedence table: LOOSEST first, `db token, dw leaf`, $00-terminated.
; EQV sits looser than XOR only because something had to; the two are measurably
; indistinguishable (see the header), so this is a free choice, not a claim.
logtab:
                db      IMP_TOKEN
                dw      lg_imp
                db      EQV_TOKEN
                dw      lg_eqv
                db      XOR_TOKEN
                dw      lg_xor
                db      OR_TOKEN
                dw      lg_or
                db      AND_TOKEN
                dw      lg_and
                db      0                   ; terminator -> drop to ev_not
ev_not:
                call    ev_sp
                cp      NOT_TOKEN
                jr      z,ev_not_do
                jr      ev_rel              ; no NOT -> drop to the relational layer
ev_not_do:
                call    stk_guard           ; D-STACKFLOOR: a NOT chain recurses HERE,
                                            ; never through ev_f
                inc     ix
                call    ev_not              ; unary, right-assoc (NOT NOT x)
                call    fac_to_int_strict_reset
                ld      a,e
                cpl
                ld      e,a
                ld      a,d
                cpl
                ld      d,a                 ; DE = ~DE (ones complement)
                ret

; --- ev_rel: relational layer ----------------------------------------------
; rel := arith [ relop arith ]   (relop is one or two of  <  =  > ).
; A comparison yields -1 (true) or 0 (false), per MSX-BASIC, using a signed
; 16-bit compare. Relop tokens: '<' $F0, '=' $EF, '>' $EE (Table 2.20); the
; compound forms (<=, >=, <>) arrive as two operator tokens and are merged.
ev_rel:
                ; string-compare S2 (repack build only): probe the LHS for a
                ; string operand before committing to the numeric ev_e below.
                ; BUG C (Fable, 2026-07-17): the old "NC => IX intact" invariant
                ; DIED with slice-4a. str_eval sub-paths now CALSLT (which loads
                ; IX before the ROM call) and then return NC -- str_fn_left/right/
                ; mid on a missing ','/')' , str_concat_tail on a malformed
                ; trailing operand, str_fn_string. Falling into ev_e with that
                ; garbage IX parsed from nowhere (PRINT LEFT$("AB") -> " 0"). So
                ; GUARD IX across the probe and RESTORE it on the NC (numeric)
                ; fallthrough; the CF (string) path discards the guard, since
                ; ev_rel_str re-derives IX from the returned HL. (The string-ARRAY
                ; path str_eval_arr also clobbers IX but always returns CF -> it
                ; only reaches evr_lhs_str, never the NC restore.)
                push    ix                  ; [guard] the cursor across str_eval
                call    str_eval_ix         ; CF set -> LHS is a string; STRPTR->desc
                jr      c,evr_lhs_str       ; string LHS -> discard guard, str path
                pop     ix                  ; NC: restore the cursor str_eval trashed
                call    ev_e                ; DE = lhs (arithmetic)
evr_scan:
                ; MEASURED (docs/logicops-vg8020-characterization.md §6): MSX-BASIC
                ; CHAINS relationals, left-associatively -- `1 = 0 = 0` is
                ; `(1 = 0) = 0` = -1, NOT a syntax error and NOT two values. Every
                ; comparison loops back here with its own -1/0 result as the next
                ; LHS, which is always numeric, so the LHS string probe above is
                ; correctly outside the loop while the RHS probe at evr_rhs is
                ; inside it (`1 = 1 = "A"` -> Type mismatch, as the reference does).
                call    ev_sp
                call    relop_bit
                ret     nc                  ; no relational operator -> plain value
                ld      c,b                 ; C = requested relation bits
                call    ixsp                ; D-IXSP
                call    relop_bit           ; a second relop? (<=, >=, <>)
                jr      nc,evr_rhs
                ld      a,c
                or      b
                ld      c,a                 ; merge the two relation bits
                inc     ix
evr_rhs:
                ; D-2 symmetric case (`5 < A$`): the LHS was just confirmed numeric (we
                ; only reach evr_rhs via the unchanged ev_e call above), so probe the RHS
                ; cursor for a string operand BEFORE ev_e reads it as a number -- ev_f_var
                ; would otherwise silently read A$'s name-keyed numeric shadow cell instead
                ; of erroring. BUG C (Fable, 2026-07-17): as with the LHS probe,
                ; a slice-4a str_eval sub-path can CALSLT then return NC, trashing
                ; IX -- so GUARD IX across the probe and restore it before both the
                ; NC fallthrough (ev_e reads IX) and the CF exit (evr_mismatch's
                ; deferred error wants a coherent cursor, not CALSLT garbage).
                push    bc
                push    de
                push    ix                  ; [bc][de][guard]
                call    str_eval_ix
                pop     ix                  ; restore the cursor str_eval may have trashed
                pop     de
                pop     bc
                jr      c,evr_mismatch      ; RHS is a string, LHS was numeric -> D-2
                push    de                  ; lhs
                ; spec §10.1: relationals over any float operand compare AS
                ; floats after widening (never int-converted, `40000=40000!`
                ; -> -1, no Overflow). Save the LHS's FACTYP+FAC on the
                ; machine stack (same fixed-size frame protocol as the ev_e/
                ; ev_t double-arithmetic sites) before the rhs eval clobbers
                ; FAC, then reset FACTYP=2 for the rhs eval.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                push    bc                  ; relation bits (in C)
                call    ev_e                ; DE = rhs
                pop     bc                  ; C = bits
                call    combine_cmp         ; pops the lhs frame + value; A =
                                            ; relation bit (1/2/4); FACTYP:=2
                ld      de,0                ; false = 0
                and     c                   ; intersect requested with actual
                jr      z,evr_chain
                dec     de                  ; true = -1 ($FFFF)
evr_chain:
                jr      evr_scan            ; and look for the NEXT relop (left-assoc)
evr_lhs_str:
                pop     af                  ; BUG C: drop the LHS-probe IX guard
                                            ; (ev_rel_str re-derives IX from HL)
                jp      ev_rel_str
evr_mismatch:
                jp      type_mismatch_set   ; sets ERRMARK+TMISMATCH, DE=0, ret (str-engine.asm)

; --- relop_bit: A = token -> CF set & B = relation bit, else CF clear -------
; '<' -> 1 (less), '=' -> 2 (equal), '>' -> 4 (greater).
relop_bit:
                cp      LT_TOKEN
                jr      z,rb_lt
                cp      EQ_TOKEN
                jr      z,rb_eq
                cp      GT_TOKEN
                jr      z,rb_gt
                or      a                   ; CF clear -> not a relop
                ret
rb_lt:
                ld      b,1
                scf
                ret
rb_eq:
                ld      b,2
                scf
                ret
rb_gt:
                ld      b,4
                scf
                ret

; --- cmp16_bits: signed compare HL(lhs) vs DE(rhs) -> A = 1/2/4 -------------
; 1 = lhs<rhs, 2 = equal, 4 = lhs>rhs. Clobbers A, HL, flags (DE preserved).
;
; HOME (subrom-mathpack migration, 2026-07-13): NOT here in page 1, but in the
; page-0 low region (basic/float-arith.asm), so the fp_sqrt PAGE-1 sub-ROM tenant's
;     page-0-resident float core can still reach it while main-ROM page 1 is
;     switched out (see float-arith.asm's cmp16_bits header). All callers here
;     (ev_rel etc.) resolve to that page-0 copy by label, unchanged.

; --- ev_sp: skip spaces in the IX stream -----------------------------------
; ⚠️ ev_sp RETURNS THE CHARACTER IN A, AND ALL 36 CALL SITES DEPEND ON IT.
; Its only exit is the `ret nz` below, which is reached with A = (ix+0) -- the
; first non-space byte -- and with the flags of `cp ' '` (always NZ). So a
; `call ev_sp` needs NO `ld a,(ix+0)` after it; every site used to carry one
; anyway, 3 B each.
; ⚠️ THE COUNT HERE SAID **24** FOR A DAY, AND THAT WAS THE WHOLE DEFECT.
; D-EVSPDUP measured "72 B in this file alone" and carved expr.asm's 24 sites --
; correctly, and the wording was honest about its scope -- but NINE MORE SITES
; sat in basic/str-engine.asm and basic/usr.asm, and a header that counts one
; file reads like a count of the tree. D-LOADSWEEP carved those nine for a
; further 27 B (18 LOW + 9 page 1) and the number above is now the whole tree.
; ✅ AND THE CONTRACT IS GATED NOW, which it was not when this comment claimed
; "there is no gate on a register contract": `make redundant-load-check`
; (tools/redundant_load_sweep.py) proves this routine's shape mechanically and
; FAILS on any `call ev_sp` that still reloads (ix+0). Anything added here that
; can return by another route, or with A holding something else, still breaks
; all 36 silently -- the sweep proves the SHAPE, not the intent -- so keep the
; single exit.
ev_sp:
                ld      a,(ix+0)
                cp      ' '
                ret     nz
                inc     ix
                jr      ev_sp

; --- ev_e: expr := mod-term { (+|-) mod-term } -----------------------------
; Operators are tokens: '+' = PLUS_TOKEN ($F1), '-' = MINUS_TOKEN ($F2). The
; operands are MOD-expressions (MSX precedence: + - is below MOD, \, * /).
ev_e:
                call    ev_mod              ; DE = first term
ev_e_lp:
                call    ev_sp
                cp      PLUS_TOKEN
                jr      z,ev_e_add
                cp      MINUS_TOKEN
                jr      z,ev_e_sub
                ret
ev_e_add:
                inc     ix
                push    de                  ; lhs
                ; spec §1 bullet 4: save the lhs's FACTYP+FAC on the machine
                ; stack (fixed-size frame) before the rhs eval clobbers FAC,
                ; reset FACTYP=2 for the rhs eval. combine_add decides int-
                ; fast-path (with signed-overflow-promotion) vs BCD add.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_mod              ; DE = rhs
                call    combine_add         ; pops the frame; DE = result
                jr      ev_e_lp
ev_e_sub:
                inc     ix
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_mod              ; DE = rhs
                call    combine_sub
                jr      ev_e_lp

; --- ev_mod: { MOD } over '\'-expressions (MSX precedence level 5) ----------
ev_mod:
                call    ev_idiv             ; DE = lhs
ev_mod_lp:
                call    ev_sp
                cp      MOD_TOKEN
                ret     nz
                ; spec §10.3: \ / MOD operands convert via the STRICT int16
                ; domain (not the address domain) -- immediately, no FAC save
                ; needed since the plain int value is captured before the
                ; rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_idiv             ; DE = rhs (divisor)
                call    fac_to_int_strict_reset
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    signed_mod_de_bc    ; D-C: MSX-signed MOD (spec §10.4)
                jr      ev_mod_lp

; --- ev_idiv: { '\' } over terms (integer division, level 4) ---------------
ev_idiv:
                call    ev_t                ; DE = lhs
ev_idiv_lp:
                call    ev_sp
                cp      IDIV_TOKEN          ; '\'
                ret     nz
                call    fac_to_int_strict_reset
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_t                ; DE = rhs (divisor)
                call    fac_to_int_strict_reset
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    signed_div_de_bc    ; D-C: MSX-signed \ (spec §10.4)
                jr      ev_idiv_lp

; --- ev_t: term := factor { ('*' | '/') factor } ---------------------------
; '/' is real division on MSX, and always float here (spec §10.1).
ev_t:
                call    ev_pw               ; `^` binds above * / (§13.3)
ev_t_lp:
                call    ev_sp
                cp      STAR_TOKEN          ; '*'
                jr      z,ev_t_mul
                cp      DIV_TOKEN           ; '/'
                jr      z,ev_t_div
                ret
ev_t_mul:
                inc     ix
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_pw               ; DE = rhs
                call    combine_mul
                jr      ev_t_lp
ev_t_div:
                inc     ix
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_pw               ; DE = rhs
                call    combine_div_float   ; ALWAYS float (spec §10.1)
                jr      ev_t_lp

; --- ev_pw: `^` layer (power operator, math pack slice 2c, repack-only -----
; docs/spec-basic-mathpack-slice2.md §13.3). Sits between ev_t and ev_f:
; binds ABOVE `*`/`/` (ev_t's three operand sites above call ev_pw instead of
; ev_f) and ABOVE unary minus (ev_f_neg's operand call below becomes ev_pw
; too) -- this single change yields BOTH `-2^2`=-4 (ev_f_neg negates the
; WHOLE pow-chain, never just the base) AND `2^-3^2`=2^-(3^2) (the exponent's
; own unary minus recurses into ev_pw, giving the pinned right-nesting for
; free -- no special case needed). LEFT-associative loop (`2^3^2`=64,
; `2^2^3`=64): each `^` pops the running lhs and combines immediately, same
; shape as ev_t_mul/ev_t_div above.
ev_pw:
                call    ev_f
ev_pw_lp:
                call    ev_sp
                cp      POW_TOKEN
                ret     nz
                inc     ix
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_f                ; rhs (ev_f's own unary-minus ->
                                            ; ev_pw call below gives the
                                            ; pinned right-nesting for free)
                call    combine_pow
                jr      ev_pw_lp            ; loop = left-assoc

; --- ev_f: factor ----------------------------------------------------------
; Decodes the crunched tokens (spec §3): constant tokens carry their binary
; value; '(' / ')' stay verbatim; PEEK is $FF $97; a bare upcased letter is a
; variable; unary minus is MINUS_TOKEN.
ev_f:
                call    stk_guard           ; D-STACKFLOOR: no recursion below the floor
                call    ev_sp
                ; empty parenthesised/argument expression: a factor can never
                ; begin with a closing ')' or a ',' (ev_f is reached only where a
                ; factor is REQUIRED -- expression start, or right after '(' /
                ; a binary operator / a function open-paren), so such a delimiter
                ; here is a missing operand. Raise the deferred "syntax error"
                ; (D-F2-3), matching the reference's `SQR()`/`()`/`(5+)`/`(,)`
                ; Syntax error (spec-basic-empty-expr-syntax-error.md).
                cp      ')'
                jp      z,ev_f_empty
                cp      ','
                jp      z,ev_f_empty
                cp      MINUS_TOKEN         ; unary minus
                jp      z,ev_f_neg
                cp      PLUS_TOKEN          ; unary plus (D-UNARYPLUS)
                jp      z,ev_f_pos          ; ⚠️ `jp`, not `jr`: ev_f_pos sits
                                            ; beside ev_f_neg, ~390 B away
                cp      '('
                jp      z,ev_f_paren
                cp      PEEK_PREFIX         ; $FF -> PEEK / VPEEK / INP function token
                jp      z,ev_f_ff
                cp      USR_TOKEN           ; $DD -> USR[n](arg) function
                jp      z,ev_usr
                cp      FN_TOKEN            ; $DE -> FN<name>[(args)] (D-DEFFN)
                jp      z,ev_fn
                cp      VARPTR_TOKEN        ; $E7 -> VARPTR(var) function
                jp      z,ev_f_varptr
                cp      BASE_TOKEN          ; $C9 -> BASE(n) function
                jp      z,ev_f_base
                cp      INSTR_TOKEN         ; $E5 -> INSTR([p,]a$,b$) (string-functions
                jp      z,ev_f_instr        ; Group C; single-byte token, not $FF-prefixed)
                ; error-handling S2a (docs/spec-basic-error-handling-s2a-packet.md
                ; §3/(f)): ERR/ERL, single-byte value tokens, same shape as
                ; VARPTR/BASE/INSTR above.
                cp      ERR_TOKEN           ; $E2 -> ERR (last error's MSX ERR code)
                jp      z,ev_f_errfn        ; ⚠️ `jp`, not `jr`, for the SAME reason as the
                                            ; ERL arm below -- and it went over on the same
                                            ; KIND of edit: D-NUMSTR's 4 bytes at
                                            ; ev_f_missop, which sits between this arm and
                                            ; its target, exactly as D-PLAYFN's PLAY arm did
                                            ; to ERL. +1 B.
                cp      ERL_TOKEN           ; $E1 -> ERL (last error's line, 65535=direct)
                ; ⚠️ `jp`, not `jr`: this arm sat ~170 lines from its target and was
                ; already at the edge of relative range. D-PLAYFN's 5-byte PLAY arm
                ; below pushed it over ("Relative jump out of range on line 504"),
                ; so the +1 B is part of PLAY(n)'s price, not a free change.
                jp      z,ev_f_erlfn
                cp      TIME_TOKEN          ; $CB -> TIME (JIFFY as an UNSIGNED word)
                jp      z,ev_f_time
                cp      CSRLIN_TOKEN        ; $E8 -> CSRLIN (0-based cursor row)
                jp      z,ev_f_csrlin       ; ⚠️ `jp`, not `jr`: the THIRD arm in this chain
                                            ; to need it, and D-NUMSTR pushed two of them
                                            ; over at once. 🎯 THIS DISPATCH CHAIN IS AT ITS
                                            ; RELATIVE-RANGE LIMIT -- assume ANY insertion
                                            ; between it and ev_f's tail costs +1 B per
                                            ; surviving `jr`, and check before pricing a
                                            ; slice that lands here. +1 B.
                ; D-ATTRFN: ATTR$ ($E9) is TOKENISED and then refused on sight —
                ; ERR 5 on both references, for the bare word, as an r-value and
                ; with an argument alike. `ev_f_attr` is a 0-byte `equ` alias of
                ; `gb_illegal` below; sited next to CSRLIN because the tokens are
                ; adjacent ($E8/$E9), not because the verbs are related.
                ; 💰 EXACTLY 5 B, AND THE CHAIN'S OWN WARNING NO LONGER ADDS TO IT.
                ; The caution above says to assume an insertion costs +1 B per
                ; surviving `jr` — MEASURED 2026-09-08, this chain has **zero** `jr`
                ; arms left, every one having already been converted by D-NUMSTR and
                ; D-PLAYFN. The caution stands for the day a `jr` reappears; today
                ; its price is nil, so do not pad a slice that lands here.
                cp      ATTR_TOKEN          ; $E9 -> ATTR$, tokenised then ERR 5
                jp      z,ev_f_attr
                cp      POINT_TOKEN         ; $ED -> POINT(x,y) (graphics G2, graphics.asm)
                jp      z,ev_f_point
                cp      PLAY_TOKEN          ; $C1 -> PLAY(n) background-queue status
                jp      z,ev_f_play         ; (D-PLAYFN, basic/play.asm)
    IF G8_RESIDENT
                cp      VDP_TOKEN           ; $C8 -> VDP(n) (graphics G8, graphics.asm)
                jp      z,ev_f_vdp
    ENDIF
                ; D-LNREF R-E (docs/spec-basic-lnref.md §3.2): $0B..$0E are ONE
                ; FAMILY in the crunched stream -- a token followed by a 2-byte
                ; little-endian value. $0B &O, $0C &H, $0D line ADDRESS, $0E line
                ; NUMBER. A range costs 9 B where the two separate `cp/jp` pairs it
                ; replaces cost 10, so $0E is gained at NET -1 B on main page 1 --
                ; which had 5 B free, i.e. a third `cp/jp` pair would have taken all
                ; of it.
                ;
                ; ⚠️ WHY THE EVALUATOR NEEDS $0E AT ALL: `IF ERL=100` puts a
                ; line-number reference inside an ORDINARY EXPRESSION on both
                ; references (docs/lnref-msx1-characterization.md §1.3). Arming ERL in
                ; branch_lineno without this arm would BREAK a shape that works today;
                ; `lnrd-erl` is the control that is green before and after, and knife
                ; K4 removes this arm to show it is the row that says so.
                ;
                ; ⚠️ $0D RIDES ALONG AND IS UNREACHABLE. LINEADDR_TOKEN is the
                ; post-RUN address form; zerobas never emits it (sysvars.inc is its
                ; only mention), so no row can reach that arm. It is in because the
                ; range IS the family -- excluding it would cost bytes to express a
                ; distinction nothing can observe.
                cp      OCT_TOKEN           ; below $0B -> not a 2-byte literal
                jr      c,ev_f_notword
                cp      LINENO_TOKEN+1      ; $0B..$0E -> 2-byte LE value
                jp      c,ev_f_word
ev_f_notword:
                cp      INT2_TOKEN          ; $1C -> 2-byte LE value
                jp      z,ev_f_word
                cp      INT1_TOKEN          ; $0F -> 1-byte value
                jp      z,ev_f_byte
                cp      SNG_TOKEN           ; $1D -> single float literal (basic/float.asm)
                jp      z,ev_f_float
                cp      DBL_TOKEN           ; $1F -> double float literal
                jp      z,ev_f_float
                cp      INT_DIGIT_BASE      ; $11
                jr      c,ev_f_var
                cp      $1A+1               ; $11..$1A -> digit token
                jr      c,ev_f_digit
                ; fall through: letter -> variable (or error)
ev_f_var:
                ld      a,(ix+0)
                call    is_letter           ; must start with a letter
                jr      nc,ev_f_missop      ; D-MISSOP: THE missing-operand site
                push    ix
                pop     hl                  ; HL = cursor
                call    var_name_key        ; BC = key, HL past the (multi-char) name
                ; D-DEFSTR (docs/spec-basic-deftbl-strcode.md §4 F3): a DEFSTR'd
                ; unsuffixed name is a STRING, and reaching a numeric factor with
                ; one is ERR 13 on both references. ev_rel's own str_eval probe
                ; catches this only at the TOP of an operand, so `B=S` errored and
                ; `B=1+S` silently read 0 -- measured, spec §3.1. Placed BEFORE the
                ; '(' dispatch so it covers ev_f_arr too. Clobbers A only.
                call    check_vartype_num
                ld      a,(hl)
                cp      '('
                jp      z,ev_f_arr          ; array-element rvalue (arrays slice-1,
                                            ; docs/spec-basic-arrays.md §9.4/§10: ev_f
                                            ; reaches ev_f_var only for a plain letter,
                                            ; never a function token, so a '(' right
                                            ; after a plain name is unambiguously a
                                            ; subscript, not a function call)
                push    hl
                pop     ix                  ; IX = advanced cursor
                ld      a,(VARTYPE)         ; F3: resolved type from var_name_key
                jp      var_load_fac        ; FAC/FACTYP=type, DE=int16 (tail call)
ev_f_tmm:                                   ; deferred FPERR=10 "type mismatch" for a string
                                            ; function given a NON-string arg (LEN(5)/ASC(5)/
                                            ; VAL(5)): str_eval returned NC with FPERR clean.
                                            ; First-error-wins keeps an inner error (a nested
                                            ; malformed string fn like LEN(LEFT$("AB")) already
                                            ; set FPERR=4 -> stays syntax error). fre_msgtab
                                            ; entry 10 = err_type_mismatch (interp.asm), the
                                            ; same house-lowercase "type mismatch" the D-2
                                            ; comparator prints; ref = capitalised.
                ld      e,10
                jr      ev_f_defer
ev_f_ifc:                                   ; deferred FPERR=3 "illegal function call" for a
                                            ; function-domain VALUE error whose operand parsed
                                            ; cleanly but is out of range (INSTR p<1, ASC(""))
                                            ; -- was a bare ev_f_err (ERRMARK only, no FPERR)
                                            ; -> silent " 0". Same first-error-wins + DE=0
                                            ; contract as ev_f_empty; mirrors SQR(x<0)/LOG
                                            ; (FPERR=3, house-lowercase). E is a dead code
                                            ; carrier -- ev_f_err zeroes DE below.
                ld      e,3
                jr      ev_f_defer
ev_f_missop:                                ; D-MISSOP (docs/spec-basic-missop.md §5/§13):
                                            ; a factor was REQUIRED and what is here cannot
                                            ; start one -- end of line, ':', or a stray
                                            ; operator. Both references call that `Missing
                                            ; operand` (ERR 24) at every such slot, measured
                                            ; at 16 of them; before this, ev_f_err returned
                                            ; DE=0 with only the ERRMARK landmark, so
                                            ; `POKE &HE000,` COMPLETED and WROTE A ZERO.
                                            ; 🔴 IT IS ITS OWN LABEL, NOT A LINE ADDED TO
                                            ; ev_f_err, AND A SHIPPED GATE IS WHY. The first
                                            ; draft sat on that shared tail -- which had
                                            ; EIGHT jump sites, only ONE of them this one.
                                            ; `make lineerr-acceptance` went 209/210: row
                                            ; a.noclose (`LINE (11,12-(20,21)`) reaches
                                            ; expr.asm's `cp ')' / jp nz,ev_f_err` for a
                                            ; parenthesised expression closed by ',', and
                                            ; BOTH references call that Syntax error (2).
                                            ; Reached only from ev_f_var's `is_letter`
                                            ; failure. Same `ld e,<code> / jr ev_f_defer`
                                            ; idiom as ev_f_tmm / ev_f_ifc above.
                ; D-NUMSTR (docs/spec-basic-numstr.md): a STRING LITERAL where a
                ; numeric factor is required is a TYPE MISMATCH, not a missing
                ; operand. `5+"AB"` read ERR 24 and both references answer 13 --
                ; so do `-"AB"`, `5-"AB"`, `5*"AB"` and `5/"AB"`.
                ; 🎯 IT ALSO FIXES `5+LEFT$("AB",1)` WITHOUT TOUCHING IT: that
                ; reaches ev_ff_strnum, whose D-LEFTTM arm evaluates the argument
                ; numerically, and THAT inner eval landed here on the `"` and
                ; deferred 24 -- which first-error-wins then kept over the type
                ; mismatch. Measured: the row was ERR 2 before D-LEFTTM and ERR 24
                ; after, one wrong code for another, and no row saw it because the
                ; probe had no string function inside a numeric expression.
                ; 🟢 A is still the offending byte here -- is_letter restores it on
                ; both paths -- and this site is reached ONLY from ev_f_var's
                ; is_letter failure (see the note above).
                ; ⚠️ SITED HERE, NOT IN THE DISPATCH CHAIN, AND THAT IS NOT STYLE.
                ; Five bytes added up there pushed TWO neighbouring `jr` arms out
                ; of relative range -- the same thing D-PLAYFN's 5-byte PLAY arm
                ; did to the ERL arm, which is written up two screens above. This
                ; site is past every one of them.
                ; ⚠️ A LITERAL CANNOT CARRY A PENDING FAULT, so unlike D-LEFTTM /
                ; D-INSTRTM / D-STRTM there is nothing to evaluate first; and
                ; ev_f_defer is still first-error-wins, so `(0*(1/0)+1)+"AB"` keeps
                ; its Division by zero.
                cp      '"'
                jr      z,ev_f_tmm          ; -> ERR 13
                ; 🔴 MISSING OPERAND IS FOR AN EMPTY SLOT, NOT FOR A WRONG ONE
                ; (D-MISSOPBOUND, docs/spec-basic-missopbound.md). The comment
                ; above says "end of line, ':', or a stray operator" -- the first
                ; two are right and THE THIRD IS NOT. Measured on 18 rows, both
                ; references split them:
                ;   `X=` and `X=:`            -> ERR 24  nothing is there
                ;   `X=*5` `X=TAB(5)` `X=THEN` `X=GOTO` `X=PRINT` `X=TO`
                ;   `X=STEP` `X=INPUT` `X=USING`  -> ERR 2, something IS there
                ; zerobas answered 24 to all of them, so NINE token classes were
                ; wrong, not the three `cursor-acceptance` happens to name.
                ; 🟢 `X=ELSE` reads 24 on all three and is NOT an exception: MSX
                ; tokenises ELSE as `:ELSE`, so the slot really does see a colon.
                ; That row is what shows the rule is END-OF-STATEMENT and not
                ; "is it a keyword" [[two-rules-that-coincide-on-every-row-you-have]].
                ld      e,FPERR_MISSOP      ; default: the slot is EMPTY
                or      a
                jr      z,ev_f_defer        ; end of line
                cp      COLON
                jr      z,ev_f_defer        ; end of statement
                ld      e,4                 ; something IS here -> fperr_to_err[4]
                                            ; = ERR 2 syntax error (interp.asm),
                                            ; the same code ev_f_empty defers
                jr      ev_f_defer

ev_f_empty:                                 ; D-F2-3: the empty parenthesised/argument
                                            ; expression -> deferred FPERR=4 "syntax error",
                                            ; checked at the statement boundary (the D-F2-1
                                            ; pattern: no mid-expression unwind). The value
                                            ; (DE=0) survives every downstream success op
                                            ; unchanged, but the flag makes the driver abort.
                ld      e,4
ev_f_defer:                                 ; shared tail: E = FPERR code to defer.
                ld      a,e                 ; D-F2-4 first-error-wins: if the argument
                call    penderr_set         ; expression ALREADY raised a hard error
                                            ; (div0/overflow/illegal), keep THAT -- the
                                            ; reference reports the first error, not the
                                            ; later reject (e.g. SIN(1/0,2) -> Division by
                                            ; zero, NOT syntax error).
                                            ; 🎯 D-PENDERR: THIS SITE IS WHERE THE RULE WAS
                                            ; FIRST WRITTEN DOWN, and it was one of only
                                            ; two of the twenty-one writers that honoured
                                            ; it. Now that the write itself enforces it,
                                            ; the hand-rolled guard is -6 B of page 1 and
                                            ; the remaining two instructions say the same
                                            ; thing (str-engine.asm penderr_set).
                ; fall into ev_f_err for the $DD landmark.
ev_f_err:                                   ; the SILENT landmark -- and as of D-EVFERR
                                            ; (docs/spec-basic-evferr.md) NOTHING JUMPS
                                            ; HERE AT ALL: it is reached only by
                                            ; FALL-THROUGH from ev_f_defer, whose job is
                                            ; to stamp the $DD landmark after a code has
                                            ; been deferred. D-MISSOPFIX split ONE of the
                                            ; eight jumps off to ev_f_missop; D-EVFERR
                                            ; measured the other seven and split ALL of
                                            ; them (two were not even assembled), at ZERO
                                            ; bytes -- every one was a `jp` whose target
                                            ; changed. 🎯 SO THE LABEL IS NO LONGER A
                                            ; SHARED TAIL, AND THAT IS THE POINT: while
                                            ; it was one, "silent" was not a decision any
                                            ; site had made, it was what a NEUTRAL tail
                                            ; gives every caller that falls into it.
                                            ; ⚠️ Keep it that way. A new `jp ev_f_err` is
                                            ; a factor deciding to fail with NO error
                                            ; code, which measured wrong at every one of
                                            ; the seven sites that had made it.
                jp      errmark_ret0        ; expression error marker, DE = 0

; --- ev_f_errfn / ev_f_erlfn: ERR / ERL -> DE (error-handling S2a, docs/ ---
; spec-basic-error-handling-s2a-packet.md §3/(f)). Single-byte value tokens,
; no operand bytes -- same "read a RAM cell, widen to DE, step one token"
; shape as ev_f_digit/byte/word above, so the outer eval()'s FACTYP=2 (int)
; setting on entry already gives these the right numeric domain; no extra
; widening code is needed here.
ev_f_errfn:                                 ; ERR -> ERRFLG (1 B) widened to DE
                ld      a,(ERRFLG)
ev_ret_e_ix:                                ; D-TAILIX (2026-10-02): the shared tail
                ld      e,a                 ; ev_f_digit and ev_f_byte jump to --
                ld      d,0                 ; DE = A, step past the token, done
                inc     ix
                ret
ev_f_erlfn:                                 ; ERL -> ERRLIN (word), widened to FAC
                                            ; (NOT the plain-DE int16 path ev_f_digit/
                                            ; byte/word use): ERRLIN holds an UNSIGNED
                                            ; word 0..65535 (a real line number can
                                            ; exceed 32767, and the direct-mode sentinel
                                            ; IS 65535), which would print as a negative
                                            ; number through the strict signed-int16
                                            ; PRINT path (print.asm exp_num: FACTYP==2 ->
                                            ; print_number, "DE = signed-16 value").
                                            ; Route through the SAME "escapes int16 ->
                                            ; promote to float" pattern evmc_abs already
                                            ; uses for ABS(-32768) (float-arith.asm
                                            ; evabs_float): widen_uint_to (HL=dest FPNUM,
                                            ; A=sign 0/$80, DE=unsigned magnitude) into
                                            ; the ARGA scratch, then round_and_finalize
                                            ; (FAC:=packed double, FACTYP:=8, DE:=silent
                                            ; flt_to_int16) -- FACTYP=8 makes print.asm's
                                            ; exp_num take the float path (flt_out reads
                                            ; FAC), rendering the true unsigned value.
                ld      hl,(ERRLIN)
                jr      ev_f_uword
; ev_f_time -- TIME (docs/spec-basic-time.md §3.2). The SAME unsigned-word-to-FAC
; problem ERL already solves, over JIFFY instead of ERRLIN, so it shares the tail
; below: 7 B here against 19 duplicated, with no restructuring on ERL's side
; (cf. [[generalisation-not-free-at-two-callers]] -- the case for sharing has to be
; this trivial to be free).
;
; `ld hl,(JIFFY)` is TWO byte reads and the timer ISR ticks between them, so an
; unguarded read can be torn ($00FF seen as $01FF). Guarded (D-TIME-2).
; CSRLIN: the cursor ROW, 0-based. MEASURED (docs/cursor-vg8020-characterization
; .md §2): a BARE pseudo-variable -- no parentheses and no argument, so
; `CSRLIN(0)` is CSRLIN followed by a separate parenthesised item and prints BOTH.
; That falls out of taking no argument here; nothing extra is needed for it.
; CSRY is 1-based, the BASIC value 0-based. flt_int_result marks the result an
; int: a factor that returns int16 in DE must ALSO set FACTYP, or a float left in
; FAC by a previous operand leaks into this value's type (the VARPTR bug).
ev_f_csrlin:
                ld      a,(CSRY)
                dec     a
                ld      e,a
                ld      d,0
                inc     ix
                jp      flt_int_result
ev_f_time:
                di
                ld      hl,(JIFFY)
                ei
ev_f_uword:                                 ; HL = an unsigned 0..65535 -> FAC (double)
                ex      de,hl               ; DE = the unsigned magnitude
                ld      hl,ARGA
                xor     a                   ; sign = positive (neither source is negative)
                call    widen_uint_to
                call    round_and_finalize
                inc     ix
                ret

; constant decoders --------------------------------------------------------
ev_f_digit:                                 ; $11..$1A -> value 0..9
                ld      a,(ix+0)
                sub     INT_DIGIT_BASE
                jr      ev_ret_e_ix

; --- stk_guard: the evaluator's STACK FLOOR (D-STACKFLOOR) -------------------
; ⚠️ SITED AFTER ev_f_digit, NOT beside ev_f_defer: 15 B between ev_f's dispatch
; and ev_f_digit put that `jr c,ev_f_digit` out of range. Its own `jr` reaches
; back to ev_f_defer from here.
; Called as the FIRST instruction of ev_f and of ev_not_do -- the two places every
; unbounded expression recursion passes through (a parenthesis, a function
; argument, a unary minus: ev_f; a `NOT NOT ...` chain: ev_not_do).
; in: nothing. out: returns (CF set) while SP is more than STK_EVAL_RESERVE above
; CTLLIM (= ARYEND+2, the arrays' first free byte). Clobbers HL and F only.
;
; 🔴 WHY IT EXISTS: since D-SPMERGE the machine stack descends from the pool's
; frontier into the free gap, and the ONLY floor was ctl_alloc's static 256 B
; margin -- tested when a FRAME is pushed, never while an expression recurses.
; MEASURED 2026-09-27 (scratchpad/stackhw_run.out): 20 nested parentheses reach
; 756 B below the frontier, 32 nested ABS 1332 B. So an array DIM'd to the edge
; was OVERWRITTEN by a later formula: `A(X)` read garbage after `B=(((...)))` with
; 300 B free, and an 8-deep formula wrecked the machine
; (scratchpad/stackcorrupt_run.out). The VG-8020 answers every one of those rows
; and raises Out of memory at 24 nested ABS: it checks as it recurses.
;
; 🎯 THE STOP IS A DEFERRED ERROR, NOT AN UNWIND. The evaluator has no
; mid-expression abort (fp_runtime_error's header); every factor that fails
; defers an FPERR and yields 0, and the statement boundary raises it. So the
; guard drops ITS OWN return address -- the word under it is the return point of
; whoever entered ev_f / ev_not_do -- and leaves as a failed factor would:
; FPERR_OOM deferred (first error wins, penderr_set), DE = 0, no deeper call.
; The levels above it then unwind normally, each seeing a cursor it cannot
; consume, and their own deferrals lose to the first.
;
; ⚠️ THE RESERVE IS NOT ctl_alloc's 256. It must hold only what runs BELOW a
; factor that passed: the deepest LEAF (a transcendental, a sub-ROM tenant's
; CALSLT frames) plus an interrupt. 🔴 The first cut used the 256 (`inc h`, 1 B)
; and every expression at the DIM edge refused, flat `B=1` included -- DIM keeps
; 256 below the FRONTIER, and the statement's own stack already sits under that.
; STK_EVAL_RESERVE (basic/sysvars.inc) is the evaluator's own number.
; 🔴 BC IS PRESERVED, AND test_sound.py IS WHY. eval's header says it clobbers
; BC, but a LITERAL factor never touched it, and ex_sound keeps the register
; number in C across `call eval` for the value -- the first cut (`ld bc,` bare)
; latched register 128 on every `SOUND n,v`. A contract its callers do not keep
; is the contract the code must keep; the push/pop is 2 B.
stk_guard:
                ld      hl,(CTLLIM)
                push    bc
                ld      bc,STK_EVAL_RESERVE
                add     hl,bc               ; HL = the floor + the reserve; CF = 0
                                            ; (CTLLIM is a RAM address far below
                                            ; $FF80, so the add cannot carry)
                pop     bc                  ; (POP touches no flag)
                sbc     hl,sp               ; CF iff SP is above it: room to recurse
                ret     c
                pop     hl                  ; drop our return: leave AS the factor
                ld      e,FPERR_OOM         ; -> ERR 7 at the statement boundary
                jr      ev_f_defer
ev_f_byte:                                  ; $0F,<byte>
                inc     ix
                ld      a,(ix+0)
                jr      ev_ret_e_ix
ev_f_word:                                  ; $0C/$1C,<word LE>
                inc     ix
                ld      a,(ix+0)
                ld      e,a                 ; value low
                inc     ix
                ld      a,(ix+0)
                ld      d,a                 ; value high
                inc     ix
                ret

; --- ev_f_float: SNG_TOKEN/DBL_TOKEN factor -> FAC/FACTYP + DE (§9.4) ------
; Copies the token's 4 (single) / 8 (double) value bytes into FAC, sets
; FACTYP (4/8), and returns DE = the value rounded to int16 (flt_to_int16,
; basic/float.asm) so every existing int consumer keeps working unchanged
; (interim divergence D-F1-2: float into an int context rounds silently).
ev_f_float:
                ld      a,(ix+0)            ; SNG_TOKEN or DBL_TOKEN
                ld      c,4                 ; C = value byte count (single)
                ld      b,4                 ; B = FACTYP value (single)
                cp      DBL_TOKEN
                jr      nz,eff_sz
                ld      c,8
                ld      b,8
eff_sz:
                inc     ix                  ; past the token
                ld      a,b
                ld      (FACTYP),a
                ld      hl,FAC
                ld      b,c                 ; B = copy count
eff_cp:
                ld      a,(ix+0)
                ld      (hl),a
                inc     hl
                inc     ix
                djnz    eff_cp
                jp      flt_to_int16        ; DE = rounded int16 (0 if out of range)

; --- ev_f_pos: unary plus is the IDENTITY -------------------------------------
; D-UNARYPLUS (2026-09-05). `A=+1` was ERR 2 here and `1` on both references:
; ev_f tested MINUS_TOKEN and had no PLUS_TOKEN arm, so a leading `+` was simply
; "not a factor". Consuming the token and re-entering ev_f is the whole fix.
;
; 🎯 RE-ENTERING ev_f RATHER THAN CALLING ev_pw IS THE POINT. Unary minus calls
; ev_pw because `^` must bind tighter than negation (-2^2 = -4); plus changes
; nothing, so the operand is just the next FACTOR. Measured on both references,
; which agree on all ten rows (scratchpad/uplus_probe.py):
;
;   A=+1  1   B=1:A=+B  1   A=(+1)  1   A=1++2  3   A=++1  1   A=+-1  -1
;   A=+2^2  4     A$="X":B$=+A$  X     B$=+"X"  X     PRINT +A$  X
;
; 🔴 THREE OF THOSE TEN ARE **NOT** CLOSED BY THIS ARM, AND A DRAFT OF THIS
; COMMENT SAID THEY WERE. It read "re-entering ev_f ... is what makes the STRING
; rows work", written from the shape before the after-run existed; it is
; corrected here rather than deleted, because being wrong about WHICH rows an arm
; reaches is the thing worth leaving on the record.
; The three STRING rows still read ERR 13, and the re-measurement says why: this
; arm is in the NUMERIC factor decoder and a string RHS never reaches it.
; `ex_let_str` asks "is this a string operand?" through basic/strvar.asm's
; `str_eval_one`, which dispatches on the FIRST BYTE and has no PLUS_TOKEN case,
; so a leading `+` falls to els_typecheck -- which evaluates numerically and
; reports Type mismatch, exactly as designed.
; 📏 THE ARM DID MOVE `B$=+"X"` AND `PRINT +A$` FROM ERR 2 TO ERR 13, which is
; the proof that the token is now consumed and that what remains is the type
; dispatch, not the factor parse. Filed with that site and its price.
;
; ⚠️ The entry priced SIX numeric rows; the probe found TEN divergences, and
; nine of the twelve rows are green after this. The four extra all came from
; asking what the arm would REACH rather than what it was for
; [[a-fix-falsifies-the-justification-beside-it]].
; ⚠️ `A=++1` re-enters ev_f a second time and terminates because IX has
; advanced past a token each time -- the regress is bounded by the line.
; ⚠️ `A=+2^2` reads 4 under BOTH bindings, so it does not separate them; it
; is recorded as a row that agrees without discriminating
; [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
ev_f_pos:
                inc     ix                  ; consume the '+'
                jp      ev_f                ; the operand is the next factor

ev_f_neg:
                inc     ix
                call    ev_pw               ; DE = operand (`^` binds tighter
                                            ; than unary minus, §13.1/13.3 --
                                            ; this is what makes -2^2=-4 AND
                                            ; 2^-3^2=2^-(3^2) fall out for free)
                call    neg_de_hl           ; HL = 0 - operand. P/V is set for
                                            ; EXACTLY one int16 operand: $8000
                                            ; (0-(-32768) = +32768, out of range).
                                            ; $8000 is its own two's-complement
                                            ; negation, so without the arm below
                                            ; the operand comes back UNCHANGED and
                                            ; `-A%` prints -32768 for A%=-32768.
                push    af                  ; carry P/V across the FACTYP read --
                                            ; `cp 2` overwrites it with parity
                ex      de,hl
                call    factyp_is2
                jr      nz,evfn_flt
                pop     af
                ret     po                  ; int, no overflow -> DE is the answer
                jp      evabs_esc           ; int $8000: the true value is +32768,
                                            ; which escapes int16 -> promote to a
                                            ; double, exactly as ABS(-32768%),
                                            ; -32768\-1 and -32768*-1 already do.
                                            ; MEASURED: the reference prints 32768
                                            ; for -cint(-32768) AND for -(-32768\1)
                                            ; (docs/fixpoint8000-msx1-sweep.md §4.6)
evfn_flt:
                pop     af
                jp      flt_neg             ; float: the sign lives in FAC, and DE's
                                            ; int16 view is already 0-operand

ev_f_paren:
                inc     ix                  ; '('
                call    ev_logic            ; DE = inner value (full expression)
                call    ev_sp
                cp      ')'
                ; D-EVFERR (docs/spec-basic-evferr.md): the CHECKED deferred
                ; FPERR=4 syntax error, not the bare ERRMARK ev_f_err -- which
                ; nothing on this path reads, so `A=(1+2` COMPLETED SILENTLY
                ; with A=0 where both references say Syntax error. Byte-neutral
                ; (the same instruction, retargeted), and the same cure
                ; vptr_close already carries. 4 rows: `A=(1+2`, `A=(1+2:B=3`,
                ; `A=((1+2)`, `PRINT(1+2`, plus `IF(1 THEN` and `FOR I=(1 TO`.
                jp      nz,ev_f_empty
                inc     ix
                ret

; --- ev_f_ff: a $FF-prefixed function token (PEEK / VPEEK / INP) -----------
; All three take a single parenthesised expression; they differ only in how the
; argument is used. We parse "( <expr> )" once, then read from RAM (PEEK), VRAM
; (VPEEK) or a Z80 port (INP). The second token byte selects the read.
ev_f_ff:
                inc     ix                  ; skip the $FF prefix
                ld      a,(ix+0)            ; the function selector byte
                ; REPACK ONLY. Every $FF function here except CVI takes one
                ; parenthesised NUMERIC argument, so membership is a set test, not a
                ; decision tree: scan the selector table with cpir (input-devices
                ; slice I1 golf). The old per-token `cp`/`jr z` chain cost 4 B per
                ; function; a table row costs 1, and that difference is what funds
                ; STICK/STRIG joining the group. cpir preserves A, and neither HL
                ; nor BC is live here (ev_ff_arg's first act is `ld c,a`).
                cp      CVI_TOKEN           ; $A8 -> CVI (STRING arg: not in the set)
                jp      z,ev_ff_cvi
                cp      CVS_TOKEN           ; $A9 -> CVS (D-MKSD; same STRING-arg body,
                jp      z,ev_ff_cvs         ; 4 bytes instead of 2)
                cp      CVD_TOKEN           ; $AA -> CVD (ditto, 8 bytes)
                jp      z,ev_ff_cvd
                cp      FRE_TOKEN           ; $8F -> FRE (EITHER type: not in the set)
                jp      z,ev_ff_fre
                ld      hl,ev_ff_argtab
                ld      bc,ev_ff_argtab_len
                cpir
                jr      z,ev_ff_arg
                jp      ev_ff_mathconv      ; ABS/SGN/INT/FIX/CINT/CSNG/CDBL, else
                                            ; LEN/ASC/VAL (string->number), else ev_f_err
; The single-numeric-argument $FF selectors, for the cpir set test above. Order is
; free. Repack-only, like the scan that reads it.
ev_ff_argtab:
                db      PEEK_TOKEN          ; $97
                db      VPEEK_TOKEN         ; $98
                db      INP_TOKEN           ; $90
                db      EOF_TOKEN           ; $AB
                db      LOF_TOKEN           ; $AD
                db      LOC_TOKEN           ; $AC  (D-LOC)
                db      DSKF_TOKEN          ; $A6
                db      POS_TOKEN           ; $91  (cursor cluster; arg DISCARDED)
                db      LPOS_TOKEN          ; $9C  (D-LPTVERB; arg DISCARDED too)
    IF I1_RESIDENT
                db      STICK_TOKEN         ; $A2  (input devices, slice I1)
                db      STRIG_TOKEN         ; $A3
    ENDIF
    IF I2_RESIDENT
                db      PDL_TOKEN           ; $A4  (input devices, slice I2)
                db      PAD_TOKEN           ; $A5
    ENDIF
ev_ff_argtab_len equ    $ - ev_ff_argtab
ev_ff_arg:
                ld      c,a                 ; C = selector (survives the parse)
                call    ixsp_paren_req     ; D-IXSP
                ; Residual found by the I1 differential (spec §3): a MISSING
                ; argument list -- `PRINT PEEK`, `PRINT STICK`, `PEEK 100` --
                ; silently evaluated to 0 here, where the reference raises a
                ; Syntax error (ERR 2, measured on the VG-8020 for PEEK / VPEEK /
                ; INP / EOF / LOF alike). Same BUG C class, and same cure, as the
                ; CVI missing-'(' fix below: defer the syntax error via ev_f_empty
                ; so the statement's check_expr_errors aborts.
ev_ff_arg_in:                               ; D-VARPTRCH: VARPTR(#n) joins here with
                                            ; IX on the `#` and C = VARPTR_TOKEN
                inc     ix
                push    bc                  ; guard the selector across the eval
                call    ev_logic            ; DE = argument (full expression)
                pop     bc
                call    evsp_close          ; D-EVSPCLOSE
                inc     ix
                ; D-F2-2 A2: CHECKED int coercion for PEEK/INP (address domain) and
                ; VPEEK (VRAM 0..16383) — the arg's FAC/FACTYP is still its own type
                ; here (flt_int_result below forces int), so re-coerce it CHECKED and
                ; abort INLINE on an out-of-domain arg. The reference overflows AT the
                ; function even in contexts that run no statement-boundary FPERR check
                ; (FOR bounds → ERR 6, pinned char_a2_vpeek.py), so this must not defer.
                ; fac_to_int_addr/_strict clobber C → guard the selector for the read
                ; dispatch below (abort paths leave BC on the stack; SAVSTK resets SP).
                ; EOF/LOF/DSKF keep their own channel handling (skip the coercion).
                push    bc
                ld      a,c
                cp      VPEEK_TOKEN
                jr      z,ev_ff_ckvram
                cp      INP_TOKEN
                jr      z,ev_ff_ckaddr
                cp      PEEK_TOKEN
                jr      z,ev_ff_ckaddr
    IF I1_RESIDENT
                ; STICK/STRIG/PDL/PAD (spec §4): the device index is a small
                ; non-negative byte, so get_byte_arg is exactly the right checked
                ; coercion -- truncate toward zero, ERR 6 outside int16, ERR 5
                ; in-int16 but negative or >255 -- and only the per-function bound
                ; is left to test. Measured domains: STICK 0..2, STRIG 0..4,
                ; PDL 1..12 (starts at 1), PAD 0..7.
                cp      STICK_TOKEN
                jr      z,ev_ff_ckstick
                cp      STRIG_TOKEN
                jr      z,ev_ff_ckstrig
    IF I2_RESIDENT
                cp      PDL_TOKEN
                jr      z,ev_ff_ckpdl
                cp      PAD_TOKEN
                jr      z,ev_ff_ckpad
    ENDIF
                jr      ev_ff_ckdone        ; PEEK/VPEEK/INP/EOF/LOF/DSKF: no byte domain
ev_ff_ckstrig:
                call    get_byte_arg        ; A = E = index (D = 0)
                cp      5                   ; STRIG: 0..4
                jr      ev_ff_ckdom
ev_ff_ckstick:
                call    get_byte_arg
                cp      3                   ; STICK: 0..2
                jr      ev_ff_ckdom
    IF I2_RESIDENT
ev_ff_ckpad:
                call    get_byte_arg
                cp      8                   ; PAD: 0..7
                jr      ev_ff_ckdom
ev_ff_ckpdl:
                call    get_byte_arg
                ; PDL's domain excludes 0, but a string arg coerces to 0 with a
                ; DEFERRED type mismatch pending (error-handling arc), surfaced at
                ; the statement boundary. The reference reports THAT (ERR 13), so
                ; don't let PDL's ERR-5 domain check preempt it -- STICK/STRIG/PAD
                ; need no such guard because 0 is legal for them, so their deferred
                ; fault already surfaces on its own.
                ; D-PENDERR: was `ld a,(TMISMATCH)`, byte for byte, and widened to
                ; ANY pending code for the same reason -- `PDL(1/0)` has the same
                ; shape (a hard zero standing in for a fault that already happened),
                ; and PDL's domain check must not preempt that one either.
                ld      a,(FPERR)
                or      a
                jr      nz,ev_ff_ckdone
                ld      a,e                 ; the byte get_byte_arg left in E
                dec     a                   ; PDL 1..12 -> 0..11 (0 -> $FF -> illegal)
                cp      12
    ENDIF
ev_ff_ckdom:
                jp      nc,gb_illegal       ; -> ERR 5 illegal function call
                jr      ev_ff_ckdone
    ELSE
                jr      ev_ff_ckdone
    ENDIF
ev_ff_ckaddr:                             ; PEEK/INP: address domain, Overflow beyond
                call    fac_to_int_addr     ; DE=checked addr; FPERR=1 outside 0..65535 wrap
                call    check_fperr_only    ; -> ERR 6 (aborts; else returns clean)
                jr      ev_ff_ckdone
ev_ff_ckvram:                               ; VPEEK: VRAM 0..16383 (the shared get_vram_arg
                call    get_vram_arg        ; leaf D-F2-2 stage B added — same as VPOKE's:
                                            ; DE=checked addr; ERR 6 >int16 / ERR 5 outside)
ev_ff_ckdone:
                pop     bc                  ; C = selector restored for the read dispatch
                call    flt_int_result      ; the function returns an int even if its
                ld      a,c                 ; dispatch on the selector
                cp      VARPTR_TOKEN        ; D-VARPTRCH: VARPTR(#n), which joined at
                jp      z,ev_ff_varptrch    ; ev_ff_arg_in with this selector. FIRST
                                            ; in the chain on purpose: LOF's `jr`
                                            ; below has no slack, and any byte put
                                            ; between it and its target breaks it
                cp      VPEEK_TOKEN
                jr      z,ev_ff_vpeek
                cp      INP_TOKEN
                jr      z,ev_ff_inp
                cp      EOF_TOKEN
                jr      z,ev_ff_eof
                cp      LOF_TOKEN
                jr      z,ev_ff_lof         ; `jp` since D-LOC: the LOC test below
                                            ; sits between this and its target
                                            ; ⚠️ D-SPMERGE step 5 tried `jr` here on
                                            ; jr_mapper's 2026-09-12 proposal and the
                                            ; ASSEMBLER REFUSED: out of range. The
                                            ; proposal was measured on the tree BEFORE
                                            ; this slice's carve moved the layout --
                                            ; Route D renews on insertion, and it
                                            ; UN-renews the same way.
                cp      LOC_TOKEN
                jp      z,ev_ff_loc         ; `jp`: ev_ff_loc's body sits past jr range,
                                            ; exactly the ev_ff_dskf landmine below
                cp      DSKF_TOKEN
                ; Landmine (spec §9.5, recurred from I1): the I2 dispatch rows just
                ; below push ev_ff_dskf out of jr range, so it takes a jp here
                ; rather than the jr it used before those rows existed.
                jp      z,ev_ff_dskf
                cp      POS_TOKEN
                jr      z,ev_ff_pos
                cp      LPOS_TOKEN
                jr      z,ev_ff_lpos
    IF I1_RESIDENT
                cp      STICK_TOKEN
                jr      z,ev_ff_stick
                cp      STRIG_TOKEN
                jr      z,ev_ff_strig
    ENDIF
    IF I2_RESIDENT
                ; PDL/PAD bodies live at the ev_f_ff tail (after CVI), reached by jp.
                cp      PDL_TOKEN
                jp      z,ev_ff_pdl
                cp      PAD_TOKEN
                jp      z,ev_ff_pad
    ENDIF
                ; PEEK: read one byte of RAM at the address in DE.
                ex      de,hl               ; HL = address
                ld      e,(hl)              ; read one byte
                ld      d,0                 ; PEEK yields 0..255
                ret
ev_ff_pos:                                 ; POS(n): the cursor COLUMN, 0-based.
                ; MEASURED: the argument is parsed and then DISCARDED -- POS(0),
                ; POS(1), POS(99), POS(-1) and POS(1+1) all give the same answer, so
                ; it is a true dummy and NOT a selector. It therefore takes no domain
                ; check (it is absent from the ev_ff_ck* chain above on purpose);
                ; `POS(-1)` must not raise. The parentheses are still REQUIRED --
                ; bare `POS` is a Syntax error, which ev_ff_arg's missing-'(' path
                ; already produces.
                ld      a,(CSRX)
                dec     a                   ; CSRX is 1-based, POS 0-based
                jr      ev_ret_e            ; D-RETTAIL: DE = A (0..255)
ev_ff_lpos:                                 ; LPOS(n): the PRINTER column, 0-based.
                ; D-LPTVERB, docs/lptverb-msx1-characterization.md §3. Every rule
                ; POS's comment above states holds here too and was re-measured
                ; rather than inherited: the argument is parsed and DISCARDED
                ; (LPOS(0)/LPOS(1)/LPOS(255)/LPOS(-1) all answer the same, R-LS4,
                ; so LPOS is absent from the ev_ff_ck* domain chain ON PURPOSE and
                ; `LPOS(-1)` must not raise -- knife K7), and the parentheses are
                ; still REQUIRED (R-LS5, from ev_ff_arg's missing-'(' path).
                ;
                ; 🔴 THE SOURCE IS LPTPOS, NOT CSRX, AND THAT IS THE WHOLE DEFECT
                ; THIS BODY CAN HAVE. It is written by copying ev_ff_pos, three
                ; lines up, whose source IS CSRX -- and on a fresh machine the
                ; screen column and the printer column are BOTH 0, so `lps-init`
                ; cannot tell a correct body from that copy. `lps-after` (3),
                ; `lps-tab` (10) and `lps-multi` (14) are the rows that can, and
                ; knife K6 is exactly that cut.
                ;
                ; No `dec a` either: LPTPOS is already 0-based, where CSRX is
                ; 1-based. A copied `dec a` would read 255 at line start.
                ld      a,(LPTPOS)
                jr      ev_ret_e            ; D-RETTAIL: DE = A (0..255)
ev_ff_vpeek:                                ; VPEEK: read one byte of VRAM (DE = addr)
                ex      de,hl               ; HL = VRAM address (RDVRM wants it here)
                call    RDVRM               ; A = VRAM[HL]; makes no register guarantees
                jr      ev_ret_e            ; D-RETTAIL: DE = A (0..255) -- VPEEK yields 0..255
    IF I1_RESIDENT
; --- STICK(n) / STRIG(n): input devices, slice I1 --------------------------
; docs/spec-basic-input-devices.md §5/§6. Thin wrappers over the published BIOS
; entries, which C-BIOS implements for real (keyboard matrix row 8 for device 0,
; PSG joystick ports for 1/2) and whose behaviour matches the VG-8020 measurement
; exactly. Entered with E = the already-range-checked device index.
;
; Both entries are documented "Registers: All", so the token cursor IX is guarded
; across the call. (On our C-BIOS target neither routine touches IX -- they are
; plain page-0 code, no CALSLT -- but the guard keeps this BIOS-AGNOSTIC, which is
; the standing rule for anything reached through a published BIOS contract.)
;
; DI/EI (traps T2, spec-traps-t2-strig.md §4): reading triggers 1..4 latches PSG
; register 15 and then reads 14, and since T2 the VBLANK ISR calls GTTRIG too (the
; STRIG event_poll stanza). A frame interrupt landing between this call's latch and
; its read would be answered by the ISR's own selection -- the same shared-latch
; hazard ex_sound already guards (basic/sound.asm, the audio-slice-3 fix). Cheap:
; the BIOS read itself is short, so the interrupt-off window is tiny.
ev_ff_stick:                                ; STICK(n): 0 = centred, else 1..8 clockwise
                ld      a,e                 ; A = device (0 cursor keys, 1/2 ports)
                push    ix
                di
                call    GTSTCK
                ei
                pop     ix
                jr      ev_ret_e            ; D-RETTAIL: DE = A (0..255) -- direction is 0..8, never negative
ev_ff_strig:                                ; STRIG(n): 0 not pressed, -1 pressed
                ld      a,e                 ; A = trigger (0 space, 1..4 buttons)
                push    ix
                di
                call    GTTRIG
                ei
                pop     ix
                ld      e,a                 ; BIOS returns $00 / $FF, and copying it
                ld      d,a                 ; into BOTH halves yields 0 / -1 ($FFFF)
                ret                         ; -- the BASIC truth convention, free
    ENDIF
ev_ff_inp:                                  ; INP: read one Z80 port (DE = port)
                ld      b,d
                ld      c,e                 ; BC = port (in (a),(c) reads from BC)
                in      a,(c)               ; A = port input
ev_ret_e:                                   ; D-RETTAIL: the shared `DE = A` return
                ld      e,a
                ld      d,0                 ; INP yields 0..255
                ret
ev_ff_eof:                                  ; EOF(n): -1 at end of the input file n
                ; Select channel n (DE = arg) so FREAD_LEFT belongs to it, then test
                ; whether every file byte has been delivered (4-byte LE == 0). fch_select
                ; uses LDIR only (no CALSLT), so IX — the evaluator's token cursor —
                ; survives; it does clobber HL/BC/A (the factor caller tolerates that,
                ; like PEEK). A bad channel number is a function error.
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52. Was
                                            ; `jp nc,ev_f_err`, which set ERRMARK and
                                            ; returned DE=0 -- and NOTHING on this path
                                            ; reads ERRMARK, so `PRINT EOF(0)` printed
                                            ; a plausible ` 0` with no error at all.
                                            ; ⚠️ THAT LAST SENTENCE WAS STALE FOR THIS
                                            ; ROW and D-EVFERR measured it: `EOF(0)` is
                                            ; channel 0, which fch_check sends to
                                            ; err_notopen_raise (59, all three) BEFORE
                                            ; the class test below runs -- so the site
                                            ; underneath was never reached by the row
                                            ; that was supposed to witness it.
                call    fch_mode_class      ; device/cassette channels have no length
                ; D-EVFERR: an OPEN device channel is what reaches this, and it
                ; is a function-domain VALUE error, not a syntax one:
                ; `OPEN"CRT:"FOR OUTPUT AS#1:A=EOF(1)` is ERR 5 on BOTH
                ; references and COMPLETED SILENTLY here. ev_f_ifc is the
                ; deferred FPERR=3 -> ERR 5 idiom; byte-neutral retarget.
                ; 🔴 D-EOFCAS (2026-09-30): NOT EVERY DEVICE CHANNEL. A TAPE opened
                ; FOR INPUT answers EOF on the CF-3300 -- 0, 0, then -1 after the
                ; last line (scratchpad/eofcas_run.out) -- and it was ERR 5 here,
                ; so the textbook tape loop died on its first EOF. Every non-disk
                ; channel goes to the seqio tenant's op 6 with its mode in H: a
                ; CAS: input channel peeks the tape, any other keeps ev_f_ifc's
                ; answer (the tenant sets the same deferred FPERR=3, first error
                ; wins, and EOF reads 0). Never fch_select one: a cassette channel
                ; owns no fat.asm ctx, and its record copy would land on CAL_BUF.
                jr      nc,eof_dev
                ; 🔴 D-EOFMODE (2026-09-30): a DISK channel answers EOF only when it
                ; is open FOR INPUT. OUTPUT, APPEND and RANDOM are all `Bad file
                ; mode` (61), trappable, on the CF-3300 -- RANDOM too, which MS
                ; Disk BASIC's documentation allows (scratchpad/eofmode_run.out).
                ; Here EOF(1) on an OUTPUT channel answered 0 and the program ran
                ; on. A = FCH_MODES[E] (fch_mode_class), INPUT = 1. INPUT$'s own
                ; 61 raise is the tail: no private copy.
                dec     a
                jp      nz,sid_badmode
                ld      a,e
                call    fch_select
                call    fat_io_eof         ; D-SEQEOF: CF = at the end -- Ctrl-Z
                                            ; NEXT counts (R1); other modes keep the
                                            ; byte count (the tenant does both)
eof_answer:
                sbc     a,a
                inc     a                   ; Z iff at the end
                ld      de,0
                ret     nz                  ; bytes remain -> not EOF -> 0
                dec     de                  ; all delivered -> EOF -> -1 ($FFFF)
                ret
ev_ff_lof:                                  ; LOF(n): length of open input file n
                ; Select channel n so FAT_FILESIZE (set by fat_find at OPEN, part of
                ; the per-channel state span) belongs to it.
                ; 🔴 D-LOFU32 (2026-09-10): THE RESULT IS A DOUBLE CARRYING THE
                ; WHOLE 32-BIT SIZE, NOT "its low 16 bits". `ld de,(FAT_FILESIZE) /
                ; ret` handed the size back as an INTEGER, so a 65280-byte file read
                ; **-256** (D-PUTDOMAIN's r.255 -- inside the supported domain, a
                ; live wrong answer) and anything past 65535 was truncated. Measured
                ; on the CF-3300: LOF(1) after PUT#1,300 prints 76800, and LOF(1)/7
                ; prints 10971.428571429 -- 14 significant digits, a DOUBLE
                ; (scratchpad/loftype_probe.py). Joost ruled "do what the reference
                ; does"; this is the u32 -> float half, the PUT offset half is
                ; separate. The dispatcher's flt_int_result above already set
                ; FACTYP=2, and this tail overrides it -- the same "publish a
                ; float, refresh DE via flt_to_int16" shape evconv_pack_same_type
                ; keeps for every ev_f_* factor.
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52 -- see ev_ff_eof
                                            ; above, including why channel 0 never
                                            ; reaches the class test
ev_ff_lof_checked:                          ; D-LOC joins here for a sequential channel
                call    fch_mode_class      ; device/cassette channels have no length
                jp      nc,ev_f_ifc         ; D-EVFERR: ERR 5, as ev_ff_eof above
                ld      a,e
                call    fch_select
                ld      hl,(FAT_FILESIZE)   ; DE:HL = the size, unsigned 32-bit
                ld      de,(FAT_FILESIZE+2)
                ld      a,h
                or      l
                or      d
                or      e
                jr      nz,lof_nz
                ld      (FAC),a             ; 0: the int 0 flt_int_result already typed
                jp      ret_de0     ; (A is 0 here)
lof_nz:
                ; The digit work is the SUBROM_IDX_LOFU32 tenant (sub/lofu32.asm):
                ; the resident form of it cost 98 B of page 1 (129 -> 31 B free,
                ; measured), so only the call, the pack and the tail stay here.
                ; 🔴 IX IS THE EVALUATOR'S TOKEN POINTER HERE (fn_call: "in: IX ->
                ; the FN token"), and subrom_call takes the entry address IN IX and
                ; CALSLT clobbers it. The first tenant cut left IX pointing at the
                ; sub-ROM table, the evaluator resumed parsing there, and every
                ; `PRINT LOF(1)` on the machine read `Syntax error` -- while the
                ; resident cut, which never touched IX, was correct. Four bytes.
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_LOFU32
                call    subrom_call         ; ARGA := the size, unpacked; CF=1 iff
                pop     ix                  ;   the sub-ROM is absent (flags survive)
                jp      c,subrom_absent_error ; reduced build w/o sub-ROM, as evmc_sqr
                call    arga_pack_fac       ; ARGA -> FAC as a double (14 digits, exact)
                jp      fac_dbl_int16       ; FACTYP := 8, then refresh DE: the silent
                                            ; address-domain contract every ev_f_* tail
                                            ; keeps (D-TAILMERGE: it was that body
                                            ; verbatim, float-arith.asm)

ev_ff_loc:                                  ; LOC(n): D-LOC (2026-09-10)
                ; Measured on the CF-3300 (D-LOCSEM, scratchpad/loc_probe.py): on a
                ; RANDOM channel LOC is the record number of the last GET/PUT
                ; (`GET #1,3` / `GET #1,7` -> 0,3,7; `PUT #1,4` -> 0,4,0); on a
                ; SEQUENTIAL channel it is constant at the FILE SIZE across reads
                ; (26,26,26) -- i.e. LOF's value. So: mode 4 (RANDOM) reads the
                ; per-channel FCH_RECNOS word; any other open mode falls into
                ; ev_ff_lof below. Same channel checks as LOF; the closed/device
                ; faces are LOF's, unmeasured for LOC and stated as such.
                call    fch_check           ; D-BADFNUM: 5 / 59 / 52, as LOF
                call    fch_modes_ptr       ; HL = &FCH_MODES[E]
                ld      a,(hl)
                cp      4                   ; RANDOM (basic/files.asm: mode = 4)
                jr      nz,ev_ff_lof_checked ; sequential/device: LOC == LOF
                ld      hl,FCH_RECNOS
                ld      d,0
                add     hl,de
                add     hl,de               ; HL = &FCH_RECNOS[E]
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the record number (int result)
                ret
; --- ev_ff_varptrch: VARPTR(#n) -- the address of channel n's FCB ------------
; D-VARPTRCH (2026-09-30). Both references answer the address of the channel's
; 265 B FCB (9 header + the 256 B record), strided 265 apart; this tree answered
; Syntax error. Since D-FCBSHAPE S1+S2 our channel block IS that shape, so the
; answer is fch_ctx_addr's, agreeing on the stride by construction (the BASE is
; machine-specific on every machine, as the variable form's is).
; The channel takes the verbs' one rule (fch_check: 5 / 59 / 52 -- `VARPTR(#2)`
; at the default MAXFILES is 52 on both references, measured by D-VARPTRN). An
; UNOPENED channel answers its address, as on the references: no mode test.
; ⚠️ fch_ctx_addr is a CALSLT and IX is the evaluator's token cursor -- the
; lof_nz lesson (every `PRINT LOF(1)` read Syntax error when a tenant call left
; IX pointing at the sub-ROM table).
ev_ff_varptrch:
                call    fch_check           ; 5 / 59 / 52; A = E = the channel
                push    ix
                call    fch_ctx_addr        ; HL = channel A's block
                pop     ix
                ex      de,hl               ; DE = the address; FACTYP is already
                ret                         ; int (ev_ff_ckdone's flt_int_result)
eof_dev:                                    ; D-EOFCAS: A = FCH_MODES[E], not disk.
                                            ; Past LOC on purpose: LOF's dispatch
                                            ; `jr` has no slack for a byte before it
                ld      h,a
                ld      l,6
                call    seq_call            ; CF = at the end (tape); 0 otherwise
                jr      eof_answer

; fch_mode_class — the shared channel-mode classifier. A = FCH_MODES[E]; raises
; ERR 59 "file not open" if that is 0; CF set if E is a disk file channel
; (FCH_MODES[E] < LPT_MODE), CF clear if it is a length-less device channel
; (LPT/CRT/CAS, mode >= LPT_MODE). Preserves E + IX (no CALSLT); clobbers A/HL.
; FCH_MODES[0] is unused/0, so a 0 channel (already rejected by fch_check before
; every call site, which raises the same 59 one step earlier) would raise 59 here
; — never reached.
;
; ⚠️ FOUR CALLERS, in THREE files — not the two this comment used to claim:
;   * ev_ff_eof / ev_ff_lof (below): CF clear -> function error, so EOF()/LOF()
;     reject device+cassette channels (which own no fat.asm ctx and would corrupt
;     the engine globals if fch_select'd).
;   * ex_print's `PRINT #n` arm (basic/print.asm) and input_common's `#n` arm
;     (basic/files.asm, INPUT# *and* LINE INPUT#): they ignore CF and dispatch on
;     A themselves, but they want the `or a` raise. D-NOTOPEN (docs/spec-basic-
;     chan-notopen-err59.md): both hand-inlined this routine's first half and
;     OMITTED the `or a`, so a not-open channel fell through to `load_error` --
;     zerobas's non-fatal print -- where the CF-3300 raises a trappable ERR 59.
;     That omission WAS the defect; calling this instead is both the fix and 8
;     bytes of page 1 back.
; Renaming a routine four statement drivers call out of the `ev_` (evaluator)
; namespace is the whole of that rename; it is sited here, beside EOF/LOF, still.
fch_mode_class:
                ld      a,e
                call    fch_modes_ptr       ; HL = &FCH_MODES[E] (basic/files.asm --
                                            ; D-NOTOPEN2 §2d(a): this routine held the
                                            ; tenth hand-inlined copy of that index)
                ld      a,(hl)              ; A = FCH_MODES[E]
                or      a                   ; S-FCH-2: 0 = the channel is NOT OPEN.
                jp      z,err_notopen_raise ; -> ERR 59 "file not open" (main.asm low
                                            ; region). MEASURED on the CF-3300: EOF(1)
                                            ; on a never-opened channel raises 59 and
                                            ; TRAPS into an armed handler; zerobas used
                                            ; to fch_select the closed slot and return
                                            ; whatever FREAD_LEFT/FAT_FILESIZE held.
                                            ; ALL FOUR callers want this: D-NOTOPEN
                                            ; measured PRINT#/INPUT#/LINE INPUT# on
                                            ; the same never-opened channel raising
                                            ; 59 and trapping on the CF-3300 too.
                cp      LPT_MODE
                ret                         ; CF set (A<LPT_MODE) = disk file channel
ev_ff_dskf:                                 ; DSKF(d): free clusters on the drive
                ; 🏗️ D-DSKFMOVE (Joost's ruling, 2026-09-17): THE BODY IS IN
                ; disk.rom AS `hk_dskf`. What is left here is the argument
                ; hand-off, the gate, and the verdict decode -- the shape KILL,
                ; NAME, FILES and COPY already use.
                ; 🔴 THE DRIVE ARGUMENT CROSSES IN RAM BECAUSE `chan_gate`
                ; CLOBBERS DE building its own return address, and that is not a
                ; guess: the first cut of D-DSKFDRV checked DE AFTER the gate and
                ; so tested `cg_back`, which made EVERY DSKF answer `Bad drive
                ; name`. The TIER 3 row passed on it -- it expects a refusal --
                ; and only the happy-path row caught it. Staging removes the
                ; hazard instead of guarding it.
                ; ⚠️ IY IS GUARDED HERE NOW, NOT AROUND THE COUNT. The count used
                ; to run main-side under its own push/pop pair; it runs inside the
                ; handler now, so the guard has to span the GATE instead -- IX and
                ; IY both, because the sub-ROM CALSLT the count ends in clobbers
                ; them and the evaluator needs both back.
                ld      (FAC),de            ; the drive argument
                push    ix
                push    iy
                ld      hl,H_DSKF
                call    chan_gate           ; no disk ROM -> Illegal function call
                pop     iy
                pop     ix
                ; 🎯 THE VERDICT COMES BACK IN DISKOP_STATUS, the same cell the
                ; dirverb handlers answer through: 0 = counted, non-zero = the
                ; drive is out of range. The BOUND is measured, not judged, and
                ; the measurement lives with the body in disk/kernel.asm.
                ; D-DSKFRANGE (2026-09-29): the cell carries the ERR CODE itself
                ; (0 = counted) -- 62 for a byte that is no drive, 5 for a value
                ; that is not a byte at all -- so the rule lives with the body.
                ld      a,(DISKOP_STATUS)
                or      a
                jp      nz,raise_error
ev_dskf_ok:
                ld      de,(FAC)            ; DE = free cluster count
                ret
ev_ff_cvs:      ld      c,4
                jr      ev_ff_cv
ev_ff_cvd:      ld      c,8
                jr      ev_ff_cv
ev_ff_cvi:      ld      c,2                 ; CVI(s$): integer from s$'s first 2 bytes
ev_ff_cv:
                ; CVI takes a STRING argument, so it cannot use ev_ff_arg's numeric
                ; ev_xor. Parse "( <string> )" by bridging the IX token cursor to the
                ; HL-based str_eval and back, then read 2 little-endian bytes from the
                ; resulting descriptor. (IX is reloaded from str_eval's advanced HL, so
                ; an inner eval clobbering IX is harmless.) Entered with IX on the
                ; CVI selector byte.
                call    ixsp_paren_req     ; D-IXSP
                                           ; BUG C class (Fable 2026-07-17): CVI missing
                                            ; '(' -> deferred syntax error (was silent
                                            ; ev_f_err -> " 0"); ref = Syntax error
                call    ixsp                ; D-IXSP
                ; 🎯 `CVI()` NEEDS NO TEST OF ITS OWN. D-CVITM added a `cp ')'` here
                ; because routing every decline straight to `ev_f_tmm` turned the
                ; reference's Syntax error into Type mismatch. Once `cvi_tmm`
                ; EVALUATES the operand first (D-CVISTRTM), `eval` meets the `)`
                ; and raises that syntax error itself, and first-error-wins keeps
                ; it -- so the test became dead weight and is gone. Its knife
                ; (K-CV3) is what noticed: after the order fix, cutting the test
                ; moved NO rows. 5 B back.
                push    bc                  ; C (the width) across the operand eval
                call    str_eval_ix         ; STRPTR -> [len][bytes]; HL advanced; CF=ok
                pop     bc
                ; BUG C class (Fable 2026-07-17): repack str_eval CALSLTs and can
                ; exit NC with garbage IX on a nested malformed string fn
                ; (CVI(LEFT$("AB")) -> silent 0) or a non-string arg -- defer via
                ; check_expr_errors rather than unwinding mid-expression.
                ; 🔴 D-CVITM: this was `ev_f_empty` (FPERR=4, Syntax error) for BOTH
                ; causes, and the reference separates them -- `CVI(5)` is Type
                ; mismatch, `CVI(LEFT$("AB"))` is Syntax error. `ev_f_tmm` is the
                ; helper written for exactly this shape (its own header names
                ; LEN(5)/ASC(5)/VAL(5)), and FIRST-ERROR-WINS does the separating
                ; for free: a nested malformed string fn has ALREADY set FPERR=4
                ; inside, so it keeps its syntax error, while a plain non-string
                ; argument arrives with FPERR clean and gets 13. Zero bytes.
                jr      nc,cvi_tmm      ; `jr` (D-SCRARITY carve): 1 B
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    evsp_close          ; D-EVSPCLOSE
                inc     ix
                ; --- D-MKHOOK: CVI/CVS/CVD belong to the DISK ROM ---------------
                ; docs/spec-basic-nodisk.md §9. Sited AFTER the operand and the
                ; `)` so a malformed call still reports its own syntax error first,
                ; which is what both references do WITH a disk -- the gate must not
                ; reorder errors it was not asked to change.
                ; ⚠️ IX IS THE TOKEN CURSOR AND THE CALL CROSSES SLOTS. CALSLT is
                ; documented to affect IX among others, and the UNCLAIMED path is a
                ; bare `ret` that would have hidden it until a disk was present --
                ; the same trap DE set for MKI$.
                ; 🏗️ D-CVMOVE (Joost's ruling, 2026-09-17): THE CONVERSION MOVED
                ; BEHIND THE HOOK, AND THAT IS A COMPATIBILITY FIX, NOT A CARVE.
                ; Until now the hook was offered as a PRESENCE TEST ONLY: main did
                ; the whole conversion after `ev_cv_back` regardless, so a foreign
                ; disk ROM that claimed H_CVI and computed the answer had it
                ; OVERWRITTEN. `hk_cv` (disk/kernel.asm) now does the work and
                ; main only reads the result out of RAM.
                ; 🔑 THE CHECKS RUN FIRST so the BODY POINTER can cross in RAM,
                ; and the reorder is unobservable: BOTH the too-short check and
                ; the unclaimed gate raise ERR 5, so whichever fires first the
                ; reading is the same. The D-CVITM check itself is UNCHANGED and
                ; still sits before pu_deref_body turns the descriptor into a body.
                ld      hl,(STRPTR)
                ld      a,(hl)              ; descriptor length
                cp      c                   ; fewer bytes than the width -> deferred
                jp      c,ev_f_ifc          ; ERR 5 (D-CVITM, now at three widths)
                ; 🔴 NOTHING IS MARSHALLED THROUGH STRSCR HERE, AND THE FIRST CUT
                ; OF THIS SLICE WAS: it staged the body pointer in STRSCR+1 and
                ; the width in STRSCR, which is where MKI$/MKS$/MKD$ STAGE THEIR
                ; RESULT -- so `CVI(MKI$(258))` and `CVS(MKS$(1.5))` wrote the
                ; pointer straight over the string they were about to convert.
                ; 12 of 32 rows DIFF, and the green ones were the arguments that
                ; are not staged strings. A ROUND TRIP IS WHERE A SHARED SCRATCH
                ; BUFFER ALIASES ITSELF, and it is the case these verbs exist for.
                ; 🎯 SO THE BODY DEREFS IT ITSELF: STRPTR is the evaluator's
                ; descriptor pointer, already in RAM, and `pu_deref_body` is in
                ; the LOW REGION ($28C1) -- callable from disk.rom by absolute
                ; address. Nothing has to cross that was not already across.
                ld      a,c
                ld      (FACTYP),a          ; the width IS the FACTYP code, so this
                                            ; is both how the width crosses AND the
                                            ; final type for the float arms
                push    ix
                push    bc                  ; C = the width, and the verb's identity
                ld      hl,H_CVI
                ld      a,c
                cp      2
                jr      z,ev_cv_hook
                ld      hl,H_CVS
                cp      4
                jr      z,ev_cv_hook
                ld      hl,H_CVD
ev_cv_hook:
                ld      de,ev_cv_back       ; call THROUGH HL: the cell is
                push    de                  ; `F7 <slot> <lo> <hi> C9`, so its own
                or      a                   ; `ret` lands here; unclaimed it is a
                jp      (hl)                ; bare `ret` and lands here at once
ev_cv_back:
                pop     bc
                pop     ix
                jp      nc,ev_f_ifc         ; no disk ROM -> Illegal function call
                ; 🎯 THE BODY RAN IN disk.rom. `hk_cv` converted everything: for
                ; width 2 the two bytes are in FAC and FACTYP is 2; for 4/8 the
                ; packed value is in FAC with FACTYP already the width. THE WIDTH *IS* THE FACTYP CODE, which
                ; is why no second table is needed on either side of the call.
                ; 🟢 `flt_int_result` IS GONE FROM THIS PATH, not relocated: it
                ; only ever set FACTYP := 2, and the body sets FACTYP itself in
                ; both arms -- so its page-1 address stopped being a dependency
                ; of a routine that has to run in another slot.
                ld      a,c
                cp      2
                jr      nz,ev_cv_float
                ld      de,(FAC)            ; the int the body produced (LE)
                ret
ev_cv_float:
                jp      flt_to_int16        ; tail: sets DE, returns to OUR caller

; --- cvi_tmm: CVI's non-string decline, with the OPERAND'S OWN FAULT FIRST ----
; 🔴 D-CVISTRTM. D-CVITM pointed this decline at `ev_f_tmm` and that is the bug
; D-STRTM had already fixed for the shared `ev_str_arg` path, in the very file
; the CVI comment sits beside: first-error-wins only splits `CVI(5)` from a
; nested fault WHEN THE INNER THING ALREADY SET FPERR. `CVI(0*(1/0)+1)` sets
; nothing -- `str_eval` declines WITHOUT EVALUATING -- so the mismatch armed
; first and the division by zero was never raised. Both references answer
; Division by zero. (Before D-CVITM this row was Syntax error, so it was wrong
; then too: that slice closed 3 of 4 and left the 4th wrong in a new way.)
; 🎯 FOR THE FOURTH TIME IN THIS CLASS -- D-LEFTTM, D-INSTRTM, D-STRTM and now
; here -- THE FIX IS THE ORDER: evaluate the operand, THEN defer.
; 🟢 AND NO DOUBLE EVALUATION, which is what makes it safe: nothing re-drives the
; operand after this point (CVI's own tail is the only continuation, and it is
; not reached). `esa_tmm` wants HL on the operand; IX is still there because
; `str_eval_ix` copies IX to HL and never writes IX.
cvi_tmm:
                push    ix
                pop     hl                  ; HL = the operand cursor, unadvanced
                jp      esa_tmm             ; `call eval` + `jp ev_f_tmm`, shared

; --- FRE(n) / FRE(s$): free memory (docs/spec-basic-binfre.md §4) -----------
; MEASURED on the VG-8020: the numeric argument is a DUMMY -- FRE(0), FRE(1),
; FRE(-1) and FRE(255) all agree once they are read at the SAME evaluation depth
; -- and the string form is selected by the argument's TYPE, never its content
; (FRE(""), FRE("ABCDE") and FRE(A$) agree). Parentheses are REQUIRED; bare FRE,
; FRE() and FRE(0,0) are Syntax errors.
;
; So the argument is accepted in EITHER type and then DISCARDED, which is why
; this cannot join ev_ff_argtab (numeric-only -- FRE("") would be a type
; mismatch) and cannot be shaped like CVI (string-only -- FRE(0) would need a
; string). It is a str_eval attempt with a numeric retry.
;
; D-BF-A(c): the reference reports TWO independent pools; zerobas has ONE free
; gap and CLEAR's string-space argument is discarded, so BOTH forms answer with
; that gap. Computed sub-side (op 15) because the array-region walk lives there.
ev_ff_fre:
                call    ixsp_paren_req     ; D-IXSP
                                           ; bare FRE -> deferred syntax error
                call    ixsp                ; D-IXSP
                push    ix                  ; guard the cursor for the numeric retry:
                call    str_eval_ix         ; a STRING argument? (repack str_eval
                                            ; CALSLTs and can exit NC with GARBAGE IX --
                                            ; the CVI landmine above)
                jr      nc,ev_fre_num       ; no -> re-read the same text as numeric
                pop     ix                  ; drop the guard; take str_eval's cursor
                push    hl
                pop     ix                  ; IX = past the string operand
    IF CLEARPOOL
                ld      a,15                ; op 15 = the STRING POOL's free bytes
                ld      (SH_OP),a           ; (stored NOW: ev_fre_close's own ev_sp
                                            ;  and (ix+0) read clobber A)
    ENDIF
                jr      ev_fre_close
ev_fre_num:
                pop     ix                  ; restore the cursor str_eval consumed
                call    ev_logic            ; the ordinary numeric argument, DISCARDED
                                            ; (no domain check: FRE(-1) must not raise,
                                            ;  exactly as POS(-1) must not)
    IF CLEARPOOL
                ; ⚠️ D-CLP: THE TWO FORMS NOW ANSWER DIFFERENT QUESTIONS, and that
                ; is the whole point of the partition. Before it, zerobas had ONE
                ; free gap and BOTH forms reported it -- D-BF-A(c). With the pool
                ; real, FRE(s$) is the pool's free bytes and FRE(n) is the
                ; VARIABLE space below the pool floor, exactly as the reference
                ; has always split them. Leaving both on op 15 makes FRE(0)
                ; answer 200 at boot, which the probe's ctl-fre0 control catches
                ; immediately (FRE(0)>1000 reads false).
                ld      a,17                ; op 17 = free VARIABLE space
                ld      (SH_OP),a
    ENDIF
ev_fre_close:
                call    evsp_close          ; D-EVSPCLOSE
                inc     ix
                push    ix                  ; call_strheap clobbers IX (the cursor)
    IF CLEARPOOL
                                            ; SH_OP already selected above -- which
                                            ; POOL to report is decided by the
                                            ; ARGUMENT'S TYPE, not here
    ELSE
                ld      a,15
                ld      (SH_OP),a           ; op = 15 (FREE_GAP)
    ENDIF
                call    call_strheap
                pop     ix
                call    flt_int_result      ; an int result even when the argument
                ld      de,(SH_PTR)         ;  was a float or a string (A only)
                ret

    IF I2_RESIDENT
; --- PDL(n) / PAD(n): analog input devices, slice I2 -----------------------
; docs/spec-basic-input-devices.md §9. Thin wrappers over GTPDL ($00DE) / GTPAD
; ($00DB), which the zerobas-tape page-0 patch supplies (C-BIOS ships both as
; debug stubs; decision D-I-6). Placed here at the ev_f_ff tail because inserting
; them among the other bodies would split forward jr's -- the I1 landmine (spec
; §9.5). Entered with E = the range-checked index. Both BIOS entries are
; documented "Registers: All", so IX (the evaluator's token cursor) is guarded
; across the call, exactly as STICK/STRIG do; and because that contract does not
; promise E either, PAD saves the sub-function on the stack rather than re-reading
; E after the call (keeps the wrapper BIOS-agnostic).
ev_ff_pdl:                                  ; PDL(n): 0..255 paddle dial position
                ld      a,e                 ; A = paddle 1..12
                push    ix
                call    GTPDL
                pop     ix
                jp      ev_ret_e            ; D-RETTAIL: DE = A (0..255) -- 0..255, never negative
ev_ff_pad:                                  ; PAD(n): touch panel read
                ld      a,e
                and     3                   ; sub-function (before the call may clobber E)
                ld      c,a                 ; C = sub 0..3
                ld      a,e                 ; A = 4*device + sub (0..7)
                push    ix
                push    bc
                call    GTPAD
                pop     bc
                pop     ix
                ; The boolean sub-functions -- sense (0/4) and button (3/7) -- return
                ; $00/$FF, which BASIC widens to 0/-1 like STRIG (copy the byte into
                ; both halves). The coordinate sub-functions -- X (1/5), Y (2/6) --
                ; return 0..255 and zero-extend. So the widening is per sub-index.
                ld      e,a
                ld      d,a                 ; boolean widen: $FF -> -1, $00 -> 0
                ld      a,c
                cp      1
                jr      z,ev_ff_pad_coord   ; sub 1 = X
                cp      2
                jr      z,ev_ff_pad_coord   ; sub 2 = Y
                ret                         ; sub 0/3 boolean -> DE = $FFFF / $0000
ev_ff_pad_coord:
                ld      d,0                 ; zero-extend a coordinate (0..255)
                ret
    ENDIF

; =============================================================================
; Math pack slice 1a: ABS/SGN/INT/FIX/CINT/CSNG/CDBL (docs/spec-basic-math-
; pack.md §9). Thin wrappers over the resident page-0 fp_*/widen_*/round_*
; primitives (float-arith.asm) + the new fp_trunc leaf (same file, §9.2).
; =============================================================================

; --- ev_ff_mathconv: dispatch on the $FF-selector byte for the seven slice- -
; 1a functions. Entered exactly like ev_ff_strnum (IX on the selector byte, A
; = the selector — same contract, str-engine.asm), reached from ev_f_ff's
; repack branch; falls through to ev_ff_strnum (LEN/ASC/VAL) when the
; selector matches none of these seven, which in turn falls to ev_f_err.
ev_ff_mathconv:
                cp      ABS_TOKEN
                jp      z,evmc_abs
                cp      SGN_TOKEN
                jp      z,evmc_sgn
                cp      INT_TOKEN
                jp      z,evmc_int
                cp      FIX_TOKEN
                jp      z,evmc_fix
                cp      CINT_TOKEN
                jp      z,evmc_cint
                cp      CSNG_TOKEN
                jp      z,evmc_csng
                cp      CDBL_TOKEN
                jp      z,evmc_cdbl
                cp      SQR_TOKEN
                jp      z,evmc_sqr
                cp      EXP_TOKEN
                jp      z,evmc_exp
                cp      LOG_TOKEN
                jp      z,evmc_log
                ; ATN/SIN/COS/TAN/RND -- the five TOTAL sub-ROM math calls -- have no
                ; arm of their own: they fall into the table scan below. SQR/EXP/LOG
                ; keep theirs because each has its own domain check or magnitude
                ; disposition; these five are the ones that are byte-identical.

; --- evmc_total_scan: the five TOTAL sub-ROM math calls, table-driven -------
; SWAP-funding carve (2026-07-28), tools/clone_scout.py's third row (estimated
; 20 B, measured 41 B). evmc_atn/sin/cos/tan/rnd were FIVE identical 10 B stubs
; -- `call evmc_prologue` / `ret nz` / `ld hl,<entry>` / `jp evmc_dispatch` --
; differing ONLY in the sub-ROM entry address, each reached by its own 5 B arm of
; the chain above. That is 78 B saying one thing five times; this is 37 B.
;
; Each of the five is total over all x (no domain check, no error tail -- see the
; per-function commentary that used to sit on each stub, preserved at the table
; rows below), which is EXACTLY what makes them collapsible: SQR/EXP/LOG are not.
;
; in: A = the $FF-selector byte, as ev_ff_mathconv was entered with.
; The table stores only the entry's LOW byte; the high byte is a constant, which
; the assembly-time guard below pins rather than assumes.
EVMC_TOTAL_N    equ     5                   ; rows in evmc_total_tab (declared ahead
                                            ; of use rather than forward-referenced)
evmc_total_scan:
                ld      hl,evmc_total_tab
                ld      b,EVMC_TOTAL_N
evmc_ts_lp:
                cp      (hl)                ; selector == this row's token?
                inc     hl                  ; HL -> the row's entry-low byte
                jr      z,evmc_ts_hit
                inc     hl                  ; HL -> the next row's token
                djnz    evmc_ts_lp
                jp      ev_ff_strnum        ; not ours -> LEN/ASC/VAL, else ev_f_err
evmc_ts_hit:
                ld      l,(hl)              ; HL = SUBROM_ENTRY_BASE_P1 + 3*idx
                ld      h,SUBROM_ENTRY_BASE_P1 >> 8
                ; evmc_prologue runs ev_mc_arg -> the whole expression evaluator, so
                ; NOTHING in a register survives it -- guard the entry on the stack.
                ; PUSH/POP do not touch flags, so the prologue's Z ("clean") still
                ; decides the `ret nz` below, exactly as in the five stubs this
                ; replaces. The pop MUST precede the `ret nz`, or the error exit
                ; would return INTO the guarded entry address.
                push    hl
                call    evmc_prologue
                pop     hl
                ret     nz                  ; malformed/empty arg -> deferred syntax
                jp      evmc_dispatch

; --- evmc_total_tab: <selector token>, <low byte of the sub-ROM entry> ------
; The five rows carry what used to be five stub headers. All are COMPUTE-ONLY
; tenants (they leave FAC correct but touch neither FACTYP nor DE), so
; evmc_dispatch does the shared FACTYP:=8 + flt_to_int16 refresh for all of them.
evmc_total_tab:
                db      ATN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ATN) & $FF
                db      SIN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SIN) & $FF
                db      COS_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_COS) & $FF
                db      TAN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_TAN) & $FF
                ; RND's argument VALUE is read by fp_rnd itself (ignored when
                ; positive, consumed as mant14 when negative) -- nothing here
                ; interprets it, so RND collapses with the other four.
                db      RND_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_RND) & $FF

; Assembly-time guard: the table stores ONE byte per entry, so every one of the
; five must share SUBROM_ENTRY_BASE_P1's 256 B page. RND has the largest index of
; the five (9), so checking it bounds all of them. On violation this references an
; undefined symbol, forcing a named ERROR rather than a silently wrong dispatch
; address -- the same technique as main.asm's $8000 ceiling assert. Emits nothing
; when it holds.
    IF ((SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_RND) >> 8) - (SUBROM_ENTRY_BASE_P1 >> 8)
                db      EVMC_TOTAL_TAB_ENTRIES_CROSS_A_256B_PAGE__STORE_FULL_ADDRESSES
    ENDIF

; --- ev_mc_arg: parse "( <numeric expr> )" from IX (positioned on the -------
; selector byte, per this group's entry contract). Leaves DE = the argument's
; int16 fast value and FAC/FACTYP set to its real type by ev_xor's own float
; plumbing (expr.asm/float-arith.asm) — UNLIKE ev_ff_arg, this does NOT force
; FACTYP:=2 afterward: every evmc_* below must see the argument's true type
; to decide its own result type (spec §9.1's "same FACTYP as x" / int-result
; columns). IX advanced past ')'. Clobbers as ev_xor.
ev_mc_arg:
                call    ixsp_paren_req     ; D-IXSP
                                           ; D-F2-4: missing '(' (bare fn / operator- or
                                            ; space-separated) -> deferred FPERR=4 "syntax
                                            ; error", NOT the silent ev_f_err. Same chokepoint
                                            ; the empty-parens gate (D-F2-3) uses.
                inc     ix
                call    ev_logic            ; DE = argument; FAC/FACTYP = its type
                call    evsp_close          ; D-EVSPCLOSE
                                            ; unclosed `f(x`) -> deferred "syntax error"
                inc     ix
                ret

; --- ev_mc_arg_checked: ev_mc_arg + "bail if a deferred error is already ----
; pending" gate (D-F2-4, docs/spec-basic-malformed-call-syntax-error.md). Every
; evmc_* below calls THIS instead of ev_mc_arg and does `ret nz` immediately
; after. FPERR is nonzero here iff the argument raised a deferred statement-abort
; -- ev_mc_arg's own missing-'('/')' exits above (FPERR=4), OR an empty-expr arg
; (`SQR()`/`LOG()`) that set FPERR=4 deep in ev_f_empty while ev_mc_arg still
; returned normally, OR any nested hard error (overflow/div0/illegal) in the arg
; expression. In ALL those cases the reference has already aborted the statement,
; so the caller must NOT run its body: no domain/overflow check (which would
; clobber FPERR=4 -> a wrong `illegal function call`/`overflow` message) and, for
; RND, no fp_rnd (which would mutate the persistent seed). A deferred TYPE
; mismatch (e.g. `RND("A")`) means the same thing and is caught by the same test.
; the cell holds at most one code per statement (D-STMTPEND: exec_stmt now
; proves that by TESTING it rather than by storing a zero), so a clean arg
; leaves it 0 here and
; the body runs unchanged. Returns Z iff no error is pending. Clobbers only A
; (every evmc_* reloads it); DE/FAC/FACTYP are ev_mc_arg's.
; D-PENDERR: this routine used to read TWO cells and its header called them "the
; OTHER deferred flag" -- the clearest statement in the tree that they were one
; concept spelled twice. -5 B, and the surviving test is bit-identical for every
; row: `RND("A")` now sets FPERR_TYPEMM where it used to set TMISMATCH.
ev_mc_arg_checked:
                call    ev_mc_arg
                ld      a,(FPERR)
                or      a
                ret                         ; Z iff no deferred error is pending

; --- evconv_pack_same_type: ARGA (already truncated by the caller — exact, --
; no guard-digit rounding pending) -> FAC, preserving FACTYP exactly as it
; already stands (4 single / 8 double; the FACTYP==2 case is handled by each
; caller's own early-out before this is ever reached). Refreshes DE via
; flt_to_int16 (float.asm), the same silent address-domain contract every
; other ev_f_* factor tail keeps. Shared by evmc_int/evmc_fix. Clobbers A, B,
; C, D, E, H, L.
evconv_pack_same_type:
                call    arga_dig_iszero
                jr      z,ecpst_zero
                ld      a,(FACTYP)
                cp      8
                jr      z,ecpst_dbl
                call    arga_pack_single
                jp      flt_to_int16
ecpst_dbl:
                call    arga_pack_fac
                jp      flt_to_int16
ecpst_zero:
                xor     a
                ld      (FAC),a
                jp      ret_de0


; --- evmc_arg_int: the math-verb argument gate, and "is it already an int?" ---
; D-NGRAM19. ABS, SGN, INT and FIX each opened with the same nine bytes:
;   call ev_mc_arg_checked / ret nz / ld a,(FACTYP) / cp 2
;
; 🔴 IT CANNOT BE A PLAIN SUBROUTINE, AND THE SWEEP'S 14 B IS AN OVER-ESTIMATE
; BECAUSE OF IT. Two things leave the run for the caller: the `ret nz` returns
; from the VERB (inside a helper it would return to the call site, one frame too
; shallow -- the D-NGRAM8 bug), and the final `cp 2` publishes a Z FLAG that each
; of the four then branches on DIFFERENTLY (`jr nz` / `jr z` / `ret z` / `ret z`).
; One flag cannot carry both answers, so the malformed case moves to CARRY and
; each site keeps a one-byte `ret c` of its own. That is the D-ARGOPEN shape: a
; flag a row can see beats a frame trick.
;   out: CF set = malformed argument (the caller returns);
;        CF clear, Z = the argument is already an int16 (FACTYP == 2).
evmc_arg_int:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                jr      nz,eai_bad          ; malformed/empty -> deferred syntax error
                jp      factyp_is2  ; CF clear; Z = already an int
eai_bad:
                scf
                ret

; --- evmc_abs: ABS(x) -> |x|, same FACTYP as x (spec §9.1). Int path: plain -
; magnitude, except the -32768 edge escapes int16 (promotes to a double
; +32768.0, mirroring float-arith.asm's -32768\-1 quirk, spec §10.4/§9.1's
; "int-domain per §10 float core"). Float path: clear FAC's sign bit in place
; (0's sign bit is already clear) and refresh DE; FACTYP untouched.
evmc_abs:
                call    evmc_arg_int        ; D-NGRAM19
                ret     c                   ; malformed -> deferred
                jr      nz,evabs_float
                ld      a,d
                cp      $80
                jr      nz,evabs_noesc
                ld      a,e
                or      a
                jr      nz,evabs_noesc
                ; DE == -32768: escapes int16 -> promote to double +32768.0
                ; Shared with ev_f_neg's unary-minus arm (D-NEG8K) -- the SAME
                ; escape, at the second operator that can produce +32768.
evabs_esc:
                ; 🎯 D-CARVE2: THE CANONICAL "RESULT IS +32768" TAIL. Two callers
                ; reach the same escape: ABS(-32768) and -32768/-1 both overflow
                ; int16 POSITIVE, so both answer 32768 as a float. The other is
                ; basic/float-arith.asm's signed divide, in the LOW region, which
                ; now jumps here -- so the 10 B come back where they are scarcest.
flt_ret_32768:
                ld      hl,ARGA
                xor     a
                ld      de,32768
                call    widen_uint_to
                jp      round_and_finalize
evabs_noesc:
                ex      de,hl
                call    abs16
                ex      de,hl
                ret
evabs_float:
                ld      a,(FAC)
                or      a
                ret     z                   ; zero: nothing to clear, DE already 0
                and     $7F
                ld      (FAC),a
                jp      flt_to_int16        ; tail call: DE refreshed; FACTYP untouched

; --- evmc_sgn: SGN(x) -> -1/0/+1, always int (FACTYP:=2, spec §9.1). -------
evmc_sgn:
                call    evmc_arg_int        ; D-NGRAM19
                ret     c                   ; malformed -> deferred
                jr      z,evsgn_int
                ld      a,(FAC)
                or      a
                jr      z,evsgn_zero
                and     $80
                jr      z,evsgn_pos
                jr      evsgn_neg
evsgn_int:
                ld      a,d
                or      e
                jr      z,evsgn_zero
                ld      a,d
                and     $80
                jr      z,evsgn_pos
evsgn_neg:
                ld      de,$FFFF
                jr      evsgn_settype
evsgn_pos:
                ld      de,1
                jr      evsgn_settype
evsgn_zero:
                ld      de,0
evsgn_settype:
                jp      set_factyp2

; --- evmc_int: INT(x) -> floor toward -infinity, same FACTYP as x (spec ----
; §9.1). fp_trunc (float-arith.asm) truncates toward 0; if a fraction was
; dropped AND x was negative, one more step (-1) makes it a floor (§9.2).
evmc_int:
                call    evmc_arg_int        ; D-NGRAM19
                ret     c                   ; malformed -> deferred
                ret     z                   ; already int: INT(x)=x
                call    arga_widen          ; D-ARGAWIDEN
                call    fp_trunc            ; CF set iff a fraction was dropped
                jr      nc,evmc_int_pack
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,evmc_int_pack     ; positive: truncate == floor already
                jr      evmc_sub1           ; negative + fraction dropped: floor = trunc-1
evmc_int_pack:
                jp      evconv_pack_same_type

; --- evmc_fix: FIX(x) -> truncate toward 0, same FACTYP as x (spec §9.1). --
; Never needs the INT adjustment ("FIX = fp_trunc", §9.2).
evmc_fix:
                call    evmc_arg_int        ; D-NGRAM19
                ret     c                   ; malformed -> deferred
                ret     z
                call    arga_widen          ; D-ARGAWIDEN
                call    fp_trunc            ; CF ignored -- FIX never adjusts
                jp      evconv_pack_same_type

; --- evmc_sub1: ARGA (INT's fp_trunc result, truncated toward 0) -= 1, ------
; preserving FACTYP as it stood on entry: fp_sub always packs a double via
; round_and_finalize, so a single-typed operand is re-rounded back down via
; round_single_and_pack — exact, since ARGA holds only integer digits at this
; point (guard digit 0), so no precision is lost by the re-round. A
; double-typed operand passes straight through fp_sub's own double result.
; Clobbers as fp_sub + round_single_and_pack.
evmc_sub1:
                ld      a,(FACTYP)
                ld      (MC_TYPE),a
                ld      hl,ARGB
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGB := +1 (exact int widen)
                call    fp_sub              ; ARGA/FAC := ARGA - 1 (FACTYP forced to 8)
                ld      a,(MC_TYPE)
                cp      8
                ret     z                   ; was already double: fp_sub's result stands
                jp      round_single_and_pack  ; re-round the exact ARGA to single (tail)

; --- evmc_cint: CINT(x) -> int16, domain -32768..32767 else Overflow -------
; (spec §9.1). ORACLE CORRECTION (2026-07-12, basic_probe_math_conv.py
; characterisation): the spec text says "rounds (half-up)", reasoned from
; general BASIC docs, but the VG-8020 does NOT round CINT at all --
; cint(2.9)=2, cint(1.5000001#)=1, cint(32767.6)=32767 (in range, not
; Overflow), cint(-32768.6)=-32768 (also in range) -- every captured case is
; bit-identical to a plain TRUNCATE toward 0. That is exactly the EXISTING
; strict int16 domain conversion \\/MOD/AND/OR/XOR/NOT operands already share
; (spec-basic-float-core.md §10.3: -32769<x<32768, truncate toward 0, else
; Overflow) -- fac_to_int_strict_reset (float-arith.asm) IS CINT, unchanged;
; no new arithmetic needed. Per the project's "the capture wins" rule, this
; supersedes the spec's stated rounding contract -- flagged in the slice
; report, not silently papered over.
evmc_cint:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                jp      fac_to_int_strict_reset ; strict -32768..32767 domain,
                                            ; truncate toward 0; FACTYP:=2 always

; --- evmc_csng: CSNG(x) -> narrow to single, round half-up (spec §11.2's ---
; store-coercion rule, reused as-is). widen_rhs_operand already dispatches on
; the live FACTYP (int/single/double), so no int early-out is needed here —
; an int operand is always exact at 6 digits anyway.
evmc_csng:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                call    arga_widen          ; D-ARGAWIDEN
                jp      round_single_and_pack

; --- evmc_cdbl: CDBL(x) -> widen to double, exact (spec §11.2's "double: ---
; exact" rule). Same widen_rhs_operand + round_and_finalize composition CSNG
; uses above, just the double pack (no digit loss possible from any source).
evmc_cdbl:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                call    arga_widen          ; D-ARGAWIDEN
                jp      round_and_finalize

; --- evmc_sqr: SQR(x) -> non-negative square root, DOUBLE (math pack slice --
; 1b, docs/spec-basic-math-pack.md §10.5). Same arg-parse + widen shape as
; evmc_int/evmc_fix (ev_mc_arg then widen_rhs_operand into ARGA), then
; DISPATCHES to fp_sqrt in the sub-ROM PAGE-1 island (sub/sub.asm) via
; subrom_call/SUBROM_ENTRY_BASE_P1+SUBROM_IDX_SQR (docs/spec-basic-subrom-
; mathpack.md §2/§3 -- fp_sqrt migrated 2026-07-13; this stub is the ONLY
; main-ROM-side change of that migration, everything else is unchanged
; behaviour). subrom_call's `or a` before its `ret` preserves A (the tenant's
; status: 0 ok, nonzero domain error x<0) and clears CF on a completed call;
; CF=1 means the sub-ROM is absent (never on the merged machine, which always
; ships it) -- handled the same defensive way as the tokeniser/detok call
; sites (basic/interp.asm/list.asm). fp_sqrt is now COMPUTE-ONLY (§3/§4): on
; success it leaves FAC correct but does NOT set FACTYP or DE (flt_to_int16
; is main-ROM-resident, not part of the imported resident-ABI surface), so
; THIS stub sets FACTYP:=8 + refreshes DE via flt_to_int16 after a successful
; return -- the same finalization fp_sqrt used to do internally before the
; move. On domain error (A<>0): FPERR:=3 + DE:=0, mirroring evmc_cint's shape
; (fac_to_int_go, the deeper leaf, sets FPERR:=1 for Overflow); interp.asm's
; fp_runtime_error maps FPERR=3 to "illegal function call" at the next
; statement-boundary check (check_expr_errors/_popbc), same D-F2-1 pattern as
; Overflow/division-by-zero -- never a `jp` out of the evaluator itself.
evmc_sqr:
                call    evmc_prologue
                ret     nz
                ; Domain check (x<0 -> "illegal function call") is done HERE, not
                ; in the tenant: CALSLT does NOT preserve A, so a tenant status
                ; byte cannot ride back in A (existing tenants return via RAM
                ; buffers, never A). ARGA holds the widened operand; sign<>0 =
                ; negative (same test fp_sqrt used internally, sign-first order,
                ; so -0.0 -> error exactly as before). x>=0 always succeeds in the
                ; tenant, so nothing is read from A after the call.
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      nz,evmc_sqr_err
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SQR
                jr      evmc_dispatch
evmc_sqr_err:
                ld      a,3
                jp      penderr_de0         ; D-PENDTAIL (-4 B, main page 1)

; --- evmc_prologue / evmc_dispatch: the body the math-function stubs shared ---
; verbatim.  Until 2026-07-27 EIGHT stubs (SQR LOG EXP ATN SIN COS TAN RND) each
; carried their own copy of the same arg-check-and-widen opening and the same
; guard-IX-dispatch-to-tenant closing; five of them (ATN SIN COS TAN RND) were
; identical end to end apart from the SUBROM_IDX_* constant.  Same shape, and the
; same fix, as basic/fat.asm's thirteen FAT shims.
;
; evmc_prologue -- the opening.  Returns NZ exactly when ev_mc_arg_checked does,
; leaving the SAME registers it left: nothing here executes before that `ret nz`,
; so each stub's own `ret nz` behaves bit-for-bit as its inline copy did.  On the
; good path `cp a` forces Z without disturbing A, and A is dead in every caller
; (the next write is `ld a,8`, or a fresh `ld a,(ARGA+...)` domain load).
; DELIBERATELY not folded into evmc_dispatch: SQR/LOG/EXP must run their domain
; checks BETWEEN the two halves.
;
; EVERY stub reaches evmc_dispatch by `jp`, not `jr`, and that is deliberate
; rather than lazy: the eight stubs are NOT contiguous -- SQR's, LOG's and EXP's
; domain-check bodies and error tails are interleaved among them -- so a `jr`
; reaches from some and not others, and which ones changes whenever anything in
; between grows.  Two builds were spent discovering that.  Uniform `jp` costs
; 5 bytes across the eight and makes the layout order irrelevant.
evmc_prologue:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax
                                            ; error (registers as the gate left them)
                call    arga_widen          ; D-ARGAWIDEN
                cp      a                   ; force Z = "clean"; A untouched, and dead
                ret

; evmc_dispatch -- the closing.  in: HL = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_x.
; IX is the parser's text cursor and subrom_call/CALSLT clobbers ALL registers
; (subromcall.asm's header), so it is guarded across the call exactly as before;
; POP does not touch flags, so CF survives to the subrom_absent_error test.  The
; entry arrives in HL and reaches IX via the stack (IX cannot be loaded from HL
; directly) -- and it MUST be loaded after the guard push, or the guard would
; save the entry address instead of the cursor.
evmc_dispatch:
                push    ix                  ; guard the text cursor
                push    hl
                pop     ix                  ; IX = tenant entry
                jp      cpow_tail           ; D-SAVECOLON carve (-8 B page 1): the
                                            ; rest was cpow_dispatch's 11 bytes
                                            ; verbatim -- `call subrom_call / pop ix
                                            ; (flags survive) / jp c,subrom_absent_error
                                            ; / jp fac_dbl_int16` (float-arith.asm).
                                            ; D-NGRAM14: tail -- FACTYP=8, then
                                            ; DE := flt_to_int16(FAC). The body is
                                            ; in basic/float-arith.asm, page-0 low:
                                            ; two of its four reachers run with page 1
                                            ; switched out and cannot leave it.

; --- evmc_log: LOG(x) -> natural logarithm, DOUBLE (math pack slice 2b, ----
; docs/spec-basic-mathpack-slice2.md §12.6). Same arg-parse + widen shape as
; evmc_sqr (ev_mc_arg then widen_rhs_operand into ARGA), then a domain check
; EXTENDED to sign-OR-zero (LOG's total domain is x>0, wider than SQR's
; x>=0): the sign check (ARGA+FPNUM_SIGN<>0) catches x<0 -- same "sign-first,
; so a hypothetical -0.0 also errors" order as evmc_sqr -- and a SEPARATE
; dig15_iszero(ARGA+FPNUM_DIG) check catches x==0 (a canonical +0.0 has
; sign=0, so the sign check alone would miss it). Both routes to the SAME
; error tail as evmc_sqr_err (verbatim: FPERR:=3 "illegal function call",
; DE:=0). Dispatches to fp_log in the sub-ROM PAGE-1 island via subrom_call/
; SUBROM_ENTRY_BASE_P1+SUBROM_IDX_LOG; same CALSLT-A-not-preserved
; discipline as evmc_sqr/evmc_atn: fp_log is COMPUTE-ONLY (leaves FAC
; correct, does not touch FACTYP/DE), so THIS stub sets FACTYP:=8 +
; refreshes DE via flt_to_int16 after a successful return.
evmc_log:
                call    evmc_prologue
                ret     nz
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      nz,evmc_log_err
                call    arga_dig_iszero
                jr      z,evmc_log_err
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LOG
                jr      evmc_dispatch
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to evmc_sqr_err,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
evmc_log_err    equ     evmc_sqr_err

; --- evmc_exp: EXP(x) -> e^x, DOUBLE (math pack slice 2b, docs/spec-basic- --
; mathpack-slice2.md §12.6). Same arg-parse + widen shape as evmc_sqr/
; evmc_atn, then a COARSE MAGNITUDE disposition instead of a domain error
; (EXP is total, but the tenant's own n8 table-reduction algebra needs
; |x|<1000 to keep every downstream dexp inside fp_mul's own preExp
; envelope, §12.4 step 3): ARGA+FPNUM_DEXP read as a SIGNED byte (safe --
; every canonical FPNUM's dexp fits widen_fac_to's own -64..63 range, so the
; high byte is always pure sign-extension); dexp>=4 <=> |x|>=1000 (a TINY x
; has a NEGATIVE dexp, so this is genuinely a magnitude test, not a sign
; test). Positive x this large -> Overflow (matches the characterized
; EXP(1000) disposition). Negative x this large -> the true mathematical
; answer underflows to 0, so this returns 0 WITHOUT an error (matches
; EXP(-1000)) -- same "fall into the common successful tail" shape as any
; other non-error disposition. Otherwise dispatch to fp_exp (SUBROM_IDX_EXP).
evmc_exp:
                call    evmc_prologue
                ret     nz
                ld      a,(ARGA+FPNUM_DEXP) ; low byte -- signed, safe (see
                                            ; header above)
                sub     4
                jp      p,evmc_exp_huge     ; dexp-4 >= 0 (no overflow in
                                            ; this range) <=> dexp>=4
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_EXP
                jr      evmc_dispatch
; ⛔ DO NOT "FIX" THIS TO MATCH THE REFERENCE. It answers 0 for EXP(-huge)
; while BOTH references answer `Overflow`, and that divergence is DELIBERATE and
; already adjudicated: docs/spec-basic-mathpack-slice2.md §12.9 records the
; reference's own `EXP(-200)` Overflow as "a full disposition BUG in the
; reference -- the true answer underflows to 0, which zerobas returns
; correctly", and `math-acceptance` encodes that decision (its truth oracle
; asserts `exp(-1000)` is 0, and `10^-70.5` is a row scored on OURS only).
;
; 🔴 D-EXPNEG (2026-08-30) DELETED THIS ARM ON EXACTLY THAT REASONING -- both
; references say Overflow, so match them -- AND WAS REVERTED. Measuring the
; references is not the same as checking whether the divergence was already
; decided; here it was, fifteen days earlier, in the file this code is specified
; by. The rows it took are kept in scratchpad/ngram14_probe.py because they
; CONFIRM §12.9's characterisation at five more arguments
; (docs/spec-basic-ngram14.md §7).
evmc_exp_huge:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,evmc_exp_overflow
                xor     a
                ld      (FAC),a             ; EXP(-huge) -> 0, not an error (§12.9)
                jp      fac_dbl_int16       ; D-NGRAM14
evmc_exp_overflow:
                ld      a,1
                jp      penderr_de0         ; D-PENDTAIL (-4 B, main page 1)

; ATN / SIN / COS / TAN / RND have no stubs of their own any more -- see
; `evmc_total_scan` and `evmc_total_tab` above (the SWAP-funding carve,
; 2026-07-28). They were five VERBATIM copies of one shape, which is precisely
; the property the table encodes: total over all x (docs/spec-basic-mathpack-
; slice2.md §6/§11.5/§14.1/§14.7/§15.4 -- no domain check, no ARGA+FPNUM_SIGN
; branch, no coarse magnitude check like evmc_exp's, no error tail), and every
; tenant COMPUTE-ONLY, so one shared `evmc_dispatch` does the FACTYP:=8 +
; flt_to_int16 refresh and the CALSLT-A-not-preserved discipline for all five.

; --- ev_f_varptr: VARPTR(<var>) -> address of the variable's value field -----
; Returns the address of the 2-byte value cell in zerobas's own variable table
; (VARTAB), NOT the reference ROM's variable-area address — zerobas's table is
; its own layout, so VARPTR yields OUR address. This is a documented divergence
; (PROVENANCE.md): a loader stub that pokes through VARPTR sees a valid, writable
; 16-bit cell, which is all the loader use needs.
;
; ⚠️ D-VPTRDOM (2026-08-19): AN UNSET SCALAR IS `Illegal function call`, AND IT
; USED TO BE CREATED HERE. The old header said "if the variable does not yet
; exist it is created (value 0) so the returned address is always valid" -- a
; deliberate design choice, and MEASURED WRONG on BOTH references: `X=VARPTR(Q)`
; with Q unset is IFC on the VG-8020 AND the CF-3300, against a `Q=1` control
; silent on all three (docs/todo-staleness-sweep-2026-08.md §4.2, and rows
; m.ctldrift/m.arydrift in lvfix-acceptance). Under the charter the reference
; wins, so the scalar path FINDS and no longer allocates.
; 🎯 THE CONSEQUENCE IS BIGGER THAN THE ROW, AND IT IS A LOSS OF COVERAGE, NOT
; OF CORRECTNESS. Arrays slice-4b §13a names VARPTR as THE ONLY eval-time scalar
; allocator, so this was also the only way a zerobas program could shift ARYTAB
; mid-statement. Closing it makes the §13a guards (`ex_let_arr`'s
; ary_snapshot_offset/ary_apply_offset and D-LVFIX's tgt_desc correction)
; UNREACHABLE FROM BASIC rather than wrong -- they still execute, they just can
; never see a nonzero offset now. They are NOT deleted: the argument for them is
; static, they are cheap, and a future eval-time allocator would need them back.
; ⚠️ What IS lost is K-LV5's live detector -- m.arydrift moved under that knife
; and nothing else did. That is recorded rather than worked around; see the
; residual, which this slice rewrites rather than closes.
; ⚠️ SCOPE: the ARRAY-element form is untouched. `VARPTR(A(1))` still auto-dims
; on read, which is what ev_f_arr does and what the references do; the oracle
; here covers the unset SCALAR only, and the fix is scoped to it.
ev_f_varptr:
                ld      c,a                 ; C = VARPTR_TOKEN (the dispatch's `cp`
                                            ; left it in A): ev_ff_arg's selector for
                                            ; the `#` form below; ixsp keeps C
                call    ixsp_paren_req     ; D-IXSP
                ; D-EVFERR: both these sites are Syntax error (2) on both
                ; references, and BOTH LOOKED GREEN because ev_f_err leaves the
                ; cursor UNADVANCED -- `A=VARPTR 5` / `A=VARPTR(5)` answered 2
                ; through exec_stmt's leftover-token layer (es_noentry), with
                ; the expression layer saying nothing at all. The rows with
                ; NOTHING left over separate them: `A=VARPTR` and `A=VARPTR(`
                ; COMPLETED SILENTLY. Byte-neutral retargets.
                call    ixsp                ; D-IXSP
                cp      '#'                 ; D-VARPTRCH: VARPTR(#n) is a channel's
                jp      z,ev_ff_arg_in      ; FCB address -- the int-argument path
                                            ; EOF/LOF/LOC take, selector in C
                call    is_letter           ; the argument must be a variable name
                jp      nc,ev_f_empty
                push    ix
                pop     hl                  ; HL = cursor at the name
                ; Fix (arrays slice-4c follow-up): VARPTR(A$) must hand back
                ; the STRING descriptor address ([len][ptr], entry+3 of the
                ; stride-6 string-scalar layout -- sub/arrays.asm elsize_
                ; from_type(1)=3), not a phantom NUMERIC entry. var_name_key's
                ; own vnk_dollar path always leaves (VARTYPE)=8 for a `$`
                ; name (that field resolves the DEFTBL/suffix numeric type
                ; only, it is not a string-ness flag), so VARTYPE alone can't
                ; steer var_alloc_or_find to the right entry kind. var_str_
                ; type (HL unmoved) answers string-ness directly; its A=1/0
                ; result is stashed in D across var_name_key below --
                ; deftbl_lookup, the only routine var_name_key's own no-
                ; suffix path calls, preserves BC/DE/HL per its own header,
                ; so D survives untouched.
                call    var_str_type        ; A = 1 iff the name has a '$' suffix
                ld      d,a
                call    var_name_key        ; BC = key, HL past the name
                push    hl
                pop     ix                  ; IX = advanced cursor
                ; F3: ensure the variable exists AT ITS RESOLVED TYPE (var_alloc_or_
                ; find allocates a zero-valued entry if none exists yet, leaving an
                ; existing one untouched), then hand back the address of its value
                ; field (entry+3 in the typed layout). type=1 (string) routes
                ; through the SAME string-scalar entry str_set_key/str_get_key
                ; use, instead of VARTYPE's numeric resolution (always 8 for a
                ; `$` name).
                ld      a,d
                or      a
                jr      nz,vptr_gottype     ; string: A is already 1 (from D)
                ld      a,(VARTYPE)
vptr_gottype:
                ; ARRAY-ELEMENT form?  VARPTR(A(subs)) / VARPTR(S$(subs)) -- a
                ; '(' right after a plain name is unambiguously a subscript list
                ; (arrays spec §9.4, the same disambiguation ev_f_var uses to
                ; reach ev_f_arr). Resolve the element ADDRESS via the shared
                ; ary_op0_resolve (op=0 RESOLVE, auto-dim on read -- exactly what
                ; ev_f_arr does, minus the FAC load) and hand it back, just as
                ; the scalar path below hands back a scalar's value-field
                ; address. Type in E across the '(' peek (which clobbers A).
                ld      e,a                 ; E = resolved type
                ld      a,(ix+0)
                cp      '('
                jr      z,vptr_arr          ; subscript -> array element
                ld      a,e                 ; scalar: A = type
                call    var_find_typed      ; D-VPTRDOM: FIND, never allocate.
                                            ; Same BC,A -> CF/HL contract as
                                            ; var_alloc_or_find and it guards IX
                                            ; (the text cursor) too, so this is a
                                            ; like-for-like swap; NC now means
                                            ; NOT SET rather than OOM, and op=4
                                            ; SCALAR_FIND cannot raise at all.
                jr      nc,vptr_unset       ; unset -> Illegal function call
                inc     hl
                inc     hl
                inc     hl                  ; HL = value field (entry+3)
                ex      de,hl               ; DE = the value-field address
vptr_close:
                call    evsp_close          ; D-EVSPCLOSE
                                            ; array subscript with no outer ')') ->
                                            ; the CHECKED deferred FPERR=4 syntax
                                            ; error, not the bare ERRMARK ev_f_err
                                            ; (which PRINT/LET's check_expr_errors
                                            ; never reads -> a silent wrong 0). Byte-
                                            ; neutral vs ev_f_err.
                inc     ix
                ret
vptr_arr:
                ; HL is still the cursor at '(' (var_name_key left it here and
                ; nothing since -- push hl/pop ix copies, the type select and
                ; the peek read via IX -- has touched it), BC = key, E = type.
                ld      a,e                 ; A = type (ary_op0_resolve wants it in A)
                call    ary_op0_resolve     ; Z: HL=cursor past ')', DE=elem addr
                                            ; NZ: FPERR mapped+set (subscript out of
                                            ; range / illegal fn call / syntax error),
                                            ; HL=cursor -- both pop [CURSOR] once
                push    hl
                pop     ix                  ; IX = cursor (ev_f_var's return contract)
                ; VARPTR yields an int16 ADDRESS in DE, so the factor's type must
                ; be int. The scalar path below gets that for free (eval() sets
                ; FACTYP=2 on entry and nothing between there and the return
                ; changes it), but THIS path runs a nested eval() -- the subscript
                ; list -- which leaves FACTYP as the SUBSCRIPT's type. A literal
                ; subscript leaves 2 (so VARPTR(X(2)) worked), but any non-literal
                ; one (scalar var, or the H4 nested array rvalue X(X(0))) leaves
                ; FACTYP=8 with the subscript's value still in FAC -- and every
                ; consumer (print.asm exp_num, LET) then reads FAC and IGNORES DE,
                ; so VARPTR(X(V)) returned V, not the address (arrays gate case
                ; arrelem.varptr.nested, root-caused 2026-07-20). Re-assert int
                ; AFTER the resolve; LD touches no flag and CALL preserves them,
                ; so the `jr z` below still reads ary_op0_resolve's own result,
                ; and DE (the address) is untouched. Covers the vptr_none
                ; fall-through too.
                ; flt_int_result (NOT the byte-identical set_factyp_int_ret):
                ; `grep flt_int_result` is the audit tool for "which factors
                ; return an int" -- VARPTR must show up in it.
                call    flt_int_result      ; FACTYP := 2 (clobbers A only)
                jr      z,vptr_close        ; Z: DE = element addr -> shared ')' tail
                                            ; NZ: fall into vptr_none -- deferred
                                            ; error (eva_deferred convention; the
                                            ; statement aborts at check_expr_errors)
vptr_none:
                jp      ret_de0     ; repack: FPERR already set on every path
                                            ; that reaches here (an ary_op0_resolve
                                            ; error), so return the deferred 0 -- no
                                            ; ')' check (it could only raise a masking
                                            ; second error)
; ⚠️ vptr_unset SITS BELOW vptr_none's `ret` ON PURPOSE, AND THE DEAD-CODE GATE
; IS WHY. Drafted ABOVE it, this block silently stole vptr_arr's NZ
; FALL-THROUGH -- the array-element error path stopped reaching vptr_none and
; started raising through here instead, which also orphaned vptr_none. `make
; deadcode` failed the build naming it, which is the only reason the reroute was
; noticed at all: it would not have shown as a wrong ANSWER, because ev_f_defer's
; penderr_set is first-error-wins and ary_op0_resolve had already set FPERR.
; ⇒ inserting a label before an existing one is an edit to whatever FELL INTO it.
vptr_unset:
                ; D-VPTRDOM: the reference's own answer for an unset scalar.
                ; FPERR=3 maps to ERR 5 `Illegal function call` (fperr_to_err,
                ; interp.asm), deferred through the shared ev_f_defer tail so
                ; first-error-wins still holds -- `VARPTR(Q)` inside an argument
                ; list that already faulted must keep the FIRST error, exactly as
                ; every other deferring factor does.
                ;
                ; D-EVFERR (docs/spec-basic-evferr.md §7): BUT THE CLOSING ')'
                ; COMES FIRST. `A=VARPTR(B` with B UNSET was ERR 5 here where
                ; both references say ERR 2, and `A=VARPTR(B$` with it -- while
                ; `B=1:A=VARPTR(B`, the SAME missing ')' with the lookup
                ; satisfied, was already 2 through vptr_close. So it is an
                ; ORDERING divergence and nothing else: the reference resolves
                ; the SCALAR only once the form is known to be well formed.
                ; 🔴 AND THE RULE IS NARROWER THAN "SYNTAX OUTRANKS DOMAIN",
                ; WHICH IS WHAT I WAS ABOUT TO SHIP. `DIM Z(2):A=VARPTR(Z(9)`
                ; is ERR 9 on ALL THREE -- the ARRAY arm's out-of-range
                ; subscript DOES outrank the missing ')', because its subscripts
                ; are evaluated while the form is being parsed. That is exactly
                ; what vptr_none's own comment predicted ("no ')' check -- it
                ; could only raise a masking second error"), untested until now
                ; and CORRECT: leave that arm alone. The two rules coincide on
                ; every scalar row and separate only on an array one
                ; [[two-rules-that-coincide-on-every-row-you-have]].
                ; ⚠️ WRITTEN OUT, NOT `call vptr_close`, WHICH WOULD BE 5 B
                ; CHEAPER. Every factor error path ends in `ret` TO THE FACTOR'S
                ; CALLER, so a `call` here puts one frame between ev_f_err's
                ; `ret` and the address it means to land on. It does unwind --
                ; through a second pass over the tail -- and that is precisely
                ; the accident abort-chain-returns-into-caller records twice as
                ; a measured failure. 8 B is the price of not repeating it.
                call    evsp_close          ; D-EVSPCLOSE
                ld      e,3
                jp      ev_f_defer

; --- ev_f_base ------------------------------------------------------------
; BASE(n) was descoped here for most of the project's life -- it parsed its
; argument, returned 0 and set ERRMARK, because zerobas kept no per-mode VDP
; table-base map and inventing one was not allowed. Graphics slice G8 retired
; that divergence: our runtime's work-area table matches the reference byte for
; byte (docs/spec-basic-graphics-g8.md §4.1, measured on both), so the real
; implementation is a word fetch and lives with its VDP(n) sibling in
; basic/graphics.asm; `IF !G8_RESIDENT` selects the stub below instead.
    IF !G8_RESIDENT
ev_f_base:
                call    ixsp_paren_req     ; D-IXSP
                ; D-EVFERR: retargeted with the five LIVE sites even though this
                ; stub is NOT ASSEMBLED (G8_RESIDENT equ 1, sysvars.inc) -- the
                ; `IF !G8_RESIDENT` arm must stay correct for
                ; `make switch-build-check` to have anything true to flip to.
                ; ⚠️ AND THE FILED CLAIM ABOUT THESE TWO SITES WAS STALE: TODO
                ; and spec-basic-missop §14.1 said "BASE is descoped and carries
                ; its own inline ERRMARK body", but G8 retired that years of
                ; slices ago -- the shipping ev_f_base is graphics.asm:1292 and
                ; raises gfx_syntax. Right conclusion, dead reasoning.
                inc     ix
                call    ev_logic            ; evaluate + discard the index argument
                call    evsp_close          ; D-EVSPCLOSE
                inc     ix
                call    errmark_expr; BASE is descoped -> expression-error marker
                jp      ret_de0     ; ...and a 0 result (no fabricated address)
    ENDIF

; --- mul16: HL = (HL * DE) low 16 bits -------------------------------------
; Shift-add, MSB-first over 16 iterations. Clobbers A, BC, DE, HL.
mul16:
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0                ; product
                ld      a,16
mul_lp:
                add     hl,hl               ; product <<= 1
                ex      de,hl
                add     hl,hl               ; multiplier <<= 1, CF = old MSB
                ex      de,hl               ; (ex does not affect flags)
                jr      nc,mul_skip
                add     hl,bc               ; bit set -> product += multiplicand
mul_skip:
                dec     a
                jr      nz,mul_lp
                ret

; --- (removed) div_de_bc / mod_de_bc / div_zero -----------------------------
; The unsigned-16-bit `/` and MOD front-ends over udiv16, with a shared
; divide-by-zero arm that set ERRMARK and returned 0. Superseded by the float
; pack: `/` is float division and `\`/MOD reach udiv16 by their own paths, so
; all three had no callers left. ⚠️ pasmo could only see TWO of them — `div_zero`
; IS referenced, but only from the other two, so it took the ROM REGION STRUCTURE
; REVIEW's transitive sweep to find it (docs/rom-region-structure-review.md §4).
; Deleted by R1's carve (docs/spec-rom-region-rebalance-r1.md A2): 26 B of
; main PAGE 1. ⚠️ udiv16 below STAYS — it has live callers.

; --- udiv16: DE / BC -> DE = quotient, HL = remainder ----------------------
; Restoring division: shift the dividend (DE) left into the remainder (HL) one
; bit at a time, subtracting the divisor when it fits and setting the quotient
; bit in DE's vacated low end. Counter in A (untouched by the body). 16 steps.
udiv16:
                ld      hl,0                ; remainder
                ld      a,16
udiv_lp:
                sla     e
                rl      d                   ; DE <<= 1; CF = old bit15
                adc     hl,hl               ; HL = HL<<1 | CF (32-bit shift of HL:DE)
                or      a                   ; clear CF for the trial subtract
                sbc     hl,bc               ; HL -= divisor; CF set if it didn't fit
                jr      nc,udiv_fit
                add     hl,bc               ; restore remainder (divisor too big)
                jr      udiv_next           ; quotient bit stays 0
udiv_fit:
                inc     e                   ; set the quotient's low bit
udiv_next:
                dec     a
                jr      nz,udiv_lp
                ret

; \U0001f534 SITED AT THE END OF THE FILE, AND THAT IS NOT ARBITRARY. Inserting it
; beside `ev_f_empty` (its natural home) pushed `ev_f_digit` 11 B further from
; the dispatch chain and pasmo refused: "Relative jump out of range on line 594".
; The dispatch's `jr c,ev_f_digit` was already at its limit, so ANY insertion
; between the two breaks it. An 11 B helper is not worth converting a `jr` to a
; `jp` to make room for [[jrslice-slice]].
; --- evsp_close: the closing-paren check every one-argument factor makes ----
; D-EVSPCLOSE. `call ev_sp / cp ')' / jp nz,ev_f_empty` stood at EIGHT sites --
; seven here and one in str-engine.asm -- 8 B each, found by the n-gram carve
; sweep (scratchpad/pair_carve_scout.py) after it was widened past a
; two-instruction window. The pair-only version could not see a three-instruction
; run, and every row it could see said "cannot win: a 3 B call is not cheaper".
;
; 🔴 AND THE OBVIOUS FOLD IS WRONG, BECAUSE `ev_f_empty` RETURNS RATHER THAN
; UNWINDING. It is a DEFERRED error: it stamps FPERR through penderr_set, falls
; into ev_f_err for the $DD landmark, and ends `ld de,0 / ret` -- no
; raise_error, no `ld sp,(SAVSTK)`. At the old sites that `ret` returned to the
; FACTOR'S caller. Behind a `call` it would return to the SITE, which would then
; execute its own next instruction (`inc ix` at six of the eight) as if the
; expression had closed correctly [[factoring-a-run-into-a-helper]].
; 🎯 SO THE HELPER DISCARDS ITS OWN FRAME BEFORE JUMPING OUT, and the stack then
; looks exactly as it did at the old site.
; ⚠️ `inc sp` TWICE, NOT `pop hl` OR `pop af`. Both pops are 1 B cheaper and both
; change what the caller receives: the flags returned through this path are the
; `cp ')'` NZ (penderr_set preserves the caller's flags across itself on
; purpose), and DE=0 is the only value ev_f_err sets -- so a `pop af` would hand
; callers garbage flags and a `pop hl` would clobber HL. Two `inc sp` touch no
; register and no flag.
evsp_close:
                call    ev_sp
                cp      ')'
                ret     z                   ; closed: A=')' and Z set, exactly as
                                            ; the open-coded sites left them
                inc     sp                  ; discard OUR return address -- the
                inc     sp                  ; deferred error must return one frame
                                            ; further out, as it did before
                jp      ev_f_empty

; --- arga_widen: widen the live RHS into ARGA -------------------------------
; D-ARGAWIDEN. `ld hl,ARGA / call widen_rhs_operand` stood at TWELVE sites --
; arrays 2, expr 5, graphics 1, printusing 1, strvar 1, vars 2 -- 6 B each, the
; n-gram sweep's top row once D-EVSPCLOSE consumed the one above it.
;
; \U0001f7e2 A TAIL JUMP, AND THAT IS WHAT MAKES IT EXACTLY EQUIVALENT. `call
; arga_widen` pushes the return-to-site; the `jp` pushes nothing; so
; `widen_rhs_operand` sees the SAME stack it saw when the sites called it
; directly, and its own `jr widen_int_to` / `jp widen_fac_to` tails return to the
; site unchanged. No frame is added, so unlike evsp_close there is nothing to
; discard [[factoring-a-run-into-a-helper]].
; ⚠️ All twelve sites are at TOP LEVEL -- checked, because D-EVSPCLOSE's eighth
; site sat inside `IF !G8_RESIDENT` and could not pay. Here sites x saving must
; reconcile against the wall exactly.
; ⚠️ Sited at the END of the file for the same reason evsp_close is: an insertion
; anywhere earlier stretches the `jr c,ev_f_digit` span that pasmo already
; refused once.
arga_widen:
                ld      hl,ARGA
                jp      widen_rhs_operand

; --- ixsp_paren_req / tgt_parse_req / arga_dig_iszero: D-PAIRCARVE2 ----------
; 💰 (2026-09-11) Three more sequences from a scan whose sizes were MEASURED by
; assembling each candidate with pasmo, not estimated:
;   call ixsp_paren + jp nz,ev_f_empty        8 sites, 6 B each
;   call tgt_parse  + jp nz,fp_runtime_error  6 sites, 6 B each
;   ld hl,ARGA+FPNUM_DIG + call dig15_iszero  7 sites, 6 B each
; ixsp_paren_req: `(` is REQUIRED -- Z returns as the pair did; NZ discards this
; helper's own return address (`inc sp` twice, evsp_close's precedent: no
; register, no flag) and jumps to ev_f_empty, whose deferred error then returns
; ONE FRAME FURTHER OUT exactly as the open-coded `jp` did. tgt_parse_req: the
; NZ exit is fp_runtime_error, which is `jr raise_error` -- an ABORT that resets
; SP -- so no frame fix is needed. arga_dig_iszero: dig15_iszero preserves HL,
; so the caller sees HL = ARGA+FPNUM_DIG and Z as before -- and it lives in the
; LOW region (basic/str-engine.asm): float-arith's callers are in the resident
; closure that sub page-1 tenants reach, and check_tenant_closure said so.
; (ixsp_paren_req moved to the LOW region, basic/str-engine.asm, by D-INPQUOTE:
; page 1 was 7 B short and the low region had 9 spare -- one budget, D-DEMOTE.)
tgt_parse_req:
                call    tgt_parse
                ret     z
                jp      fp_runtime_error
; --- ixsp_paren: ixsp, then "is it `(`?" -- Z iff '(' is next ----------------
; 💰 D-PAIRCARVE (2026-09-11): NINE live sites went straight from `call ixsp` to
; `cp '('` (ixsp's own header counted them); 5 B each against 3 for a call:
; 9 x 2 saved less this 6-byte body = 12 B. A and the flags are exactly what the
; open-coded pair left.
ixsp_paren:
                call    ixsp
                cp      '('
                ret

; --- set_factyp2 / factyp_is2: the two FACTYP idioms as calls ------------------
; 💰 D-PAIRCARVE (2026-09-11): `ld a,2` + `ld (FACTYP),a` stood at EIGHT sites and
; `ld a,(FACTYP)` + `cp 2` at EIGHT more, 5 B each against 3 for a call:
; 16 x 2 saved less two 5/6-byte bodies = 21 B. set_factyp2 returns with A = 2,
; as the pair did; factyp_is2 returns A = FACTYP and Z iff it is 2.
set_factyp2:
                ld      a,2
                ld      (FACTYP),a
                ret
factyp_is2:
                ld      a,(FACTYP)
                cp      2
                ret

; --- ixsp: step the evaluator cursor, then skip blanks ----------------------
; D-IXSP. `inc ix / call ev_sp` stood at SIXTEEN sites -- ten in expr.asm, six in
; str-engine.asm -- 5 B each. It was ranked ELEVENTH until D-IXSIZE corrected the
; sizer: `inc ix` is DD 23, two bytes, and the sweep had been pricing it as one.
;
; \U0001f7e2 FRAME-NEUTRAL AND FLAG-TRANSPARENT. `ret` after `call ev_sp` disturbs
; neither A nor the flags, so every site sees exactly what it saw open-coded --
; nine of them go straight on to `cp '('`, and the rest to `call relop_bit`,
; `push ix`, `call is_letter` or `call str_eval_ix`. Nothing here jumps outward,
; so unlike evsp_close there is no frame to discard.
; ⚠️ SIXTEEN SITES, FIFTEEN LIVE: expr.asm's is inside `IF !G8_RESIDENT`, which is
; OFF in the shipping build, so it costs nothing and saves nothing. Checked
; BEFORE building this time -- it is what made D-EVSPCLOSE's prediction miss.
ixsp:
                inc     ix
                jp      ev_sp

; --- mul16sat: HL = HL * DE, SATURATED to $FFFF on 16-bit overflow ----------
; D-GETEOF2. `mul16` returns the low 16 bits, which is fine for every caller
; that knows its operands fit -- and wrong for a BOUND TEST, where a wrapped
; product reads as a SMALL offset and accepts a record that is nowhere near the
; file. Record 300 at reclen 256 is 76800; low word 11264, which is "inside" any
; file bigger than 11 KB.
; \U0001f3af SATURATION IS THE RIGHT ANSWER RATHER THAN A WIDER PRODUCT, because the
; only question asked of it is `offset >= size` and `size` is 16-bit: anything
; that overflows is past EOF by definition, so $FFFF answers correctly without a
; 32-bit compare. Clobbers A, BC, DE, HL, exactly as mul16 does.
mul16sat:
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0
                ld      a,16
ms_lp:
                add     hl,hl               ; product <<= 1
                jr      c,ms_sat            ; ...carried out of 16 bits
                ex      de,hl
                add     hl,hl               ; multiplier <<= 1, CF = old MSB
                ex      de,hl               ; (ex does not affect flags)
                jr      nc,ms_skip
                add     hl,bc               ; bit set -> product += multiplicand
                jr      c,ms_sat            ; ...and that carried too
ms_skip:
                dec     a
                jr      nz,ms_lp
                ret
ms_sat:
                ld      hl,$FFFF            ; past any 16-bit file size
                ret
