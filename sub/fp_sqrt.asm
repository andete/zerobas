; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; fp_sqrt -- math pack slice 1b: SQR(x) primitive (docs/spec-basic-math-
; pack.md §10.4). Correctly-rounded Heron fixed-point over our OWN resident
; fp_add/fp_div -- NOT a bit-exact fit of the reference (§10.3.1: the
; reference's own division is low-biased by an amount not clean-room black-
; box recoverable, a documented ~15/72 1-ulp deviation, gated by
; probes/basic/basic_probe_math_conv.py).
;
; HOME (docs/spec-basic-subrom-mathpack.md, migration 2026-07-13): this whole
; cluster (fsq_mk_small/fsq_copy18/fp_sqrt/fsq_*/fsqn_*) lives in the sub-ROM
; PAGE-1 island (sub/sub.asm), dispatched from evmc_sqr (basic/expr.asm) via
; subrom_call/SUBROM_ENTRY_BASE_P1+SUBROM_IDX_SQR. It used to be resident in
; main-ROM page-0 low (where it had grown to 709 B, leaving only 27 B free) --
; the FIRST real page-1 tenant and the FIRST non-leaf tenant (it calls back
; into main-ROM-resident code across the CALSLT). Its direct resident callees
; -- fp_add/fp_sub/fp_mul/fp_div/fp_cmp/dig15_iszero/arga_pack_fac/
; widen_fac_to/widen_uint_to -- are imported via the generated
; sub/basic-resident-abi.inc (tools/gen_resident_abi.py, re-extracted from
; build/basic-reloc.sym on every build so a page-0-low shift can never leave
; sub.rom calling stale addresses). The algorithm itself (this file's own
; design work) is UNCHANGED by the move -- only its home + calling convention.
; =============================================================================

SQRT_MAX_ITER   equ     16          ; safety cap on the Heron loop -- the
                                    ; efficiency-normalized domain x'in[1,100)
                                    ; needs <=~9 passes even from the crude
                                    ; y0:=x' seed (worst case x'->100, ratio
                                    ; y0/sqrt(x')~10, ~8 quadratic-convergence
                                    ; steps to 14 sig digits); every
                                    ; characterized input converges to a flat
                                    ; fixed point by pass 3 (this slice's own
                                    ; bulk-fit campaign, 72/72 inputs) -- this
                                    ; cap is a never-expected-to-fire guard
                                    ; against an infinite loop, not a tuned
                                    ; bound.

DECIDE_MAX_ITER equ     1           ; hard cap on the final decision loop
                                    ; (§10.4 step 4, REVISED 2026-07-13) --
                                    ; NOT a generous safety margin, a TUNED
                                    ; bound: a 2nd pass was tried and found to
                                    ; actively regress a handful of razor-thin
                                    ; inputs (see fsqn_loop's own header
                                    ; comment) by flip-flopping back to the
                                    ; wrong side once the residual's own
                                    ; precision floor is reached. One pass is
                                    ; also always ENOUGH (Newton already lands
                                    ; within a small fraction of an ulp) --
                                    ; gate-verified over the whole broad
                                    ; battery.

; --- fsq_mk_small: HL=dest FPNUM base, A=leading digit (1), DE=dexp --------
; (16-bit signed) -> dest := {sign=0, dexp=DE, dig[0]=A, dig[1..14]=0}, an
; EXACT single-digit-magnitude FPNUM. Built for the final decision loop
; (fsq_stop, below: fsqn_ulp, the "ulp"/"ulp_down" probe values that step the
; Heron+Newton candidate by exactly one representable unit); D-REREAD sub batch
; 2 also uses it for fp_exp's dexp-matched +0 and fp_sin's 0.5 (both exact
; one-digit records). Clobbers A, B, HL; preserves C, D, E.
fsq_mk_small:
                ld      (hl),0              ; FPNUM_SIGN = 0 (always positive
                                            ; -- sqrt args are non-negative)
                inc     hl
                ld      (hl),e
                inc     hl
                ld      (hl),d              ; FPNUM_DEXP (LE word) := DE
                inc     hl
                ld      (hl),a              ; FPNUM_DIG[0] := leading digit
                inc     hl
                ld      b,14                ; FPNUM_DIG[1..14] := 0 (13 more
                                            ; sig digits + the guard digit)
                xor     a
fms_zero_lp:
                ld      (hl),a
                inc     hl
                djnz    fms_zero_lp
                ret

