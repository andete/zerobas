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

; --- eval: HL = cursor in -> DE = value, HL advanced past the expression -----
; Preserves the caller's IX. Clobbers A, BC, DE, HL.
eval:
                push    ix
                push    hl
                pop     ix                  ; IX = cursor
    IF ROM_BASE < $4000
                ld      a,2
                ld      (FACTYP),a          ; §9.4: eval() sets FACTYP=2 (int) on entry
    ENDIF
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
; TWO IMPLEMENTATIONS, gated. The lean 16 KB cart keeps the original hand-rolled
; chain below (basic.rom is byte-frozen, and it ships without EQV/IMP); the
; repack build uses the table-driven layer, which fits SIX levels into less space
; than the old THREE.
    IF ROM_BASE < $4000
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
                jp      z,ev_not            ; past the tightest layer -> NOT / relational
                push    hl
                call    ev_lg_next          ; DE = lhs, from the tighter level
                pop     hl
ev_lg_lp:
                call    ev_sp
                ld      a,(ix+0)
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
    ELSE
; --- the original hand-rolled chain (LEAN 16 KB build, byte-frozen) ---------
ev_logic:
ev_xor:
                call    ev_or               ; DE = lhs
ev_xor_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      XOR_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                ; spec §10.3 "strict int16 domain": convert the operand NOW
                ; (fac_to_int_strict re-derives it from FAC/FACTYP if it was
                ; float, ignoring the already-address-domain-rounded DE), then
                ; reset FACTYP=2 so it doesn't leak stale into the rhs eval —
                ; no FAC save is needed here (unlike ev_e/ev_t's double-
                ; widening sites) because the conversion to a plain int
                ; happens immediately, before the rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_or               ; DE = rhs
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl                  ; HL = lhs
                ld      a,l
                xor     e
                ld      l,a
                ld      a,h
                xor     d
                ld      h,a
                ex      de,hl               ; DE = lhs XOR rhs
                jr      ev_xor_lp
ev_or:
                call    ev_and
ev_or_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      OR_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_and
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl
                ld      a,l
                or      e
                ld      l,a
                ld      a,h
                or      d
                ld      h,a
                ex      de,hl               ; DE = lhs OR rhs
                jr      ev_or_lp
ev_and:
                call    ev_not
ev_and_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      AND_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de
                call    ev_not
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                pop     hl
                ld      a,l
                and     e
                ld      l,a
                ld      a,h
                and     d
                ld      h,a
                ex      de,hl               ; DE = lhs AND rhs
                jr      ev_and_lp
    ENDIF
ev_not:
                call    ev_sp
                ld      a,(ix+0)
                cp      NOT_TOKEN
                jr      z,ev_not_do
                jp      ev_rel              ; no NOT -> drop to the relational layer
ev_not_do:
                inc     ix
                call    ev_not              ; unary, right-assoc (NOT NOT x)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
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
    IF ROM_BASE < $4000
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
                push    ix
                pop     hl                  ; HL = cursor (bridge for the probe)
                call    str_eval            ; CF set -> LHS is a string; STRPTR->desc
                jr      c,evr_lhs_str       ; string LHS -> discard guard, str path
                pop     ix                  ; NC: restore the cursor str_eval trashed
    ENDIF
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
                ld      a,(ix+0)
                call    relop_bit
                ret     nc                  ; no relational operator -> plain value
                ld      c,b                 ; C = requested relation bits
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                call    relop_bit           ; a second relop? (<=, >=, <>)
                jr      nc,evr_rhs
                ld      a,c
                or      b
                ld      c,a                 ; merge the two relation bits
                inc     ix
evr_rhs:
    IF ROM_BASE < $4000
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
                push    ix
                pop     hl
                call    str_eval
                pop     ix                  ; restore the cursor str_eval may have trashed
                pop     de
                pop     bc
                jp      c,evr_mismatch      ; RHS is a string, LHS was numeric -> D-2
    ENDIF
                push    de                  ; lhs
    IF ROM_BASE < $4000
                ; spec §10.1: relationals over any float operand compare AS
                ; floats after widening (never int-converted, `40000=40000!`
                ; -> -1, no Overflow). Save the LHS's FACTYP+FAC on the
                ; machine stack (same fixed-size frame protocol as the ev_e/
                ; ev_t double-arithmetic sites) before the rhs eval clobbers
                ; FAC, then reset FACTYP=2 for the rhs eval.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                push    bc                  ; relation bits (in C)
                call    ev_e                ; DE = rhs
                pop     bc                  ; C = bits
    IF ROM_BASE < $4000
                call    combine_cmp         ; pops the lhs frame + value; A =
                                            ; relation bit (1/2/4); FACTYP:=2
    ELSE
                pop     hl                  ; HL = lhs
                call    cmp16_bits          ; A = actual relation bit (1/2/4)
    ENDIF
    IF ROM_BASE < $4000
                ld      de,0                ; false = 0
                and     c                   ; intersect requested with actual
                jr      z,evr_chain
                dec     de                  ; true = -1 ($FFFF)
evr_chain:
                jp      evr_scan            ; and look for the NEXT relop (left-assoc)
    ELSE
                ; LEAN 16 KB build: byte-frozen, one comparison only (no chaining).
                and     c                   ; intersect requested with actual
                jr      z,evr_false
                ld      de,$FFFF            ; true = -1
                ret
evr_false:
                ld      de,0                ; false = 0
                ret
    ENDIF
    IF ROM_BASE < $4000
evr_lhs_str:
                pop     af                  ; BUG C: drop the LHS-probe IX guard
                                            ; (ev_rel_str re-derives IX from HL)
                jp      ev_rel_str
