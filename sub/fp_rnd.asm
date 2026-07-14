; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; fp_rnd -- math pack slice 2e: RND(x) (docs/spec-basic-mathpack-slice2.md
; §15). The LAST slice-2 function, and categorically different from every
; other tenant in this file: RND is not a bounded-deviation approximation, it
; is a pseudo-random generator whose whole contract IS sequence
; reproducibility, so the target is bit-for-bit reference-IDENTITY (like the
; slice-2c `^` positive-int path), not a documented-deviation envelope. That
; is both ACHIEVABLE (the recurrence is exact integer arithmetic mod 1e14 --
; no coefficients-in-ROM wall) and REQUIRED (a program that reseeds with
; RND(-k) and reads the sequence must get the SAME numbers as the reference).
;
; THE MODEL (§15.1, characterized black-box VG-8020 2026-07-14, 19 anchors +
; a 20000-state sweep proven bit-for-bit in tools/sim_math_chain.py
; rnd_validate -- don't re-probe): state S is a 14-digit decimal integer in
; [0,1e14); advance(S) := (A*S + C) mod 1e14, A=21132486540519,
; C=14389820420821, S0=40649651372358 (the power-on/NEW/CLEAR/RUN reset
; seed, set by clear_vars, basic/vars.asm). RND(x>0): S:=advance(S), return
; S*1e-14 (the ARGUMENT VALUE IS IGNORED -- any positive x steps once).
; RND(0): return S*1e-14, NO advance (repeats the last value). RND(x<0):
; S:=advance(mant14), return S*1e-14, where mant14 is the WIDENED ARGA's own
; 14 mantissa-digit slots read as a 14-digit integer (dexp/sign ignored --
; this is exactly why RND(-1)=RND(-0.001)=RND(-1E9): same mantissa
; 1.000...). Always returns a DOUBLE (FACTYP:=8, this stub's own job, not
; this tenant's -- see basic/expr.asm evmc_rnd). No domain errors: total
; over every x.
;
; WHY NOT fp_mul (§15.2). advance needs the LOW 14 digits of A*S+C; A*S is
; ~2e27, and fp_mul produces the HIGH 14 significant digits of a product --
; exactly the digits RND needs DISCARDED. So this tenant does NOT use ANY
; resident fp op (no fp_add/fp_sub/fp_mul/fp_div/fp_poly_horner) -- it is a
; dedicated 14-digit BCD schoolbook multiply-add, little-endian (index
; 0=units), mirroring tools/sim_math_chain.py's rnd_advance_bcd EXACTLY
; (same loop structure, same drop-the-overflow-digit rule, same final
; ripple-carry +C) -- proven equal to the exact recurrence over the 19
; captured anchors AND a 20000-state sweep before this file was written.
; Every OTHER digit array in this codebase (ARGA_DIG, RND_STATE below) is
; MSD-first (dig[0] = the most significant digit), so the multiply-add's own
; little-endian working copies (RND_LE/RND_ACCLE) are produced/consumed via
; a plain byte-order reversal (rnd_reverse14) at the boundary -- this keeps
; the core loop a literal transcription of the already-proven sim algorithm
; (lowest bug risk) while every OTHER cell in this file stays in the
; codebase's own MSD-first convention.
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), the 9th and LAST page-1
; tenant, appended to sub_p1_table after fp_tan: `jp fp_rnd` at
; SUBROM_IDX_RND=9. Dispatched from evmc_rnd (basic/expr.asm) via
; SUBROM_ENTRY_BASE_P1+3*SUBROM_IDX_RND, the evmc_atn shape (total function,
; no domain check). COMPUTE-ONLY: leaves FAC correct but does NOT touch
; FACTYP/DE, exactly like every prior tenant -- evmc_rnd sets FACTYP:=8 +
; refreshes DE after a successful return. Self-contained: the resident-ABI
; surface touched is a SUBSET of what fp_sqrt/fp_atan/... already use
; (dig15_iszero + arga_pack_fac ONLY -- no fp_add/fp_sub/fp_mul/fp_div, no
; widen_fac_to/widen_uint_to, since RND never widens an fp record through
; the resident ops) -- no new page-0 relocation, closure-check clean.
;
; RAM (§15.3/§15.4). RND_SEED (basic/sysvars.inc) is the ONLY persistent
; claim -- the 14-digit state must survive arbitrary statements between
; calls, so it cannot reuse transient scratch; it lives in the unused TAIL
; SLACK of the SUB_INT_RAM trampoline reservation ($F142..$F148), guarded by
; a build-time ASSERT in basic/subromcall.asm (sub_int_template_end -
; sub_int_template <= RND_SEED - SUB_INT_RAM) so future trampoline growth
; that would collide FAILS THE BUILD instead of silently overlapping. Every
; OTHER cell this tenant uses (RND_STATE/RND_LE/RND_ACCLE/RND_I/RND_J/
; RND_IJ/RND_AJ/RND_CARRY/RND_K, basic/sysvars.inc) is a TRANSIENT alias
; over already-justified dead scratch (MATH_A/MATH_T/MULPROD) -- no new RAM
; claim, safe by the same "one factor at a time" argument every math tenant
; already carries, made STRONGER here since fp_rnd calls no resident fp op
; that could itself recurse into this scratch (see the WHY NOT fp_mul note
; above).
;
; Resident-ABI surface: dig15_iszero, arga_pack_fac (sub/basic-resident-
; abi.inc) + RAM (ARGA/RND_SEED/RND_STATE/RND_LE/RND_ACCLE/RND_I/RND_J/
; RND_IJ/RND_AJ/RND_CARRY/RND_K/FAC). Clobbers A, B, C, D, E, H, L.
;
; PROVENANCE: A/C/S0 are constants recovered PURELY BLACK-BOX (observe the
; VG-8020's RND output, fit the LCG recurrence -- scratchpad/char_rnd*.py +
; tools/sim_math_chain.py) -- admissible per §4.2, the same footing as the
; division characterization; never MSX ROM disassembly (PROVENANCE.md).
; =============================================================================

; --- rnd_digmul: B=d1 (0-9), C=d2 (0-9) -> A := d1*d2 (0..81, fits a byte). -
; A plain repeated-add loop -- digits are single BCD values 0-9, so up to 9
; iterations is simplest and fast enough (RND is not a hot loop). Clobbers
; A, B.
rnd_digmul:
                ld      a,b
                or      a
                jr      z,rdm_zero
                xor     a
rdm_lp:
                add     a,c
                djnz    rdm_lp
                ret
rdm_zero:
                xor     a
                ret

; --- rnd_reverse14: HL=src base (14B), DE=dst base (14B, a DISTINCT --------
; buffer -- this does not support reversing a region in place). dst[i] :=
; src[13-i], i=0..13: a byte-order reversal, self-inverse, used BOTH ways
; (an MSD-first digit array -> its little-endian mirror before the
; multiply-add, and the little-endian result -> back to MSD-first after).
; Clobbers A, B, HL, DE.
rnd_reverse14:
                ld      a,l
                add     a,13
                ld      l,a
                ld      a,h
                adc     a,0
                ld      h,a                 ; HL := src+13 (descending read
                                            ; pointer; DE stays the ascending
                                            ; write pointer, dst+0..dst+13)
                ld      b,14
rr14_lp:
                ld      a,(hl)
                ld      (de),a
                dec     hl
                inc     de
                djnz    rr14_lp
                ret

; --- rnd_unpack_seed: RND_SEED (7B packed BCD, 2 digits/byte, MSD-first) ---
; -> RND_STATE (14B unpacked digit array, values 0-9, MSD-first). Same
; nibble convention as arga_pack_fac's own FAC-mantissa packing, just
; unpacked instead of packed. Clobbers A, B, C, H, L, D, E.
rnd_unpack_seed:
                ld      hl,RND_SEED
                ld      de,RND_STATE
                ld      b,7
runp_lp:
                ld      a,(hl)
                ld      c,a
                and     $F0
                rrca
                rrca
                rrca
                rrca                        ; A := high nibble (first digit)
                ld      (de),a
                inc     de
                ld      a,c
                and     $0F                 ; A := low nibble (second digit)
                ld      (de),a
                inc     de
                inc     hl
                djnz    runp_lp
                ret

; --- rnd_pack_seed: RND_STATE (14B unpacked digit array, MSD-first) -> -----
; RND_SEED (7B packed BCD, 2 digits/byte, MSD-first). The inverse of
; rnd_unpack_seed above; same nibble-pack loop shape as arga_pack_fac's own
; mantissa packer. Clobbers A, B, H, L, D, E.
rnd_pack_seed:
                ld      hl,RND_STATE
                ld      de,RND_SEED
                ld      b,7
rpk_lp:
                ld      a,(hl)
                add     a,a
                add     a,a
                add     a,a
                add     a,a                 ; A := digit0<<4
                inc     hl
                or      (hl)                ; | digit1
                inc     hl
                ld      (de),a
                inc     de
                djnz    rpk_lp
                ret

; --- rnd_advance_bcd_le: RND_LE (14B unpacked digit array, LITTLE-ENDIAN, --
; index 0=units) = S -> RND_ACCLE (14B, LE) := (S*RND_A_LE + RND_C_LE) mod
; 1e14, the 14-digit BCD schoolbook multiply-add (§15.2). Mirrors tools/
; sim_math_chain.py's rnd_advance_bcd EXACTLY: for each multiplier digit
; A[j] (j=0..13, weight 10^j), multiply the WHOLE 14-digit S by that single
; digit with a running carry, adding into the accumulator SHIFTED by j
; places; any partial-product digit that would land at accumulator index
; >=14 is dropped (mod 1e14 -- it cannot affect the low-14-digit result).
; Then C is added with a 14-digit BCD ripple-carry add, the final carry (out
; of index 13) dropped the same way. Uses RND_I/RND_J/RND_IJ/RND_AJ/
; RND_CARRY (basic/sysvars.inc) as loop-index scratch, since the nested loop
; needs more live state than Z80's register file holds across the
; rnd_digmul call. Clobbers A, B, C, D, E, H, L.
rnd_advance_bcd_le:
                ; acc := 0
                ld      hl,RND_ACCLE
                ld      b,14
                xor     a
rabl_zero:
                ld      (hl),a
                inc     hl
                djnz    rabl_zero
                ; for j := 0 to 13
                xor     a
                ld      (RND_J),a
rabl_jloop:
                ld      a,(RND_J)
                cp      14
                jr      nc,rabl_jdone
                ld      hl,RND_A_LE
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)              ; A[j]
                or      a
                jr      z,rabl_jnext        ; A[j]=0 -> no contribution, skip
                ld      (RND_AJ),a
                xor     a
                ld      (RND_CARRY),a
                xor     a
                ld      (RND_I),a
                ; for i := 0 to 13-j (i.e. while i+j<14)