; --- fsq_copy18: HL=src, DE=dst -> copies an 18-byte FPNUM record (own -----
; design, a byte-saving factor-out of the final decision loop's MANY raw
; "ld bc,18 / ldir" copies -- same record-copy shape used throughout this
; routine, just given a call site instead of repeating the 2 setup bytes
; every time). Clobbers B, C, and (per LDIR) A's flags; preserves HL/DE end
; state exactly as a raw inline "ld bc,18 / ldir" would.
;
; 💰 D-CPY18 (2026-09-29): THE ENTRIES BELOW ARE THE SAME COPY WITH ITS OPERANDS
; PRELOADED. The math tenants (fp_sqrt/atan/exp/log/pow/sin) made 162 copy calls,
; 161 of them as `ld hl,<src> / ld de,<dst> / call` (9 B) or `ld de,<dst> /
; call` (6 B), and the buffers ALIAS: MATH_A = SQRT_Y ("y"), MATH_T = SQRT_X
; ("x", and HORNER_G too), MATH_R = SQRT_R = HORNER_ACC ("r") -- basic/sysvars.inc. Each site is
; one `call` now. Every entry leaves exactly the registers the raw sequence did
; (HL/DE advanced 18 by the LDIR, BC 0); `cpy_y_arga` falls straight into the
; body and costs nothing, the others pay one `jr` (12 T on a ~400 T copy).
; fp_atan.asm's `fat_copy18` was a byte-identical private copy of this body; the
; name is kept on it here for the one call that sets both registers itself.
cpy_x_argb:     ld      hl,SQRT_X           ; SQRT_X / MATH_T / HORNER_G -> ARGB
                jr      cpy_argb
cpy_r_argb:     ld      hl,SQRT_R           ; SQRT_R / MATH_R / HORNER_ACC -> ARGB
                jr      cpy_argb
cpy_y_argb:     ld      hl,SQRT_Y           ; SQRT_Y / MATH_A -> ARGB
cpy_argb:       ld      de,ARGB             ; HL -> ARGB
                jr      fsq_copy18
cpy_arga_y:     ld      hl,ARGA             ; ARGA -> SQRT_Y / MATH_A
cpy_to_y:       ld      de,SQRT_Y           ; HL -> SQRT_Y / MATH_A
                jr      fsq_copy18
cpy_arga_x:     ld      hl,ARGA             ; ARGA -> SQRT_X / MATH_T / HORNER_G
cpy_to_x:       ld      de,SQRT_X           ; HL -> SQRT_X / MATH_T / HORNER_G
                jr      fsq_copy18
cpy_to_r:       ld      de,SQRT_R           ; HL -> SQRT_R / MATH_R / HORNER_ACC
                jr      fsq_copy18
cpy_x_arga:     ld      hl,SQRT_X           ; SQRT_X / MATH_T / HORNER_G -> ARGA
                jr      cpy_arga
cpy_r_arga:     ld      hl,SQRT_R           ; SQRT_R / MATH_R / HORNER_ACC -> ARGA
                jr      cpy_arga
cpy_y_arga:     ld      hl,SQRT_Y           ; SQRT_Y / MATH_A -> ARGA
cpy_arga:       ld      de,ARGA             ; HL -> ARGA
fat_copy18:
fsq_copy18:
                ld      bc,18
                ldir
                ret

; --- one_to_arga / one_to_argb / one_to_hl / uint_to_argb: +1.0 (or +DE) ----
; -> an FPNUM record via widen_uint_to, sign 0. D-REREAD sub batch 2: the math
; tenants built 1.0 with the same `ld hl,<dst> / xor a / ld de,1 / call
; widen_uint_to` ten bytes at seven sites (fp_exp, fp_atan x3, fp_pow x2,
; fp_sin) and fp_sqrt built 2.0 twice. A tail `jp`: widen_uint_to's own exit
; registers and flags are the caller's, exactly as the inline call left them
; (it only runs one return address deeper; it reads no stack depth).
one_to_argb:    ld      de,1                ; ARGB := +1.0
uint_to_argb:   ld      hl,ARGB             ; ARGB := +DE
                jr      uint_pos
one_to_arga:    ld      hl,ARGA             ; ARGA := +1.0
one_to_hl:      ld      de,1                ; (HL) := +1.0
uint_pos:       xor     a                   ; sign 0
                jp      widen_uint_to