evr_mismatch:
                jp      type_mismatch_set   ; sets ERRMARK+TMISMATCH, DE=0, ret (str-engine.asm)
    ENDIF

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
; HOME depends on the build (subrom-mathpack migration, 2026-07-13):
;   * lean 16 KB cart (ROM_BASE >= $4000): defined HERE (page 1), byte-identical
;     to the pre-migration expr.asm.
;   * repack build (ROM_BASE < $4000): defined in the page-0 low region
;     (basic/float-arith.asm) instead, so the fp_sqrt PAGE-1 sub-ROM tenant's
;     page-0-resident float core can still reach it while main-ROM page 1 is
;     switched out (see float-arith.asm's cmp16_bits header). All callers here
;     (ev_rel etc.) resolve to that page-0 copy by label, unchanged.
    IF ROM_BASE >= $4000
cmp16_bits:
                ld      a,h
                cp      d
                jr      nz,c16_ne
                ld      a,l
                cp      e
                jr      nz,c16_ne
                ld      a,2                 ; equal
                ret
c16_ne:
                or      a
                sbc     hl,de               ; lhs - rhs; signed: less iff S xor V
                jp      pe,c16_vset
                jp      m,c16_lt            ; V clear -> less iff S set
                jr      c16_gt
c16_vset:
                jp      p,c16_lt            ; V set  -> less iff S clear
                jr      c16_gt
c16_lt:
                ld      a,1
                ret
c16_gt:
                ld      a,4
                ret
    ENDIF

; --- ev_sp: skip spaces in the IX stream -----------------------------------
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
                ld      a,(ix+0)
                cp      PLUS_TOKEN
                jr      z,ev_e_add
                cp      MINUS_TOKEN
                jr      z,ev_e_sub
                ret
ev_e_add:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                ; spec §1 bullet 4: save the lhs's FACTYP+FAC on the machine
                ; stack (fixed-size frame) before the rhs eval clobbers FAC,
                ; reset FACTYP=2 for the rhs eval. combine_add decides int-
                ; fast-path (with signed-overflow-promotion) vs BCD add.
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                call    ev_mod              ; DE = rhs
    IF ROM_BASE < $4000
                call    combine_add         ; pops the frame; DE = result
    ELSE
                pop     hl                  ; HL = lhs
                add     hl,de
                ex      de,hl               ; DE = sum
    ENDIF
                jr      ev_e_lp
ev_e_sub:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
    ENDIF
                call    ev_mod              ; DE = rhs
    IF ROM_BASE < $4000
                call    combine_sub
    ELSE
                pop     hl                  ; HL = lhs
                or      a                   ; clear carry
                sbc     hl,de               ; HL = lhs - rhs
                ex      de,hl
    ENDIF
                jr      ev_e_lp

; --- ev_mod: { MOD } over '\'-expressions (MSX precedence level 5) ----------
ev_mod:
                call    ev_idiv             ; DE = lhs
ev_mod_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      MOD_TOKEN
                ret     nz
    IF ROM_BASE < $4000
                ; spec §10.3: \ / MOD operands convert via the STRICT int16
                ; domain (not the address domain) -- immediately, no FAC save
                ; needed since the plain int value is captured before the
                ; rhs eval can clobber FAC.
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_idiv             ; DE = rhs (divisor)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
    IF ROM_BASE < $4000
                call    signed_mod_de_bc    ; D-C: MSX-signed MOD (spec §10.4)
    ELSE
                call    mod_de_bc           ; DE = remainder
    ENDIF
                jr      ev_mod_lp

; --- ev_idiv: { '\' } over terms (integer division, level 4) ---------------
ev_idiv:
                call    ev_t                ; DE = lhs
ev_idiv_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      IDIV_TOKEN          ; '\'
                ret     nz
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                inc     ix
                push    de                  ; lhs (dividend)
                call    ev_t                ; DE = rhs (divisor)
    IF ROM_BASE < $4000
                call    fac_to_int_strict_reset
    ENDIF
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
    IF ROM_BASE < $4000
                call    signed_div_de_bc    ; D-C: MSX-signed \ (spec §10.4)
    ELSE
                call    div_de_bc           ; DE = quotient
    ENDIF
                jr      ev_idiv_lp

; --- ev_t: term := factor { ('*' | '/') factor } ---------------------------
; '/' is real division on MSX; the repack build makes it always float (spec
; §10.1); the lean build keeps the integer-quotient divergence (unchanged).
ev_t:
    IF ROM_BASE < $4000
                call    ev_pw               ; `^` binds above * / (§13.3)
    ELSE
                call    ev_f                ; DE = factor
    ENDIF
ev_t_lp:
                call    ev_sp
                ld      a,(ix+0)
                cp      STAR_TOKEN          ; '*'
                jr      z,ev_t_mul
                cp      DIV_TOKEN           ; '/'
                jr      z,ev_t_div
                ret
ev_t_mul:
                inc     ix
                push    de                  ; lhs
    IF ROM_BASE < $4000
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_pw               ; DE = rhs
                call    combine_mul
    ELSE
                call    ev_f                ; DE = rhs
                pop     hl                  ; HL = lhs
                call    mul16               ; HL = lhs * rhs (low 16 bits)
                ex      de,hl               ; DE = product
    ENDIF
                jr      ev_t_lp
ev_t_div:
                inc     ix
    IF ROM_BASE < $4000
                push    de                  ; lhs
                call    push_lhs_frame
                call    set_factyp_int_ret  ; FACTYP:=2 for the rhs eval
                call    ev_pw               ; DE = rhs
                call    combine_div_float   ; ALWAYS float (spec §10.1)
    ELSE
                push    de                  ; lhs (dividend)
                call    ev_f                ; DE = rhs (divisor)
                ld      b,d
                ld      c,e                 ; BC = divisor
                pop     de                  ; DE = dividend
                call    div_de_bc           ; DE = quotient
    ENDIF
                jr      ev_t_lp

    IF ROM_BASE < $4000
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
                ld      a,(ix+0)
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
    ENDIF

; --- ev_f: factor ----------------------------------------------------------
; Decodes the crunched tokens (spec §3): constant tokens carry their binary
; value; '(' / ')' stay verbatim; PEEK is $FF $97; a bare upcased letter is a
; variable; unary minus is MINUS_TOKEN.
ev_f:
                call    ev_sp
                ld      a,(ix+0)
    IF ROM_BASE < $4000
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
    ENDIF
                cp      MINUS_TOKEN         ; unary minus
                jp      z,ev_f_neg
                cp      '('
                jp      z,ev_f_paren
                cp      PEEK_PREFIX         ; $FF -> PEEK / VPEEK / INP function token
                jp      z,ev_f_ff
                cp      USR_TOKEN           ; $DD -> USR[n](arg) function
                jp      z,ev_usr
                cp      VARPTR_TOKEN        ; $E7 -> VARPTR(var) function
                jp      z,ev_f_varptr
                cp      BASE_TOKEN          ; $C9 -> BASE(n) function
                jp      z,ev_f_base
    IF ROM_BASE < $4000
                cp      INSTR_TOKEN         ; $E5 -> INSTR([p,]a$,b$) (string-functions
                jp      z,ev_f_instr        ; Group C; single-byte token, not $FF-prefixed)
                ; error-handling S2a (docs/spec-basic-error-handling-s2a-packet.md
                ; §3/(f)): ERR/ERL, single-byte value tokens, same shape as
                ; VARPTR/BASE/INSTR above.
                cp      ERR_TOKEN           ; $E2 -> ERR (last error's MSX ERR code)
                jp      z,ev_f_errfn
                cp      ERL_TOKEN           ; $E1 -> ERL (last error's line, 65535=direct)
                jp      z,ev_f_erlfn
                cp      TIME_TOKEN          ; $CB -> TIME (JIFFY as an UNSIGNED word)
                jp      z,ev_f_time
                cp      POINT_TOKEN         ; $ED -> POINT(x,y) (graphics G2, graphics.asm)
                jp      z,ev_f_point
    IF G8_RESIDENT
                cp      VDP_TOKEN           ; $C8 -> VDP(n) (graphics G8, graphics.asm)
                jp      z,ev_f_vdp
    ENDIF
    ENDIF
                cp      HEX_TOKEN           ; $0C -> 2-byte LE value (&H)
                jp      z,ev_f_word
                cp      OCT_TOKEN           ; $0B -> 2-byte LE value (&O)
                jp      z,ev_f_word
                cp      INT2_TOKEN          ; $1C -> 2-byte LE value
                jp      z,ev_f_word
                cp      INT1_TOKEN          ; $0F -> 1-byte value
                jp      z,ev_f_byte
    IF ROM_BASE < $4000
                cp      SNG_TOKEN           ; $1D -> single float literal (basic/float.asm)
                jp      z,ev_f_float
                cp      DBL_TOKEN           ; $1F -> double float literal
                jp      z,ev_f_float
    ENDIF
                cp      INT_DIGIT_BASE      ; $11
                jr      c,ev_f_var
                cp      $1A+1               ; $11..$1A -> digit token
                jp      c,ev_f_digit
                ; fall through: letter -> variable (or error)
ev_f_var:
                ld      a,(ix+0)
                call    is_letter           ; must start with a letter
                jr      nc,ev_f_err
                push    ix
                pop     hl                  ; HL = cursor
                call    var_name_key        ; BC = key, HL past the (multi-char) name
    IF ROM_BASE < $4000
                ld      a,(hl)
                cp      '('
                jp      z,ev_f_arr          ; array-element rvalue (arrays slice-1,
                                            ; docs/spec-basic-arrays.md §9.4/§10: ev_f
                                            ; reaches ev_f_var only for a plain letter,
                                            ; never a function token, so a '(' right
                                            ; after a plain name is unambiguously a
                                            ; subscript, not a function call)
    ENDIF
                push    hl
                pop     ix                  ; IX = advanced cursor
    IF ROM_BASE < $4000
                ld      a,(VARTYPE)         ; F3: resolved type from var_name_key
                jp      var_load_fac        ; FAC/FACTYP=type, DE=int16 (tail call)
    ELSE
                call    var_get_key         ; BC = key -> DE = value
                ret
    ENDIF
    IF ROM_BASE < $4000
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
ev_f_empty:                                 ; D-F2-3: the empty parenthesised/argument
                                            ; expression -> deferred FPERR=4 "syntax error",
                                            ; checked at the statement boundary (the D-F2-1
                                            ; pattern: no mid-expression unwind). The value
                                            ; (DE=0) survives every downstream success op
                                            ; unchanged, but the flag makes the driver abort.
                ld      e,4
ev_f_defer:                                 ; shared tail: E = FPERR code to defer.
                ld      a,(FPERR)           ; D-F2-4 first-error-wins: if the argument
                or      a                   ; expression ALREADY raised a hard error
                jr      nz,ev_f_err         ; (div0/overflow/illegal), keep THAT -- the
                                            ; reference reports the first error, not the
                                            ; later reject (e.g. SIN(1/0,2) -> Division by
                                            ; zero, NOT syntax error). Only a still-clean
                                            ; FPERR takes E's deferred code.
                ld      a,e
                ld      (FPERR),a
                ; fall into ev_f_err for the $DD landmark.
    ENDIF
ev_f_err:
                ld      a,$DD               ; expression error marker
                ld      (ERRMARK),a
                ld      de,0
                ret

    IF ROM_BASE < $4000
; --- ev_f_errfn / ev_f_erlfn: ERR / ERL -> DE (error-handling S2a, docs/ ---
; spec-basic-error-handling-s2a-packet.md §3/(f)). Single-byte value tokens,
; no operand bytes -- same "read a RAM cell, widen to DE, step one token"
; shape as ev_f_digit/byte/word above, so the outer eval()'s FACTYP=2 (int)
; setting on entry already gives these the right numeric domain; no extra
; widening code is needed here.
ev_f_errfn:                                 ; ERR -> ERRCODE (1 B) widened to DE
                ld      a,(ERRCODE)
                ld      e,a
                ld      d,0
                inc     ix
                ret
ev_f_erlfn:                                 ; ERL -> ERRLINE (word), widened to FAC
                                            ; (NOT the plain-DE int16 path ev_f_digit/
                                            ; byte/word use): ERRLINE holds an UNSIGNED
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
                ld      hl,(ERRLINE)
                jr      ev_f_uword
; ev_f_time -- TIME (docs/spec-basic-time.md §3.2). The SAME unsigned-word-to-FAC
; problem ERL already solves, over JIFFY instead of ERRLINE, so it shares the tail
; below: 7 B here against 19 duplicated, with no restructuring on ERL's side
; (cf. [[generalisation-not-free-at-two-callers]] -- the case for sharing has to be
; this trivial to be free).
;
; `ld hl,(JIFFY)` is TWO byte reads and the timer ISR ticks between them, so an
; unguarded read can be torn ($00FF seen as $01FF). Guarded (D-TIME-2).
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
    ENDIF

; constant decoders --------------------------------------------------------
ev_f_digit:                                 ; $11..$1A -> value 0..9
                ld      a,(ix+0)
                sub     INT_DIGIT_BASE
                ld      e,a
                ld      d,0
                inc     ix
                ret
ev_f_byte:                                  ; $0F,<byte>
                inc     ix
                ld      a,(ix+0)
                ld      e,a
                ld      d,0
                inc     ix
                ret
ev_f_word:                                  ; $0C/$1C,<word LE>
                inc     ix
                ld      a,(ix+0)
                ld      e,a                 ; value low
                inc     ix
                ld      a,(ix+0)
                ld      d,a                 ; value high
                inc     ix
                ret

    IF ROM_BASE < $4000
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
    ENDIF

ev_f_neg:
                inc     ix
    IF ROM_BASE < $4000
                call    ev_pw               ; DE = operand (`^` binds tighter
                                            ; than unary minus, §13.1/13.3 --
                                            ; this is what makes -2^2=-4 AND
                                            ; 2^-3^2=2^-(3^2) fall out for free)
    ELSE
                call    ev_f                ; DE = operand
    ENDIF
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = 0 - operand
                ex      de,hl
    IF ROM_BASE < $4000
                ld      a,(FACTYP)
                cp      2
                jr      z,evfn_ret
                call    flt_neg
evfn_ret:
    ENDIF
                ret

ev_f_paren:
                inc     ix                  ; '('
                call    ev_logic            ; DE = inner value (full expression)
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret

; --- ev_f_ff: a $FF-prefixed function token (PEEK / VPEEK / INP) -----------
; All three take a single parenthesised expression; they differ only in how the
; argument is used. We parse "( <expr> )" once, then read from RAM (PEEK), VRAM
; (VPEEK) or a Z80 port (INP). The second token byte selects the read.
ev_f_ff:
                inc     ix                  ; skip the $FF prefix
                ld      a,(ix+0)            ; the function selector byte
    IF ROM_BASE < $4000
                ; REPACK ONLY. Every $FF function here except CVI takes one
                ; parenthesised NUMERIC argument, so membership is a set test, not a
                ; decision tree: scan the selector table with cpir (input-devices
                ; slice I1 golf). The old per-token `cp`/`jr z` chain -- which the
                ; lean build below still uses byte-for-byte -- costs 4 B per
                ; function; a table row costs 1, and that difference is what funds
                ; STICK/STRIG joining the group. cpir preserves A, and neither HL
                ; nor BC is live here (ev_ff_arg's first act is `ld c,a`).
                cp      CVI_TOKEN           ; $A8 -> CVI (STRING arg: not in the set)
                jp      z,ev_ff_cvi
                ld      hl,ev_ff_argtab
                ld      bc,ev_ff_argtab_len
                cpir
                jr      z,ev_ff_arg
                jp      ev_ff_mathconv      ; ABS/SGN/INT/FIX/CINT/CSNG/CDBL, else
                                            ; LEN/ASC/VAL (string->number), else ev_f_err
    ELSE
                ; LEAN 16 KB build: the original chain, unchanged. basic.rom is
                ; byte-frozen, so the golf above must not reach it.
                cp      PEEK_TOKEN          ; $97 -> PEEK
                jr      z,ev_ff_arg
                cp      VPEEK_TOKEN         ; $98 -> VPEEK
                jr      z,ev_ff_arg
                cp      INP_TOKEN           ; $90 -> INP
                jr      z,ev_ff_arg
                cp      EOF_TOKEN           ; $AB -> EOF
                jr      z,ev_ff_arg
                cp      LOF_TOKEN           ; $AD -> LOF
                jr      z,ev_ff_arg
                cp      DSKF_TOKEN          ; $A6 -> DSKF
                jr      z,ev_ff_arg
                cp      CVI_TOKEN           ; $A8 -> CVI (takes a STRING arg)
                jp      z,ev_ff_cvi
                jp      ev_f_err            ; unknown $FF function
    ENDIF
; The single-numeric-argument $FF selectors, for the cpir set test above. Order is
; free. Repack-only, like the scan that reads it.
    IF ROM_BASE < $4000
ev_ff_argtab:
                db      PEEK_TOKEN          ; $97
                db      VPEEK_TOKEN         ; $98
                db      INP_TOKEN           ; $90
                db      EOF_TOKEN           ; $AB
                db      LOF_TOKEN           ; $AD
                db      DSKF_TOKEN          ; $A6
    IF I1_RESIDENT
                db      STICK_TOKEN         ; $A2  (input devices, slice I1)
                db      STRIG_TOKEN         ; $A3
    ENDIF
    IF I2_RESIDENT
                db      PDL_TOKEN           ; $A4  (input devices, slice I2)
                db      PAD_TOKEN           ; $A5
    ENDIF
ev_ff_argtab_len equ    $ - ev_ff_argtab
    ENDIF
ev_ff_arg:
                ld      c,a                 ; C = selector (survives the parse)
                inc     ix                  ; skip the selector byte
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
    IF ROM_BASE < $4000
                ; Residual found by the I1 differential (spec §3): a MISSING
                ; argument list -- `PRINT PEEK`, `PRINT STICK`, `PEEK 100` --
                ; silently evaluated to 0 here, where the reference raises a
                ; Syntax error (ERR 2, measured on the VG-8020 for PEEK / VPEEK /
                ; INP / EOF / LOF alike). Same BUG C class, and same cure, as the
                ; CVI missing-'(' fix below: defer the syntax error via ev_f_empty
                ; so the statement's check_expr_errors aborts. Repack-only -- the
                ; lean 16 KB basic.rom is byte-frozen and keeps the old ev_f_err.
                jp      nz,ev_f_empty
    ELSE
                jp      nz,ev_f_err
    ENDIF
                inc     ix
                push    bc                  ; guard the selector across the eval
                call    ev_logic            ; DE = argument (full expression)
                pop     bc
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
    IF ROM_BASE < $4000
                jp      nz,ev_f_empty       ; unclosed / extra arg -> ERR 2 (as above)
    ELSE
                jp      nz,ev_f_err
    ENDIF
                inc     ix
    IF ROM_BASE < $4000
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
                ; DEFERRED type mismatch pending (error-handling arc: TMISMATCH set,
                ; surfaced at the statement boundary). The reference reports THAT
                ; (ERR 13), so don't let PDL's ERR-5 domain check preempt it --
                ; STICK/STRIG/PAD need no such guard because 0 is legal for them, so
                ; their deferred TMISMATCH already surfaces on its own.
                ld      a,(TMISMATCH)
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
    ENDIF                                   ;  arg was a float (clobbers A only; C kept)
                ld      a,c                 ; dispatch on the selector
                cp      VPEEK_TOKEN
                jr      z,ev_ff_vpeek
                cp      INP_TOKEN
                jr      z,ev_ff_inp
                cp      EOF_TOKEN
                jr      z,ev_ff_eof
                cp      LOF_TOKEN
                jr      z,ev_ff_lof
                cp      DSKF_TOKEN
    IF ROM_BASE < $4000
                ; Landmine (spec §9.5, recurred from I1): the I2 dispatch rows just
                ; below push ev_ff_dskf out of jr range in the repack build, so it
                ; takes a jp here. The lean 16 KB basic.rom has no I1/I2 rows and is
                ; byte-frozen, so it keeps the original jr.
                jp      z,ev_ff_dskf
    ELSE
                jr      z,ev_ff_dskf
    ENDIF
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
ev_ff_vpeek:                                ; VPEEK: read one byte of VRAM (DE = addr)
                ex      de,hl               ; HL = VRAM address (RDVRM wants it here)
                call    RDVRM               ; A = VRAM[HL]; makes no register guarantees
                ld      e,a
                ld      d,0                 ; VPEEK yields 0..255
                ret
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
                ld      e,a
                ld      d,0                 ; direction is 0..8, never negative
                ret
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
                ld      e,a
                ld      d,0                 ; INP yields 0..255
                ret
ev_ff_eof:                                  ; EOF(n): -1 at end of the input file n
                ; Select channel n (DE = arg) so FREAD_LEFT belongs to it, then test
                ; whether every file byte has been delivered (4-byte LE == 0). fch_select
                ; uses LDIR only (no CALSLT), so IX — the evaluator's token cursor —
                ; survives; it does clobber HL/BC/A (the factor caller tolerates that,
                ; like PEEK). A bad channel number is a function error.
                ld      a,e
                call    fch_valid
                jp      nc,ev_f_err
                call    ev_chan_hasfile     ; device/cassette channels have no length
                jp      nc,ev_f_err         ; -> function error (never fch_select them)
                ld      a,e
                call    fch_select
                ld      hl,FREAD_LEFT
                ld      a,(hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                ld      de,0
                ret     nz                  ; bytes remain -> not EOF -> 0
                dec     de                  ; all delivered -> EOF -> -1 ($FFFF)
                ret
ev_ff_lof:                                  ; LOF(n): length of open input file n
                ; Select channel n so FAT_FILESIZE (set by fat_find at OPEN, part of
                ; the per-channel state span) belongs to it; return its low 16 bits.
                ld      a,e
                call    fch_valid
                jp      nc,ev_f_err
                call    ev_chan_hasfile     ; device/cassette channels have no length
                jp      nc,ev_f_err         ; -> function error (never fch_select them)
                ld      a,e
                call    fch_select
                ld      de,(FAT_FILESIZE)
                ret

; ev_chan_hasfile — CF set if channel E is a disk file channel (FCH_MODES[E] <
; LPT_MODE), CF clear if it is a length-less device channel (LPT/CRT/CAS, mode >=
; LPT_MODE). Lets EOF()/LOF() reject device+cassette channels (which own no fat.asm
; ctx and would corrupt the engine globals if fch_select'd) as a function error.
; Preserves E + IX (no CALSLT); clobbers A/HL. FCH_MODES[0] is unused/0, so a 0
; channel (already rejected by fch_valid) would read as a file channel — harmless.
ev_chan_hasfile:
                ld      a,e
                add     a,FCH_MODES & $FF   ; HL = FCH_MODES + E (page-local; array is
                ld      l,a                 ; well within one page of its base)
                ld      a,FCH_MODES >> 8
                adc     a,0
                ld      h,a
                ld      a,(hl)              ; A = FCH_MODES[E]
                cp      LPT_MODE
                ret                         ; CF set (A<LPT_MODE) = disk file channel
ev_ff_dskf:                                 ; DSKF(d): free clusters on the drive
                ; The drive arg (DE) is ignored (single drive). Returns the count
                ; of free FAT entries — = free KB on a 1 KB/cluster 720 KB volume.
                ; CALSLT (inside fat_count_free) clobbers IX/IY, and IX is the
                ; evaluator's live token cursor — guard it on the stack.
                push    ix
                push    iy
                call    fat_count_free      ; DE = free cluster count
                pop     iy
                pop     ix
                ret
ev_ff_cvi:                                  ; CVI(s$): integer from s$'s first 2 bytes
                ; CVI takes a STRING argument, so it cannot use ev_ff_arg's numeric
                ; ev_xor. Parse "( <string> )" by bridging the IX token cursor to the
                ; HL-based str_eval and back, then read 2 little-endian bytes from the
                ; resulting descriptor. (IX is reloaded from str_eval's advanced HL, so
                ; an inner eval clobbering IX is harmless.) Entered with IX on the
                ; CVI selector byte.
                inc     ix                  ; skip the CVI selector
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
    IF ROM_BASE < $4000
                jp      nz,ev_f_empty       ; BUG C class (Fable 2026-07-17): CVI missing
                                            ; '(' -> deferred syntax error (was silent
                                            ; ev_f_err -> " 0"); ref = Syntax error
    ELSE
                jp      nz,ev_f_err
    ENDIF
                inc     ix
                call    ev_sp
                push    ix
                pop     hl
                call    str_eval            ; STRPTR -> [len][bytes]; HL advanced; CF=ok
    IF ROM_BASE < $4000
                ; BUG C class (Fable 2026-07-17): repack str_eval CALSLTs and can
                ; exit NC with garbage IX on a nested malformed string fn
                ; (CVI(LEFT$("AB")) -> silent 0) or a non-string arg -- defer FPERR=4
                ; via ev_f_empty so check_expr_errors aborts. Lean str_eval is local
                ; (IX-safe), so it keeps the plain ev_f_err (ev_f_empty is repack-only).
                jp      nc,ev_f_empty
    ELSE
                jp      nc,ev_f_err         ; not a string operand
    ENDIF
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
    IF ROM_BASE < $4000
                jp      nz,ev_f_empty       ; BUG C class: missing ')' -> deferred syntax err
    ELSE
                jp      nz,ev_f_err
    ENDIF
                inc     ix
    IF ROM_BASE < $4000
                call    flt_int_result      ; CVI returns an int; a float nested in
                                            ;  the string arg must not stick (A only)
                ld      hl,(STRPTR)
                call    pu_deref_body       ; arrays slice-4a: HL(desc)->HL(body);
                                            ; shared with printusing.asm/field.asm
                ld      a,(hl)              ; low byte
                inc     hl
                ld      e,a
                ld      a,(hl)              ; high byte
                ld      d,a                 ; DE = int (LE)
                ret
    ELSE
                ld      hl,(STRPTR)
                inc     hl                  ; -> the value bytes
                ld      e,(hl)              ; low byte
                inc     hl
                ld      d,(hl)              ; high byte  -> DE = int (LE)
                ret
    ENDIF

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
                ld      e,a
                ld      d,0                 ; 0..255, never negative
                ret
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

    IF ROM_BASE < $4000
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
                cp      ATN_TOKEN
                jp      z,evmc_atn
                cp      EXP_TOKEN
                jp      z,evmc_exp
                cp      LOG_TOKEN
                jp      z,evmc_log
                cp      SIN_TOKEN
                jp      z,evmc_sin
                cp      COS_TOKEN
                jp      z,evmc_cos
                cp      TAN_TOKEN
                jp      z,evmc_tan
                cp      RND_TOKEN
                jp      z,evmc_rnd
                jp      ev_ff_strnum        ; not ours -> LEN/ASC/VAL, else ev_f_err

; --- ev_mc_arg: parse "( <numeric expr> )" from IX (positioned on the -------
; selector byte, per this group's entry contract). Leaves DE = the argument's
; int16 fast value and FAC/FACTYP set to its real type by ev_xor's own float
; plumbing (expr.asm/float-arith.asm) — UNLIKE ev_ff_arg, this does NOT force
; FACTYP:=2 afterward: every evmc_* below must see the argument's true type
; to decide its own result type (spec §9.1's "same FACTYP as x" / int-result
; columns). IX advanced past ')'. Clobbers as ev_xor.
ev_mc_arg:
                inc     ix                  ; skip the selector byte
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_empty       ; D-F2-4: missing '(' (bare fn / operator- or
                                            ; space-separated) -> deferred FPERR=4 "syntax
                                            ; error", NOT the silent ev_f_err. Same chokepoint
                                            ; the empty-parens gate (D-F2-3) uses.
                inc     ix
                call    ev_logic            ; DE = argument; FAC/FACTYP = its type
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_empty       ; D-F2-4: missing ')' (extra arg `f(x,y)` /
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
; RND, no fp_rnd (which would mutate the persistent seed). The D-2 TMISMATCH flag
; (e.g. `RND("A")`) is checked the same way -- it too means the reference aborted.
; exec_stmt clears BOTH flags per statement, so a clean arg leaves them 0 here and
; the body runs unchanged. Returns Z iff FPERR==0 AND TMISMATCH==0. Clobbers only A
; (every evmc_* reloads it); DE/FAC/FACTYP are ev_mc_arg's.
ev_mc_arg_checked:
                call    ev_mc_arg
                ld      a,(FPERR)
                or      a
                ret     nz                  ; a deferred numeric error is pending
                ld      a,(TMISMATCH)       ; ...and the OTHER deferred flag (D-2 type
                or      a                   ; mismatch, e.g. RND("A")) equally means the
                ret                         ; reference already aborted -> Z iff BOTH clean

; --- evconv_pack_same_type: ARGA (already truncated by the caller — exact, --
; no guard-digit rounding pending) -> FAC, preserving FACTYP exactly as it
; already stands (4 single / 8 double; the FACTYP==2 case is handled by each
; caller's own early-out before this is ever reached). Refreshes DE via
; flt_to_int16 (float.asm), the same silent address-domain contract every
; other ev_f_* factor tail keeps. Shared by evmc_int/evmc_fix. Clobbers A, B,
; C, D, E, H, L.
evconv_pack_same_type:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
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
                ld      de,0
                ret

; --- evmc_abs: ABS(x) -> |x|, same FACTYP as x (spec §9.1). Int path: plain -
; magnitude, except the -32768 edge escapes int16 (promotes to a double
; +32768.0, mirroring float-arith.asm's -32768\-1 quirk, spec §10.4/§9.1's
; "int-domain per §10 float core"). Float path: clear FAC's sign bit in place
; (0's sign bit is already clear) and refresh DE; FACTYP untouched.
evmc_abs:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                ld      a,(FACTYP)
                cp      2
                jr      nz,evabs_float
                ld      a,d
                cp      $80
                jr      nz,evabs_noesc
                ld      a,e
                or      a
                jr      nz,evabs_noesc
                ; DE == -32768: escapes int16 -> promote to double +32768.0
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
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                ld      a,(FACTYP)
                cp      2
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
                ld      a,2
                ld      (FACTYP),a
                ret

; --- evmc_int: INT(x) -> floor toward -infinity, same FACTYP as x (spec ----
; §9.1). fp_trunc (float-arith.asm) truncates toward 0; if a fraction was
; dropped AND x was negative, one more step (-1) makes it a floor (§9.2).
evmc_int:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                ld      a,(FACTYP)
                cp      2
                ret     z                   ; already int: INT(x)=x
                ld      hl,ARGA
                call    widen_rhs_operand   ; ARGA := FPNUM(x)
                call    fp_trunc            ; CF set iff a fraction was dropped
                jr      nc,evmc_int_pack
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,evmc_int_pack     ; positive: truncate == floor already
                jp      evmc_sub1           ; negative + fraction dropped: floor = trunc-1
evmc_int_pack:
                jp      evconv_pack_same_type

; --- evmc_fix: FIX(x) -> truncate toward 0, same FACTYP as x (spec §9.1). --
; Never needs the INT adjustment ("FIX = fp_trunc", §9.2).
evmc_fix:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                ld      a,(FACTYP)
                cp      2
                ret     z
                ld      hl,ARGA
                call    widen_rhs_operand
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
                ld      hl,ARGA
                call    widen_rhs_operand
                jp      round_single_and_pack

; --- evmc_cdbl: CDBL(x) -> widen to double, exact (spec §11.2's "double: ---
; exact" rule). Same widen_rhs_operand + round_and_finalize composition CSNG
; uses above, just the double pack (no digit loss possible from any source).
evmc_cdbl:
                call    ev_mc_arg_checked   ; D-F2-4 gate
                ret     nz                  ; malformed/empty arg -> deferred syntax error
                ld      hl,ARGA
                call    widen_rhs_operand
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
                jp      evmc_dispatch
evmc_sqr_err:
                ld      a,3
                ld      (FPERR),a
                ld      de,0
                ret

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
                ld      hl,ARGA
                call    widen_rhs_operand
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
                call    subrom_call         ; CF=1 iff sub-ROM absent. Result in FAC.
                pop     ix                  ; restore the text cursor (flags survive)
                jp      c,subrom_absent_error ; reduced build w/o sub-ROM (never on the
                                            ; merged machine, which always ships it)
                ld      a,8
                ld      (FACTYP),a
                jp      flt_to_int16        ; tail: DE := flt_to_int16(FAC)

; --- evmc_atn: ATN(x) -> arctangent, DOUBLE (math pack slice 2a, docs/spec- -
; basic-mathpack-slice2.md §11.5). Same arg-parse + widen shape as evmc_sqr
; (ev_mc_arg then widen_rhs_operand into ARGA), then DISPATCHES to fp_atan in
; the sub-ROM PAGE-1 island (sub/sub.asm) via subrom_call/
; SUBROM_ENTRY_BASE_P1+SUBROM_IDX_ATN. This is evmc_sqr's shape MINUS the
; domain check: ATN is total over all x (§6 "no error"), so there is no
; ARGA+FPNUM_SIGN branch and no error tail -- every call falls straight
; through to the dispatch. Same CALSLT-A-not-preserved discipline as
; evmc_sqr: fp_atan is COMPUTE-ONLY (leaves FAC correct but does not touch
; FACTYP/DE), so THIS stub sets FACTYP:=8 + refreshes DE via flt_to_int16
; after a successful return; CF (not A) is the only reliable post-call
; signal, and CF=1 only means "sub-ROM absent" (never on the merged machine).
evmc_atn:
                call    evmc_prologue
                ret     nz
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ATN
                jp      evmc_dispatch

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
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      z,evmc_log_err
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LOG
                jp      evmc_dispatch
evmc_log_err:
                ld      a,3
                ld      (FPERR),a
                ld      de,0
                ret

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
                jp      evmc_dispatch
evmc_exp_huge:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,evmc_exp_overflow
                xor     a
                ld      (FAC),a             ; EXP(-huge) -> 0, not an error
                ld      a,8
                ld      (FACTYP),a
                jp      flt_to_int16
evmc_exp_overflow:
                ld      a,1
                ld      (FPERR),a
                ld      de,0
                ret

; --- evmc_sin / evmc_cos / evmc_tan: SIN(x)/COS(x)/TAN(x), DOUBLE (math -----
; pack slice 2d, docs/spec-basic-mathpack-slice2.md §14.7). evmc_atn's shape
; VERBATIM (SIN/COS/TAN are total over all x, §6/§14.1 "no domain check" --
; no ARGA+FPNUM_SIGN branch, no coarse magnitude check like evmc_exp's, no
; error tail): every call falls straight through to the dispatch. Same
; CALSLT-A-not-preserved discipline as every prior evmc_*: fp_sin/fp_cos/
; fp_tan are COMPUTE-ONLY (leave FAC correct but do not touch FACTYP/DE), so
; each of these stubs sets FACTYP:=8 + refreshes DE via flt_to_int16 after a
; successful return; CF (not A) is the only reliable post-call signal, and
; CF=1 only means "sub-ROM absent" (never on the merged machine).
evmc_sin:
                call    evmc_prologue
                ret     nz
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SIN
                jp      evmc_dispatch
evmc_cos:
                call    evmc_prologue
                ret     nz
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_COS
                jp      evmc_dispatch
evmc_tan:
                call    evmc_prologue
                ret     nz
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_TAN
                jp      evmc_dispatch

; --- evmc_rnd: RND(x) -> pseudo-random value in [0,1), DOUBLE (math pack ---
; slice 2e, docs/spec-basic-mathpack-slice2.md §15.4/§15.5). evmc_atn's
; shape VERBATIM (RND is total over all x -- no domain check, no error
; tail): ev_mc_arg then widen_rhs_operand into ARGA, dispatch to fp_rnd in
; the sub-ROM PAGE-1 island via subrom_call/SUBROM_ENTRY_BASE_P1+
; 3*SUBROM_IDX_RND, same CALSLT-A-not-preserved discipline as every prior
; evmc_*: fp_rnd is COMPUTE-ONLY (leaves FAC correct but does not touch
; FACTYP/DE), so THIS stub sets FACTYP:=8 + refreshes DE via flt_to_int16
; after a successful return; CF (not A) is the only reliable post-call
; signal, and CF=1 only means "sub-ROM absent" (never on the merged
; machine). Note: the argument's VALUE is read by fp_rnd itself (ignored
; when positive, consumed as mant14 when negative, ignored when zero) --
; this stub does not interpret it at all, just widens+dispatches.
evmc_rnd:
                call    evmc_prologue
                ret     nz
                ld      hl,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_RND
                jp      evmc_dispatch
    ENDIF

; --- ev_f_varptr: VARPTR(<var>) -> address of the variable's value field -----
; Returns the address of the 2-byte value cell in zerobas's own variable table
; (VARTAB), NOT the reference ROM's variable-area address — zerobas's table is
; its own layout, so VARPTR yields OUR address. This is a documented divergence
; (PROVENANCE.md): a loader stub that pokes through VARPTR sees a valid, writable
; 16-bit cell, which is all the loader use needs. If the variable does not yet
; exist it is created (value 0) so the returned address is always valid.
ev_f_varptr:
                inc     ix                  ; skip the VARPTR token
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_sp
                ld      a,(ix+0)
                call    is_letter           ; the argument must be a variable name
                jp      nc,ev_f_err
                push    ix
                pop     hl                  ; HL = cursor at the name
    IF ROM_BASE < $4000
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
    ENDIF
                call    var_name_key        ; BC = key, HL past the name
                push    hl
                pop     ix                  ; IX = advanced cursor
    IF ROM_BASE < $4000
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
                call    var_alloc_or_find   ; BC,A -> CF/HL = entry base
                jr      nc,vptr_none        ; OOM (FPERR set) -> deferred, DE=0
                inc     hl
                inc     hl
                inc     hl                  ; HL = value field (entry+3)
                ex      de,hl               ; DE = the value-field address
    ELSE
                ; ensure the variable exists: read its value, write it back. A new
                ; variable is allocated with its current (0) value; an existing one
                ; is left unchanged. Then var_find gives the entry address.
                push    bc
                call    var_get_key         ; DE = current value (0 if unset)
                pop     bc
                push    bc
                call    var_set_key         ; allocate-if-new, value unchanged
                pop     bc
                call    var_find            ; CF set, HL = entry address
                jr      nc,vptr_none        ; table full -> address 0 (defensive)
                inc     hl
                inc     hl                  ; HL = value field (entry+2)
                ex      de,hl               ; DE = the value-field address
    ENDIF
vptr_close:
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
    IF ROM_BASE < $4000
                jp      nz,ev_f_empty       ; malformed close (incl. a consumed
                                            ; array subscript with no outer ')') ->
                                            ; the CHECKED deferred FPERR=4 syntax
                                            ; error, not the bare ERRMARK ev_f_err
                                            ; (which PRINT/LET's check_expr_errors
                                            ; never reads -> a silent wrong 0). Byte-
                                            ; neutral vs ev_f_err; repack-only, as
                                            ; ev_f_empty itself is (lean keeps the
                                            ; frozen ev_f_err below).
    ELSE
                jp      nz,ev_f_err
    ENDIF
                inc     ix
                ret
    IF ROM_BASE < $4000
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
                ; fall-through too. Repack-only -- lean has no array path here.
                ; flt_int_result (NOT the byte-identical set_factyp_int_ret):
                ; `grep flt_int_result` is the audit tool for "which factors
                ; return an int" -- VARPTR must show up in it.
                call    flt_int_result      ; FACTYP := 2 (clobbers A only)
                jr      z,vptr_close        ; Z: DE = element addr -> shared ')' tail
                                            ; NZ: fall into vptr_none -- deferred
                                            ; error (eva_deferred convention; the
                                            ; statement aborts at check_expr_errors)
    ENDIF
vptr_none:
                ld      de,0                ; no address (OOM / deferred error -> 0)
    IF ROM_BASE < $4000
                ret                         ; repack: FPERR already set on every path
                                            ; that reaches here (var_alloc_or_find OOM
                                            ; or an ary_op0_resolve error), so return
                                            ; the deferred 0 -- no ')' check (it could
                                            ; only raise a masking second error)
    ELSE
                call    ev_sp               ; lean: original bytes (byte-frozen)
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ret
    ENDIF

; --- ev_f_base ------------------------------------------------------------
; BASE(n) was descoped here for most of the project's life -- it parsed its
; argument, returned 0 and set ERRMARK, because zerobas kept no per-mode VDP
; table-base map and inventing one was not allowed. Graphics slice G8 retired
; that divergence: our runtime's work-area table matches the reference byte for
; byte (docs/spec-basic-graphics-g8.md §4.1, measured on both), so the real
; implementation is a word fetch and lives with its VDP(n) sibling in
; basic/graphics.asm. The LEAN build has no graphics at all, so it keeps the
; stub.
    IF !G8_RESIDENT
ev_f_base:
                inc     ix                  ; skip the BASE token
                call    ev_sp
                ld      a,(ix+0)
                cp      '('
                jp      nz,ev_f_err
                inc     ix
                call    ev_logic            ; evaluate + discard the index argument
                call    ev_sp
                ld      a,(ix+0)
                cp      ')'
                jp      nz,ev_f_err
                inc     ix
                ld      a,$DD               ; BASE is descoped -> expression-error marker
                ld      (ERRMARK),a
                ld      de,0                ; ...and a 0 result (no fabricated address)
                ret
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

; --- div_de_bc / mod_de_bc: DE / BC -> quotient / remainder in DE -----------
; Unsigned 16-bit divide. zerobas treats operands as 0..65535 (address math),
; diverging from MSX's signed integer divide — documented; signed/float is a
; later model. Division by zero yields 0 and sets ERRMARK (no crash). Clobber
; A, BC, HL.
div_de_bc:
                ld      a,b
                or      c
                jr      z,div_zero          ; divisor 0 -> error, result 0
                call    udiv16              ; DE = quotient, HL = remainder
                ret
mod_de_bc:
                ld      a,b
                or      c
                jr      z,div_zero
                call    udiv16              ; HL = remainder
                ex      de,hl               ; DE = remainder
                ret
div_zero:
                ld      a,$DD               ; expression-error marker (cf. ev_f_err)
                ld      (ERRMARK),a
                ld      de,0
                ret

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
