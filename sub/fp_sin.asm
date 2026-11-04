; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; Clean-room: own design. The range reduction and both polynomials are this
; project's own (docs/spec-basic-mathpack-slice2.md §14); the coefficients come
; from our own decimal minimax fitter, tools/gen_math_coeffs.py -- never the
; reference ROM's own coefficients. Agreement with the reference is a black-box
; characterization result, not a copied one.
; ---------------------------------------------------------------------------
; fp_sin -- math pack slice 2d: SIN(x)/COS(x)/TAN(x). Both polynomials are this
; project's own (tools/gen_math_coeffs.py); the RANGE REDUCTION is the
; reference's, measured black-box (D-TANBIG, 2026-11-04 -- Joost: adopt it):
;
;   t   := round14(|x| * INV_TWO_PI)          INV_TWO_PI = round14(1/(2pi))
;   SIN := sin(2pi * frac(t)), x's sign       (SIN odd)
;   COS := sin(2pi * frac(round14(0.25 - t))) (COS even; the 0.25 - t is
;                                              rounded BEFORE the fraction)
;   TAN := SIN / COS, and a COS of exactly 0 is Overflow (FPERR 1)
;
; scratchpad/tanbig_model.py fits all 19 measured VG-8020 rows with it (1E10..
; 1E38, the 5E13/7E13 TAN-Overflow edge, both signs, SIN(1000), COS(pi/2)'s
; -6.2831853071796E-14). It REPLACES slice 2d's own 2-part Cody-Waite reduction,
; which was 3-6 orders more accurate on large angles and therefore answered
; every one of them differently from the reference (the 07-13 "be accurate"
; sign-off assumed the reference's constants could only be read from its ROM;
; they are two 14-digit roundings). What still differs is the polynomial: up
; to ~2 units in the 14th digit, the reference's own coefficients being out of
; reach by construction.
;
; sn_kernel turns a turns value s into sin(2pi*s): q := 4*frac|s| in [0,4),
; n := round(q), r := (q - n)*HALF_PI in [-pi/4, pi/4], sin(r) = r*S(r^2),
; cos(r) = C(r^2) (own deg-6 decimal-minimax polys), then sc_select(n & 3, plus
; 2 for a negative s). A |s| >= 1E13 has no fraction digit left -> 0 directly.
; SIN and COS each run it once; TAN runs it twice (x waits on the stack).
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from
; evmc_sin/evmc_cos/evmc_tan (basic/expr.asm) via subrom_call/
; SUBROM_ENTRY_BASE_P1+SUBROM_IDX_{SIN,COS,TAN}. Reuses fp_sqrt.asm's record
; copies (fat_copy18, the cpy_* entries, fsq_mk_small), fp_atan.asm's
; fp_poly_horner and math-coeffs.inc's SIN_COEF/COS_COEF/INV_TWO_PI/HALF_PI.
; Resident-ABI surface: fp_add/fp_sub/fp_mul/fp_div/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to.
;
; Every path ends in a plain `ret`, no status byte in A (subrom_call's
; A-not-preserved-across-CALSLT lesson); the one error, TAN's Overflow, is the
; deferred FPERR the caller raises. COMPUTE-ONLY: FAC correct, FACTYP/DE are
; each evmc_* stub's job.
;
; ZERO-SAFE PACK: arga_pack_fac requires a nonzero ARGA_DIG (round_and_
; finalize's precondition, bypassed when it is called directly), and SIN(0),
; COS(pi/2-ish) and every |s| >= 1E13 hand it an exact 0 -- packed directly that
; is a non-canonical "$40" lead byte (fp_pow's `0.5^2000` class). fsc_pack_arga
; guards both SIN and COS; TAN ends in fp_div, a round_and_finalize consumer
; that already carries the guard.
;
; RAM: no claims beyond the MATH_*/HORNER_*/SQRT_* aliases (basic/sysvars.inc):
; MATH_A/MATH_T/HORNER_G/MATH_R/HORNER_ACC as EXP/LOG/ATN use them; MATH_J
; (=SQRT_POW10) holds quad; MATH_N (=SQRT_K) the wrapper's x-sign byte, which
; sn_kernel never touches. TAN's 18-byte x stash is on the stack, as
; mathwrap's own MW_HOST save is -- the MW_HOST area has no 18 B left.
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
; no renormalisation -- the record stays canonical). q's original value
; survives in A: q&1 is tested with `bit`, and fat_copy18 is a bare `ld bc,18
; / ldir` that never touches A (D-REREAD sub batch 2 dropped the AF stash).
; Clobbers A, B, C, D, E, H, L.
sc_select:
                ex      de,hl               ; DE := target address (was HL)
                bit     0,a
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
                                            ; pre-advance); A = q still
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

