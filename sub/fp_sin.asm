; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; fp_sin -- math pack slice 2d: SIN(x)/COS(x)/TAN(x) (docs/spec-basic-
; mathpack-slice2.md §14). ONE shared reduction (sincos_kernel) produces BOTH
; sv=sin(r) and cv=cos(r) for a range-reduced r; SIN/COS/TAN differ only in a
; final quadrant-select (sc_select) -- no second reduction, no re-run, no
; stack stash (the fp_pow y-stash problem, §13.5, is sidestepped entirely
; because the whole SIN/COS/TAN cluster shares ONE input, unlike POW's x AND
; y). Reduction: n := round(a*2/pi) (a=|x|, add-0.5-then-truncate, §14.5 step
; 3 -- avoids a digit-carry loop); r := a - n*SIN_C1 - n*SIN_C2 (2-part
; Cody-Waite split, SIN_C1 exactly 5 sig digits so n*C1 is EXACT for
; |n|<=1e9, §14.3); sin(r)=r*S(r^2), cos(r)=C(r^2) via two OWN decimal-
; minimax deg-6 Horner polys (S(u)=sin(sqrt u)/sqrt u, C(u)=cos(sqrt u),
; tools/gen_math_coeffs.py -- never the MSX ROM's own coefficients).
;
; ACCURACY (§14.2, pre-proven by tools/sim_math_chain.py BEFORE this asm was
; written, 24cb6f2): SIN/COS worst abs error 1.0E-14 (~1 ulp), 100%
; correctly-rounded on the moderate battery (|x|<=~1000); large-|x| abs error
; grows ~|x|*1E-14 (n*C2 rounding, the ONLY reduction error given the exact
; n*C1) but stays 3-6 orders better than the reference's own weak ~13-digit
; pi (SIN(1000) 1649 ulp, SIN(1E5) 2.9M ulp off truth). TAN=SIN/COS
; bit-for-bit (§1.2); worst 11 ulp (band edge |sin| or |cos|~=0.1) in the
; well-conditioned 0.1<=|tan|<=10 band, captured (not asserted tight) near
; pi/2 and beyond the exact-n reduction range. Documented bounded deviation,
; ATN/EXP/LOG-shape gate (truth-bound + informational reference report; no
; per-input never-worse claim -- academic here, the reference is 3-6 orders
; worse everywhere it matters, §14.1/§14.2).
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from
; evmc_sin/evmc_cos/evmc_tan (basic/expr.asm) via subrom_call/
; SUBROM_ENTRY_BASE_P1+SUBROM_IDX_{SIN,COS,TAN}. Sixth/seventh/eighth page-1
; tenants (after fp_sqrt/fp_atan/fp_exp/fp_log/fp_pow); reuses fp_atan.asm's
; fat_copy18/fp_poly_horner directly (same assembly unit, sub/sub.asm
; includes fp_atan.asm before this file) and math-coeffs.inc's
; SIN_COEF/COS_COEF/TWO_OVER_PI/SIN_C1/SIN_C2 records (already emitted +
; committed, §14.3). Resident-ABI surface is the SAME SUBSET every prior
; page-1 tenant uses (fp_add/fp_sub/fp_mul/fp_div/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to) -- no new page-0 relocation
; (§14.9; fp_cmp is NOT needed here, unlike fp_atan/fp_pow's reduction
; compares -- the round-half-then-truncate n-extraction needs no fp_cmp at
; all, same "hand-extracted from the widened record's own dexp/digit fields"
; idiom fp_exp's n8 extraction uses).
;
; sincos_kernel/fp_sin/fp_cos/fp_tan are TOTAL functions over all x (§6/§14.1
; "no domain check"): every path ends in a plain `ret`, no status byte in A
; (subrom_call's own A-not-preserved-across-CALSLT lesson -- only CF is
; reliable, and it only ever signals "sub-ROM absent"). COMPUTE-ONLY: leaves
; FAC correct but does NOT touch FACTYP/DE -- those are each evmc_* stub's
; job, exactly as for fp_sqrt/fp_atan/fp_exp/fp_log/fp_pow.
;
; ALGORITHM -- sincos_kernel (§14.5, input ARGA=widened x -> sets sv=MATH_A,
; cv=MATH_R, quad=MATH_J; MATH_N is UNTOUCHED by the kernel, reserved for the
; wrappers' own x-sign stash):
;   1. a := |x| (MATH_A := ARGA, sign forced 0).
;   2. q := a*TWO_OVER_PI (fp_mul, widen -> ARGA).
;   3. q' := q+0.5 (fp_add against an inline-built 0.5 record, widen ->
;      ARGA); round(q)=floor(q') for q>=0. Read dexp' (signed low byte, safe
;      per widen_fac_to's +-64 guarantee):
;        dexp'<=0 (q' in [0.5,1), n=0) -> quad:=0, r:=a directly (the
;          reduction is skipped entirely -- n*C1=n*C2=0 exactly, so
;          computing it through fp_mul/fp_sub would be a no-op at best and,
;          per fp_exp's own step-8 "canonical zero has dexp=0" alignment
;          gotcha, a LATENT correctness risk at worst if a's own dexp is far
;          from 0 -- skipping is both faster and safer);
;        dexp'>=15 (the units digit falls off the 14-digit array, |x| >=
;          ~1.57E14, x meaningless) -> FLOOR: sv:=0.0, cv:=1.0, quad:=0,
;          `ret` immediately (closest to the reference's own 0-return,
;          finite, no 0/0 -- our floor sits further out than the reference's
;          own 1E13, so we are never worse there, §14.1);
;        1<=dexp'<=14 -> quad := (dexp'==1 ? d[0] : 2*d[dexp'-2]+d[dexp'-1])
;          & 3 (10==2 mod 4; AND 3 on an unpacked 0-9 digit byte IS mod 4,
;          a binary-encoding property, not a decimal one), read BEFORE the
;          truncation below (indices dexp'-1/dexp'-2 are always < dexp', so
;          truncation never touches them); nf := q' with dig[dexp'..13]+
;          guard zeroed in place (a pure suffix-zero truncation -- the +0.5
;          already rounded, no separate round-up needed), copied to MATH_T.
;   4. Reduce (skipped on the dexp'<=0 fast path above): r := a - nf*SIN_C1
;      (fp_mul, widen, ARGB; ARGA:=a from MATH_A; fp_sub, widen -> MATH_R
;      temp); r := r - nf*SIN_C2 (fp_mul, widen, ARGB; ARGA:=r from MATH_R;
;      fp_sub, widen -> ARGA). nf*SIN_C1 is EXACT (SIN_C1 is 5 sig digits,
;      |nf|<=1E9 by construction -- §14.3); nf now dead (MATH_T free).
;   5. u := r*r: copy r(ARGA)->MATH_A (a retired), copy->ARGB, fp_mul (ARGA
;      still r) -> u, widen -> HORNER_G (=MATH_T).
;   6. sv := r*S(u): S := fp_poly_horner(HORNER_G, SIN_COEF) (HORNER_G=u
;      preserved across the call, per fp_poly_horner's own contract), widen,
;      ARGB:=S; ARGA:=MATH_A(r); fp_mul -> sv=r*S, widen; store sv->MATH_A
;      (r retired).
;   7. cv := C(u): C := fp_poly_horner(HORNER_G, COS_COEF) (the SAME u --
;      HORNER_G was never touched by step 6's own Horner call, so both S and
;      C see the identical reduced point, the whole point of the shared
;      kernel), widen; store cv->MATH_R. `ret`.
;
; sc_select(q, target) -- shared quadrant-select helper (§14.6): source :=
; (q&1==0) ? MATH_A(sv) : MATH_R(cv); fat_copy18 source->target (ARGA or
; ARGB, caller's choice); if q&2 -> flip target's sign byte (exact fp
; negate, no renormalisation needed -- the record stays canonical). fp_sin
; uses qq=quad+0 -> ARGA/FAC (+ reapplies the ORIGINAL x-sign, SIN odd);
; fp_cos uses qq=(quad+1)&3 -> ARGA/FAC (no x-sign, COS even); fp_tan uses
; BOTH qq=quad+0 -> ARGA(sinv) and qq=(quad+1)&3 -> ARGB(cosv), then fp_div,
; then reapplies the x-sign (TAN odd: SIN odd / COS even).
;
; DEVIATION found live (this implementation's own pass, the fp_pow-
; precedent class of self-caught contract gap, NOT in the literal §14.6
; pseudocode): arga_pack_fac's own header requires the caller to have
; "already verified ... ARGA_DIG isn't the all-zero case" (round_and_
; finalize's precondition, bypassed when arga_pack_fac is called directly).
; sc_select's straight fat_copy18 into ARGA does NOT establish that --
; SIN(0)=0 hits this LIVE: at x=0 the kernel's own dexp'<=0 fast path forces
; quad:=0, so fp_sin's sc_select(qq=0) selects sv=MATH_A=0.0 EXACTLY (r=a=0,
; so step 6's r*S(u) took fp_mul's own zero-product fast path) and copies
; that all-zero record straight into ARGA -- calling arga_pack_fac on it
; directly would pack a non-canonical "$40" lead byte (the SAME bug class
; fp_pow's `0.5^2000` finding hit, fp_pow.asm's fpw_done comment) instead of
; the FAC:=0 the zero convention needs. Fixed by fsc_pack_arga (below), a
; shared zero-safe pack tail for fp_sin/fp_cos (mirroring fp_pow's own
; dig15_iszero-guarded fpw_done shape) applied DEFENSIVELY to BOTH (COS(0)
; itself is safe -- qq=1 selects cv=1.0, never sv -- but COS can select sv
; in odd quadrants for OTHER x, and a coincidental exact-zero r is not
; provably impossible for an engineered test input, so the guard costs a
; few bytes and closes the whole class rather than one instance). fp_tan
; needs NO such guard: it goes through fp_div, which is a round_and_finalize
; consumer and so already carries the dig15_iszero guard on its OWN result
; path (round_and_finalize's own header). TAN's final x-sign reapplication
; is inlined directly on FAC's own lead byte (flt_neg's exact shape, basic/
; float.asm) rather than importing flt_neg itself -- flt_neg is main-ROM-
; only and NOT in the resident-ABI surface, and FAC is a plain RAM address
; (not a call target), so no new relocation is needed to read/write it
; directly (§14.9).
;
; RAM (§14.7 -- NO new claims beyond the slice-2a/2b/2c MATH_*/HORNER_* and
; SQR-precedent SQRT_* aliases, basic/sysvars.inc): the kernel reuses
; MATH_A/MATH_T/HORNER_G/MATH_R/HORNER_ACC exactly as EXP/LOG/ATN do; MATH_J
; (=SQRT_POW10) holds quad; MATH_N (=SQRT_K+SQRT_ITER, 2B) holds the
; wrapper's x-sign byte (the kernel leaves it completely untouched -- the
; whole point of NOT keeping it in a register across the `call
; sincos_kernel`). SQR/ATN/EXP/LOG/POW/SIN/COS/TAN never run concurrently
; (one factor at a time, every prior slice's own argument).
;
; CANONICAL-OPERAND DISCIPLINE (fp_sqrt/fp_atan/fp_exp/fp_pow's hard-won
; lesson, reused verbatim): every fp_add/fp_sub/fp_mul/fp_div operand is
; either a raw copy of an already-canonical record (a MATH_*/HORNER_* cell,
; a math-coeffs.inc constant, or the hand-built 0.5/0.0/1.0 inline records
; below, all guard=0 by construction) or a FRESH widen_fac_to of the
; immediately-preceding op's own FAC result -- never the raw post-op ARGA
; guard bytes directly.
;
; Resident-ABI surface: fp_add/fp_sub/fp_mul/fp_div/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to (sub/basic-resident-abi.inc) + RAM
; (ARGA/ARGB/FAC/MATH_*/HORNER_*). Clobbers A, B, C, D, E, H, L.
; =============================================================================

; --- sc_select: A=q (0..3), HL=target FPNUM address (ARGA or ARGB) --------
; source := (q&1==0) ? MATH_A(sv) : MATH_R(cv); copy source->target (18
; bytes); if q&2 set -> flip target's sign byte in place (exact fp negate,
; no renormalisation -- the record stays canonical). q's original value must
; survive the fat_copy18 call (which clobbers A/B/C and advances HL/DE via
; its own ldir), so it is stashed on the machine stack rather than a
; register -- same reasoning fp_pow's frac path uses for its own y-stash
; (this file's header). Clobbers A, B, C, D, E, H, L.
sc_select:
                push    af                  ; stash q (AF only used locally
                                            ; below, safe to push first)
                ex      de,hl               ; DE := target address (was HL)
                and     1
                jr      nz,scs_cv
                ld      hl,MATH_A           ; source := sv
                jr      scs_copy
scs_cv:
                ld      hl,MATH_R           ; source := cv
scs_copy:
                push    de                  ; stash the target's ORIGINAL
                                            ; address -- fat_copy18/ldir
                                            ; advances DE to target+18, so it
                                            ; must be re-derived from the
                                            ; stack for the sign-flip check
                call    fat_copy18          ; target := source (18-byte copy)
                pop     hl                  ; HL := target address (restored,
                                            ; pre-advance)
                pop     af                  ; A := q (restored)
                and     2
                ret     z
                ld      a,(hl)
                xor     $80
                ld      (hl),a              ; flip target's sign byte
                ret

; --- fsc_pack_arga: shared zero-safe FAC-pack tail for fp_sin/fp_cos -------
; (own fp_pow-precedent fix -- see this file's header). IN: ARGA already
; holds the final (possibly sign-flipped) magnitude. dig15_iszero(ARGA_DIG)
; first: zero -> FAC:=0 directly (the raf_zero_ok shape); nonzero ->
; arga_pack_fac, the normal path. Clobbers A, B, C, D, E, H, L (as
; dig15_iszero/arga_pack_fac).
fsc_pack_arga:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      z,fsc_pack_zero
                jp      arga_pack_fac       ; tail
fsc_pack_zero:
                xor     a
                ld      (FAC),a
                ret

; --- sincos_kernel: ARGA (an already-widened FPNUM: the caller's x, ---------
; dig[14]=0 fresh per widen_rhs_operand's contract) -> sv->MATH_A, cv->
; MATH_R, quad(0..3)->MATH_J. COMPUTE-ONLY, plain `ret` on every path; MATH_N
; is never touched (reserved for the wrappers' own x-sign stash, see this
; file's header). Works on a=|x| -- the wrappers own the x-sign.
sincos_kernel:
                ; --- step 1: a := |x| ---------------------------------------
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := x (persistent)
                xor     a
                ld      (MATH_A+FPNUM_SIGN),a   ; MATH_A := |x| = a

                ; --- step 2: q := a*TWO_OVER_PI -----------------------------
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                ld      hl,TWO_OVER_PI
                ld      de,ARGB
                call    fat_copy18          ; ARGB := TWO_OVER_PI
                call    fp_mul              ; FAC/ARGA := a*TWO_OVER_PI = q
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := q, canonical

                ; --- step 3: q' := q+0.5; round(q)=floor(q') for q>=0 -------
                ld      hl,ARGB
                xor     a
                ld      (hl),a              ; ARGB sign := 0
                inc     hl
                ld      (hl),a              ; ARGB dexp lo := 0
                inc     hl
                ld      (hl),a              ; ARGB dexp hi := 0
                inc     hl
                ld      (hl),5              ; dig[0] := 5 (value 5*10^-1=0.5)
                inc     hl
                ld      b,14                ; dig[1..13]+guard, all zero
                xor     a
sck_half_zero:
                ld      (hl),a
                inc     hl
                djnz    sck_half_zero
                call    fp_add              ; FAC/ARGA := q+0.5 = q'
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := q', canonical (dexp in
                                            ; -64..63, widen_fac_to's own
                                            ; guarantee -- safe signed-byte
                                            ; read below)
                ld      a,(ARGA+FPNUM_DEXP) ; dexp' (low byte)
                or      a
                jp      m,sck_dexp_le0      ; dexp'<0 -> the <=0 fast path
                jr      z,sck_dexp_le0      ; dexp'==0 -> ditto
                cp      15
                jp      p,sck_floor         ; dexp'-15>=0 <=> dexp'>=15

                ; --- 1<=dexp'<=14: quad, then truncate nf in place ----------
                ld      b,a                 ; B := dexp' (survives both the
                                            ; quad calc and the truncation
                                            ; below)
                cp      1
                jr      z,sck_quad_single
                ; dexp'>=2: quad := (2*d[dexp'-2]+d[dexp'-1]) & 3
                push    bc                  ; protect B(dexp') across the
                                            ; digit-array walk (C is scratch)
                ld      hl,ARGA+FPNUM_DIG
                ld      e,a
                ld      d,0
                add     hl,de
                dec     hl                  ; HL -> dig[dexp'-1]
                ld      a,(hl)
                ld      c,a                 ; C := d[dexp'-1]
                dec     hl                  ; HL -> dig[dexp'-2]
                ld      a,(hl)
                add     a,a                 ; A := 2*d[dexp'-2]
                add     a,c                 ; A += d[dexp'-1]
                and     3
                pop     bc
                jr      sck_quad_done
sck_quad_single:
                ld      a,(ARGA+FPNUM_DIG)  ; dexp'==1: quad := d[0]&3
                and     3
sck_quad_done:
                ld      (MATH_J),a          ; quad
                ; truncate: zero dig[dexp'..13]+guard (15-dexp' bytes),
                ; leaving nf = q' with only its integer part
                ld      a,b                 ; A := dexp' (reload, B untouched
                                            ; by the quad calc above)
                ld      hl,ARGA+FPNUM_DIG
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> dig[dexp']
                ld      a,15
                sub     b
                ld      b,a                 ; B := 15-dexp' (bytes to zero)
                xor     a
sck_trunc_zero:
                ld      (hl),a
                inc     hl
                djnz    sck_trunc_zero
                ld      hl,ARGA
                ld      de,MATH_T
                call    fat_copy18          ; MATH_T := nf (persistent)
                jp      sck_reduce
sck_dexp_le0:
                ; q' in [0.5,1), n=0 -- skip the reduction entirely (n*C1=
                ; n*C2=0 exactly; see this file's header for why skipping,
                ; not computing, is the safe choice here)
                xor     a
                ld      (MATH_J),a          ; quad := 0
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a (r = a directly)
                jp      sck_have_r
sck_floor:
                ; dexp'>=15: |x|>=~1.57E14, x meaningless -- FLOOR
                ld      hl,MATH_A
                xor     a
                ld      de,0
                call    widen_uint_to       ; MATH_A := 0.0 (sv)
                ld      hl,MATH_R
                xor     a
                ld      de,1
                call    widen_uint_to       ; MATH_R := 1.0 (cv)
                xor     a
                ld      (MATH_J),a          ; quad := 0
                ret

                ; --- step 4: reduce: r := a - nf*SIN_C1 - nf*SIN_C2 ---------
sck_reduce:
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := nf
                ld      hl,SIN_C1
                ld      de,ARGB
                call    fat_copy18          ; ARGB := SIN_C1
                call    fp_mul              ; FAC/ARGA := nf*SIN_C1 (EXACT,
                                            ; §14.3)
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := nf*SIN_C1
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := a
                call    fp_sub              ; FAC/ARGA := a - nf*C1 = r1
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := r1 (temporary)

                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := nf (still intact)
                ld      hl,SIN_C2
                ld      de,ARGB
                call    fat_copy18          ; ARGB := SIN_C2
                call    fp_mul              ; FAC/ARGA := nf*SIN_C2
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := nf*SIN_C2
                ld      hl,MATH_R
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r1
                call    fp_sub              ; FAC/ARGA := r1 - nf*C2 = r2 = r
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := r, canonical (nf now
                                            ; dead, MATH_T free)
sck_have_r:
                ; --- step 5: u := r*r ---------------------------------------
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := r (a retired)
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := r (ARGA still r)
                call    fp_mul              ; FAC/ARGA := r*r = u
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,HORNER_G
                call    fat_copy18          ; HORNER_G := u (=MATH_T)

                ; --- step 6: sv := r*S(u) -----------------------------------
                ld      hl,SIN_COEF
                call    fp_poly_horner      ; FAC/ARGA := S(u); HORNER_G(u)
                                            ; preserved across the call
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := S
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                call    fp_mul              ; FAC/ARGA := r*S = sv
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := sv (r retired)

                ; --- step 7: cv := C(u) -------------------------------------
                ld      hl,COS_COEF
                call    fp_poly_horner      ; FAC/ARGA := C(u); SAME u as
                                            ; step 6 (HORNER_G untouched by
                                            ; fp_poly_horner, its own
                                            ; contract) -- the whole point of
                                            ; the shared kernel
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := cv
                ret
                ; [MATH_A=sv, MATH_R=cv, MATH_J=quad]

; --- fp_sin: ARGA (widened x) -> FAC (double, sv/cv-derived, sign-corrected)
; SIN is odd: the kernel works on a=|x|, so the ORIGINAL x-sign is saved
; before the kernel runs (which overwrites ARGA) and reapplied at the end.
fp_sin:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      (MATH_N),a          ; save x-sign BEFORE the kernel
                                            ; clobbers ARGA
                call    sincos_kernel       ; sv->MATH_A, cv->MATH_R,
                                            ; quad->MATH_J
                ld      a,(MATH_J)
                and     3                   ; qq := (quad+0)&3
                ld      hl,ARGA
                call    sc_select           ; ARGA := sv or cv per qq
                                            ; (quadrant sign-flip already
                                            ; applied by sc_select itself)
                ld      a,(MATH_N)
                or      a
                jr      z,fsin_pack
                ld      a,(ARGA+FPNUM_SIGN)
                xor     $80
                ld      (ARGA+FPNUM_SIGN),a ; reapply the ORIGINAL x-sign
                                            ; (SIN is odd)
fsin_pack:
                jp      fsc_pack_arga       ; tail: FAC := signed result
                                            ; (zero-safe, see header)

; --- fp_cos: ARGA (widened x) -> FAC (double). COS is even: COS(|x|)=COS(x),
; no x-sign handling needed at all.
fp_cos:
                call    sincos_kernel
                ld      a,(MATH_J)
                add     a,1
                and     3                   ; qq := (quad+1)&3
                ld      hl,ARGA
                call    sc_select           ; ARGA := sv or cv per qq
                jp      fsc_pack_arga

; --- fp_tan: ARGA (widened x) -> FAC (double). TAN(x) = SIN(x)/COS(x)
; bit-for-bit (§1.2): sc_select both sinv (qq=quad+0) and cosv (qq=
; (quad+1)&3) from the SAME kernel call, then fp_div. TAN is odd (SIN odd /
; COS even): the ORIGINAL x-sign is saved before the kernel and reapplied to
; FAC's own lead byte at the end -- inlined directly (flt_neg's exact shape,
; basic/float.asm) rather than importing flt_neg itself, which is main-ROM-
; only and NOT in the resident-ABI surface; FAC is a plain RAM address, not
; a call target, so reading/writing it directly needs no new relocation.
fp_tan:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      (MATH_N),a          ; save x-sign BEFORE the kernel
                call    sincos_kernel
                ld      a,(MATH_J)
                and     3                   ; qq := quad+0
                ld      hl,ARGA
                call    sc_select           ; ARGA := sinv
                ld      a,(MATH_J)
                add     a,1
                and     3                   ; qq := (quad+1)&3
                ld      hl,ARGB
                call    sc_select           ; ARGB := cosv
                call    fp_div              ; FAC/ARGA := sinv/cosv,
                                            ; correctly rounded.
                                            ; round_and_finalize's OWN
                                            ; dig15_iszero guard already
                                            ; makes this zero-safe (unlike
                                            ; arga_pack_fac) -- TAN needs no
                                            ; fsc_pack_arga-style fix.
                                            ; cosv->0 near pi/2: fp_div's own
                                            ; divisor-zero path (FPERR:=2,
                                            ; FAC:=0) is the tenant's
                                            ; disposition there -- the
                                            ; characterized reference shows a
                                            ; large FINITE instead (not an
                                            ; error), but only a tiny-nonzero
                                            ; cosv (not an exact 0) is known
                                            ; to occur (§14.10 point 2); not
                                            ; guarded further per the
                                            ; contract's own instruction
                                            ; ("add a guard only if a live
                                            ; probe surfaces one").
                ld      a,(MATH_N)
                or      a
                ret     z
                ld      a,(FAC)
                or      a
                ret     z                   ; value-0 lead byte exempt (same
                                            ; flt_neg discipline)
                xor     $80
                ld      (FAC),a             ; reapply the ORIGINAL x-sign
                ret
