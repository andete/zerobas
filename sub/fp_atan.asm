; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; fp_atan -- math pack slice 2a: ATN(x) primitive (docs/spec-basic-mathpack-
; slice2.md §11). Two-stage argument reduction (|x|>1 -> 1/x; a>2-sqrt(3) ->
; the tan-half-angle substitution) + a single degree-8 minimax polynomial in
; g=a^2 (own decimal Remez fit, tools/gen_math_coeffs.py, cross-checked vs
; Cody & Waite's ATAN structure -- NEVER the MSX ROM's own coefficients,
; which are binary-format anyway and out of clean-room bounds, §4/§11.3
; point 3). NOT a bit-exact fit of the reference -- the reference's own
; polynomial is a hidden ~1980s approximation (§1.1: up to 2 ulp off
; mathematical truth even on ATN, the BEST-behaved transcendental).
;
; ACCURACY (§11.10, user sign-off 2026-07-13 -- DOCUMENTED BOUNDED DEVIATION):
; this ships own-derived, gated against host `Decimal` truth (never the
; reference). It is NOT strictly correctly-rounded: the 14-digit reduction+
; Horner+reconstruction chain (~15 chained fp_* ops) accumulates rounding to
; ~2 ulp (reaching correctly-rounded needs 3 internal guard digits -- an
; extended-precision layer the resident 14-digit BCD primitives don't provide,
; the same clean-room wall as the division deviation and the SQR floor). ATN is
; the ONLY slice-2 function whose reference is accurate enough to occasionally
; beat our chain, so the user chose to document a bounded deviation rather than
; build that layer. The gate asserts |zerobas - truth| <= 2 ulp (the
; reference's OWN worst envelope) + a battery-wide correctly-rounded floor, NOT
; == truth and NOT a never-worse-than-reference invariant (relaxed for ATN,
; §2/§11.10). Result: 44/61 correctly-rounded, worst 2 ulp.
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from evmc_atn
; (basic/expr.asm) via subrom_call/SUBROM_ENTRY_BASE_P1+SUBROM_IDX_ATN --
; the FIRST transcendental tenant, reusing the page-1 mechanism fp_sqrt
; proved (docs/spec-basic-subrom-mathpack.md). Its resident-ABI surface is a
; SUBSET of fp_sqrt's (fp_add/fp_sub/fp_mul/fp_div/fp_cmp/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to, sub/basic-resident-abi.inc) --
; no new page-0 relocation needed (§11.4).
;
; fp_atan is a TOTAL function (no domain error, unlike fp_sqrt's x<0):
; every path ends in a plain `ret`, no status byte is read by the caller
; (evmc_atn only reads CF, per the subrom_call A-not-preserved-across-CALSLT
; lesson -- docs/spec-basic-subrom-mathpack.md §3).
;
; ALGORITHM (§11.2):
;   0. x==0            -> FAC:=0, return (dig15_iszero on ARGA+FPNUM_DIG).
;   1. sign-fold: s := sign(x); work with a:=|x|; s is re-applied to the
;      final magnitude at the very end (atan is odd).
;   2. reduction 1: a>1  -> a:=1/a, remember MATH_RECIP:=1 (now a in [0,1]).
;   3. reduction 2: a>BREAK (=2-sqrt(3)~=0.267949) ->
;      a := (a*SQRT3-1)/(a+SQRT3), remember MATH_BREAK:=1
;      (now |a| <= 2-sqrt(3) ~= 0.268 -- the fitted polynomial's domain).
;   4. core: g:=a*a; P:=fp_poly_horner(g, ATAN_COEF) (a minimax fit of
;      atan(a)/a as a function of g, degree 8); r:=a*P.
;   5. reconstruct: if MATH_BREAK, r:=r+PI_6; if MATH_RECIP, r:=PI_2-r;
;      apply s onto r's sign; pack FAC.
;
; RAM (docs/spec-basic-mathpack-slice2.md §11.6 -- RAM below DRVA_DPB is
; EXHAUSTED, no new claim permitted): reuses the SQR scratch cells as
; generic math scratch via the MATH_*/HORNER_* aliases (basic/sysvars.inc)
; -- SQR and ATN never run concurrently. MATH_A (=SQRT_Y) holds the
; persistent reduced argument "a" across the WHOLE routine (survives the
; fp_poly_horner call, which never touches it); MATH_T (=SQRT_X) is the
; reduction-stage scratch, retired before the core stage and then reused as
; HORNER_G (same cell, sequential, never simultaneous); MATH_R (=SQRT_R,
; itself FOUTBUF-backed) holds the post-core "r" and is temporarily stood in
; for by fp_poly_horner's OWN accumulator (HORNER_ACC, same cell) during the
; core stage -- MATH_R is not yet live at that point (r doesn't exist until
; AFTER the Horner call returns), so there is no simultaneous-use conflict.
; MATH_SIGN/MATH_RECIP/MATH_BREAK (=SQRT_K/SQRT_ITER/SQRT_POW10) are the
; three 1-byte flags. See each alias's own sysvars.inc header for the full
; reuse argument.
;
; CANONICAL-OPERAND DISCIPLINE (fp_sqrt's hard-won lesson, reused verbatim):
; every fp_add/fp_sub/fp_mul/fp_div operand fed into this routine is either
; a raw copy of an already-canonical record (a MATH_*/HORNER_* persistent
; cell or a math-coeffs.inc constant, which the generator emits with
; guard=0) or a FRESH widen_fac_to of the immediately-preceding op's own FAC
; result -- never the raw post-op ARGA guard bytes directly.
;
; Resident-ABI surface: fp_add/fp_sub/fp_mul/fp_div/fp_cmp/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to (sub/basic-resident-abi.inc) + RAM
; (ARGA/ARGB/FAC/MATH_*/HORNER_*). Clobbers A, B, C, D, E, H, L (as the
; routines it calls).
; =============================================================================

; --- fat_copy18: HL=src, DE=dst -> copies an 18-byte FPNUM record (own -----
; design; kept as its own local copy rather than importing fp_sqrt.asm's
; fsq_copy18 so this file stays self-contained -- identical body). Clobbers
; B, C, and (per LDIR) A's flags; preserves HL/DE end state exactly as a raw
; "ld bc,18 / ldir" would.
fat_copy18:
                ld      bc,18
                ldir
                ret

; --- fp_poly_horner: HL -> a count-prefixed coeff table (`db n` then n -----
; 18-byte FPCONST-shaped records, listed HIGH-order first c[n-1]..c[0]); the
; evaluation point "g" must already be canonical in HORNER_G before this is
; called. Returns FAC (a canonical copy is also left in HORNER_ACC, though
; the caller re-widens ARGA fresh per the usual discipline) := Sigma
; c[i]*g^i, via Horner's method: acc:=c[top]; for each successively lower i,
; acc:=acc*g+c[i]. Tenant-local (NOT resident-ABI) -- reusable verbatim by
; the slice-2b/2c/2d transcendentals (docs/spec-basic-mathpack-slice2.md
; §11.3 point 2).
;
; HORNER_CNT/HORNER_PTR (own loop bookkeeping, see their sysvars.inc header)
; are needed because B/H/L -- the natural Z80 loop-counter/pointer
; registers -- are clobbered by the fp_mul/fp_add calls inside the loop
; body, same reasoning as every other persistent cell here.
;
; Degree-0 (n=1) robustness: the final pack always re-derives FAC from
; HORNER_ACC regardless of how many loop passes ran, so a future 1-term
; caller (never exercised by ATN's own n=9) still gets a correct FAC VALUE.
; Caveat for such a future caller: with n=1 NO fp_add runs, so FACTYP is not
; refreshed here (ATN's n=9 loop runs fp_add, which sets FACTYP=8); a 1-term
; caller that then feeds FAC to a FACTYP-sensitive step must set FACTYP itself.
;
; Clobbers A, B, C, D, E, H, L.
fp_poly_horner:
                ld      a,(hl)              ; n := term count
                inc     hl
                dec     a                   ; remaining lower-order terms
                                            ; after taking c[top]
                ld      (HORNER_CNT),a
                ld      (HORNER_PTR),hl     ; HL now on c[top]'s record
                ld      de,HORNER_ACC
                call    fat_copy18          ; acc := c[top] (a FPCONST record
                                            ; is already canonical, guard=0,
                                            ; per gen_math_coeffs.py)
                ld      hl,(HORNER_PTR)
                ld      de,18
                add     hl,de
                ld      (HORNER_PTR),hl     ; advance past c[top]
fph_loop:
                ld      a,(HORNER_CNT)
                or      a
                jr      z,fph_done          ; no more terms -- acc stands
                ; --- acc := acc*g ---------------------------------------
                ld      hl,HORNER_ACC
                ld      de,ARGA
                call    fat_copy18          ; ARGA := acc
                ld      hl,HORNER_G
                ld      de,ARGB
                call    fat_copy18          ; ARGB := g
                call    fp_mul              ; FAC/ARGA := acc*g (rounded)
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,HORNER_ACC
                call    fat_copy18          ; acc := acc*g
                ; --- acc := acc + c[i] -----------------------------------
                ld      hl,HORNER_ACC
                ld      de,ARGA
                call    fat_copy18          ; ARGA := acc
                ld      hl,(HORNER_PTR)
                ld      de,ARGB
                call    fat_copy18          ; ARGB := c[i] (raw table copy,
                                            ; canonical per the generator)
                call    fp_add              ; FAC/ARGA := acc + c[i] (rounded)
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,HORNER_ACC
                call    fat_copy18          ; acc := acc + c[i]
                ; --- advance the table pointer, decrement remaining count -
                ld      hl,(HORNER_PTR)
                ld      de,18
                add     hl,de
                ld      (HORNER_PTR),hl
                ld      a,(HORNER_CNT)
                dec     a
                ld      (HORNER_CNT),a
                jr      fph_loop
fph_done:
                ld      hl,HORNER_ACC
                ld      de,ARGA
                call    fat_copy18          ; ARGA := final acc (canonical)
                call    arga_pack_fac       ; FAC := acc (guaranteed correct
                                            ; regardless of loop-pass count)
                ret

; --- fp_atan: ARGA (an already-widened FPNUM: the caller's x, dig[14]=0 -----
; fresh per widen_rhs_operand's contract) -> FAC (double). TOTAL function --
; every exit path is a plain `ret`, no status byte (fp_atan never sets A
; meaningfully; the caller only relies on subrom_call's own CF, per the SQR
; A-not-preserved-across-CALSLT lesson). COMPUTE-ONLY (subrom-mathpack spec
; §3/§4): leaves FAC correct on every path (the compute paths via the trailing
; fp_* whose result stands in FAC/ARGA; the x==0 fast path writes FAC:=0
; directly), but does NOT touch FACTYP or DE -- those are main-side-only
; (flt_to_int16 is
; not part of the imported resident-ABI surface); evmc_atn sets FACTYP:=8 +
; refreshes DE itself after a successful return.
fp_atan:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      nz,fat_nonzero
                ; x==0 -> FAC:=0 (double), exact (§11.2 step 0 / §6 "ATN(0)=0
                ; exact")
                xor     a
                ld      (FAC),a
                ret
fat_nonzero:
                ; --- step 1: sign-fold (atan is odd) ------------------------
                ld      a,(ARGA+FPNUM_SIGN)
                ld      (MATH_SIGN),a       ; s := sign(x)
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := x (full copy incl. s)
                xor     a
                ld      (MATH_A+FPNUM_SIGN),a   ; MATH_A := |x| (a >= 0 now)

                ; --- step 2: reduction 1 -- |x|>1 -> a:=1/a -----------------
                xor     a
                ld      (MATH_RECIP),a      ; default: no reduction-1
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,ARGB
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGB := 1.0 (clean)
                call    fp_cmp              ; A=cmp(a,1)
                cp      4
                jr      nz,fat_r1_done      ; a<=1 -> skip
                ld      a,1
                ld      (MATH_RECIP),a
                ld      hl,MATH_A
                ld      de,ARGB
                call    fat_copy18          ; ARGB := a (denominator)
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGA := 1.0 (numerator)
                call    fp_div              ; FAC/ARGA := 1/a (rounded)
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := new a = 1/a_old
fat_r1_done:

                ; --- step 3: reduction 2 -- a>BREAK -> the tan-half-angle ---
                ; substitution a := (a*SQRT3-1)/(a+SQRT3)
                xor     a
                ld      (MATH_BREAK),a      ; default: no reduction-2
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,BREAK
                ld      de,ARGB
                call    fat_copy18          ; ARGB := BREAK (canonical const)
                call    fp_cmp              ; A=cmp(a,BREAK)
                cp      4
                jr      nz,fat_r2_done      ; a<=BREAK -> skip
                ld      a,1
                ld      (MATH_BREAK),a
                ; numerator := a*SQRT3 - 1
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,SQRT3
                ld      de,ARGB
                call    fat_copy18          ; ARGB := SQRT3
                call    fp_mul              ; FAC/ARGA := a*SQRT3
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := clean widen
                ld      hl,ARGB
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGB := 1.0
                call    fp_sub              ; FAC/ARGA := a*SQRT3 - 1
                call    widen_to_arga
                                            ; ARGA := clean widen (numerator)
                ld      de,MATH_T
                call    fat_copy18          ; MATH_T := numerator (persistent)
                ; denominator := a + SQRT3
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a (original, untouched)
                ld      hl,SQRT3
                ld      de,ARGB
                call    fat_copy18          ; ARGB := SQRT3
                call    fp_add              ; FAC/ARGA := a + SQRT3
                call    widen_to_arga
                                            ; ARGA := clean widen (denom)
                ld      de,ARGB
                call    fat_copy18          ; ARGB := denominator
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := numerator
                call    fp_div              ; FAC/ARGA := numerator/denom
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := new a
fat_r2_done:

                ; --- step 4: core -- g:=a*a; P:=horner(g); r:=a*P -----------
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,MATH_A
                ld      de,ARGB
                call    fat_copy18          ; ARGB := a
                call    fp_mul              ; FAC/ARGA := a*a = g
                call    widen_to_arga
                                            ; ARGA := clean widen of g
                ld      de,HORNER_G
                call    fat_copy18          ; HORNER_G := g (MATH_T retired)

                ld      hl,ATAN_COEF
                call    fp_poly_horner      ; FAC/ARGA := P(g)
                call    widen_to_arga
                                            ; ARGA := clean widen of P
                ld      de,MATH_T
                call    fat_copy18          ; MATH_T := P (persistent)

                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,MATH_T
                ld      de,ARGB
                call    fat_copy18          ; ARGB := P
                call    fp_mul              ; FAC/ARGA := a*P = r
                call    widen_to_arga
                                            ; ARGA := clean widen of r
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := r (persistent)

                ; --- step 5: reconstruct ------------------------------------
                ld      a,(MATH_BREAK)
                or      a
                jr      z,fat_no_break
                ld      hl,MATH_R
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                ld      hl,PI_6
                ld      de,ARGB
                call    fat_copy18          ; ARGB := PI_6
                call    fp_add              ; FAC/ARGA := r + PI_6
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := updated r
fat_no_break:
                ld      a,(MATH_RECIP)
                or      a
                jr      z,fat_no_recip
                ld      hl,PI_2
                ld      de,ARGA
                call    fat_copy18          ; ARGA := PI_2
                ld      hl,MATH_R
                ld      de,ARGB
                call    fat_copy18          ; ARGB := r
                call    fp_sub              ; FAC/ARGA := PI_2 - r
                call    widen_to_arga
                                            ; ARGA := clean widen
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := updated r
fat_no_recip:
                ; --- apply sign, pack FAC ------------------------------------
                ld      hl,MATH_R
                ld      de,ARGA
                call    fat_copy18          ; ARGA := final magnitude r
                ld      a,(MATH_SIGN)
                ld      (ARGA+FPNUM_SIGN),a ; r is always > 0 here (x<>0 on
                                            ; this path), so a direct sign
                                            ; overwrite is safe -- no
                                            ; canonical-zero corner case
                call    arga_pack_fac       ; FAC := signed result
                ret