rabl_iloop:
                ld      a,(RND_I)
                ld      hl,RND_J
                add     a,(hl)              ; A := i+j
                cp      14
                jr      nc,rabl_idone       ; i+j>=14 -> the rest falls off
                                            ; the top, dropped (mod 1e14)
                ld      (RND_IJ),a          ; stash the target acc index
                ld      a,(RND_I)
                ld      hl,RND_LE
                ld      e,a
                ld      d,0
                add     hl,de
                ld      b,(hl)              ; B := S_le[i]
                ld      a,(RND_AJ)
                ld      c,a                 ; C := A_le[j]
                call    rnd_digmul          ; A := S[i]*A[j] (0..81)
                ld      b,a                 ; B := product, stashed across
                                            ; the acc/carry reads below
                ld      a,(RND_IJ)
                ld      hl,RND_ACCLE
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> acc[i+j]
                ld      a,b
                add     a,(hl)              ; + acc[i+j]
                ld      c,a
                ld      a,(RND_CARRY)
                add     a,c                 ; A := p = product+acc[ij]+carry
                                            ; (<=81+9+9=99, fits a byte)
                ; digit := p mod 10, carry := p div 10 (repeated-subtract;
                ; p<=99, at most 9 iterations). HL still -> acc[i+j] (this
                ; loop only touches A/B).
                ld      b,0
