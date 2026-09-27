; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; Clean-room: own design. The reduction and the polynomial shape are this
; project's own (docs/spec-basic-mathpack-slice2.md); the coefficients come from
; our own decimal minimax fitter, tools/gen_math_coeffs.py -- never the
; reference ROM's own constants. Agreement with the reference is a black-box
; characterization result, not a copied one.
; ---------------------------------------------------------------------------
; fp_exp -- math pack slice 2b: EXP(x) primitive (docs/spec-basic-mathpack-
; slice2.md §12.4). Classic table-assisted range reduction: n8 := nearest-int
; (x*8/ln10) splits x into a decade part n (n8>>3) and an eighth-of-a-decade
; part m (n8&7, 0..7); the remainder r = x - n8*(ln10/8) (split hi/lo for
; exactness) is fed to a degree-9 minimax poly E(r)=(exp(r)-1)/r (own decimal
; Remez fit, tools/gen_math_coeffs.py -- never the MSX ROM's own binary-format
; coefficients, §4/§12.3); the implicit leading 1 of exp(r)=1+r*E(r) keeps the
; reconstruction's error amplification down to ~1.1x (not the ~7.5x a direct
; exp-poly form would cost, §12.3). Table T-hat[m]=round14(10^(m/8)) folds the
; eighth-decade part back in exactly; the final *10^n scale is an EXACT decimal
; shift (no digit rounding).
;
; ACCURACY (§12.1, pre-proven by tools/sim_math_chain.py BEFORE this asm was
; written -- the §11.10/ATN lesson applied forward): the 14-digit chain's
; worst case is 1 ulp, 92.0% correctly-rounded vs host `Decimal` truth (NEVER
; the reference, same framework as SQR/ATN). The gate asserts |zerobas-truth|
; <= 2 ulp (a +1 margin over the measured worst, covering the sim's own
; documented no-sticky-digit modelling limit) + a battery-wide exact-count
; floor (drift tripwire). Per-input never-worse-than-reference is NOT
; asserted (§12.1: the reference is 3-45 ulp off truth here, so our chain
; beats it trivially in aggregate -- asserting per-input would just mean
; "never worse than a much worse thing", not a meaningful bound).
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from evmc_exp
; (basic/expr.asm) via subrom_call/SUBROM_ENTRY_BASE_P1+SUBROM_IDX_EXP.
; Third page-1 tenant (after fp_sqrt, fp_atan); reuses fp_atan.asm's
; fat_copy18 + fp_poly_horner DIRECTLY (same assembly unit, sub/sub.asm
; includes fp_atan.asm first) rather than re-duplicating them -- unlike
; fat_copy18 itself (which fp_atan.asm keeps as ITS OWN private duplicate of
; fp_sqrt.asm's fsq_copy18 for file self-containment), EXP and LOG are
; delivered as a matched pair in this one slice and already share the
; math-coeffs.inc table set, so sharing this file's own new helpers
; (fexp_cmp16/fexp_tbl18addr below) with fp_log.asm is the same kind of
; reuse, not a new precedent. Resident-ABI surface is the SAME SUBSET of
; fp_sqrt's fp_atan already uses (fp_add/fp_sub/fp_mul/fp_div/fp_cmp/
; dig15_iszero/arga_pack_fac/widen_fac_to/widen_uint_to) -- no new page-0
; relocation (§12.8).
;
; fp_exp is a TOTAL function over the stub-guaranteed domain |x|<1000
; (evmc_exp's own coarse dexp>=4 disposition, §12.6): every path ends in a
; plain `ret`, no status byte in A (subrom_call's A-not-preserved-across-
; CALSLT lesson -- only CF is reliable, and it only ever signals "sub-ROM
; absent"). COMPUTE-ONLY: leaves FAC correct (or, on the tenant's own
; internal overflow/underflow disposition, a zeroed FAC lead byte + FPERR as
; appropriate) but does NOT touch FACTYP/DE -- those are evmc_exp's job,
; exactly as for fp_sqrt/fp_atan.
;
; ALGORITHM (§12.4):
;   1. MATH_A := x (persistent copy). q := x*EXP_RC (=x*8/ln10).
;   2. n8 := nearest-int(q), hand-extracted from the WIDENED q record's own
;      dexp/digit fields (no float compare needed): dexp<=0 -> magnitude 0
;      (round via dig[0] when dexp==0); 1<=dexp<=4 -> magnitude = digits
;      d[0..dexp-1] as a decimal integer, round-half-away via d[dexp];
;      dexp>4 -> defensive (can't happen given the stub's |x|<1000 bound) --
;      treated directly as the step-3 bound breach by sign. Sign applied,
;      stored in MATH_N.
;   3. Bounds: n8>552 -> FPERR:=1, FAC:=0, ret (Overflow). n8<-552 -> FAC:=0,
;      ret (silent underflow). Keeps every later dexp inside fp_mul's own
;      +-63 preExp envelope with margin (check_preexp_bounds, float-arith.asm)
;      -- borderline overflow/underflow AT the true magnitude boundary is
;      disposed by the FINAL step-8 fp_mul's own round_and_finalize, which
;      the sim proved lands exactly on the characterized reference
;      thresholds (EXP(145.062) ok / EXP(145.063) Overflow, etc.).
;   4. m := n8 & 7 (low byte, two's-complement-correct for negatives) into
;      MATH_J; n8fp := widen(|n8|) + sign poke -> MATH_T; n := n8 arithmetic-
;      shift-right 3, overwriting MATH_N (n8 itself now dead).
;   5. Reduce: r := x - n8fp*EXP_C1 - n8fp*EXP_C2 [- EXP_TCOR[m-1] if m<>0],
;      each subtraction re-widened canonical per the usual discipline. Final
;      r moves directly into HORNER_G (=MATH_T, n8fp's cell -- dead by then).
;   6. Core: E := fp_poly_horner(HORNER_G, EXP_COEF); w := r*E (r re-read
;      from HORNER_G, untouched by the Horner call per its own contract).
;   7. Reconstruct mantissa: m<>0 -> p := T-hat[m] + T-hat[m]*w; m=0 ->
;      p := 1.0 + w. Stored in MATH_A (x long since retired).
;   8. Scale (exact): p's OWN dexp field += n directly (a power-of-ten
;      rescale is a pure dexp shift, no digit multiply -- fp_sqrt's own
;      SQRT_K rescale precedent), then FAC := p_rescaled + 0.0 via fp_add
;      (NOT fp_mul with a literal 10^n record -- that was tried first and
;      found to mis-overflow whenever p<1, since fp_mul's own preExp PRE-
;      check runs before normalisation and doesn't know the true final
;      dexp; fp_add has no such pre-check, so round_and_finalize's post-op
;      bound check on the TRUE dexp is what disposes a genuine overflow/
;      underflow here). Plain tail-call `ret` (via `jp fp_add`) --
;      COMPUTE-ONLY.
;
; RAM (docs/spec-basic-mathpack-slice2.md §12.6 -- NO new claims beyond the
; slice-2a MATH_*/HORNER_* aliases, basic/sysvars.inc): MATH_A (=SQRT_Y)
; holds x from entry through step 5's first subtraction, then is REUSED
; (step 7) to hold p, the post-mantissa-reconstruction value, until the
; step-8 scale multiply consumes it -- the two roles never overlap (x is
; long dead by step 7). MATH_T/HORNER_G (=SQRT_X) holds n8fp (step 4-5) and
; then, once n8fp's last use (the second C1/C2 product) is past, is
; OVERWRITTEN with the final reduced r for the Horner call (step 5's tail /
; step 6) -- same "retire, then reuse the freed cell for the next quantity"
; discipline fp_atan.asm's own MATH_T->HORNER_G handoff uses. MATH_R/
; HORNER_ACC (=SQRT_R, FOUTBUF-backed) is transient scratch across steps 5-7
; (a product-in-flight, then E, then w) -- never needed simultaneously with
; fp_poly_horner's OWN use of the same cell as HORNER_ACC (that runs
; entirely inside step 6's `call fp_poly_horner`, between our own reads/
; writes of the cell). MATH_N (2B, =SQRT_K+SQRT_ITER) holds n8 (steps 2-4)
; then n (steps 4-8, n8 itself being dead once n8fp/m are extracted).
; MATH_J (1B, =SQRT_POW10) holds m for the whole routine.
;
; CANONICAL-OPERAND DISCIPLINE (fp_sqrt/fp_atan's hard-won lesson, reused
; verbatim): every fp_add/fp_sub/fp_mul/fp_div operand is either a raw copy
; of an already-canonical record (a MATH_*/HORNER_* cell or a math-coeffs.inc
; constant, guard=0 by construction) or a FRESH widen_fac_to of the
; immediately-preceding op's own FAC result -- never the raw post-op ARGA
; guard bytes directly.
;
; Resident-ABI surface: fp_add/fp_sub/fp_mul/fp_div/fp_cmp/dig15_iszero/
; arga_pack_fac/widen_fac_to/widen_uint_to (sub/basic-resident-abi.inc) + RAM
; (ARGA/ARGB/FAC/FPERR/MATH_*/HORNER_*). Clobbers A, B, C, D, E, H, L (as the
; routines it calls).
; =============================================================================

; --- fexp_cmp16: own local duplicate of the resident cmp16_bits body -------
; (basic/float-arith.asm) -- deliberately NOT added to the resident-ABI
; surface: this is a plain 16-bit SIGNED integer compare for the n8 vs +-552
; bound check (§12.4 step 3), not an FPNUM operation, so importing the
; resident cmp16_bits would be an unjustified new relocation (§12.8 "NO new
; page-0 relocations" -- the whole point of keeping this tenant-local).
; HL=lhs, DE=rhs -> A = 1(lhs<rhs) / 2(equal) / 4(lhs>rhs). Clobbers A, HL.
fexp_cmp16:
                ld      a,h
                cp      d
                jr      nz,fc16_ne
                ld      a,l
                cp      e
                jr      nz,fc16_ne
                ld      a,2
                ret
fc16_ne:
                or      a
                sbc     hl,de
                jp      pe,fc16_vset
                jp      m,fc16_lt
                jr      fc16_gt
fc16_vset:
                jp      p,fc16_lt
                jr      fc16_gt
fc16_lt:
                ld      a,1
                ret
fc16_gt:
                ld      a,4
                ret

; --- fexp_tbl18addr: HL=table base, A=0-based record index -> HL := base + --
; 18*index (18*A computed as 16A+2A: two doublings then a third, saving the
; A/2A partial before continuing to 4A/8A/16A, then adding the saved 2A back
; in -- §12.4/§12.5 "Table record addressing: HL := base + 18*m (compute
; m*16 + m*2)"). Own local helper (tenant-local, NOT resident-ABI) for
; POW8_TBL/EXP_TCOR/LNK_TBL/NEGLNK_TBL/LOG_BP addressing. Shared verbatim by
; fp_log.asm (same assembly unit, called directly -- the EXP/LOG matched-pair
; reuse this file's own header explains). Clobbers A, D, E, H, L.
fexp_tbl18addr:
                push    hl                  ; save table base
                ld      e,a
                ld      d,0                 ; DE := index
                ld      h,d
                ld      l,e                 ; HL := index (8-bit-load copy, no
                                            ; native 16-bit reg-reg move)
                add     hl,hl               ; 2*index
                ld      d,h
                ld      e,l                 ; DE := 2*index (stashed)
                add     hl,hl               ; 4*index
                add     hl,hl               ; 8*index
                add     hl,hl               ; 16*index
                add     hl,de               ; 16*index + 2*index = 18*index
                ex      de,hl               ; DE := 18*index
                pop     hl                  ; HL := table base
                add     hl,de               ; HL := base + 18*index
                ret

; --- fp_exp: ARGA (an already-widened FPNUM: the caller's x, dig[14]=0 -----
; fresh per widen_rhs_operand's contract; |x|<1000 guaranteed by evmc_exp's
; own coarse dexp>=4 disposition, §12.6) -> FAC (double). TOTAL over that
; domain; every exit is a plain `ret`. COMPUTE-ONLY (leaves FAC correct, or a
; zeroed lead byte + FPERR on the tenant's own internal overflow/underflow
; disposition; never touches FACTYP/DE -- evmc_exp's job).
fp_exp:
                ; --- step 1: MATH_A := x; q := x*EXP_RC ---------------------
                ld      hl,ARGA
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := x (persistent)
                ld      hl,EXP_RC
                ld      de,ARGB
                call    fat_copy18          ; ARGB := EXP_RC (ARGA already x)
                call    fp_mul              ; FAC/ARGA := x*EXP_RC = q
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := clean widen of q

                ; --- step 2: n8 := nearest-int(q), hand-extracted -----------
                ld      a,(ARGA+FPNUM_DEXP) ; low byte -- safe as a signed
                                            ; 8-bit read: widen_fac_to's own
                                            ; header guarantees dexp in
                                            ; -64..63, so the high byte is
                                            ; always pure sign-extension
                or      a
                jp      m,fexp_dexp_le0     ; dexp<0 -> magnitude 0
                jr      z,fexp_dexp_eq0     ; dexp==0 -> magnitude 0, round
                                            ; via dig[0]
                cp      5
                jp      p,fexp_dexp_gt4     ; dexp-5>=0 <=> dexp>=5 (defensive
                                            ; -- unreachable given the stub's
                                            ; own |x|<1000 bound, but handled
                                            ; safely per §12.4 step 2)
                ; 1<=dexp<=4: magnitude := digits d[0..dexp-1] as decimal,
                ; round-half-away via d[dexp]
                ld      b,a                 ; B := dexp (loop count 1..4)
                ld      hl,0                ; HL := magnitude accumulator
                ld      de,ARGA+FPNUM_DIG   ; DE -> dig[0]
fexp_magloop:
                push    bc                  ; save the outer loop counter
                add     hl,hl               ; HL*2
                push    hl                  ; stash 2x
                add     hl,hl               ; HL*4
                add     hl,hl               ; HL*8
                pop     bc                  ; bc := 2x
                add     hl,bc               ; HL := 8x+2x = 10x
                ld      a,(de)
                ld      c,a
                ld      b,0
                add     hl,bc               ; HL += next digit
                inc     de
                pop     bc                  ; restore the outer loop counter
                djnz    fexp_magloop
                ; DE now -> dig[dexp] (the first digit NOT yet consumed) --
                ; the rounding digit
                ld      a,(de)
                cp      5
                jr      c,fexp_mag_done
                inc     hl
                jr      fexp_mag_done
fexp_dexp_eq0:
                ld      hl,0
                ld      a,(ARGA+FPNUM_DIG)
                cp      5
                jr      c,fexp_mag_done
                inc     hl
                jr      fexp_mag_done
fexp_dexp_le0:
                ld      hl,0                ; dexp<0: value < 0.1 strictly,
                                            ; always rounds to 0 (no digit
                                            ; check needed)
fexp_mag_done:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,fexp_n8_signed
                xor     a
                sub     l
                ld      l,a
                ld      a,0
                sbc     a,h
                ld      h,a                 ; HL := -HL (two's complement)
fexp_n8_signed:
                ld      (MATH_N),hl         ; MATH_N := n8
                jr      fexp_bounds
fexp_dexp_gt4:
                ; defensive: |n8| would be far beyond 552 regardless of sign
                ; -- dispatch directly to the matching bound-breach tail
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jp      z,fexp_overflow
                jp      fexp_underflow

                ; --- step 3: bounds -552..552 (16-bit signed) ---------------
fexp_bounds:
                ld      hl,(MATH_N)
                ld      de,552
                call    fexp_cmp16
                cp      4
                jp      z,fexp_overflow     ; n8>552
                ld      hl,(MATH_N)
                ld      de,-552
                call    fexp_cmp16
                cp      1
                jp      z,fexp_underflow    ; n8<-552

                ; --- step 4: m := n8&7; n8fp := widen(|n8|)+sign -> MATH_T; -
                ; n := n8>>3 (arithmetic), overwriting MATH_N -------------
                ld      hl,(MATH_N)
                ld      a,l
                and     7
                ld      (MATH_J),a          ; m
                ld      a,h
                bit     7,a
                jr      z,fexp_n8pos
                xor     a
                sub     l
                ld      e,a
                ld      a,0
                sbc     a,h
                ld      d,a                 ; DE := |n8|
                ld      a,$80
                jr      fexp_n8widen
fexp_n8pos:
                ex      de,hl               ; DE := n8 (already >=0)
                xor     a
fexp_n8widen:
                push    af                  ; stash the sign flag across the
                                            ; widen_uint_to call (clobbers
                                            ; everything)
                ld      hl,MATH_T
                xor     a
                call    widen_uint_to       ; MATH_T := widen(|n8|), sign
                                            ; forced 0 (mirrors fp_atan's
                                            ; "xor a" widen shape)
                pop     af
                or      a
                jr      z,fexp_n8_nosign
                ld      a,$80
                ld      (MATH_T+FPNUM_SIGN),a   ; poke the real sign
fexp_n8_nosign:
                ld      hl,(MATH_N)         ; reload the ORIGINAL n8 (still
                                            ; intact -- untouched above)
                sra     h
                rr      l
                sra     h
                rr      l
                sra     h
                rr      l                   ; HL := n8>>3 (arithmetic) = n
                ld      (MATH_N),hl         ; MATH_N := n (n8 now dead)

                ; --- step 5: reduce: r := x - n8fp*EXP_C1 - n8fp*EXP_C2 -----
                ; [- EXP_TCOR[m-1] if m<>0] ----------------------------------
                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := n8fp
                ld      hl,EXP_C1
                ld      de,ARGB
                call    fat_copy18          ; ARGB := EXP_C1
                call    fp_mul              ; FAC/ARGA := n8fp*EXP_C1
                call    widen_to_arga
                ld      de,ARGB
                call    fat_copy18          ; ARGB := product1
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := x
                call    fp_sub              ; FAC/ARGA := x - product1 = r1
                call    widen_to_arga
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := r1 (temporary)

                ld      hl,MATH_T
                ld      de,ARGA
                call    fat_copy18          ; ARGA := n8fp (still intact)
                ld      hl,EXP_C2
                ld      de,ARGB
                call    fat_copy18          ; ARGB := EXP_C2
                call    fp_mul              ; FAC/ARGA := n8fp*EXP_C2
                call    widen_to_arga
                ld      de,ARGB
                call    fat_copy18          ; ARGB := product2
                ld      hl,MATH_R
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r1
                call    fp_sub              ; FAC/ARGA := r1 - product2 = r2
                ld      hl,ARGA
                call    widen_fac_to

                ld      a,(MATH_J)
                or      a
                jr      z,fexp_no_tcor
                ld      hl,ARGA
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := r2 (stash)
                ld      a,(MATH_J)
                dec     a                   ; m-1 (0-based EXP_TCOR index)
                ld      hl,EXP_TCOR
                call    fexp_tbl18addr
                ld      de,ARGB
                call    fat_copy18          ; ARGB := EXP_TCOR[m-1]
                ld      hl,MATH_R
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r2
                call    fp_sub              ; FAC/ARGA := r2 - EXP_TCOR[m-1]
                ld      hl,ARGA
                call    widen_fac_to
fexp_no_tcor:
                ; final r -> HORNER_G (=MATH_T, n8fp now dead)
                ld      hl,ARGA
                ld      de,HORNER_G
                call    fat_copy18          ; HORNER_G := r

                ; --- step 6: core: E := horner(r, EXP_COEF); w := r*E -------
                ld      hl,EXP_COEF
                call    fp_poly_horner      ; FAC/ARGA := E(r); HORNER_G (=r)
                                            ; preserved across the call
                call    widen_to_arga
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := E (persistent)
                ld      hl,HORNER_G
                ld      de,ARGA
                call    fat_copy18          ; ARGA := r (still canonical)
                ld      hl,MATH_R
                ld      de,ARGB
                call    fat_copy18          ; ARGB := E
                call    fp_mul              ; FAC/ARGA := r*E = w
                call    widen_to_arga
                ld      de,MATH_R
                call    fat_copy18          ; MATH_R := w (E retired)

                ; --- step 7: reconstruct mantissa ---------------------------
                ld      a,(MATH_J)
                or      a
                jr      z,fexp_m_zero
                ; m<>0: v := That[m]*w; p := That[m] + v
                ld      a,(MATH_J)
                ld      hl,POW8_TBL
                call    fexp_tbl18addr      ; HL := POW8_TBL + 18*m
                ld      de,ARGA
                call    fat_copy18          ; ARGA := That[m]
                ld      hl,MATH_R
                ld      de,ARGB
                call    fat_copy18          ; ARGB := w
                call    fp_mul              ; FAC/ARGA := That[m]*w = v
                call    widen_to_arga
                ld      de,ARGB
                call    fat_copy18          ; ARGB := v
                ld      a,(MATH_J)
                ld      hl,POW8_TBL
                call    fexp_tbl18addr      ; HL := POW8_TBL + 18*m (re-fetch)
                ld      de,ARGA
                call    fat_copy18          ; ARGA := That[m]
                call    fp_add              ; FAC/ARGA := That[m]+v = p
                call    widen_to_arga
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := p (x long dead)
                jr      fexp_scale
fexp_m_zero:
                ; m==0: p := 1.0 + w
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGA := 1.0
                ld      hl,MATH_R
                ld      de,ARGB
                call    fat_copy18          ; ARGB := w
                call    fp_add              ; FAC/ARGA := 1.0+w = p
                call    widen_to_arga
                ld      de,MATH_A
                call    fat_copy18          ; MATH_A := p

fexp_scale:
                ; --- step 8: FAC := p rescaled by 10^n. A power-of-ten -----
                ; rescale is a PURE DEXP SHIFT, no digit multiply needed --
                ; the FPNUM digit array is magnitude-independent, exactly
                ; fp_sqrt's own SQRT_K rescale precedent ("dexp+=SQRT_K --
                ; exact, no digit shift"). Building a literal 10^n FPNUM
                ; record and going through fp_mul was tried FIRST and found
                ; LIVE (this slice's own hardware gate) to mis-overflow:
                ; fp_mul's own preExp PRE-check (dexpA+dexpB, evaluated
                ; BEFORE normalisation, spec §10.2 "even when the normalised
                ; result would fit") is a full unit too strict whenever p's
                ; OWN dexp is 0 (p<1, e.g. the m=0 reconstruction with a
                ; negative r) -- EXP(145.062), a sim-PROVEN exact anchor,
                ; spuriously overflowed this way (n=63, p<1 -> dexp(p)=0,
                ; scale record dexp=64, preExp=0+64=64>63, abort -- even
                ; though the TRUE final dexp, p's dexp(0)+n(63)=63, is
                ; comfortably in bounds). Fixed by adjusting MATH_A's own
                ; dexp field directly (exact, no precision lost) and then
                ; routing through fp_add with a zero ARGB: fp_add has NO
                ; pre-check (its own header: "only genuine result overflow
                ; observed" -- round_and_finalize's OWN post-op bound check,
                ; on the TRUE resulting dexp, is what catches a real
                ; overflow/underflow here), and fp_add is already in the
                ; imported resident-ABI surface -- no new relocation.
                ;
                ; SECOND bug, found the SAME way (this slice's own hardware
                ; gate, negative-x rows): a "canonical" zero (widen_uint_to
                ; with magnitude 0, which always sets dexp:=0) is NOT a safe
                ; ARGB here -- fp_add's own alignment ADOPTS WHICHEVER
                ; operand has the LARGER dexp (basic/float-arith.asm fp_add:
                ; "dexpA<dexpB -> shift ARGA_DIG right, adopt dexpB"), so
                ; whenever the rescaled p's true dexp is NEGATIVE (any
                ; sufficiently negative x), it looks "smaller" than the
                ; zero's dexp=0 and gets WRONGLY shifted right + rebased to
                ; dexp=0 -- corrupting the very value this step exists to
                ; preserve exactly (caught via EXP(-10)/(-20)/(-147.3)
                ; printing truncated/misplaced digits). Fix: build ARGB's
                ; zero with its dexp field forced to MATCH ARGA's (rescaled)
                ; dexp exactly, so the alignment diff is always 0 (a true
                ; no-op) regardless of sign -- round_and_finalize then
                ; bound-checks ARGA's OWN unaltered dexp.
                ld      hl,(MATH_A+FPNUM_DEXP)
                ld      de,(MATH_N)         ; n
                add     hl,de
                ld      (MATH_A+FPNUM_DEXP),hl  ; MATH_A's dexp += n (exact)
                ld      hl,MATH_A
                ld      de,ARGA
                call    fat_copy18          ; ARGA := p, rescaled
                ld      hl,(ARGA+FPNUM_DEXP)    ; = the rescaled p's own dexp
                ld      de,ARGB
                xor     a
                ld      (de),a              ; ARGB sign := 0
                inc     de
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a              ; ARGB dexp := SAME as ARGA (not
                                            ; the canonical-zero 0 -- see
                                            ; above); Z80 has no `ld (de),l`/
                                            ; `ld (de),h` -- route through A
                inc     de
                xor     a
                ld      b,15                ; dig[0..13] + guard, all zero
fexp_scale_zero:
                ld      (de),a
                inc     de
                djnz    fexp_scale_zero
                jp      fp_add              ; tail: FAC := p_rescaled + 0
                                            ; (dexp-matched zero -> alignment
                                            ; is a no-op; round_and_finalize
                                            ; disposes a genuine true-
                                            ; magnitude overflow/underflow on
                                            ; the TRUE dexp). COMPUTE-ONLY --
                                            ; evmc_exp sets FACTYP/DE.
fexp_overflow:
                ld      a,1
                call    penderr_set
                xor     a
                ld      (FAC),a
                ret
; ⛔ UNDERFLOW IS SILENT ON PURPOSE, AND IT IS NOT THE SAME AS OVERFLOW HERE.
; The true answer underflows to 0 and zerobas returns it; both references throw
; `Overflow` instead, which docs/spec-basic-mathpack-slice2.md §12.9 records as
; a full disposition BUG in the reference. `math-acceptance` encodes that
; decision -- its truth oracle asserts `exp(-1000)` is 0, and `10^-70.5` is
; scored on OURS only.
;
; 🔴 CORRECTION 2026-09-05 (D-EXPBAND) -- THE PARAGRAPH ABOVE IS RIGHT ABOUT
; THE DECISION AND WRONG ABOUT ITS EXTENT, and the sentence that misleads is
; "both references throw `Overflow` instead". They do not, except inside a BAND:
;
;     result >= 1E-64        value        refs == ours
;     [1E-65, 1E-64)         0            refs == ours   <- NOT a deviation
;     [1E-129, 1E-65)        Overflow     ours 0         <- the deviation
;     < 1E-129               0            refs == ours   <- NOT a deviation
;
; x in (-297.033, -149.668] only, both edges landing exactly on a decade and
; bracketed to <0.02 in x on BOTH references -- a band 64 decades wide. Every
; sample anyone had taken (`EXP(-200)`, the `10^-70.5` row = EXP(-162)) happened
; to fall inside it, so a half-line read as obvious.
; 🎯 AND `exp(-1000)`, THE ANCHOR THE PARAGRAPH ABOVE CITES AS PROOF WE
; DEVIATE, IS A ROW WHERE THE REFERENCES RETURN 0 -- it agrees with us. It still
; belongs in the gate (it pins OUR value), but it never witnessed a deviation
; [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The four band edges are
; now gate rows in probes/basic/basic_probe_math_conv.py.
; ⚠️ THE DECISION IS UNCHANGED AND STRENGTHENED: 0 is the references' OWN answer
; on both sides of their band, so returning 0 throughout is the consistent
; reading, not a unilateral one. D-EXPNEG (below) stays reverted.
;
; 🔴 D-EXPNEG (2026-08-30) FOLDED THIS INTO `fexp_overflow` to match the
; references, AND WAS REVERTED. Measuring the references is not the same as
; checking whether the divergence was already DECIDED; here it was, fifteen days
; earlier (docs/spec-basic-ngram14.md §7).
fexp_underflow:
                xor     a
                ld      (FAC),a
                ret