; --- tn_turns: ARGA (widened x) -> ARGA := t = |x|*INV_TWO_PI, canonical ---
; (D-TANBIG). The reference's own first step, rounded to 14 digits by fp_mul
; exactly as it rounds: every later quantisation the reference shows (SIN 0
; from 1E13, COS 0 from 7E13) is this product losing its fraction digits.
tn_turns:
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := |x|
                ld      hl,INV_TWO_PI
                call    cpy_argb            ; ARGB := 1/(2pi)
                call    fp_mul              ; FAC/ARGA := |x|/(2pi) = t
                jp      widen_to_arga       ; tail

; --- cs_turns: ARGA (widened x) -> ARGA := 0.25 - t, canonical ---------------
; COS(x) = SIN-in-turns of a quarter turn minus t, the 14-digit difference
; taken BEFORE the fraction (that rounding is what makes COS(1E13) .951 and
; COS(7E13) 0 on the reference). COS is even: tn_turns already took |x|.
cs_turns:
                call    tn_turns            ; ARGA := t
                ld      hl,ARGA
                call    cpy_argb            ; ARGB := t
                ld      hl,ARGA
                ld      de,0
                ld      a,2
                call    fsq_mk_small        ; ARGA := 0.2
                ld      a,5
                ld      (ARGA+FPNUM_DIG+1),a    ; ARGA := 0.25
                call    fp_sub              ; FAC/ARGA := 0.25 - t
                jp      widen_to_arga       ; tail