rabl_dm_lp:
                cp      10
                jr      c,rabl_dm_done
                sub     10
                inc     b
                jr      rabl_dm_lp
rabl_dm_done:
                ld      (hl),a              ; acc[i+j] := digit
                ld      a,b
                ld      (RND_CARRY),a       ; carry := carry-out
                ld      a,(RND_I)
                inc     a
                ld      (RND_I),a
                jr      rabl_iloop
rabl_idone:                                 ; carry beyond position 13 for
                                            ; this j is dropped -- nothing
                                            ; to do
rabl_jnext:
                ld      a,(RND_J)
                inc     a
                ld      (RND_J),a
                jr      rabl_jloop
rabl_jdone:
                ; acc += C: 14-digit ripple-carry BCD add (LE, index 0
                ; upward -- the low-to-high carry-propagation direction);
                ; the final carry out of index 13 is dropped (mod 1e14).
                xor     a
                ld      (RND_CARRY),a
                xor     a
                ld      (RND_I),a
rabl_cadd_lp:
                ld      a,(RND_I)
                cp      14
                jr      nc,rabl_cadd_done
                ld      hl,RND_ACCLE
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> acc[i]
                ld      b,(hl)              ; B := acc[i]
                push    hl                  ; keep acc[i]'s address for the
                                            ; store below (the C_LE lookup
                                            ; below needs HL as scratch)
                ld      a,(RND_I)
                ld      hl,RND_C_LE
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)              ; A := C_le[i]
                add     a,b                 ; + acc[i]
                ld      c,a
                ld      a,(RND_CARRY)
                add     a,c                 ; A := acc[i]+C[i]+carry (<=19)
                ld      b,0
                cp      10
                jr      c,rabl_ca_nc
                sub     10
                ld      b,1