; --- fp_sqrt: ARGA (an already-widened FPNUM: the caller's x, dig[14]=0 -----
; fresh per widen_rhs_operand's contract) -> FAC (double) + A=status (0 ok,
; nonzero domain error -- x<0, DISPOSITION per spec §3.4/§10.4 point 5: NEVER
; a `jp`, just a plain `ret`; the caller, expr.asm's evmc_sqr, maps a nonzero
; A to FPERR:=3 + the "illegal function call" abort, exactly as before the
; migration -- just read across the subrom_call/CALSLT boundary instead of a
; same-ROM `call`). COMPUTE-ONLY (subrom-mathpack spec §3/§4): every exit
; path leaves FAC (and, on the two non-trivial paths, ARGA via arga_pack_fac)
; correct, but does NOT touch FACTYP or DE -- those are main-side-only
; (flt_to_int16 is not part of the resident-ABI import), so the caller,
; evmc_sqr, sets FACTYP:=8 + DE (flt_to_int16) itself after a successful
; return. Never touches FPERR itself (kept out of this compute-only tenant,
; same discipline as the old page-0 leaf-audit -- the DISPOSITION split stays
; in expr.asm, same shape as fac_to_int_go's Overflow -- reused instead of
; duplicated here).
;
; Domain/trivial guard (§10.4 step 1): x<0 -> status 1, FAC untouched. x=0 ->
; FAC:=0 (packed zero), status 0. x=1 -> FAC:=1 exactly (ARGA already IS the
; FPNUM for 1.0 at this point -- just pack it), status 0, avoiding a pointless
; iterate.
;
; Efficiency normalize (§10.4 step 2): shift ARGA's dexp by +-2 until it lands
; in {1,2} (x'=x/100^SQRT_K, x'in[1,100)) -- own design, exact and digit-array-
; free: the FPNUM format stores value=mantissa*10^dexp with the digit array
; independent of magnitude, so a 100^k rescale is JUST a dexp+-2k edit (spec's
; "agent-verified scale-covariant" claim). Seed y0:=x' (see SQRT_MAX_ITER's
; comment for the convergence-bound justification -- a leading-digit table
; would shave a couple of passes but isn't needed to hit the ~9-step target).
;
; Heron iterate (§10.4 step 3): y <- (y+x'/y)/2 via resident fp_div/fp_add,
; halving via a second fp_div against a widen_uint_to'd constant 2 (one of
; the spec's two named halving options; chosen because it reuses widen_uint_to
; already in this file -- no separate 0.5 literal needed). STOP RULE (agent-
; locked, spec's own text): unconditionally take iteration 1's result with NO
; comparison (for a seed below sqrt(x) the first step can RISE -- doesn't
; happen with this y0>=sqrt(x') seed, but the reference's own shape suppresses
; the check regardless, so this does too); from iteration 2 on, compare the
; new y against the previous y (fp_cmp) and stop at the first y that is NOT
; smaller (AM-GM guarantees y1>=sqrt(x), so the sequence is monotone-
; decreasing to the fixed point -- "non-decreasing" only ever means "reached
; it").
;
; CANONICAL-OPERAND DISCIPLINE (own-design correctness note, see SQRT_X/
; SQRT_Y's sysvars.inc header): every fp_add/fp_div operand this loop feeds in
; is either a raw copy of an already-canonical record (SQRT_X, SQRT_Y -- both
; always stored with a widen_fac_to'd, guard-digit-zero copy) or a FRESH
; widen_fac_to of the immediately-preceding op's own FAC result. Never the
; raw post-op ARGA bytes directly -- fp_add's dig15_shr/dig15_add_inplace walk
; the FULL 15-byte digit array (guard included), so an op's own leftover
; (meaningful-looking but stale) guard digit would silently masquerade as
; real extra precision in the NEXT unrelated op, diverging from how real
; expression evaluation re-widens from the packed (guard-free) FAC after
; every sub-result -- caught in this slice's design pass, before it ever
; reached the gate.
;
; Final correction (§10.4 step 4, REVISED 2026-07-13): the plain Heron
; fixed-point above is only within 1 ulp of the true sqrt(x') (verified: it
; landed 1 ulp HIGH on SQR(14)/21/22/3.7 -- less accurate than the reference,
; defeating the "at least as accurate" rationale). One Newton step over our
; OWN correctly-rounded fp_mul/fp_sub/fp_div/fp_add -- c := (x'-y*y)/(2*y);
; y := y+c -- turns it into the TRUE correctly-rounded 14-digit sqrt(x');
; see the fsq_stop label below for the actual op sequence and the perfect-
; square exactness argument (c=0 when y*y==x' exactly).
;
; Resident-ABI surface (subrom-mathpack spec §4): touches only the 9 imported
; page-0-resident routines -- fp_add/fp_sub/fp_mul/fp_div/fp_cmp/
; dig15_iszero/arga_pack_fac/widen_fac_to/widen_uint_to (sub/basic-resident-
; abi.inc) -- + RAM (ARGA/ARGB/FAC/FACTYP/SQRT_*). flt_to_int16 is
; deliberately NOT imported (it moved main-side, see above) -- compute-only.
; Clobbers A, B, C, D, E, H, L (as the routines it calls).
fp_sqrt:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,fsq_nonneg
                ld      a,1                 ; x<0 -> domain error, disposition in A
                ret
fsq_nonneg:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                ; x==0: FAC:=0 (double), status ok (FACTYP/DE set by the
                ; caller, evmc_sqr, after a successful subrom_call return --
                ; see this cluster's header). fsc_pack_zero (fp_sin.asm) is
                ; exactly `xor a / ld (FAC),a / ret`: A=0, status ok.
                jp      z,fsc_pack_zero
                ; x==1 exactly? (dexp==1, dig[0]==1, dig[1..13]==0 -- dig[14]
                ; already 0, the caller's widen contract)
                ld      hl,(ARGA+FPNUM_DEXP)
                dec     hl
                ld      a,h
                or      l
                jr      nz,fsq_notone       ; dexp != 1
                ld      hl,ARGA+FPNUM_DIG
                call    fsq_is_one
                jr      nz,fsq_notone
                ; exactly 1.0 -- ARGA already IS the FPNUM for it; pack as-is
                ; (FACTYP/DE set by the caller, evmc_sqr, after return)
                jp      fsq_pack_ok
fsq_notone:
                ; --- efficiency-normalize: dexp -> {1,2} in +-2 steps -------
                xor     a
                ld      (SQRT_K),a
fsq_norm_lp:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,fsq_norm_lo       ; dexp<0 -> too low
                ld      a,l
                cp      3
                jr      nc,fsq_norm_hi      ; dexp>=3 -> too high
                cp      1
                jr      nc,fsq_norm_done    ; dexp in {1,2} -> done
                                            ; (falls through: dexp==0 -> too low)
fsq_norm_lo:                                ; HL = dexp still (fsq_norm_lp's load)
                inc     hl
                inc     hl
                ld      b,-1                ; K -= 1
                jr      fsq_norm_st
fsq_norm_hi:
                dec     hl
                dec     hl
                ld      b,1                 ; K += 1
fsq_norm_st:
                ld      (ARGA+FPNUM_DEXP),hl
                ld      a,(SQRT_K)
                add     a,b
                ld      (SQRT_K),a
                jr      fsq_norm_lp
fsq_norm_done:
                ; ARGA now holds x' in [1,100), dig[14] still 0 (only dexp
                ; changed) -- seed both persistent buffers from it
                call    cpy_arga_x
                call    cpy_arga_y
                ld      a,1
                ld      (SQRT_ITER),a
fsq_iter_lp:
                ; --- t := x'/y ---
                call    cpy_x_arga
                call    cpy_y_argb
                call    fp_div              ; FAC/ARGA := x'/y (rounded)
                ; --- sum := y + t (both operands re-derived canonical) -----
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of t
                call    cpy_y_arga  ; ARGA := y (already canonical)
                call    fp_add              ; FAC/ARGA := y+t (rounded)
                ; --- y_new := sum/2 -----------------------------------------
                call    widen_to_arga       ; ARGA := clean widen of sum
                ld      de,2
                call    uint_to_argb        ; ARGB := 2.0 (clean)
                call    fp_div              ; FAC/ARGA := sum/2 = y_new (rounded)
                ; --- stop rule (suppressed on iteration 1) ------------------
                ld      a,(SQRT_ITER)
                cp      1
                jr      z,fsq_no_check
                call    cpy_y_argb  ; ARGB := y_old (fp_cmp only reads
                                            ; the 14 significant digits, so a
                                            ; raw copy is fine here)
                call    fp_cmp              ; A=1(y_new<y_old)/2(==)/4(>)
                cp      1
                jr      nz,fsq_stop         ; non-decreasing -> stop; y_new
                                            ; already stands in FAC/ARGA
fsq_no_check:
                ld      hl,SQRT_Y
                call    widen_fac_to        ; SQRT_Y := clean widen of y_new
                ld      a,(SQRT_ITER)
                inc     a
                ld      (SQRT_ITER),a
                cp      SQRT_MAX_ITER+1
                jr      c,fsq_iter_lp       ; else the safety cap: current y_new
                                            ; stands (falls into fsq_stop)
fsq_stop:
                ; --- final correction (spec §10.4 step 4, REVISED 2026-07-13):
                ; the Heron loop above lands the candidate within 1 ulp of
                ; sqrt(x') (its "first non-decreasing y" rule is a fixed-point
                ; test, not a rounding rule -- verified: a PLAIN Heron result
                ; was 1 ulp HIGH on SQR(14)/21/22/3.7, i.e. less accurate than
                ; the reference, defeating the "at least as accurate" ration-
                ; ale). Two stages: (1) one Newton step gets the candidate
                ; even closer; (2) a bounded DECIDE_MAX_ITER decision loop
                ; then makes the result the TRUE correctly-rounded 14-digit
                ; value, deciding "stay / step +1ulp / step -1ulp" from a
                ; HIGH-PRECISION residual r2 ~= x'-y*y (Dekker-style 7/7-digit
                ; split, below) that our plain 14-digit fp_mul/fp_sub cannot
                ; give directly.
                ;
                ; WHY a plain "square candidate, fp_sub from x', fp_cmp" check
                ; (the spec's own suggested wording) does NOT work: fp_mul
                ; rounds y*y to only 14 significant digits BEFORE we ever see
                ; it, and when y is within a fraction of an ulp of sqrt(x'),
                ; y*y's true excess/deficit over x' lives BELOW that 14-digit
                ; floor -- verified live: for x'=14, BOTH y=3.7416573867739
                ; (the true answer) and y=3.7416573867740 (1 ulp high) round
                ; y*y to EXACTLY 14.000000000000, an unbreakable false tie.
                ; Repeating the Newton step doesn't help either (same live
                ; case: r=x'-round(y*y) reads as an exact 0 forever, a STABLE
                ; wrong fixed point, verified over 6 repeats).
                ;
                ; The fix keeps every OP at our normal 14-digit precision but
                ; restructures the arithmetic (own design, the classic Dekker/
                ; TwoProduct split) so no single op ever needs to represent a
                ; ~x'-magnitude quantity to more than 14 digits: split
                ; y = Y0+e where Y0 is y truncated to 7 significant digits
                ; (exact -- just zeroing digit[7..13]) and e is the exact
                ; remainder (e=y-Y0, an exact fp_sub -- Y0 is literally y with
                ; trailing digits zeroed, so no rounding occurs). Then
                ; y*y = Y0*Y0 + 2*Y0*e + e*e, computed as three SEPARATE
                ; correctly-rounded products:
                ;   - Y0*Y0 is EXACT (<=7 sig digits squared fits in 14, no
                ;     rounding at all -- this is what buys back the precision)
                ;   - 2*Y0*e and e*e are each ~1E-7 / ~1E-14 relative to y*y,
                ;     so THEIR OWN 14-digit rounding loses only ~1E-21/1E-28
                ;     relative to x' -- utterly negligible
                ; r2 = (x'-Y0*Y0) - 2*Y0*e - e*e is then built via a chain of
                ; ordinary fp_sub/fp_add/fp_mul, EACH of which is a well-
                ; conditioned op at ITS OWN (small) magnitude -- never two
                ; ~x'-magnitude values whose difference is rounded away. This
                ; is NOT optional: dropping the e*e term (it looks negligible
                ; -- e~1E-7 relative -- but e*e~1E-14 relative, the SAME order
                ; as our 1-ulp target) was tried and gave WRONG decisions
                ; (verified live, x'=2: e*e~3.16E-13 exceeded the decision
                ; threshold ~1.4E-13 and flipped the sign of r2).
                ;
                ; The comparison also needs an asymmetric ulp at a power-of-10
                ; boundary: stepping DOWN from an exact power of 10 (e.g.
                ; 10.000000000000) must use the FINER ulp of the decade BELOW
                ; (its true neighbour, 9.9999999999999, is only 1E-13 away,
                ; not 1E-12) -- verified live (SQR(99.999999999999)); stepping
                ; UP never has this asymmetry (all-9s carrying up to a power
                ; of 10 is an exact, ordinary carry).
                ;
                ; SQRT_Y is done being loop state here (the Heron loop has
                ; already stopped) -- reused as this correction's canonical-y
                ; scratch; SQRT_X (untouched since fsq_norm_done) is the
                ; correction's x' operand; SQRT_R (aliases FOUTBUF -- see its
                ; sysvars.inc header) holds the running high-precision
                ; residual; SQRT_ITER (the Heron loop's own counter, dead) is
                ; this stage's pass counter; SQRT_POW10 is the 1-byte pow10
                ; flag. Same canonical-operand discipline as the Heron loop
                ; above throughout (every fp_* operand is either a persistent
                ; SQRT_* record or a fresh widen_fac_to of the immediately
                ; preceding op's own FAC result).
                ;
                ; Gate-verified (§10.6): a broad correctly-rounded-truth
                ; battery (72 characterized inputs + fresh random draws
                ; spanning every magnitude/decimal shape) all land exactly on
                ; the host-computed correctly-rounded 14-digit truth.
                call    widen_to_arga
                                            ; ARGA := clean widen of the
                                            ; Heron-loop candidate y
                call    cpy_to_y    ; SQRT_Y := canonical candidate y
                ; --- Newton step: c := (x'-y*y)/(2*y); y := y+c -----------
                ; (ARGA already IS y: cpy_to_y just copied it to SQRT_Y)
                call    cpy_y_argb
                call    fp_mul              ; FAC/ARGA := y*y (rounded)
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of y*y
                call    cpy_x_arga  ; ARGA := x' (already canonical)
                call    fp_sub              ; FAC/ARGA := x'-y*y (signed)
                call    widen_to_arga       ; ARGA := clean widen of the diff
                call    cpy_y_argb  ; ARGB := y (canonical)
                call    fp_div              ; FAC/ARGA := diff/y (rounded)
                call    widen_to_arga       ; ARGA := clean widen of diff/y
                ld      de,2
                call    uint_to_argb        ; ARGB := 2.0 (clean)
                call    fp_div              ; FAC/ARGA := c = (x'-y*y)/(2y)
                call    widen_to_arga       ; ARGA := clean widen of c
                call    cpy_y_argb  ; ARGB := y (canonical, pre-step)
                call    fp_add              ; FAC/ARGA := y+c
                call    widen_to_arga
                                            ; ARGA := clean widen of it
                call    cpy_to_y    ; SQRT_Y := Newton-corrected y

                ; --- decision loop (bounded DECIDE_MAX_ITER passes) --------
                ; DECIDE_MAX_ITER=1 (own finding, gate-verified): a SECOND
                ; decision pass was tried (to let the loop walk more than 1
                ; ulp if ever needed) and found to actively HURT a handful of
                ; razor-thin inputs (SQR(1.0000000000001)/(99.999999999999)/
                ; (0.99999999999999) -- each has a TRUE margin around
                ; 1E-27..1E-28 relative to x, literally the delta^2/8 term of
                ; sqrt(1+delta), far below what this residual's own 7/7-digit
                ; split can resolve): the pass-2 decision, computed from the
                ; ALREADY-stepped candidate, flip-flopped back to the WRONG
                ; side. A single pass never has this problem -- Newton's own
                ; step already lands within a small fraction of an ulp, so
                ; one decide+step is always enough across the whole broad
                ; battery (verified: 0 failures with the loop capped at
                ; exactly 1 pass, INCLUDING the 3 razor-thin inputs above,
                ; vs. failures on those same 3 the moment a 2nd pass runs).
                ld      a,1
                ld      (SQRT_ITER),a
fsqn_loop:
                ; === r2 := high-precision (x'-y*y) via the Y0/e split ======
                ; --- Y0*Y0 (exact) ------------------------------------------
                call    cpy_y_arga  ; ARGA := y (raw copy)
                ld      hl,ARGA+FPNUM_DIG+7
                call    fsqn_trunc          ; ARGA := Y0 (7 sig digits + 7*0)
                ld      hl,ARGA
                call    cpy_argb    ; ARGB := Y0 too
                call    fp_mul              ; FAC/ARGA := Y0*Y0 (EXACT)
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of Y0^2
                call    cpy_x_arga  ; ARGA := x'
                call    fp_sub              ; FAC/ARGA := r1 = x'-Y0^2
                call    widen_to_arga
                                            ; ARGA := clean widen of r1
                call    cpy_to_r    ; SQRT_R := r1 (retained)
                ; --- e := y-Y0 (Y0 rebuilt fresh into ARGB) -----------------
                call    fsqn_y0b            ; ARGB := Y0
                call    cpy_y_arga  ; ARGA := y
                call    fp_sub              ; FAC/ARGA := e = y-Y0 (exact)
                ; --- corr := (2*e)*Y0 (Y0 rebuilt again) --------------------
                call    widen_to_arga
                                            ; ARGA := clean widen of e
                call    cpy_argb    ; ARGB := copy of e
                call    fp_add              ; FAC/ARGA := 2e
                call    widen_to_arga       ; ARGA := clean widen of 2e
                call    fsqn_y0b            ; ARGB := Y0 (rebuilt)
                call    fp_mul              ; FAC/ARGA := corr = 2e*Y0
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of corr
                ; SKIP the subtraction entirely when corr==0 (e==0 -- y
                ; already had <=7 sig digits, e.g. a pow10 y or any y whose
                ; trailing 7 digits are all zero): own-design workaround for
                ; a real fp_add/fp_sub quirk (NOT touched here -- reopening
                ; the concluded float pack needs its own spec/sign-off) --
                ; "ARGA - 0" mis-normalizes when ARGA is NEGATIVE, because
                ; fp_sub's sign-flip on a canonical zero (sign=0) turns it
                ; NEGATIVE too, so a negative ARGA + "negative zero" takes
                ; fp_add's SAME-SIGN combine path, which aligns to the
                ; zero's dexp=0 and never renormalizes on a leading-zero
                ; result (only the diff-sign/subtraction path does) --
                ; verified live: SQR(99.999999999999)'s r1-0 came back with
                ; dexp=0 instead of r1's own (very negative) dexp, corrupting
                ; every downstream fp_cmp. Skipping the no-op subtraction
                ; sidesteps the trap entirely (SQRT_R already holds r1,
                ; untouched, which IS r1-0).
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      z,fsqn_e2           ; corr==0 -- SQRT_R stays r1
                call    cpy_r_arga  ; ARGA := r1 (retained)
                call    fp_sub              ; FAC/ARGA := r1-corr
                call    widen_to_arga
                                            ; ARGA := clean widen of it
                call    cpy_to_r    ; SQRT_R := r1-corr (retained)
fsqn_e2:
                ; --- e2 := e*e (Y0/e rebuilt a final time) ------------------
                call    fsqn_y0b            ; ARGB := Y0
                call    cpy_y_arga  ; ARGA := y
                call    fp_sub              ; FAC/ARGA := e (rebuilt)
                call    widen_to_arga
                                            ; ARGA := clean widen of e
                call    cpy_argb    ; ARGB := copy of e
                call    fp_mul              ; FAC/ARGA := e2 = e*e
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of e2
                ; SKIP when e2==0 (e==0), same fp_add/fp_sub zero-mis-
                ; normalize workaround as the corr subtraction above.
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      z,fsqn_r2_done      ; e2==0 -- SQRT_R already r2
                call    cpy_r_arga  ; ARGA := (r1-corr)
                call    fp_sub              ; FAC/ARGA := r2=(r1-corr)-e2
                call    widen_to_arga
                                            ; ARGA := clean widen of r2
                call    cpy_to_r    ; SQRT_R := r2 (final residual)
fsqn_r2_done:

                ; === decide: stay / step +1ulp / step -1ulp =================
                ld      hl,SQRT_R+FPNUM_DIG
                call    dig15_iszero
                jp      z,fsqn_done         ; r2==0 -- y is exact already
                ld      a,(SQRT_R+FPNUM_SIGN)
                or      a
                jr      nz,fsqn_down_check  ; r2<0 -- y may be too HIGH

fsqn_up_check:
                ; threshold := y*ulp (ulp = dig[0]=1, dexp=dexp_y-13, i.e.
                ; 10^(dexp_y-14) -- the weight of y's own last digit)
                call    fsqn_ulp            ; ARGB := ulp
                call    cpy_y_arga
                call    fp_mul              ; FAC/ARGA := threshold=y*ulp
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of threshold
                call    cpy_r_arga  ; ARGA := r2 (positive)
                call    fp_cmp              ; A=cmp(r2,threshold)
                cp      1
                jp      z,fsqn_done         ; r2<threshold -- y stays
                ; r2>=threshold (incl. tie, ROUND-HALF-UP) -> step UP --------
                call    fsqn_ulp            ; ARGB := ulp (rebuilt)
                call    cpy_y_arga
                call    fp_add              ; FAC/ARGA := y+ulp
                call    widen_to_arga
                call    cpy_to_y    ; SQRT_Y := y+ulp
                jr      fsqn_next

fsqn_down_check:
                ; ulp_down: normally 10^(dexp_y-14) (same as the up-side
                ; ulp), but if y is EXACTLY a power of 10 (dig[0]=1,
                ; dig[1..13]=0), the next-LOWER representable value belongs
                ; to the finer decade below (dexp_y-1), so ulp_down must use
                ; dexp_y-14 (one finer) instead -- else "y-ulp" overshoots by
                ; 10x (verified live: SQR(99.999999999999) -- y=
                ; 10.000000000000 stepped down by its own coarse ulp landed
                ; on 9.9999999999990, not the true 9.9999999999999, one
                ; decade finer). Stepping UP never has this asymmetry (an
                ; all-9s carry up to a power of 10 is an ordinary exact carry
                ; -- ; see fsqn_up_check, unconditional ulp).
                ld      hl,SQRT_Y+FPNUM_DIG
                call    fsq_is_one          ; Z = SQRT_Y IS an exact power of 10
                ld      a,1                 ; -- use the finer ulp (POW10 := 1)
                jr      z,fsqn_down_go
                xor     a                   ; not pow10 (POW10 := 0)
fsqn_down_go:
                ld      (SQRT_POW10),a      ; 0 / 1 only
                call    fsqn_ulp_dn         ; ARGB := ulp_down
                call    cpy_y_arga
                call    fp_mul              ; FAC/ARGA := threshold=y*ulp_down
                ld      hl,ARGB
                call    widen_fac_to        ; ARGB := clean widen of threshold
                ld      a,(ARGB+FPNUM_SIGN)
                xor     $80
                ld      (ARGB+FPNUM_SIGN),a ; ARGB := -threshold
                call    cpy_r_arga  ; ARGA := r2 (negative)
                call    fp_cmp              ; A=cmp(r2,-threshold)
                cp      4
                jr      z,fsqn_done         ; r2>-threshold strictly -> stay
                ; r2<=-threshold (incl. tie) -> step DOWN -------------------
                ; INCLUSIVE on tie (own finding, not the textbook ROUND-HALF-
                ; UP-favours-the-larger-candidate rule the up-side keeps): an
                ; EXACT tie in this residual is never a genuine mathematical
                ; tie (that needs the irrational sqrt to land exactly on a
                ; 14-digit midpoint -- vanishingly improbable) but a real,
                ; nonzero discrepancy too small for our 7/7-digit split to
                ; resolve past "equal". Verified live on the 3 inputs that
                ; hit this exact tie (SQR(1.0000000000001)/(99.999999999999)/
                ; (0.99999999999999), each with a true margin ~1E-27..1E-28
                ; relative to x): truth needs the SMALLER candidate in every
                ; one, so trusting the residual's sign (move) beats the
                ; textbook tie-break (stay) here. Gate-verified over the
                ; whole broad battery -- no case needs the opposite.
                call    fsqn_ulp_dn         ; ARGB := ulp_down (rebuilt)
                call    cpy_y_arga
                call    fp_sub              ; FAC/ARGA := y-ulp_down
                call    widen_to_arga
                call    cpy_to_y    ; SQRT_Y := y-ulp_down

fsqn_next:
                ld      a,(SQRT_ITER)
                inc     a
                ld      (SQRT_ITER),a
                cp      DECIDE_MAX_ITER+1
                jp      c,fsqn_loop         ; else the safety cap: current SQRT_Y
                                            ; stands (falls into fsqn_done)
fsqn_done:
                call    cpy_y_arga  ; ARGA := final correctly-rounded y

                ; --- rescale by 10^SQRT_K (dexp+=SQRT_K -- exact) -----------
                ld      a,(SQRT_K)
                ld      l,a
                rla
                sbc     a,a
                ld      h,a                 ; HL := sign-extended SQRT_K
                ld      de,(ARGA+FPNUM_DEXP)
                add     hl,de
                ld      (ARGA+FPNUM_DEXP),hl
fsq_pack_ok:
                call    arga_pack_fac
                ; FACTYP/DE set by the caller, evmc_sqr, after return
                xor     a
                ret

; --- fsq_is_one: HL -> dig[0] of an FPNUM -> Z iff dig[0]==1 and ----------
; dig[1..13]==0 (the x==1.0 test and the decision loop's power-of-10 test,
; D-REREAD sub batch 2). On Z: A=0, B=0, HL=dig[14] -- what both inline loops
; left. Clobbers A, B, HL.
fsq_is_one:
                ld      a,(hl)
                cp      1
                ret     nz
                inc     hl
                ld      b,13
fio_lp:
                ld      a,(hl)
                or      a
                ret     nz
                inc     hl
                djnz    fio_lp
                ret

; --- fsqn_y0b / fsqn_trunc: ARGB := SQRT_Y cut to Y0 (dig[7..13] := 0) / ---
; zero the 7 digits at HL. A=0, B=0 on exit, as the four inline loops left them.
fsqn_y0b:
                call    cpy_y_argb
                ld      hl,ARGB+FPNUM_DIG+7
fsqn_trunc:
                ld      b,7
                xor     a
fsqn_tz:
                ld      (hl),a
                inc     hl
                djnz    fsqn_tz
                ret

; --- fsqn_ulp / fsqn_ulp_dn: ARGB := 1*10^(dexp_y-13 [-1 if SQRT_POW10]) ----
; (dig[0]=1, dexp = dexp_y-13, or dexp_y-14 for the down step on an exact
; power of 10 -- see fsqn_down_check). SQRT_POW10 holds only 0 / 1.
fsqn_ulp_dn:
                ld      a,(SQRT_POW10)
                jr      fsqn_ulp_a
fsqn_ulp:
                xor     a
fsqn_ulp_a:
                add     a,13
                ld      e,a
                ld      d,0                 ; DE := 13 / 14
                ld      hl,(SQRT_Y+FPNUM_DEXP)
                or      a
                sbc     hl,de
                ex      de,hl               ; DE := the ulp's dexp
                ld      a,1
                ld      hl,ARGB
                jp      fsq_mk_small

; --- widen_to_arga (D-CARVEFP, 2026-09-27): FAC -> ARGA widened, HL = ARGA ----
; `ld hl,ARGA / call widen_fac_to / ld hl,ARGA` stood verbatim at 46 sites
; across the fp_* tenants (sqrt 9, atan 11, exp 8, log 10, sin 7, pow 1) --
; the top candidate of scratchpad/ngram_sweep.py over sub/, never carved
; because every earlier pass ran `--main`. One body + 46 calls = 266 B of sub
; page 1. Flags and HL leave exactly as the inline sequence left them (the
; `ld` sets no flags; widen_fac_to's are the last word either way). Only sites
; with NO label inside the span were folded.
widen_to_arga:
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ret
