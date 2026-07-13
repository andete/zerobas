; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; fp_log -- math pack slice 2b: LOG(x) (natural logarithm) primitive
; (docs/spec-basic-mathpack-slice2.md §12.5). Classic split-plus-breakpoint-
; table reduction: x = m*10^e' with m in [1,10) (e'=dexp-1, exact/free); an
; 8-way ascending breakpoint scan (LOG_BP[1..8]) picks the nearest tabulated
; K-hat[j]=round14(10^(j/8)) so that s=(m-K-hat)/(m+K-hat) is small (the
; classic atanh-of-a-ratio log identity: ln(m/K-hat) = 2*atanh(s)); a degree-5
; minimax poly in g=s*s (own decimal Remez fit for 2*atanh(sqrt g)/sqrt g,
; tools/gen_math_coeffs.py -- never the MSX ROM's own binary-format
; coefficients, §4/§12.3) gives r = s*Q(g) = ln(m/K-hat). Reconstruction adds
; back e'*ln10 (hi/lo split for exactness) and ln(K-hat[j]) (pre-tabulated,
; LNK_TBL, "absorption" of K-hat's own rounding); the e'=-1 decade gets ONE
; merged additive (NEGLNK_TBL) instead of the split e'*C1+LNK path, because
; that split cancels a full decade above the final result there and would
; cost up to 10 ulp (§12.3's "kills the cancellation").
;
; ACCURACY (§12.1, pre-proven by tools/sim_math_chain.py BEFORE this asm was
; written): worst case 4 ulp, 87.3% correctly-rounded vs host `Decimal`
; truth (never the reference). All the >2-ulp cases are in the j=8 FOLD path
; (x in [0.866,1)), where den=m'+1 inherently spans 15 digits and
; d(r)/d(s)=2 doubles the division's own rounding -- the same clean-room
; extended-precision wall as the division deviation (§10.3.1) and the SQR
; floor (§10.4/§10.4's precision floor); documented bounded deviation, NOT a
; per-input never-worse-than-reference invariant (§12.1: the reference is
; itself 1-5 ulp off truth here, so asserting never-worse would just mean
; "never worse than a worse thing").
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from evmc_log
; (basic/expr.asm) via subrom_call/SUBROM_ENTRY_BASE_P1+SUBROM_IDX_LOG.
; Fourth page-1 tenant; reuses fp_atan.asm's fat_copy18 + fp_poly_horner and
; fp_exp.asm's fexp_tbl18addr DIRECTLY (same assembly unit, sub/sub.asm
; includes fp_atan.asm then fp_exp.asm before this file -- see fp_exp.asm's
; own header for why sharing those helpers across the matched EXP/LOG pair is
; not a new precedent). Resident-ABI surface is the SAME subset fp_sqrt/
; fp_atan/fp_exp already use -- no new page-0 relocation (§12.8).
;
; fp_log is a TOTAL function over the stub-guaranteed domain x>0 (evmc_log's
; own sign-OR-zero domain check, §12.6): every path ends in a plain `ret`.
; COMPUTE-ONLY -- leaves FAC correct, never touches FACTYP/DE (evmc_log's
; job, same as every other math-pack tenant).
;
; ALGORITHM (§12.5):
;   1. Split (exact, free): e' := dexp-1 -> MATH_N. MATH_A := x with dexp
;      forced to 1 (so its digit array now reads as a mantissa m in [1,10)).
;   2. j-scan: j := #{k in 1..8 : m > LOG_BP[k]}, an ascending fp_cmp loop
;      with early exit on the first not-greater (A==4 <=> greater, the
;      fp_atan `cp 4` idiom); loop bookkeeping in HORNER_CNT/HORNER_PTR
;      (free until the Horner call). j==8 (m exceeds every breakpoint) folds:
;      m's dexp := 0 (m/10, exact -- no digit shift needed, just the dexp
;      field), e' += 1, j := 0. Final j stored in MATH_J.
;   3. s := (m - K-hat[j]) / (m + K-hat[j]) -> MATH_A (m retired). K-hat[j]
;      = POW8_TBL[j] (0-based, direct index -- POW8_TBL[0] is exactly 1.0,
;      so j==0 needs NO special case here).
;   4. Core: g := s*s -> HORNER_G (MATH_T retired); Q := fp_poly_horner(g,
;      LOG_COEF); r := s*Q (s re-read from MATH_A, replaced there by r).
;   5. Reconstruct (ascending magnitude, the sim-proven order):
;        e'==-1  -> FAC := r + NEGLNK_TBL[j] (ONE scale-matched add), ret.
;        else: if e'<>0: build e'fp := widen(|e'|)+sign -> MATH_T;
;              r += e'fp*LN10_C2. If j<>0: r += LNK_TBL[j-1]. If e'<>0:
;              r += e'fp*LN10_C1 (final -- the largest addend rounds last,
;              at the true result scale). FAC := r, ret.
;      LOG(1): j=0, num=m-1=0 exactly -> s=0 -> r=0 -> e'=0,j=0 both skip
;      every add -> FAC stays exactly the 0 fp_mul (step 4) already left,
;      no special-case path needed (proven in-sim).
;
; RAM (docs/spec-basic-mathpack-slice2.md §12.6 -- NO new claims beyond the
; slice-2a MATH_*/HORNER_* aliases, basic/sysvars.inc): MATH_A (=SQRT_Y)
; holds m (steps 1-2), then s (step 3, m retired), then r (step 4 onward,
; s retired, updated in place through each reconstruction add). MATH_T/
; HORNER_G (=SQRT_X) is unused until step 4's g, then -- once the Horner call
; is past and Q has been copied out -- reused (step 5) to hold e'fp for the
; two LN10_C1/LN10_C2 products (same "retire, then reuse" discipline as
; fp_exp.asm's MATH_T handoff). MATH_R/HORNER_ACC (=SQRT_R) is fp_poly_
; horner's OWN accumulator during step 4's `call fp_poly_horner`; this file
; never uses MATH_R itself (LOG's own working set fits MATH_A+MATH_T alone).
; HORNER_CNT/HORNER_PTR double as the j-scan's own loop counter/breakpoint
; pointer (step 2) -- dead again by the time step 4's Horner call needs
; them (same cell, sequential, never simultaneous, per fp_atan.asm's own
; HORNER_CNT/HORNER_PTR header). MATH_N (2B) holds e' for the whole routine;
; MATH_J (1B) holds j for the whole routine (post-fold value).
;
; CANONICAL-OPERAND DISCIPLINE: identical to fp_exp.asm/fp_atan.asm -- every
; fp_add/fp_sub/fp_mul/fp_div operand is either a raw copy of an already-
; canonical record or a FRESH widen_fac_to of the immediately-preceding op's
; own FAC result, never raw post-op ARGA guard bytes.
;
; Resident-ABI surface: fp_add/fp_sub/fp_mul/fp_div/fp_cmp/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to (sub/basic-resident-abi.inc) + RAM
; (ARGA/ARGB/FAC/MATH_*/HORNER_*). Clobbers A, B, C, D, E, H, L.
; =============================================================================

; --- fp_log: ARGA (an already-widened FPNUM: the caller's x, dig[14]=0 -----
; fresh per widen_rhs_operand's contract; x>0 guaranteed by evmc_log's own
; sign-OR-zero domain check, §12.6) -> FAC (double). TOTAL over that domain;
; every exit is a plain `ret`. COMPUTE-ONLY.
fp_log:
                ; --- step 1: split (exact, free) -----------------------------
                ld      hl,(ARGA+FPNUM_DEXP)
                dec     hl                  ; e' := dexp-1
                ld      (MATH_N),hl
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := x (full copy incl.
                                            ; digit array)
                ld      hl,1
                ld      (MATH_A+FPNUM_DEXP),hl  ; force dexp:=1 -> the digit
                                            ; array now reads as mantissa m
                                            ; in [1,10), exact (no data moved)

                ; --- step 2: j-scan (ascending, early-exit; A==4 <=> greater)
                xor     a
                ld      (HORNER_CNT),a      ; j := 0 (running scan count)
                ld      hl,LOG_BP
                ld      (HORNER_PTR),hl     ; -> LOG_BP[1] (first record)
flog_jscan_loop:
                ld      a,(HORNER_CNT)
                cp      8
                jr      z,flog_jscan_done   ; scanned all 8 -> j=8 (fold)
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := m
                ld      hl,(HORNER_PTR)
                ld      de,ARGB
                call    fat_copy18          ; ARGB := LOG_BP[current]
                call    fp_cmp              ; A = cmp(m, LOG_BP[current])
                cp      4
                jr      nz,flog_jscan_done  ; m<=bp: stop, j stands
                ld      hl,(HORNER_PTR)
                ld      de,18
                add     hl,de
                ld      (HORNER_PTR),hl     ; advance to the next breakpoint
                ld      a,(HORNER_CNT)
                inc     a
                ld      (HORNER_CNT),a
                jr      flog_jscan_loop
flog_jscan_done:
                ld      a,(HORNER_CNT)
                cp      8
                jr      nz,flog_no_fold
                ; fold: m's dexp := 0 (m/10, exact); e' += 1; j := 0
                xor     a
                ld      (MATH_A+FPNUM_DEXP),a
                ld      (MATH_A+FPNUM_DEXP+1),a
                ld      hl,(MATH_N)
                inc     hl
                ld      (MATH_N),hl
                xor     a
                ld      (HORNER_CNT),a
flog_no_fold:
                ld      a,(HORNER_CNT)
                ld      (MATH_J),a          ; j (final, post-fold)

                ; --- step 3: s := (m-Khat[j])/(m+Khat[j]) -> MATH_A ---------
                ; (m retired) -------------------------------------------------
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := m
                ld      a,(MATH_J)
                ld      hl,POW8_TBL
                call    fexp_tbl18addr      ; HL := POW8_TBL + 18*j
                ld      de,ARGB
                call    fat_copy18          ; ARGB := Khat[j]
                call    fp_sub              ; FAC/ARGA := m-Khat[j] = num
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_T
                call    fat_copy18          ; MATH_T := num
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := m (still intact)
                ld      a,(MATH_J)
                ld      hl,POW8_TBL
                call    fexp_tbl18addr      ; HL := POW8_TBL + 18*j (re-fetch)
                ld      de,ARGB
                call    fat_copy18          ; ARGB := Khat[j]
                call    fp_add              ; FAC/ARGA := m+Khat[j] = den
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := den
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := num
                call    fp_div              ; FAC/ARGA := num/den = s
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := s (m retired)

                ; --- step 4: core: g := s*s -> HORNER_G; Q := horner(g); ----
                ; r := s*Q (s from MATH_A; r replaces it there) --------------
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := s
                ld      hl,MATH_A
                ld      de,ARGB
                call    fat_copy18          ; ARGB := s
                call    fp_mul              ; FAC/ARGA := s*s = g
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,HORNER_G
                call    fat_copy18          ; HORNER_G := g (MATH_T retired)
                ld      hl,LOG_COEF
                call    fp_poly_horner      ; FAC/ARGA := Q(g)
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_T
                call    fat_copy18          ; MATH_T(=HORNER_G) := Q
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := s
                ld      hl,MATH_T
                ld      de,ARGB
                call    fat_copy18          ; ARGB := Q
                call    fp_mul              ; FAC/ARGA := s*Q = r
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := r (replaces s)

                ; --- step 5: reconstruct -------------------------------------
                ld      hl,(MATH_N)
                ld      de,-1
                or      a
                sbc     hl,de               ; HL := e' - (-1) = e'+1
                ld      a,h
                or      l
                jr      nz,flog_not_negone
                ; e' == -1: FAC := r + NEGLNK_TBL[j]
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                ld      a,(MATH_J)
                ld      hl,NEGLNK_TBL
                call    fexp_tbl18addr
                ld      de,ARGB
                call    fat_copy18          ; ARGB := NEGLNK_TBL[j]
                jp      fp_add              ; tail: FAC := r+NEGLNK_TBL[j]
                                            ; (COMPUTE-ONLY; round_and_
                                            ; finalize packs FAC)
flog_not_negone:
                ld      hl,(MATH_N)
                ld      a,h
                or      l
                jr      z,flog_no_e1
                ; e' != 0: e'fp := widen(|e'|) + sign -> MATH_T
                ld      hl,(MATH_N)
                ld      a,h
                bit     7,a
                jr      z,flog_epos
                xor     a
                sub     l
                ld      e,a
                ld      a,0
                sbc     a,h
                ld      d,a                 ; DE := |e'|
                ld      a,$80
                jr      flog_ewiden
flog_epos:
                ex      de,hl               ; DE := e' (already >=0)
                xor     a
flog_ewiden:
                push    af                  ; stash the sign flag across the
                                            ; widen_uint_to call
                ld      hl,MATH_T
                xor     a
                call    widen_uint_to       ; MATH_T := widen(|e'|), sign
                                            ; forced 0
                pop     af
                or      a
                jr      z,flog_enosign
                ld      a,$80
                ld      (MATH_T+FPNUM_SIGN),a
flog_enosign:
                ; r += e'fp*LN10_C2
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := e'fp
                ld      hl,LN10_C2
                ld      de,ARGB
                call    fat_copy18          ; ARGB := LN10_C2
                call    fp_mul              ; FAC/ARGA := e'fp*LN10_C2
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := product
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                call    fp_add              ; FAC/ARGA := r + product
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := updated r
flog_no_e1:
                ; if j != 0: r += LNK_TBL[j-1]
                ld      a,(MATH_J)
                or      a
                jr      z,flog_no_j
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                ld      a,(MATH_J)
                dec     a                   ; j-1 (0-based LNK_TBL index)
                ld      hl,LNK_TBL
                call    fexp_tbl18addr
                ld      de,ARGB
                call    fat_copy18          ; ARGB := LNK_TBL[j-1]
                call    fp_add              ; FAC/ARGA := r + LNK_TBL[j-1]
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := updated r
flog_no_j:
                ; if e' != 0: r += e'fp*LN10_C1 (final -- largest addend last)
                ld      hl,(MATH_N)
                ld      a,h
                or      l
                ret     z                   ; e'==0: FAC already correct (the
                                            ; last op to touch it -- either
                                            ; the j-add above or, if that too
                                            ; was skipped, step 4's own final
                                            ; fp_mul -- already packed it)
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := e'fp (still intact --
                                            ; only ever read via fat_copy18
                                            ; since it was built)
                ld      hl,LN10_C1
                ld      de,ARGB
                call    fat_copy18          ; ARGB := LN10_C1
                call    fp_mul              ; FAC/ARGA := e'fp*LN10_C1
                ld      hl,ARGA
                call    widen_fac_to
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := product
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r
                jp      fp_add              ; tail: FAC := r + product (final)