rabl_ca_nc:
                pop     hl                  ; HL -> acc[i] (restored)
                ld      (hl),a
                ld      a,b
                ld      (RND_CARRY),a
                ld      a,(RND_I)
                inc     a
                ld      (RND_I),a
                jr      rabl_cadd_lp
rabl_cadd_done:
                ret

; --- fp_rnd: ARGA (widened arg x) -> FAC (double, S*1e-14 in [0,1)) --------
; (§15.4). Total function, no domain check -- every path ends in a plain
; `ret` via the fsc_pack_arga tail (fp_sin.asm, SAME assembly unit -- sub.asm
; includes fp_sin.asm before this file, §15.4/precedent).
fp_rnd:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      z,frnd_zero_arg     ; RND(0): no advance, output the
                                            ; CURRENT seed as-is
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      nz,frnd_reseed      ; RND(x<0): reseed from mant14
                ; RND(x>0): the argument VALUE is ignored -- advance from
                ; the CURRENT RND_SEED (§15.1)
                call    rnd_unpack_seed     ; RND_STATE(MSD,14B) := unpack(RND_SEED)
                ld      hl,RND_STATE
                jr      frnd_do_advance
frnd_reseed:
                ; mant14 = ARGA's own 14 digit slots (already an unpacked
                ; MSD-first array, exactly RND_STATE's own convention) --
                ; dexp/sign are ignored per §15.1, so no unpack step needed,
                ; use ARGA's digits directly as the advance input.
                ld      hl,ARGA+FPNUM_DIG
frnd_do_advance:
                ; HL -> the 14-byte MSD-first S input for this advance
                ; (either RND_STATE, just unpacked above, or ARGA's own
                ; digits for a reseed)
                ld      de,RND_LE
                call    rnd_reverse14       ; RND_LE(LE,14B) := reverse(S)
                call    rnd_advance_bcd_le  ; RND_ACCLE(LE,14B) :=
                                            ; (S*A+C) mod 1e14
                ld      hl,RND_ACCLE
                ld      de,RND_STATE
                call    rnd_reverse14       ; RND_STATE(MSD,14B) :=
                                            ; reverse(RND_ACCLE) = new state
                call    rnd_pack_seed       ; RND_SEED(7B packed) :=
                                            ; pack(RND_STATE) -- persists
                jr      frnd_output
frnd_zero_arg:
                call    rnd_unpack_seed     ; RND_STATE(MSD,14B) :=
                                            ; unpack(RND_SEED), NO advance
                ; falls through to frnd_output with RND_STATE = the
                ; current (unchanged) seed