; --- sn_kernel: ARGA (widened turns s, either sign) -> ARGA := sin(2pi*s) ---
; COMPUTE-ONLY; the caller packs (fsc_pack_arga) or divides (fp_tan). MATH_N
; is never touched (the wrappers' x-sign stash).
;   1. quad := 2 if s<0 (sin(-2pi*a) = sin(2pi*a + pi)); a := |s|.
;   2. a >= 1E13 (dexp >= 14): every digit is an integer digit -> 0.
;   3. f := a - int(a) (int = a with dig[dexp..14] zeroed; a<1 -> f = a).
;   4. q := 4f in [0,4); n := floor(q+0.5) in 0..4; quad := (quad+n)&3.
;   5. r := (q-n)*HALF_PI in [-pi/4, pi/4]; sv = r*S(r^2), cv = C(r^2).
;   6. ARGA := sc_select(quad): sin(n*pi/2 + r).
sn_kernel:
                ld      a,(ARGA+FPNUM_SIGN)
                rlca
                add     a,a                 ; $80 -> 2, 0 -> 0
                ld      (MATH_J),a          ; quad := 2 for a negative s
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; ARGA := a = |s|

                ; --- steps 2-3: f := frac(a) --------------------------------
                ld      a,(ARGA+FPNUM_DEXP) ; dexp (low byte; widen's +-64)
                or      a
                jp      m,snk_have_f        ; a < 0.1: f = a
                jr      z,snk_have_f        ; a < 1 (or a = 0): f = a
                cp      14
                jp      p,snk_zero          ; a >= 1E13: an integer
                push    af
                ld      hl,ARGA
                call    cpy_argb            ; ARGB := a
                pop     af
                ld      e,a
                ld      d,0
                ld      hl,ARGB+FPNUM_DIG
                add     hl,de               ; HL -> dig[dexp]
                neg
                add     a,15
                ld      b,a                 ; B := 15-dexp (digits + guard)
                xor     a
snk_trunc:
                ld      (hl),a
                inc     hl
                djnz    snk_trunc           ; ARGB := int(a)
                call    fp_sub              ; FAC/ARGA := a - int(a) = f
                call    widen_to_arga
snk_have_f:
                ; --- step 4: q := 4f; n; quad ------------------------------
                ld      hl,ARGB
                ld      de,1
                ld      a,4
                call    fsq_mk_small        ; ARGB := 4
                call    fp_mul              ; FAC/ARGA := 4f = q
                call    widen_to_arga
                call    cpy_arga_y          ; MATH_A := q
                ld      hl,ARGB
                ld      de,0
                ld      a,5
                call    fsq_mk_small        ; ARGB := 0.5
                call    fp_add              ; FAC/ARGA := q + 0.5 = q'
                call    widen_to_arga
                ld      a,(ARGA+FPNUM_DEXP)
                dec     a
                ld      a,0
                jr      nz,snk_n            ; q' < 1: n = 0
                ld      a,(ARGA+FPNUM_DIG)  ; q' in [1,4.5): n = its units digit
snk_n:
                push    af                  ; n (cpy_y_arga's ldir takes BC)
                ld      hl,MATH_J
                add     a,(hl)
                and     3
                ld      (hl),a              ; quad := (quad + n) & 3
                call    cpy_y_arga          ; ARGA := q
                pop     af
                or      a
                jr      z,snk_have_d        ; n = 0: d = q
                ld      hl,ARGB
                ld      de,1
                call    fsq_mk_small        ; ARGB := n (A = n)
                call    fp_sub              ; FAC/ARGA := q - n = d (exact)
                call    widen_to_arga
snk_have_d:
                ; --- step 5: r := d*HALF_PI --------------------------------
                ld      hl,HALF_PI
                call    cpy_argb
                call    fp_mul              ; FAC/ARGA := r
                call    widen_to_arga
                call    cpy_arga_y          ; MATH_A := r
                ld      hl,ARGA
                call    cpy_argb            ; ARGB := r (ARGA still r)
                call    fp_mul              ; FAC/ARGA := r*r = u
                call    widen_to_arga
                call    cpy_to_x            ; HORNER_G := u (=MATH_T)
                ld      hl,SIN_COEF
                call    fp_poly_horner      ; FAC/ARGA := S(u); HORNER_G(u)
                                            ; preserved across the call
                call    widen_to_arga
                call    cpy_argb            ; ARGB := S
                call    cpy_y_arga          ; ARGA := r
                call    fp_mul              ; FAC/ARGA := r*S = sv
                call    widen_to_arga
                call    cpy_to_y            ; MATH_A := sv (r retired)
                ld      hl,COS_COEF
                call    fp_poly_horner      ; FAC/ARGA := C(u), the SAME u
                call    widen_to_arga
                call    cpy_to_r            ; MATH_R := cv
                ; --- step 6: select -----------------------------------------
                ld      a,(MATH_J)
                ld      hl,ARGA
                jp      sc_select           ; tail: ARGA := sin(n*pi/2 + r)
snk_zero:
                ld      hl,ARGA
                xor     a
                ld      de,0
                jp      widen_uint_to       ; tail: ARGA := 0.0

; --- fp_sin: ARGA (widened x) -> FAC. SIN is odd: the kernel sees t = |x|/2pi
; and the ORIGINAL x-sign is reapplied at the end.
fp_sin:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      (MATH_N),a          ; save x-sign BEFORE tn_turns
                                            ; clears it
                call    tn_turns
                call    sn_kernel           ; ARGA := sin(2pi*t)
                call    fs_resign           ; ... with x's sign
                jp      fsc_pack_arga       ; tail (zero-safe, see header)

; --- fs_resign: flip ARGA's sign when the saved x-sign (MATH_N) is negative.
fs_resign:
                ld      a,(MATH_N)
                or      a
                ret     z
                ld      a,(ARGA+FPNUM_SIGN)
                xor     $80
                ld      (ARGA+FPNUM_SIGN),a
                ret

; --- fp_cos: ARGA (widened x) -> FAC. COS(x) = sin(2pi*(0.25 - t)).
fp_cos:
                call    cs_turns
                call    sn_kernel
                jp      fsc_pack_arga

; --- fp_tan: ARGA (widened x) -> FAC. TAN(x) = SIN(x)/COS(x), each by its own
; reduction exactly as the reference computes them (D-TANBIG): two kernel
; runs, so x waits on the stack (18 B, mathwrap's own reserve shape) while
; the first one owns every MATH_* cell. A COS of exactly 0 is Overflow, as on
; the VG-8020 (TAN(1E38): SIN 0, COS 0, ERR 6) -- FPERR 1, raised by the
; caller like every other deferred numeric error.
fp_tan:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      (MATH_N),a          ; save x-sign
                ld      hl,-FPNUM_SIZE
                add     hl,sp
                ld      sp,hl               ; 18 B reserved
                ex      de,hl
                ld      hl,ARGA
                call    fat_copy18          ; stack := x
                call    tn_turns
                call    sn_kernel
                call    fs_resign           ; ARGA := SIN(x)
                call    ftn_swap            ; stack := SIN(x), ARGA := x
                call    cs_turns
                call    sn_kernel           ; ARGA := COS(x)
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      z,ftn_ovf
                ld      hl,ARGA
                call    cpy_argb            ; ARGB := COS(x)
                call    ftn_swap            ; ARGA := SIN(x)
                ld      hl,FPNUM_SIZE
                add     hl,sp
                ld      sp,hl               ; release
                jp      fp_div              ; tail: FAC := SIN/COS
ftn_ovf:
                ld      a,1
                ld      (FPERR),a           ; Overflow
                ld      hl,FPNUM_SIZE
                add     hl,sp
                ld      sp,hl               ; release
                ret

; --- ftn_swap: exchange ARGA with fp_tan's 18 stack bytes (at SP+2 here).
ftn_swap:
                ld      hl,2
                add     hl,sp
                ld      de,ARGA
                ld      b,FPNUM_SIZE
fsw_lp:
                ld      a,(de)
                ld      c,(hl)
                ld      (hl),a
                ld      a,c
                ld      (de),a
                inc     hl
                inc     de
                djnz    fsw_lp
                ret