; --- frnd_output: RND_STATE (14-digit MSD-first unpacked state S) -> ARGA --
; -> FAC, the normalised double S*1e-14 (§15.4 step 3). Left-shifts out
; leading zeros: if the state has k leading zero digits, the mantissa is
; digits d[k..13] left-justified (padded low with k zeros), dexp := -k
; (this codebase's own FPNUM convention: value = mantissa(d0.d1d2...d13) *
; 10^(dexp-1), so k leading zeros -> value = 0.00..0(k)d[k]... =
; (d[k].d[k+1]...)*10^(-1-k) = mantissa'*10^(dexp-1) with dexp=-k -- verified
; against tools/sim_math_chain.py rnd_output's own worked example before
; this code was written). k=14 (the state is all-zero, S=0 -- astronomically
; rare but valid) is guarded directly: FAC:=0, skipping arga_pack_fac
; entirely (its own precondition is "ARGA_DIG isn't the all-zero case" --
; the recurring 2c/2d/2e gotcha, don't skip the guard).
frnd_output:
                ld      hl,RND_STATE
                ld      b,14
                xor     a
                ld      (RND_K),a
frnd_k_lp:
                ld      a,(hl)
                or      a
                jr      nz,frnd_k_found
                inc     hl
                ld      a,(RND_K)
                inc     a
                ld      (RND_K),a
                djnz    frnd_k_lp
                ; all 14 digits were zero: S=0 -> FAC:=0 directly
                xor     a
                ld      (FAC),a
                ret
frnd_k_found:
                ; HL -> RND_STATE+k (the scan above stopped exactly here,
                ; without advancing past the first nonzero digit); RND_K=k.
                ld      de,ARGA+FPNUM_DIG
                ld      a,14
                ld      c,a
                ld      a,(RND_K)
                ld      b,a                 ; B := k
                ld      a,c
                sub     b                   ; A := 14-k (the copy count)
                ld      c,a
                ld      b,0                 ; BC := 14-k
                ldir                        ; ARGA_DIG[0..13-k] :=
                                            ; RND_STATE[k..13]; DE now ->
                                            ; ARGA_DIG+(14-k)
                ; zero-pad the remaining k mantissa digits + the guard byte
                ; dig[14] (k+1 bytes total; DE is already positioned right
                ; after the copied span)
                ld      a,(RND_K)
                ld      b,a
                inc     b                   ; B := k+1
                xor     a
frnd_zpad:
                ld      (de),a
                inc     de
                djnz    frnd_zpad
                xor     a
                ld      (ARGA+FPNUM_SIGN),a ; sign := 0 (RND's range is
                                            ; [0,1), always non-negative)
                ld      a,(RND_K)
                or      a
                jr      z,frnd_dexp_zero
                neg                         ; A := -k (two's-complement byte,
                                            ; exact for 1<=k<=13)
                ld      l,a
                ld      h,$FF               ; sign-extend to a 16-bit dexp
                jr      frnd_dexp_store
frnd_dexp_zero:
                ld      hl,0
frnd_dexp_store:
                ld      (ARGA+FPNUM_DEXP),hl
                jp      fsc_pack_arga       ; tail: dig15_iszero-guarded
                                            ; pack -> FAC (fp_sin.asm, same
                                            ; assembly unit, §15.4)

; --- Page-1 constants A/C, little-endian digit arrays (index 0=units) -----
; (§15.1/§15.2). Black-box recovered from the VG-8020 (scratchpad/
; char_rnd*.py, fit against the LCG recurrence) + proven against 19 captured
; anchors + a 20000-state sweep in tools/sim_math_chain.py (RND_A/RND_C,
; commit bc6417b) BEFORE this file was written. Stored pre-reversed
; (little-endian) as literal data -- unlike RND_STATE/RND_SEED (which are
; runtime values, reversed via rnd_reverse14 at the multiply-add boundary),
; these are fixed at assembly time, so writing them already-reversed avoids
; a runtime reversal for every advance() call.
; A = 21132486540519 -- MSD-first digits 2,1,1,3,2,4,8,6,5,4,0,5,1,9
RND_A_LE:       db      9,1,5,0,4,5,6,8,4,2,3,1,1,2
; C = 14389820420821 -- MSD-first digits 1,4,3,8,9,8,2,0,4,2,0,8,2,1
RND_C_LE:       db      1,2,8,0,2,4,0,2,8,9,8,3,4,1
