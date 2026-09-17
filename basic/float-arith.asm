; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; float-arith.asm — math float pack, slice F2: arithmetic + relationals +
; signed-int migration (repack build only — the whole file is included only
; inside basic/main.asm. docs/spec-basic-float-core.md
; §10 is the oracle-pinned behavioural contract this file implements; §9.4 is
; the F1 runtime protocol (FAC/FACTYP) it extends. No disassembly anywhere —
; every algorithm below is own-design over the MSX2 TH BCD number FORMAT
; (basic/float.asm's header); the pinned VALUES (rounding ties, overflow/
; underflow walls, conversion-domain boundaries, signed \/MOD results) come
; from probes/basic/basic_probe_float_arith.py (VG-8020), distilled into the
; spec.
;
; Representation used by the arithmetic core (own design, deliberately NOT
; the packed-BCD FAC/TKDIG shape — see sysvars.inc's FPNUM_* comment): a
; "digit array" is 15 bytes, one decimal digit VALUE (0-9) per byte, MSD
; first — dig[0..13] are the 14 significant mantissa digits, dig[14] is a
; guard digit carried through alignment/multiply/divide for half-up rounding
; (spec §10.2). An FPNUM record is [sign:1][dexp:2 signed][dig:15] (18 bytes,
; FPNUM_SIGN/FPNUM_DEXP/FPNUM_DIG field offsets, sysvars.inc). Working over
; plain one-digit-per-byte arrays (rather than packed nibbles) lets add/sub/
; mul/div be expressed as ordinary byte arithmetic, with Z80 LDIR/LDDR doing
; every alignment/normalisation shift as a straight memmove.
;
; ARGA doubles as the answer: every op (fp_add/fp_sub/fp_mul/fp_div) ends by
; leaving its result in ARGA (sign/dexp/dig), then round_and_finalize packs
; ARGA into FAC (always DOUBLE, spec §10.1: "single precision is a storage
; format only") + sets FACTYP=8 + DE := a SILENT flt_to_int16 conversion of
; the result (basic/float.asm), so unwired int consumers keep working.
;
; Runtime errors (spec §10.2 D-F2-1): FPERR (sysvars.inc) is 0/1(overflow)/
; 2(division-by-zero). Every op SETS the flag and returns a defined value (DE
; = 0, FAC left as a packed zero) — no mid-expression unwind, matching the
; existing ev_f_err / type_mismatch_set convention (str-engine.asm). The
; statement-level abort (basic/interp.asm fp_runtime_error) is wired in by
; the drivers that check FPERR after eval()/ev_rel, mirroring D-2's TMISMATCH
; pattern exactly.

; =============================================================================
; cmp16_bits -- RELOCATED HERE (page-0 low region) in the repack build
; =============================================================================
; Signed 16-bit compare HL(lhs) vs DE(rhs) -> A = 1(lhs<rhs)/2(equal)/4(lhs>rhs).
; A pure leaf (no calls); clobbers A, HL, flags (DE preserved). Defined HERE
; rather than in basic/expr.asm where it started, so it lands in the page-0 low
; region ($2812-$3FFF) rather than page 1 ($4000+).
;
; WHY (subrom-mathpack migration, 2026-07-13): the resident float core
; (fp_mul/fp_cmp + the fp_add/fp_sub/fp_div exponent compares) calls cmp16_bits,
; AND that core now runs as the fp_sqrt PAGE-1 sub-ROM tenant (sub/fp_sqrt.asm).
; While a page-1 tenant runs, main-ROM page 1 is switched OUT (sub-ROM mapped in
; its place), so a `call cmp16_bits` to a page-1 address would execute sub-ROM
; garbage -> spurious Overflow (caught live: SQR(x) returned FPERR=1 for every
; x>=0 until this move). cmp16_bits is the ONE transitive page-1 dependency of
; the float core that the docs/spec-basic-subrom-mathpack.md §4 leaf-audit's
; 9-routine list missed (it enumerated the DIRECT callees, not their callees).
; Relocated to page 0 it is reachable from BOTH the normal page-1 interpreter
; callers (ev_rel etc. -- page 0 is always mapped when they run) and the page-1
; tenant's page-0-resident float routines.
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

; =============================================================================
; div10 -- RELOCATED HERE (page-0 low region) in the repack build
; =============================================================================
; HL = HL/10, A = remainder (0..9). Shift-and-subtract (standard binary
; divide); a pure leaf (no calls). Clobbers A, B, HL. Defined HERE rather than in
; basic/print.asm where it started, so it lands in the page-0 low region
; ($2812-$3FFF) rather than page 1 ($4000+).
;
; WHY (subrom-mathpack migration, 2026-07-13): widen_uint_to (below, page-0
; resident) calls div10, AND widen_uint_to runs inside the fp_sqrt PAGE-1
; sub-ROM tenant (sub/fp_sqrt.asm). While a page-1 tenant runs, main-ROM
; page 1 is switched OUT (sub-ROM mapped in its place), so `call div10` to the
; print.asm page-1 address ($5233) executed the sub-ROM's $FF pad bytes =
; `rst $38` -> a stack-neutral rst38<->keyint loop that wedged the machine
; with no output and no prompt (caught live 2026-07-13 with the openMSX
; z80.acceptIRQ probe + stack capture: every SQR(x>=0) hung; PC pinned in
; C-BIOS int_end with the tenant's CALSLT frames still on the stack). div10 is
; the SECOND transitive page-1 dependency of the float core after cmp16_bits
; (above) -- found by the full-closure re-audit (114 labels from the 9
; resident-ABI roots + the flt_to_int16 tail) that the cmp16_bits fix
; prompted; that audit shows these two are the ONLY page-1 escapes. Relocated
; to page 0 it is reachable from BOTH the normal page-1 caller (dgt_push in
; basic/print.asm, which D-DGTPUSH collapsed the three of them into -- page 0 is
; always mapped when it runs; detok.inc keeps a separate sub-side copy) and the
; page-1 tenant's page-0-resident float routines.
; (its copy stays in print.asm, page 1).
div10:
                xor     a
                ld      b,16
d10_lp:
                add     hl,hl               ; shift dividend left, into quotient
                rla                         ; A = running remainder<<1 | carry
                cp      10
                jr      c,d10_skip
                sub     10
                inc     l                   ; set quotient bit
d10_skip:
                djnz    d10_lp
                ret

; =============================================================================
; Low-level digit-array helpers (own design)
; =============================================================================

; --- ret_de0: DE := 0, then return -- the shared zero-result tail -----------
; `ld de,0` + `ret` stood at FOURTEEN main-ROM sites, 4 B each, as the "no value /
; zero" return. A `jp` here is 3 B: -14 B of sites against 4 B of helper.
; 🎯 SITED IN THE LOW REGION ON PURPOSE. Eight of the fourteen users are page-1
; files and page 1 is the ceiling every slice fights, so the helper pays its 4 B
; out of the other half of the budget. The two regions share one total but have
; SEPARATE ceilings, which is what makes the placement worth a sentence.
; ⚠️ FLAG-TRANSPARENT, and that is load-bearing: neither `ld de,0` nor `jp` writes
; F, so a caller returning CF/Z set BEFORE the old `ld de,0` still returns it.
; Nothing that touches flags may be added here.
ret_de0:
                ld      de,0
                ret

; --- dig15_zero15: zero-fill the 15-byte digit array at (HL). HL preserved. --
; Clobbers A, B.
dig15_zero15:
                push    hl
                ld      b,15
                call    zero_fill
                pop     hl
                ret

; --- zero_fill: HL=ptr, B=count -> zero B bytes at (HL). HL NOT preserved --
; (ends just past the zeroed span; dig15_zero15 above wraps it with a push/
; pop for its own HL-preserving contract). Shared by dig15_zero15 and every
; other digit-array/scratch zero-init in this file. Clobbers A, B, HL.
zero_fill:
                xor     a
zf_lp:
                ld      (hl),a
                inc     hl
                djnz    zf_lp
                ret

; --- dig15_iszero: HL -> 15-byte digit array. ZF set iff all 15 are 0. -------
; HL preserved. Clobbers A, B.
dig15_iszero:
                push    hl
                ld      b,15
diz_lp:
                ld      a,(hl)
                or      a
                jr      nz,diz_done
                inc     hl
                djnz    diz_lp
diz_done:
                pop     hl
                ret

; --- dig15_cmp: HL=ptrA(idx0), DE=ptrB(idx0), B=digit count (caller sets — --
; 15 for a full array incl. guard, 14 for fp_cmp's significant-digits-only
; compare), MSD first. out: A = 1 (A<B) / 2 (A==B) / 4 (A>B) — same
; convention as expr.asm's cmp16_bits. Clobbers A, B, C, HL, DE.
dig15_cmp:
dcm_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                cp      c
                jr      c,dcm_lt
                jr      nz,dcm_gt
                inc     hl
                inc     de
                djnz    dcm_lp
                ld      a,2
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to c16_lt,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
dcm_lt          equ     c16_lt
dcm_gt:
                ld      a,4
                ret

; --- dig15_add_inplace: ARGA_DIG += ARGB_DIG, digit-wise decimal add, ------
; processing index 14 (LSD) up to index 0 (MSD) so carry propagates toward
; the significant end. out: CF set iff a carry propagates OUT of position 0
; (ARGA_DIG[0] already holds that position's correct low digit; the caller
; renormalises). Clobbers A, B, C, HL, DE.
dig15_add_inplace:
                ld      hl,ARGA+FPNUM_DIG+14
                ld      de,ARGB+FPNUM_DIG+14
                ld      b,15
                or      a                   ; CF=0: no carry into the LSD
dai_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                adc     a,c
                cp      10
                jr      c,dai_nc
                sub     10
                scf
                jr      dai_st
dai_nc:
                or      a
dai_st:
                ld      (hl),a
                dec     hl
                dec     de
                djnz    dai_lp
                ret

; --- dig15_sub_inplace: (HL@idx14) -= (DE@idx14), 15-byte arrays, in place --
; into the HL (minuend) array. Assumes minuend>=subtrahend (no final borrow;
; callers pre-compare via dig15_cmp). Clobbers A, B, C, HL, DE.
dig15_sub_inplace:
                ld      b,15
                or      a                   ; CF=0: no borrow into the LSD
dsi_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                sbc     a,c
                jr      nc,dsi_nb
                add     a,10
                scf
                jr      dsi_st
dsi_nb:
                or      a
dsi_st:
                ld      (hl),a
                dec     hl
                dec     de
                djnz    dsi_lp
                ret

; --- dig15_shr: shift the 15-byte digit array at (HL) right by ------------
; (FP_SHIFTAMT) positions, zero-filling the vacated low end; a digit shifted
; beyond index 14 is dropped (spec §10.2: "a digit beyond the guard is
; dropped"). HL NOT preserved (no caller needs it after — every call site
; reloads HL fresh); ends pointing past the zero-filled span. Clobbers A,
; B, C, D, E, H, L.
dig15_shr:
                ld      a,(FP_SHIFTAMT)
                or      a
                ret     z
                cp      15
                jr      nc,dshr_allzero
                push    hl
                ld      c,a
                ld      d,h
                ld      e,l
                ld      a,e
                add     a,14
                ld      e,a                 ; DE = base+14 (dst end)
                ld      a,l
                add     a,14
                sub     c
                ld      l,a                 ; HL = base+(14-shift) (src end)
                ld      a,15
                sub     c
                ld      b,0
                ld      c,a                 ; BC = 15-shift
                lddr
                pop     hl                  ; HL = base (needed to start the zero-fill;
                                            ; no caller relies on HL after this routine,
                                            ; so no final restore is needed before ret)
                ld      a,(FP_SHIFTAMT)
                ld      b,a
                jr      zero_fill           ; tail call
dshr_allzero:
                jp      dig15_zero15

; --- dig15_shl: shift the 15-byte digit array at (HL) left by -------------
; (FP_SHIFTAMT) positions, zero-filling the vacated high end (used by the
; leading-zero normalise after subtract-cancellation, and by fp_div's
; "remainder *= 10" step). HL NOT preserved (same rationale as dig15_shr).
; Clobbers A, B, C, D, E, H, L.
dig15_shl:
                ld      a,(FP_SHIFTAMT)
                or      a
                ret     z
                cp      15
                jr      nc,dshl_allzero
                ld      c,a
                ld      d,h
                ld      e,l                 ; DE = base (dst start)
                ld      a,l
                add     a,c
                ld      l,a                 ; HL = base+shift (src start)
                ld      a,15
                sub     c
                ld      b,0
                ld      c,a                 ; BC = 15-shift
                ldir                        ; after this, DE = base+(15-shift)
                ld      a,(FP_SHIFTAMT)
                ld      b,a
dshl_zlp:
                xor     a
                ld      (de),a
                inc     de
                djnz    dshl_zlp
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to dshr_allzero,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
dshl_allzero    equ     dshr_allzero

; --- dig_to_word: HL -> digit array (idx0, MSD first), B = digit count -----
; (1..5) -> DE = the represented value. Same *10+digit accumulation idiom as
; tkf_int_value (basic/float.asm), applied to a caller-chosen array instead
; of the fixed TKDIG (own design, adapted reuse of an established pattern).
; Clobbers A, B, C, HL.
dig_to_word:
                ld      de,0
                ld      a,b
                or      a
                ret     z
dtw_lp:
                ld      a,(hl)
                ld      c,a
                push    hl
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de
                ex      de,hl
                pop     hl
                inc     hl
                djnz    dtw_lp
                ret

; --- arga_find_first_nonzero: scan ARGA_DIG[0..14] for the first nonzero ---
; digit. out: CF clear + A = index (0..14) of the first nonzero digit; CF set
; if all 15 are zero. Clobbers A, B, HL.
arga_find_first_nonzero:
                ld      hl,ARGA+FPNUM_DIG
                ld      b,0
affn_lp:
                ld      a,(hl)
                or      a
                jr      nz,affn_found
                inc     hl
                inc     b
                ld      a,b
                cp      15
                jr      nz,affn_lp
                scf
                ret
affn_found:
                ld      a,b
                or      a
                ret

; --- arga_inc14: ARGA_DIG[0..13] += 1 (big-decimal), for guard-digit ------
; half-up rounding. out: CF set iff the increment carried out of index 0 (all
; 14 digits were 9). Clobbers A, B, HL.
arga_inc14:
                ld      hl,ARGA+FPNUM_DIG+13
                ld      b,14
                scf
ai14_lp:
                jr      nc,ai14_done
                ld      a,(hl)
                add     a,1
                cp      10
                jr      c,ai14_nc
                sub     10
                scf
                jr      ai14_st
ai14_nc:
                or      a
ai14_st:
                ld      (hl),a
                dec     hl
                djnz    ai14_lp
ai14_done:
                ret

; --- arga_carry_renorm: ARGA_DIG shifts right by 1 (drops the old guard), --
; ARGA_DIG[0] := 1, ARGA_DEXP += 1. Used both by fp_add's same-sign carry-out
; and by round_and_finalize's guard-round carry-out (spec §10.2: "carry
; renormalise", `99999999999999#+1` -> `1E+14`). Clobbers A, HL, DE, BC.
arga_carry_renorm:
                ld      hl,ARGA+FPNUM_DIG+13
                ld      de,ARGA+FPNUM_DIG+14
                ld      bc,14
                lddr
                ld      a,1
                ld      (ARGA+FPNUM_DIG),a
                ld      hl,(ARGA+FPNUM_DEXP)
                inc     hl
                ld      (ARGA+FPNUM_DEXP),hl
                ret

; --- arga_pack_fac: ARGA_SIGN/ARGA_DEXP/ARGA_DIG[0..13] -> FAC (double). ----
; Lead byte = sign | (dexp+64); mantissa packed 2 digits/byte, MSD first —
; same technique as tkf_emit_mantissa (basic/float.asm), applied to ARGA
; instead of TKDIG. Caller (round_and_finalize) has already verified
; -63<=dexp<=63 and that ARGA_DIG isn't the all-zero case. Clobbers A, B, HL,
; DE.
; 🎯 ONE BODY, TWO ENTRIES, AND THE ONLY DIFFERENCE WAS A LOOP COUNT.
; arga_pack_single (below, and its callers are unchanged) was a 35-byte copy of
; this routine with `ld b,3` where this one had `ld b,7` -- 6 digits instead of
; 14, the same nibble pack over the same ARGA into the same FAC. Two ENTRY
; POINTS setting the count and falling into one body is 27 B smaller, and it is
; the shape this file already uses for fac_to_int_addr/fac_to_int_strict and for
; widen_fac_to/widen_lhsframe_to. tools/clone_scout.py named the pair; it priced
; only the 22-byte HEADER spans (14 B) because `apf_lp`/`aps_lp` are separate
; symbols, so the identical 13-byte LOOPS were invisible to it -- the saving is
; nearly twice the estimate. ⚠️ A ranked estimate is a floor on ITS OWN SHAPE.
; 🔴 BC IS GUARDED RATHER THAN RE-DOCUMENTED, and that is not caution: this is a
; RESIDENT-ABI entry (sub/basic-resident-abi.inc, tools/gen_resident_abi.py), so
; its callers include six sub-ROM math-pack tenants whose own headers quote the
; "Clobbers A, B, HL, DE" contract. Widening that contract to include C would
; have to be verified at every one of them; `push bc`/`pop bc` costs 2 B and
; STRENGTHENS it instead -- B comes back too.
arga_pack_fac:
                push    bc                  ; the contract says B is clobbered; this
                ld      c,7                 ; keeps the promise anyway, and C with it
                jr      arga_pack_go        ; 14 digits -> 7 mantissa bytes (double)
arga_pack_single:
                push    bc
                ld      c,3                 ; 6 digits -> 3 mantissa bytes (single)
arga_pack_go:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      b,a
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,l
                add     a,64
                or      b
                ld      (FAC),a
                ld      hl,ARGA+FPNUM_DIG
                ld      de,FAC+1
                ld      b,c
apf_lp:
                ld      a,(hl)
                add     a,a
                add     a,a
                add     a,a
                add     a,a
                inc     hl
                or      (hl)
                inc     hl
                ld      (de),a
                inc     de
                djnz    apf_lp
                pop     bc
                ret

; --- round_and_finalize: ARGA (unrounded, 15-digit incl. guard) -> FAC -----
; (packed double) + FACTYP=8 + DE (silent flt_to_int16). Shared tail for
; fp_add/fp_sub/fp_mul/fp_div: guard-digit half-up round (spec §10.2), a
; possible second carry-renormalise if rounding carries out of the leftmost
; digit, then the -63..63 dec_exp bound check (>63 -> Overflow/FPERR=1; <-63
; -> silent zero, both ops' underflow convention). A pre-round ARGA that is
; ALREADY all-zero (genuine zero result, or fp_mul/fp_div's underflow/
; div-by-zero shortcuts) skips rounding and the bound check entirely.
round_and_finalize:
                call    arga_dig_iszero
                jp     z,raf_zero_ok
                ld      a,(ARGA+FPNUM_DIG+14)
                cp      5
                jr      c,raf_noround
                call    arga_inc14
                jr      nc,raf_noround
                call    arga_carry_renorm
raf_noround:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      (FP_TMP_B),hl
                call    check_preexp_bounds ; shared bound-check gate (defined below,
                                            ; with fp_mul): out of bounds -> aborts this
                                            ; ENTIRE round_and_finalize call, returning
                                            ; straight to OUR caller with FAC/FACTYP/DE
                                            ; already set to the zero/error result (see
                                            ; check_preexp_bounds's own header comment);
                                            ; in bounds -> falls through normally below
                call    arga_pack_fac

; --- fac_dbl_int16: publish FAC as a DOUBLE, then hand DE to our caller -------
; D-NGRAM14: the tail four sites wrote out -- this one by fallthrough, `^`'s
; below by `jp`, and two in basic/expr.asm (evmc_dispatch, evmc_exp_huge).
; It is a TAIL, not a call: whoever jumps here returns to THEIR caller out of
; `flt_to_int16`, exactly as the open-coded copy did, so no frame moves.
;
; 🔴 IT LIVES IN THE PAGE-0 LOW REGION, AND THAT IS NOT A PREFERENCE. Siting it
; in page 1 -- where the other two reachers are, and where the free bytes are --
; builds, and `subrom-closure-check` REFUSES it: these two sites run inside the
; page-1 tenant's RESIDENT CLOSURE, with page 1 switched out, so a `jp` into it
; hangs. The cheaper-looking split was measured, rejected by a gate, and the
; direction inverted. (docs/spec-basic-ngram14.md §2)
fac_dbl_int16:
                ld      a,8
                ld      (FACTYP),a
                jp      flt_to_int16        ; tail call: sets DE, returns to our caller
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to cpow_x0_pos,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
raf_zero_ok     equ     cpow_x0_pos

; =============================================================================
; F3 S3a store coercion — single-precision (6 sig digit) round + pack
; (docs/spec-basic-float-core.md §11.2). vars.asm's var_store_fac calls these
; after widen_rhs_operand has filled ARGA with an EXACT widen of the RHS (int/
; single/double source, always exact — no rounding happened yet); these round
; that exact 14-digit array down to 6 significant digits, half-up with carry
; renormalise, and pack the result as a single FAC. Same shape as arga_inc14/
; arga_carry_renorm/arga_pack_fac/round_and_finalize above, scoped to 6 digits
; / 3 mantissa bytes instead of 14/7 — kept as SEPARATE routines rather than
; parameterising the existing ones, so F2's hot arithmetic path (fp_add/sub/
; mul/div, all always 14-digit double) is untouched byte-for-byte.
; =============================================================================

; --- arga_inc6: ARGA_DIG[0..5] += 1 (six-digit big-decimal), for the SINGLE --
; store-coercion's guard-digit half-up round. out: CF set iff the increment
; carried out of index 0 (all six digits were 9). Clobbers A, B, HL.
arga_inc6:
                ld      hl,ARGA+FPNUM_DIG+5
                ld      b,6
                scf
ai6_lp:
                jr      nc,ai6_done
                ld      a,(hl)
                add     a,1
                cp      10
                jr      c,ai6_nc
                sub     10
                scf
                jr      ai6_st
ai6_nc:
                or      a
ai6_st:
                ld      (hl),a
                dec     hl
                djnz    ai6_lp
ai6_done:
                ret

; --- arga_renorm6: after arga_inc6 carries out of digit 0 (six 9's rounded --
; up, e.g. 999999+1 -> 1000000), ARGA_DIG[0]:=1, ARGA_DIG[1..5]:=0, ARGA_DEXP
; += 1. Unlike the double-precision arga_carry_renorm (which shifts a 14-wide
; window right to drop the old guard), single coercion has no wider mantissa
; to preserve — the digits beyond index 5 were never part of the 6-digit
; result, so this just re-seeds a canonical "1 followed by zeros". Clobbers
; A, B, HL.
arga_renorm6:
                ld      a,1
                ld      (ARGA+FPNUM_DIG),a
                xor     a
                ld      hl,ARGA+FPNUM_DIG+1
                ld      b,5
ar6_lp:
                ld      (hl),a
                inc     hl
                djnz    ar6_lp
                ld      hl,(ARGA+FPNUM_DEXP)
                inc     hl
                ld      (ARGA+FPNUM_DEXP),hl
                ret

; --- arga_pack_single: ARGA_SIGN/ARGA_DEXP/ARGA_DIG[0..5] -> FAC (single). ---
; Same nibble-packing technique as arga_pack_fac, scoped to 6 digits / 3
; mantissa bytes. Caller (round_single_and_pack) has already verified
; -63<=dexp<=63 and that ARGA_DIG isn't the all-zero case. Clobbers A, B, HL,
; DE.
; arga_pack_single is now the SECOND ENTRY POINT of arga_pack_fac above -- same
; body, `ld c,3` instead of `ld c,7`. Its callers (round_single_and_pack below,
; basic/expr.asm's CSNG) are unchanged, and so is its register contract.

; --- round_single_and_pack: ARGA (exact, widen_rhs_operand'd) -> FAC (packed -
; single) + FACTYP=4 + DE (silent flt_to_int16). Store-coercion counterpart of
; round_and_finalize: round to 6 sig digits, half-up, carry renormalise (spec
; §11.2), then the shared -63..63 dec_exp bound check (reused from
; check_preexp_bounds — on overflow its own abort tail sets FACTYP=8, a
; harmless wrinkle here since FPERR=1 makes the caller (var_store_fac) drop
; the store unconditionally, so nothing ever reads that stale FACTYP=8).
round_single_and_pack:
                call    arga_dig_iszero
                jr      z,rsp_zero_ok
                ld      a,(ARGA+FPNUM_DIG+6)   ; the 7th digit is the round digit
                cp      5
                jr      c,rsp_noround
                call    arga_inc6
                jr      nc,rsp_noround
                call    arga_renorm6
rsp_noround:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      (FP_TMP_B),hl
                call    check_preexp_bounds ; shared -63..63 bound gate (defined above,
                                            ; with round_and_finalize); out of bounds ->
                                            ; aborts straight to OUR caller (see its own
                                            ; header comment)
                call    arga_pack_single
                ld      a,4
                ld      (FACTYP),a
                jp      flt_to_int16        ; tail call: sets DE, returns to our caller
; --- fac_zero_mantissa: make a ZERO FAC byte-identical to the reference's ----
; docs/spec-basic-faczero.md (D-FACZERO). in: A = 0. Clears FAC+1..FAC+7.
; Clobbers HL and B; A stays 0, so every caller's following `ld a,<type>` is
; unaffected and DE is untouched.
;
; 🔴 EVERY ZERO EXIT USED TO WRITE THE LEAD BYTE AND STOP. Lead byte 0 IS "the
; value is zero" -- flt_out never reads further and nothing printed wrong -- so
; the mantissa kept whatever the destination happened to hold. Measured: a fresh
; slot gave `0 255 255 255` where both references give `0 0 0 0`, and
; `A!=1.5 : A!=0` gave `0 21 0 0` -- 21 being 1.5's OWN leftover mantissa byte.
; That is a read of stale memory wearing the value's clothes.
;
; ⚠️ IT IS INVISIBLE TODAY AND WOULD NOT HAVE BEEN FOR LONG. `MKS$`/`MKD$` are
; the next slice; they emit these exact bytes as a STRING, which a program
; writes to disk. The scout that asked "is our float byte-identical to the
; reference's?" -- a question about whether that slice was small -- is what
; found it, before the verb could ship the divergence to a file.
fac_zero_mantissa:
                ld      hl,FAC+1
                ld      b,7                 ; always all 7: single copies 4 bytes and
                                            ; double 8, and a uniformly canonical FAC
                                            ; costs nothing over clearing only 3
fzm_lp:         ld      (hl),a
                inc     hl
                djnz    fzm_lp
                ret

rsp_zero_ok:
                xor     a
                ld      (FAC),a
                call    fac_zero_mantissa   ; D-FACZERO: and the mantissa too
                ld      a,4
                ld      (FACTYP),a
                jp      ret_de0

; =============================================================================
; fp_add / fp_sub — double BCD add/subtract (spec §10.2)
; =============================================================================

; --- fp_add: ARGA + ARGB -> ARGA -> round_and_finalize. No pre-check (spec: -
; "only genuine result overflow observed" for add/sub); round_and_finalize's
; own bound check catches it. Clobbers A, B, C, D, E, H, L.
fp_add:
                ; align: diff = dexpA - dexpB (range -126..126, fits in a
                ; signed byte since each dexp is -63..63 — H after sbc is
                ; pure sign-extension, so testing H's sign bit alone decides
                ; which operand has the smaller exponent and needs shifting).
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,(ARGB+FPNUM_DEXP)
                or      a
                sbc     hl,de               ; HL = dexpA - dexpB
                ld      a,h
                or      a
                jp      p,fpa_agtb          ; diff>=0 -> dexpA>=dexpB
                ; dexpA < dexpB: shift ARGA_DIG right by |diff|, adopt dexpB
                ld      a,l
                neg
                ld      (FP_SHIFTAMT),a
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_shr
                ld      hl,(ARGB+FPNUM_DEXP)
                ld      (ARGA+FPNUM_DEXP),hl
                jr      fpa_combine
fpa_agtb:
                ; dexpA >= dexpB: shift ARGB_DIG right by diff; ARGA_DEXP
                ; (=dexpA) is already the common exponent, no update needed
                ld      a,l
                ld      (FP_SHIFTAMT),a
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_shr
fpa_combine:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      b,a
                ld      a,(ARGB+FPNUM_SIGN)
                cp      b
                jr      nz,fpa_diffsign
                call    dig15_add_inplace
                jr      nc,fpa_done
                call    arga_carry_renorm
                jr      fpa_done
fpa_diffsign:
                ld      hl,ARGA+FPNUM_DIG
                ld      de,ARGB+FPNUM_DIG
                ld      b,15
                call    dig15_cmp
                cp      2
                jr      z,fpa_zero_result
                cp      4
                jr      z,fpa_a_bigger
                ; B bigger: ARGB_DIG -= ARGA_DIG in place, then adopt B's sign
                ; and copy ARGB_DIG -> ARGA_DIG.
                ld      hl,ARGB+FPNUM_DIG+14
                ld      de,ARGA+FPNUM_DIG+14
                call    dig15_sub_inplace
                ld      a,(ARGB+FPNUM_SIGN)
                ld      (ARGA+FPNUM_SIGN),a
                ld      hl,ARGB+FPNUM_DIG
                ld      de,ARGA+FPNUM_DIG
                ld      bc,15
                ldir
                jr      fpa_leadzero
fpa_a_bigger:
                ld      hl,ARGA+FPNUM_DIG+14
                ld      de,ARGB+FPNUM_DIG+14
                call    dig15_sub_inplace   ; sign stays ARGA's (already correct)
fpa_leadzero:
                call    arga_find_first_nonzero
                jr      c,fpa_zero_result
                                            ; arga_find_first_nonzero's own
                                            ; affn_found path already does its
                                            ; own "or a" right before ret, so Z
                                            ; here already reflects A (=k) --
                                            ; ret/jr don't touch flags, so no
                                            ; need to re-test
                jr      z,fpa_sub_finalize  ; k=0: already normalised
                ld      (FP_SHIFTAMT),a
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_shl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,(FP_SHIFTAMT)
                ld      e,a
                ld      d,0
                or      a
                sbc     hl,de
                ld      (ARGA+FPNUM_DEXP),hl
                jr      fpa_sub_finalize
fpa_zero_result:
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_zero15
fpa_done:
                jp      round_and_finalize

; --- fpa_sub_finalize: effective-subtraction (opposite-sign combine) tail --
; bug-for-bug reference-compat (docs/spec-float-subtract-tie-compat.md §3):
; the reference rounds an exact guard-digit tie (==5) TOWARD ZERO for
; effective subtraction, vs round_and_finalize's blanket half-up (which stays
; correct for effective addition). Pre-nudge the tie 5->4 so the unchanged
; half-up tail drops it, then fall into the shared, byte-identical tail.
; Only the two fpa_leadzero exits (k=0 and post-shift) route here; the
; same-sign add exits (dig15_add_inplace's jr nc/call arga_carry_renorm)
; keep going straight to fpa_done, unchanged.
fpa_sub_finalize:
                ld      a,(ARGA+FPNUM_DIG+14)   ; guard digit
                cp      5
                jp      nz,round_and_finalize   ; 0-4 down, 6-9 up: unchanged half-up tail
                dec     a                       ; exact tie 5 -> 4 so half-up drops it (toward zero)
                ld      (ARGA+FPNUM_DIG+14),a
                jp      round_and_finalize

; --- fp_sub: ARGA - ARGB, realised as ARGA + (-ARGB) (flip ARGB's sign, ----
; reuse fp_add's combine logic). ARGB is transient scratch, dead after this
; call, so the flip is never undone. Clobbers as fp_add.
fp_sub:
                ld      a,(ARGB+FPNUM_SIGN)
                xor     $80
                ld      (ARGB+FPNUM_SIGN),a
                jp      fp_add

; =============================================================================
; fp_mul — double BCD multiply (spec §10.2)
; =============================================================================

; --- digit_mul: A=i(0-9), C=j(0-9) -> A=i*j(0-81), via i repeated adds of j -
; (own design: a lookup table was considered but ROM bytes, not cycles, are
; the binding constraint here — a BASIC multiply statement runs this at most
; 196 times once, not in a hot loop). Preserves B, HL. Clobbers C, D, E.
digit_mul:
                ; D-MULZERO (2026-09-11): count down J, not I -- i*j is symmetric, and
                ; the two operands are NOT symmetric in practice. The outer loop walks
                ; ARGA (the variable: `X=I*2` has up to 9 in a digit), the inner walks
                ; ARGB (the literal: ONE non-zero digit and thirteen zeros). Counting
                ; the inner digit makes `*2` two iterations instead of up to nine, and
                ; gives j=0 an early-out that the old shape could not have: it spun i
                ; times adding zero, thirteen times per pass. Two bytes, and the
                ; header's "not in a hot loop" was the claim this refutes -- 392,000
                ; calls in the loop D-SPEEDPROF profiled.
                ld      d,c                 ; D = j (countdown)
                ld      e,a                 ; E = i (addend)
                ld      c,0                 ; C = accumulator
                or      a
                ret     z                   ; i=0 -> A is already 0
                ld      a,d
                or      a
                ret     z                   ; j=0 -> the product is 0, and A is it
dmul_lp:
                ld      a,c
                add     a,e
                ld      c,a
                dec     d
                jr      nz,dmul_lp
                ld      a,c
                ret

; --- fp_mul: ARGA * ARGB -> ARGA -> round_and_finalize. Overflow/underflow -
; PRE-CHECK on the stored dec_exps (spec §10.2: "even when the normalised
; result would fit"): e(a)+e(b) > 63 -> Overflow; < -63 -> silent 0. Then a
; 14x14 -> 28-digit schoolbook long multiply (MSD-first digit arrays, own
; design), normalise (product's leading digit 0 -> shift the 15-digit
; sig+guard window by one, dexp-=1), then the shared round_and_finalize tail
; (which re-checks the bound as a backstop against a round-carry pushing
; dexp past 63). Clobbers A, B, C, D, E, H, L.
; --- check_preexp_bounds: HL = a pre-normalisation exponent sum/difference -
; (the caller has already stashed it into FP_TMP_B) -> on overflow/underflow,
; aborts the WHOLE fp_add/fp_sub/fp_mul/fp_div operation: sets FAC=0/
; FACTYP=8/DE=0 (+FPERR=1 on overflow; untouched, i.e. still silent, on
; underflow) via the shared raf_zero_ok tail, and returns not to the direct
; caller of check_preexp_bounds but to THAT caller's own caller. This is
; needed because check_preexp_bounds is always reached via a plain "call"
; from exactly one of three direct callers (round_and_finalize's own final
; bound check, or fp_mul's/fp_div's own PRE-check), each of which was
; itself reached purely by tail jumps (jp, never call) from whoever invoked
; the overall fp_XXX operation -- so the only stack entry pushed since that
; original call is the "call check_preexp_bounds" return address, a resume
; point back inside the direct caller's own body that must NOT run (it
; would keep computing with an out-of-range exponent and overwrite the
; zero/error result being set here). The single shared "pop hl" below
; discards exactly that one entry before falling into raf_zero_ok's own
; "ret", so that ret lands on the ORIGINAL caller of the whole operation --
; a full abort, not a resume. (Own design; same single-level-discard shape
; as sdivmod_zerocheck, used there for the identical reason.)
; Falls through with a normal ret (to the direct caller, computation
; continues) if in bounds. Clobbers A, D, E, H, L.
check_preexp_bounds:
                ld      de,63
                call    cmp16_bits
                cp      4
                jr      nz,cpb_check_uf
                ld      a,1
                call    penderr_set
                jr      cpb_abort
cpb_check_uf:
                ld      hl,(FP_TMP_B)
                ld      de,$FFC1            ; -63
                call    cmp16_bits
                cp      1
                ret     nz                  ; in bounds -> normal return
cpb_abort:
                pop     hl                  ; discard direct caller's dead resume addr
                jp      raf_zero_ok         ; shared zero-pack tail (round_and_finalize)

fp_mul:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,(ARGB+FPNUM_DEXP)
                add     hl,de               ; HL = preExp; range -126..126, no
                                            ; special overflow handling needed for
                                            ; this plain 16-bit add itself
                ld      (FP_TMP_B),hl
                call    check_preexp_bounds
                call    xor_sign
                push    af                  ; stash result sign (ARGA_DIG is still
                                            ; needed below as a multiply INPUT)
                ld      hl,MULPROD
                ld      b,28
                call    zero_fill
                ld      a,13
                ld      (MUL_I),a
fpm_outer:
                ; (no zero-digit skip: the inner loop is code-size-bound, not
                ; speed-bound, here -- digit_mul(0,j)=0 makes a zero pass a
                ; correct no-op through the accumulation anyway, so the extra
                ; branch to skip it would only cost bytes, not save them)
                ld      a,(MUL_I)
                ld      hl,ARGA+FPNUM_DIG
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)
                ; D-MULZERO (2026-09-11): a ZERO multiplicand digit contributes
                ; nothing from a 14-digit pass, and there is no carry to propagate
                ; because every partial product is 0 -- so skip the whole pass.
                ; `FOR I=1 TO 2000:X=I*2:NEXT` costs 2719 jiffies of marginal time
                ; here against the CF-3300's 577 (4.7x, the interpreter's single
                ; biggest constant -- D-SPEEDPROF's profile puts ~47% of that loop
                ; in this multiply), and I is 1-4 significant digits of 14.
                or      a
                jr      z,fpm_outer_next
                ld      (MUL_ADIG),a
                ld      a,(MUL_I)
                add     a,(MULPROD & $FF)+14 ; bug fix: MUL_PP = MULPROD+MUL_I+14, not
                                            ; $F000+MUL_I+14 -- MULPROD's low byte
                                            ; ($8E) plus the max offset (27) never
                                            ; carries past $FF, so the low-byte-only
                                            ; add stays correct and H is always $F0
                ld      l,a
                ld      h,$F0               ; MULPROD's page (sysvars.inc)
                ld      (MUL_PP),hl
                ld      hl,ARGB+FPNUM_DIG+13
                ld      b,14
                xor     a
                ld      (MUL_CARRY),a
fpm_inner:
                ld      a,(hl)
                ld      c,a
                ld      a,(MUL_ADIG)
                call    digit_mul           ; A = i*j (0..81); preserves B, C, HL
                ld      d,a
                ld      a,(MUL_CARRY)
                add     a,d                 ; A = i*j + carry_in (<= 81+9 = 90)
                push    hl                  ; save PB (about to clobber HL for MUL_PP)
                ld      hl,(MUL_PP)
                add     a,(hl)              ; A = MULPROD[pos] + i*j + carry_in (<=99)
                ld      d,0
fpm_reduce:
                cp      10
                jr      c,fpm_reduce_done
                sub     10
                inc     d
                jr      fpm_reduce
fpm_reduce_done:
                ld      (hl),a
                ld      a,d
                ld      (MUL_CARRY),a
                dec     hl
                ld      (MUL_PP),hl
                pop     hl                  ; HL = PB restored
                dec     hl
                djnz    fpm_inner
                ; propagate any leftover MUL_CARRY (0..9) further left
                ld      a,(MUL_CARRY)
                or      a
                jr      z,fpm_outer_next
                ld      hl,(MUL_PP)
                ld      d,a
fpm_carry_lp:
                ld      a,(hl)
                add     a,d
                cp      10
                jr      c,fpm_carry_st
                sub     10
                ld      d,1
                jr      fpm_carry_st2
fpm_carry_st:
                ld      d,0
fpm_carry_st2:
                ld      (hl),a
                ld      a,d
                or      a
                jr      z,fpm_outer_next
                dec     hl
                jr      fpm_carry_lp
fpm_outer_next:
                ld      a,(MUL_I)
                or      a
                jr      z,fpm_after
                dec     a
                ld      (MUL_I),a
                jr      fpm_outer
fpm_after:
                pop     af                  ; result sign, stashed above
                ld      (ARGA+FPNUM_SIGN),a
                ld      a,(MULPROD)
                ld      hl,MULPROD          ; default (mantissa>=.1) copy source
                or      a
                jr      nz,fpm_norm_go
                ; product mantissa < .1 -> window = MULPROD[1..15], dexp = preExp-1
                ; (adjusted in place in FP_TMP_B -- round_and_finalize overwrites
                ; it fresh from ARGA_DEXP right after, so no caller downstream
                ; ever sees this pre-decrement; own simplification merging what
                ; used to be two near-duplicate copy+store+tail-call blocks)
                ld      hl,MULPROD+1
                ld      de,(FP_TMP_B)
                dec     de
                ld      (FP_TMP_B),de
fpm_norm_go:
                ld      de,ARGA+FPNUM_DIG
                ld      bc,15
                ldir
                ld      hl,(FP_TMP_B)
                ld      (ARGA+FPNUM_DEXP),hl
                jp      round_and_finalize

; =============================================================================
; fp_div — double BCD divide (spec §10.2)
; =============================================================================

; --- fpd_trial_digit: repeatedly subtract DIVPAD from DIVREM while it fits, -
; counting iterations (0..9). out: A = the digit found. Clobbers A, B, C, D,
; E, H, L, and (MUL_CARRY) as a transient counter (fp_mul never runs
; concurrently with fp_div, so sharing the cell is safe — same reasoning as
; every other cross-routine scratch reuse in this file).
fpd_trial_digit:
                xor     a
                ld      (MUL_CARRY),a
fpdtd_lp:
                ld      hl,DIVREM
                ld      de,DIVPAD
                ld      b,15
                call    dig15_cmp
                cp      1
                jr      z,fpdtd_done
                ld      hl,DIVREM+14
                ld      de,DIVPAD+14
                call    dig15_sub_inplace
                ld      hl,MUL_CARRY
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      fpdtd_lp
fpdtd_done:
                ld      a,(MUL_CARRY)
                ret

; --- fp_div: ARGA / ARGB -> ARGA -> round_and_finalize. Divisor 0 ---------
; -> Division-by-zero (FPERR=2). Overflow PRE-CHECK on stored dec_exps: e(a)-
; e(b)+1 > 63 -> Overflow (even when the true quotient would fit, spec
; §10.2); < -63 -> silent 0. Long division producing 15 quotient digits
; (14 + guard) via the classic "zero-pad, trial-subtract, append a 0 digit"
; method over 15-digit-wide arrays (own design). Clobbers A, B, C, D, E, H, L.
fp_div:
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      nz,fpd_go
                ld      a,2
                call    penderr_set
                jp      raf_zero_ok         ; shared zero-pack tail (round_and_finalize)
fpd_go:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,(ARGB+FPNUM_DEXP)
                or      a
                sbc     hl,de
                inc     hl
                ld      (FP_TMP_B),hl
                call    check_preexp_bounds ; shared with fp_mul (above)
                call    xor_sign
                ld      (FP_RSIGN),a
                xor     a
                ld      (DIVPAD),a
                ld      hl,ARGB+FPNUM_DIG
                ld      de,DIVPAD+1
                ld      bc,14
                ldir
                xor     a
                ld      (DIVREM),a
                ld      hl,ARGA+FPNUM_DIG
                ld      de,DIVREM+1
                ld      bc,14
                ldir
                ld      hl,DIVREM
                ld      de,DIVPAD
                ld      b,15
                call    dig15_cmp
                cp      1
                jr      z,fpd_k0
                ld      hl,(FP_TMP_B)
                ld      (ARGA+FPNUM_DEXP),hl
                call    fpd_trial_digit
                ld      (ARGA+FPNUM_DIG),a
                ld      a,1
                ld      (FP_LHSVAL),a       ; next quotient slot index (reused; the
                                            ; combine_* int-value stash is dead here)
                jr      fpd_loop
fpd_k0:
                ld      hl,(FP_TMP_B)
                dec     hl
                ld      (ARGA+FPNUM_DEXP),hl
                xor     a
                ld      (FP_LHSVAL),a
fpd_loop:
                ld      a,(FP_LHSVAL)
                cp      15
                jr      nc,fpd_loop_done
                ld      a,1
                ld      (FP_SHIFTAMT),a
                ld      hl,DIVREM
                call    dig15_shl
                call    fpd_trial_digit     ; A = next quotient digit (0..9)
                ld      c,a                 ; C = digit (survives the reload below)
                ld      a,(FP_LHSVAL)
                ld      hl,ARGA+FPNUM_DIG
                ld      e,a
                ld      d,0
                add     hl,de               ; HL = ARGA_DIG + slot
                ld      (hl),c              ; QDIG[slot] = digit
                ld      hl,FP_LHSVAL
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      fpd_loop
fpd_loop_done:
                ld      a,(FP_RSIGN)
                ld      (ARGA+FPNUM_SIGN),a
                jp      round_and_finalize

; =============================================================================
; fp_cmp — double compare (spec §10.1: "compare AS floats after widening")
; =============================================================================

; --- fp_cmp: ARGA vs ARGB -> A = 1 (A<B) / 2 (A==B) / 4 (A>B), same relation-
; bit convention as expr.asm's cmp16_bits. Handles zero operands (canonical
; sign=0 from every widen_*/fp_* producer) and cross-sign ordering before
; falling to a magnitude compare (dexp, then digits). Clobbers A, B, C, D, E,
; H, L.
fp_cmp:
                call    arga_dig_iszero
                jr      z,fcmp_a_zero
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      z,fcmp_b_zero
                ld      a,(ARGA+FPNUM_SIGN)
                ld      b,a
                ld      a,(ARGB+FPNUM_SIGN)
                cp      b
                jr      nz,fcmp_diffsign
                ; same sign, both nonzero: compare magnitude (dexp, then digits)
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,(ARGB+FPNUM_DEXP)
                call    cmp16_bits          ; A=1/2/4 for magA vs magB
                cp      2
                jr      nz,fcmp_have_mag
                ld      hl,ARGA+FPNUM_DIG
                ld      de,ARGB+FPNUM_DIG
                push    bc
                ld      b,14                ; compare only the 14 significant digits
                call    dig15_cmp
                pop     bc
fcmp_have_mag:
                ; A = 1(magA<magB)/2(eq)/4(magA>magB). Positive sign: same
                ; ordering. Negative sign: reversed (bigger magnitude = smaller
                ; value) — swap 1<->4, keep 2.
                ld      c,a
                ld      a,b
                or      a
                jr      z,fcmp_ret_c        ; positive: relation bit as computed
                ld      a,c
                cp      1
                jp     z,fcmp_neg_swap4
                cp      4
                jp     z,fcmp_neg_swap1
                ld      a,2
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to c16_gt,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
fcmp_neg_swap4  equ     c16_gt
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to c16_lt,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
fcmp_neg_swap1  equ     c16_lt
fcmp_ret_c:
                ld      a,c
                ret
fcmp_diffsign:
                ; different sign, both nonzero: positive > negative. Same
                ; sign-to-relation shape as fcmp_b_zero below (ARGA vs an
                ; implicit 0 on the right) — share its tail rather than
                ; re-testing the already-loaded B register.
                jr      fcmp_b_zero
fcmp_a_zero:
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      z,fcmp_both_zero
                ld      a,(ARGB+FPNUM_SIGN)
                or      a
                jp     z,fcmp_a_lt         ; B positive -> A(0)<B
                ld      a,4                 ; B negative -> A(0)>B
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to c16_lt,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
fcmp_a_lt       equ     c16_lt
fcmp_b_zero:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jp     z,fcmp_a_gt2        ; A positive -> A>B(0)
                ld      a,1                 ; A negative -> A<B(0)
                ret
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to c16_gt,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
fcmp_a_gt2      equ     c16_gt
fcmp_both_zero:
                ld      a,2
                ret

; =============================================================================
; Converters: fac_to_int_strict / fac_to_int_addr (spec §10.3)
; =============================================================================

; --- dcc_bound5: DE = a 5-entry unpacked-digit bound table (tkf_ref32767/ --
; 32768/65535, basic/float.asm) -> CF set iff CVT's 5 leading digits are <=
; bound, AND DE := their value (dig_to_word, unconditionally — callers that
; got CF clear ignore it). Reuses dig15_cmp (this file, B=5) rather than
; basic/float.asm's tkf_cmp5, which hardcodes `ld hl,TKDIG` internally and
; silently ignores any HL the caller sets — NOT what CVT-based callers need
; (caught in review: calling tkf_cmp5 with CVT+FPNUM_DIG in HL was actually
; comparing stale TKDIG data). Shared by every dexp==5 bound check in
; domain_convert_core below. Clobbers A, B, C, D, E, H, L.
dcc_bound5:
                ld      hl,CVT+FPNUM_DIG
                ld      b,5
                call    dig15_cmp           ; A=1(<)/2(=)/4(>); clobbers DE (bound ptr)
                cp      4
                jr      z,dcc_bound5_over
                scf                         ; <= bound
                jr      dcc_bound5_go
dcc_bound5_over:
                or      a                   ; > bound
dcc_bound5_go:
                push    af
                ld      hl,CVT+FPNUM_DIG
                ld      b,5
                call    dig_to_word
                pop     af
                ret

; --- domain_convert_core: shared unpack+classify body for BOTH converters --
; (CVT_MODE, own scratch: 0 = the STRICT int16 domain for \/MOD/AND/OR/XOR/
; NOT, -32769<x<32768, no wrap; 1 = the ADDRESS domain for POKE/VPOKE/HEX$
; and flt_to_int16 (float.asm), -32769<x<65536, a value >=32768 wraps).
; out: CF clear + DE=result, or CF set + DE=0 (out of domain — the caller
; decides whether that means FPERR or plain silence). Does NOT check
; FACTYP==2 (every caller gates that itself). Clobbers A, B, C, D, E, H, L.
domain_convert_core:
                ld      hl,CVT
                call    widen_fac_to
                ld      hl,CVT+FPNUM_DIG
                call    dig15_iszero
                jr      z,dcc_zero
                ld      hl,(CVT+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,dcc_zero          ; dexp<0 -> |x|<1 -> 0, in domain (dexp
                                            ; fits a signed byte, so H is pure sign
                                            ; extension: bit7 set iff dexp<0)
                ld      a,l
                or      a
                jr      z,dcc_zero          ; dexp==0 -> also |x|<1 -> 0
                ; dexp is confirmed positive here (H=0), so L alone (1..63) is
                ; the whole value — no need to reload (CVT+FPNUM_DEXP) or call
                ; the general cmp16_bits just to compare it against 5.
                cp      6
                jr      nc,dcc_overflow     ; dexp>=6 -> dexp>5
                cp      5
                jr      z,dcc_dexp5
                ld      b,a                 ; B = dexp (1..4)
                ld      hl,CVT+FPNUM_DIG
                call    dig_to_word
                jr      dcc_applysign
dcc_dexp5:
                ; pick the symmetric (no-wrap) bound table: 32768 if negative
                ; (both modes share this), else 32767 if strict, else fall
                ; into the address-domain positive/wrap path below.
                ld      de,tkf_ref32768
                ld      a,(CVT+FPNUM_SIGN)
                or      a
                jr      nz,dcc_bound_pick   ; negative -> tkf_ref32768
                ld      de,tkf_ref32767
                ld      a,(CVT_MODE)
                or      a
                jr      z,dcc_bound_pick    ; strict, positive -> tkf_ref32767
                ; address domain, positive: bound 65535, plus the wrap
                ld      de,tkf_ref65535
                call    dcc_bound5          ; DE := the truncated value (dig_to_word)
                jr      nc,dcc_overflow
                ; wrap iff DE>32767 -- DE already holds the actual VALUE (not
                ; just digits), so a plain 16-bit compare against the literal
                ; bound replaces the second digit-level dig15_cmp entirely
                ; (own simplification found in review: no need to re-compare
                ; digits when the value itself is sitting right there).
                ld      hl,32767
                or      a
                sbc     hl,de
                jr      nc,dcc_ret_ok       ; 32767>=DE -> no wrap, DE is already right
                ; wrap: bump DE by 1 iff any fractional digit (dig[5..13]) is
                ; nonzero (spec §10.3: "any fraction rounds UP in the high
                ; half"; DE-65536 == DE unchanged, DE-65535 == DE+1, both mod
                ; 65536 — so the whole wrap collapses to this one check).
                ld      hl,CVT+FPNUM_DIG+5
                ld      b,9
dcc_frac_lp:
                ld      a,(hl)
                or      a
                jr      nz,dcc_frac_yes
                inc     hl
                djnz    dcc_frac_lp
                jr      dcc_ret_ok
dcc_frac_yes:
                inc     de
                jr      dcc_ret_ok
dcc_bound_pick:
                call    dcc_bound5
                jr      nc,dcc_overflow
dcc_applysign:
                ld      a,(CVT+FPNUM_SIGN)
                or      a
                jr      z,dcc_ret_ok
                call    neg_de              ; DE = -DE (float.asm)
dcc_ret_ok:
                or      a                  ; CF clear
                ret
dcc_zero:
                ld      de,0
                or      a
                ret
dcc_overflow:
                ld      de,0
                scf
                ret

; --- fac_to_int_addr (statement/function int arguments: POKE, VPOKE, HEX$) /
; fac_to_int_strict (\, MOD, AND, OR, XOR, NOT operands): two thin entry
; points (CVT_MODE=1/0, sysvars.inc) sharing one body — both are "FACTYP=2
; -> pass-through (DE unchanged), else domain_convert_core in the caller's
; domain, out-of-domain -> FPERR=1 (overflow), DE=0". Clobbers A, B, C, D,
; E, H, L.
fac_to_int_addr:
                ld      a,1
                jr      fac_to_int_go
fac_to_int_strict:
                xor     a
fac_to_int_go:
                ld      (CVT_MODE),a
                call    factyp_is2
                ret     z
                call    domain_convert_core
                ret     nc
                ld      a,1
                jp      penderr_set

; --- eval_addr: HL(cursor) -> DE = a checked ADDRESS-domain int value, ----
; HL(cursor advanced). Thin wrapper combining eval + fac_to_int_addr — the
; shared shape POKE/VPOKE's argument parses both need (basic/poke.asm,
; basic/vdpio.asm). Clobbers as eval + fac_to_int_addr.
eval_addr:
                call    eval
                push    hl
                call    fac_to_int_addr
                pop     hl
                ret

; --- eval_chan: evaluate a file-channel-number expression, surfacing a channel-
; expr FP error as a run abort (spec §5.7 gaps). eval, then — for a NUMERIC
; channel only — an address-domain int coercion so an out-of-range channel value
; sets FPERR=1 (Overflow) (gap 1: `INPUT#99999*99999`); then check_expr_errors
; surfaces that Overflow OR a deferred mid-expression Division-by-zero (gap 2:
; `PRINT#1+0*(1/0)`) as an abort. A TMISMATCH channel (`INPUT#A$`) SKIPS the
; coercion (the coercion on a hard-zeroed type-mismatch state must not spuriously
; fault) and is raised as `Type mismatch` by check_expr_errors' own leading test
; -- D-BADFNUM §6, MEASURED on the CF-3300. It used to fall through to channel 0
; and derail to "load error". Shared by INPUT#/LINE INPUT# (files.asm) and PRINT#
; (print.asm); the tail `jp check_expr_errors` keeps that routine's SP-clean
; abort semantics (it
; pops the driver's resume addr, which is eval_chan's caller). Repack-only (low
; region). out: DE = channel number, HL past the expr. Clobbers as eval +
; fac_to_int_addr.
eval_chan:
                call    eval
                call    fperr_test          ; D-FPCARVE: -1 B
                jr      nz,evc_check        ; is skipped for ANY pending fault, not only a
                                            ; type one. It was only ever skipped to keep a
                                            ; hard-zeroed type-mismatch state from
                                            ; faulting spuriously; the same argument covers
                                            ; a pending div0/overflow, and skipping stops
                                            ; fac_to_int_addr writing Overflow OVER an
                                            ; earlier code. penderr_set would refuse that
                                            ; write anyway -- this makes it moot AND free.
                push    hl
                call    fac_to_int_addr     ; out-of-int-domain channel -> FPERR=1 (overflow)
                pop     hl
evc_check:
                ; D-BADFNUM §6: check_expr_errors, NOT check_fperr_only -- the same
                ; routine with the TMISMATCH test in front of it (check_fperr_only is
                ; its fall-in entry point, so this costs ZERO bytes and the tail-`jp`
                ; shape that keeps the abort chain SP-clean is unchanged).
                ; MEASURED: `PRINT #A$,"X"` is `Type mismatch` on the CF-3300. It used
                ; to hard-zero to channel 0 and derail to `load error`; leaving it
                ; alone was deliberate while `load error` was the status quo, but
                ; D-BADFNUM moves the cell either way -- channel 0 now raises ERR 59,
                ; so NOT taking this would have traded an obviously wrong answer for a
                ; confidently wrong one. On the non-mismatch path TMISMATCH is 0, so
                ; that arm is bit-identical to before.
                jp      check_expr_errors   ; surface TMISMATCH/Overflow/DivZero as
                                            ; abort, else ret

; --- fac_to_int_strict_reset: fac_to_int_strict, then FACTYP := 2. Shared --
; tail for expr.asm's logical/\/MOD operand sites (ev_xor/ev_or/ev_and/
; ev_not/ev_mod/ev_idiv), every one of which needs the reset immediately
; after the conversion (spec §1 bullet 4's per-operand protocol) — 11 call
; sites collapse to one call each here. Clobbers as fac_to_int_strict, +A.
fac_to_int_strict_reset:
                call    fac_to_int_strict
                jp      set_factyp2

; =============================================================================
; Widening loaders (spec §1 bullet 1)
; =============================================================================

; --- widen_fac_to / widen_lhsframe_to: HL = dest FPNUM base. Two thin ------
; entry points sharing ONE unpack body (wsrc_common below): the FAC/FACTYP
; globals, or the LHS_FAC/LHS_FACTYP machine-stack-popped frame, are
; equally-shaped [lead+mantissa byte][type byte] sources — (WSRC)/(WSRC_TYP)
; (sysvars.inc, own scratch) hold which pair this call unpacks. Fills dest:
; sign, dexp (signed -64..63), dig[0..13] (zero-padded to 14 for a single;
; dig[14]=0, meaningless for a freshly-unpacked operand). A source lead byte
; of 0 -> canonical zero (sign=0, dexp=0, all digits 0). Own design: same
; nibble-split technique as flt_out/flt_to_int16 (basic/float.asm), applied
; to a caller-chosen destination. Clobbers A, B, C, D, E, H, L.
widen_fac_to:
                ld      de,FACTYP
                ld      (WSRC_TYP),de
                ld      de,FAC
                jr      wsrc_go
widen_lhsframe_to:
                ld      de,LHS_FACTYP
                ld      (WSRC_TYP),de
                ld      de,LHS_FAC
wsrc_go:
                ld      (WSRC),de
                push    hl                  ; dest base
                ld      de,(WSRC)
                ld      a,(de)
                or      a
                jr      nz,wsrc_nz
                pop     hl
                ld      b,18
                jp      zero_fill           ; tail call
wsrc_nz:
                ld      c,a
                pop     hl                  ; HL = dest base
                and     $80
                ld      (hl),a
                inc     hl
                ld      a,c
                and     $7F
                sub     64
                ld      e,a
                ld      d,0
                bit     7,a
                jr      z,wsrc_dexp_ok
                ld      d,$FF
wsrc_dexp_ok:
                ld      (hl),e
                inc     hl
                ld      (hl),d
                inc     hl                  ; HL -> dest dig[0]
                ld      de,(WSRC_TYP)
                ld      a,(de)
                cp      8
                ld      b,7
                jr      z,wsrc_mbytes_ok
                ld      b,3
wsrc_mbytes_ok:
                ld      de,(WSRC)
                inc     de                  ; DE -> source's mantissa byte 0
                ld      c,$0F               ; D-NEXTCOST: the nibble mask, hoisted
wsrc_unpack:
                ; 🔬 D-NEXTCOST (2026-09-13): C HOLDS THE MASK, NOT THE BYTE, and the
                ; byte is RE-READ for its low nibble. `and c` is one byte where
                ; `and $0F` is two, and it costs 4 T against 7, so dropping the stash
                ; pays for the second read twice over: -3 B in the loop (+2 for the
                ; hoist, net -1 in a region measured 0 B free on 2026-09-13) and
                ; ~7 T per mantissa byte.
                ; 🎯 WHY THIS LOOP: D-NEXTCOST counted it at FOURTEEN iterations per
                ; empty `NEXT` -- two widen_src calls of seven bytes each -- because
                ; the loop variable is a faithful 14-digit BCD double that for_get
                ; unpacks and for_set repacks every iteration. It is ~15 % of an empty
                ; FOR/NEXT profile (scratchpad/nextcost_counts.out).
                ; ⚠️ The earlier `push af`/`pop af` this replaces was already removed
                ; by D-MULZERO's follow-on; C was its stand-in and is now free for the
                ; mask. `widen_src` documents C as clobbered and nothing after the
                ; loop reads it (zero_fill touches only A, B, HL).
                ld      a,(de)
                rrca
                rrca
                rrca
                rrca
                and     c
                ld      (hl),a
                inc     hl
                ld      a,(de)
                and     c
                ld      (hl),a
                inc     hl
                inc     de
                djnz    wsrc_unpack
                push    hl                  ; save the dest write cursor across the
                                            ; re-read below (its own indirection needs
                                            ; HL as scratch)
                ld      hl,(WSRC_TYP)
                ld      a,(hl)
                pop     hl
                cp      8
                ld      b,9
                jr      nz,wsrc_padcount
                ld      b,1
wsrc_padcount:
                jp      zero_fill           ; tail call

; --- widen_int_to: HL = dest FPNUM base, DE = SIGNED int16 value -> fills --
; dest. Derives sign+magnitude then falls into widen_uint_to's body (below),
; which already does the binary->BCD digit work; widen_uint_to's own zero-
; check subsumes DE==0 here (sign positive, magnitude 0), so no separate
; zero case is needed. Clobbers as widen_uint_to.
widen_int_to:
                push    hl                  ; guard dest (abs16 clobbers DE)
                ex      de,hl               ; HL = value
                call    abs16               ; HL=|value|, A=sign
                ex      de,hl               ; DE = |value|
                pop     hl                  ; HL = dest restored
                jp      widen_uint_to

; =============================================================================
; LHS machine-stack frame (spec §1 bullet 4) + operand dispatch helpers
; =============================================================================

; --- push_lhs_frame: push FACTYP + FAC (10 bytes, as 5 word-pushes) onto the
; Z80 machine stack, where they must STAY (as a persistent frame for the
; matching combine_* to pop later) even though this routine itself needs to
; return. A bare "ret" at the end would be wrong: by the time it runs, the
; 5 words just pushed sit ON TOP of the "call push_lhs_frame" return address
; (pushes grow downward), so a plain "ret" would pop OUR OWN FIRST-PUSHED
; word and treat it as a jump target instead of returning to the caller.
; Fixed by popping the return address off FIRST (out of the way of the
; frame pushes), then pushing it back on top right before the final ret --
; own design, the standard "preserve a persistent stack frame across a call
; boundary" idiom. Uses DE as the stash (safe here because at all 6 call
; sites -- evr_rhs, ev_e_add, ev_e_sub, ev_t_mul, ev_t_div, ev_pw_lp -- the very
; next thing the caller does after this call is invoke the rhs sub-evaluator,
; which overwrites DE with the rhs value before DE is ever read again; the
; lhs value this DE might have held was already pushed to the stack by the
; caller BEFORE this call). The matching pop side (pop_lhs_and_probe,
; below) can't use this same trick -- ITS callers need DE preserved -- so
; it avoids the whole hazard a different way: see its own header comment.
; Called right after the caller has already pushed the LHS's plain DE
; value, so the two together form one fixed-size frame the matching
; combine_* pops in the opposite order. Clobbers A, DE, HL.
; ⛔ AND THAT IS ALSO WHY `push de / call push_lhs_frame / call
; set_factyp_int_ret` MUST STAY OPEN-CODED AT ALL SIX SITES. It is the
; top-ranked live candidate in `ngram_sweep --main` (6 sites x 7 B) and it is
; DECLINED, 2026-08-29, for a structural reason rather than a measured one:
;   * The run is a FIXED-SIZE FRAME PROTOCOL. The caller's `push de` and this
;     routine's five word-pushes must end up CONTIGUOUS, because the matching
;     combine_* pops them as one frame. Put the run behind a `call` and that
;     helper's own return address is pushed BETWEEN the two -- it lands INSIDE
;     the frame. Exactly the D-NGRAM8 hazard, one level up.
;   * The one arrangement that avoids it is a helper that re-pushes its return
;     address under the frame and TAIL-JUMPS here (`pop hl / push de / push hl /
;     jp push_lhs_frame`), so this routine's own ret lands back in the original
;     caller. That works -- and it cannot carry the `set_factyp_int_ret` half,
;     because THIS ROUTINE CAPTURES (FACTYP) INTO THE FRAME (`ld a,(FACTYP) /
;     push af` below) and the reset to 2 must therefore happen AFTER it. Reduced
;     to just the frame half, the helper saves 1 B per site and costs 6, i.e.
;     ZERO.
;   * Stashing the return address in a register instead is blocked at the
;     largest site: `evr` (basic/expr.asm) holds the relation bits in BC across
;     this call and pushes them immediately after.
; 🎯 So the sweep will keep ranking it, and the answer will keep being no.
; [[a-shared-tail-is-not-a-decision]]
push_lhs_frame:
                pop     de                  ; DE = our own return address (taken
                                            ; off the stack so it's not in the way)
                ld      hl,(FAC+6)
                push    hl
                ld      hl,(FAC+4)
                push    hl
                ld      hl,(FAC+2)
                push    hl
                ld      hl,(FAC+0)
                push    hl
                ld      a,(FACTYP)
                push    af
                push    de                  ; return address back on top of the
                                            ; frame we just pushed
                ret

; --- pop_lhs_and_probe: shared preamble for combine_add/sub/mul/cmp -------
; (below): pops the lhs frame (FACTYP+FAC, written by push_lhs_frame above),
; then the lhs value (into FP_LHSVAL). TWO return addresses sit on top of
; that frame by the time this runs, not one: this routine's own (pushed by
; "call pop_lhs_and_probe") AND its DIRECT caller's -- combine_add/sub/mul/
; cmp/div_float is itself reached via a plain "call" from an ev_* site made
; AFTER push_lhs_frame already ran, so that combine_* return address is
; ALSO sitting on top of the frame, one slot further down, for the entire
; time combine_* is running (an earlier version of this fix only accounted
; for one level and got the frame data wrong as a result -- caught by the
; eval() integration tests reading back a corrupted LHS_FACTYP). Fixed by
; stashing BOTH in RAM (PLF_RA = ours, PLF_RA2 = our caller's -- neither is
; a register, since DE and BC must both stay live across this call for
; various combine_* callers) before touching the frame, then restoring
; PLF_RA2 to the stack first (so it's sitting exactly where combine_* will
; expect its own eventual return address to be) and finally jumping to
; PLF_RA (a "jp (hl)" is equivalent to a "ret" here but doesn't need the
; target on the stack first). Note LD/PUSH/JP(HL) never touch flags on the
; Z80, so the ZF the final "cp 2" sets for our caller survives this restore
; untouched. out: ZF set iff both LHS_FACTYP and the current (rhs) FACTYP
; are int (==2); ZF clear (and A holds the mismatching FACTYP value)
; otherwise. Clobbers A, HL (DE, BC preserved).
pop_lhs_and_probe:
                pop     hl                  ; HL = our own return address
                ld      (PLF_RA),hl
                pop     hl                  ; HL = our direct caller's (combine_*'s
                                            ; own) return address
                ld      (PLF_RA2),hl
                pop     af
                ld      (LHS_FACTYP),a
                pop     hl
                ld      (LHS_FAC+0),hl
                pop     hl
                ld      (LHS_FAC+2),hl
                pop     hl
                ld      (LHS_FAC+4),hl
                pop     hl
                ld      (LHS_FAC+6),hl
                pop     hl
                ld      (FP_LHSVAL),hl
                ; A still holds LHS_FACTYP's value here, untouched since the
                ; "pop af" above -- none of "pop hl" / "ld (nn),hl" affect A
                ; on the Z80, so no need to reload it from RAM
                cp      2
                jr      nz,plap_ret         ; NZ -> mismatch; ZF stays clear below
                call    factyp_is2
                                           ; ZF set iff both int
plap_ret:
                ld      hl,(PLF_RA2)        ; does not affect flags
                push    hl                  ; restore our caller's (combine_*'s
                                            ; own) return address to the stack,
                                            ; exactly where it needs to be for
                                            ; ITS eventual ret/tail-jump home
                ld      hl,(PLF_RA)         ; does not affect flags
                jp      (hl)                ; jump to OUR return address directly
                                            ; (cheaper than push+ret); does not
                                            ; affect flags -- ZF from the cp above
                                            ; reaches our caller intact

; --- set_factyp_int_ret: FACTYP := 2, ret. Shared tail for combine_add/sub/
; mul's int-fast-path success returns (the result value is already in DE).
; Clobbers A.
set_factyp_int_ret:
                jp      set_factyp2

; --- widen_lhs_operand: HL = dest FPNUM base. Dispatches on LHS_FACTYP to --
; either widen_int_to(FP_LHSVAL) or widen_lhsframe_to. Clobbers as whichever
; it calls.
widen_lhs_operand:
                push    hl
                ld      a,(LHS_FACTYP)
                cp      2
                pop     hl
                jr      nz,wlo_float
                ld      de,(FP_LHSVAL)
                jr      widen_int_to
wlo_float:
                jp      widen_lhsframe_to

; --- widen_rhs_operand: HL = dest FPNUM base, DE = the RHS's plain int -----
; value (used iff FACTYP==2). Dispatches on the CURRENT (live) FACTYP.
; Clobbers as whichever it calls.
widen_rhs_operand:
                push    hl
                call    factyp_is2
                pop     hl
                jr      nz,wro_float
                jr      widen_int_to
wro_float:
                jp      widen_fac_to

; --- widen_both_operands: DE = the rhs's plain int value -> stash into ----
; FP_TMP_B, widen ARGA<-lhs and ARGB<-rhs. Shared "enter the float path"
; prelude for combine_add/sub/mul/cmp/div_float (below) — every one of them
; does exactly this before calling its BCD op. Clobbers as widen_lhs_
; operand + widen_rhs_operand.
widen_both_operands:
                ld      (FP_TMP_B),de
                ld      hl,ARGA
                call    widen_lhs_operand
                ld      hl,ARGB
                ld      de,(FP_TMP_B)
                jr      widen_rhs_operand   ; tail call

; --- xor_sign: A = ARGA_SIGN XOR ARGB_SIGN, masked to bit 7 — the standard -
; "result sign" for * and / (spec §10.2). Shared by fp_mul and fp_div.
; Clobbers A, B.
xor_sign:
                ld      a,(ARGA+FPNUM_SIGN)
                ld      b,a
                ld      a,(ARGB+FPNUM_SIGN)
                xor     b
                and     $80
                ret

; =============================================================================
; mul16x16_32 — unsigned 16x16->32 multiply (int-overflow-promotion check)
; =============================================================================

; --- abs16: HL = signed int16 -> HL = |HL|, A = the original sign (0/$80). -
; Shared magnitude-extraction used by combine_mul (below) for both operands.
; Clobbers A, DE.
abs16:
                ld      a,h
                and     $80
                ret     z
                push    af
                ex      de,hl
                ld      hl,0
                or      a
                sbc     hl,de
                pop     af
                ret

; --- mul16x16_32: HL(multiplicand, unsigned) * DE(multiplier, unsigned) ----
; -> 32-bit unsigned product in (MUL32) [low16][high16], LE. Classic shift-
; double-and-add over 16 iterations, MSB-first on the multiplier; own-design
; extension of expr.asm's mul16 (which only keeps the low 16 bits) to the
; full width, needed to detect MSX-signed 16-bit multiply overflow (spec
; §10.2 int-overflow promotion) exactly rather than by wraparound. All
; working state in RAM except the loop counter (register pressure: operand +
; operand + 32-bit accumulator exceeds the comfortable register budget).
; Clobbers A, B, HL, DE.
mul16x16_32:
                ld      (MULCAND),hl
                ld      (MULTPLR),de
                ld      hl,MUL32
                ld      b,4
                call    zero_fill
                ld      b,16
m32_lp:
                ld      hl,(MUL32)
                add     hl,hl
                ld      (MUL32),hl
                ld      hl,(MUL32+2)
                adc     hl,hl
                ld      (MUL32+2),hl
                ld      hl,(MULTPLR)
                add     hl,hl
                ld      (MULTPLR),hl
                jr      nc,m32_skip
                ld      hl,(MUL32)
                ld      de,(MULCAND)
                add     hl,de
                ld      (MUL32),hl
                jr      nc,m32_skip
                ld      hl,(MUL32+2)
                inc     hl
                ld      (MUL32+2),hl
m32_skip:
                djnz    m32_lp
                ret

; =============================================================================
; combine_* — expr.asm binary-operator dispatch entry points (spec §1
; bullet 4)
; =============================================================================
; Called with: the LHS frame (FACTYP+FAC) already pushed via push_lhs_frame,
; the LHS's plain DE value pushed BEFORE that (so the stack, top to bottom,
; is [frame][lhs value][...caller's own frame]), and DE/FACTYP/FAC holding
; the just-evaluated RHS. Each pops the LHS frame + value, decides int-fast-
; path vs BCD-widen-and-combine, and returns DE=result with FACTYP set
; (2 for the int paths, 8 — via round_and_finalize — for any float path).

; --- caddsub_widen_both: widen FP_LHSVAL -> ARGA and FP_TMP_B -> ARGB (both
; plain int16 values) to double. Shared int-overflow-promotion prelude for
; combine_add/combine_sub AND combine_mul (below) — every "the int fast path
; overflowed, redo it in BCD" tail starts here, differing only in which BCD
; op the caller goes on to call. Clobbers A, B, C, D, E, H, L.
caddsub_widen_both:
                ld      hl,ARGA
                ld      de,(FP_LHSVAL)
                call    widen_int_to
                ld      hl,ARGB
                ld      de,(FP_TMP_B)
                jp      widen_int_to        ; tail call

; --- combine_add / combine_sub: ev_e's '+'/'-' sites. Two thin entry points
; sharing one body (FP_OPMODE, own scratch, 0=add/1=sub) — the int fast path
; differs only in adc-vs-sbc (both set P/V on signed 16-bit overflow, unlike
; plain ADD HL,ss) and which BCD op to promote into; the float path differs
; only in which BCD op to call. Clobbers A, B, C, D, E, H, L.
combine_add:
                xor     a
                jr      caddsub_go
combine_sub:
                ld      a,1
caddsub_go:
                ld      (FP_OPMODE),a
                call    pop_lhs_and_probe
                jr      nz,caddsub_float
                ld      (FP_TMP_B),de
                ld      hl,(FP_LHSVAL)
                ld      a,(FP_OPMODE)
                or      a                   ; CF=0 (needed by adc/sbc) + tests the mode
                jr      nz,caddsub_int_sub
                adc     hl,de
                jr      caddsub_int_check
caddsub_int_sub:
                sbc     hl,de
caddsub_int_check:
                jp      po,caddsub_ok       ; P/V clear -> no signed overflow
                ; Overflowed. The reference promotes to a double — EXCEPT for a
                ; SUBTRACT whose RHS is $8000, where its own int subtract wraps
                ; mod 65536 and never promotes: `0-cint(-32768)` prints -32768,
                ; `1-cint(-32768)` prints -32767, `100-cint(-32768)` prints
                ; -32668, `32767-cint(-32768)` prints -1 (MEASURED at all four,
                ; docs/fixpoint8000-msx1-sweep.md §5.4). $8000 is its own two's-
                ; complement negation, so an `a + neg16(b)` subtract cannot see
                ; the overflow at all. `sbc hl,de` has ALREADY produced exactly
                ; the wrapped value, so the whole quirk is a SUPPRESSED
                ; promotion — no arithmetic changes. '+' is NOT exempt:
                ; `(-32768\1)+(-32768\1)` promotes to -65536 (measured), which
                ; is why the operation mode is tested and not just DE.
                or      a                   ; A still holds FP_OPMODE — nothing
                                            ; between its load and here touches A
                jr      z,caddsub_ovf       ; '+' -> always promote
                ld      a,d
                xor     $80
                or      e
                jr      z,caddsub_ok        ; '-' with RHS $8000 -> stay int
caddsub_ovf:
                call    caddsub_widen_both
                ld      a,(FP_OPMODE)
                or      a
                jp      z,fp_add
                jp      fp_sub
caddsub_ok:
                ex      de,hl
                jp      set_factyp_int_ret
caddsub_float:
                call    widen_both_operands
                ld      a,(FP_OPMODE)
                or      a
                jp      z,fp_add
                jp      fp_sub

; --- combine_mul: ev_t's '*' site. int path checks the SIGNED 16-bit product
; against the sign-dependent bound (32767 positive / 32768 negative) via a
; full unsigned 32-bit magnitude product (mul16x16_32) — mul16's low-16-only
; result can't distinguish "exact" from "wrapped".
combine_mul:
                call    pop_lhs_and_probe
                jr      nz,cmul_float
                ld      (FP_TMP_B),de
                ld      hl,(FP_LHSVAL)
                call    abs16               ; HL=|lhs|, A=lhs sign (0/$80)
                ld      (FP_RSIGN),a
                push    hl                  ; |lhs|
                ld      hl,(FP_TMP_B)
                call    abs16               ; HL=|rhs|, A=rhs sign
                or      a
                jr      z,cmul_rmag_ok
                ld      a,(FP_RSIGN)
                xor     $80
                ld      (FP_RSIGN),a
cmul_rmag_ok:
                ex      de,hl               ; DE = |rhs|
                pop     hl                  ; HL = |lhs|
                call    mul16x16_32         ; -> MUL32 (32-bit unsigned product)
                ld      hl,(MUL32+2)
                ld      a,h
                or      l
                jr      nz,cmul_overflow    ; high word nonzero -> definitely > 32768
                ld      hl,(MUL32)
                ld      a,(FP_RSIGN)
                ld      de,32768
                or      a
                jr      nz,cmul_boundcmp    ; negative -> bound stays 32768
                dec     de                  ; positive -> bound 32767
cmul_boundcmp:
                or      a
                sbc     hl,de               ; unsigned compare (a signed cmp16_bits
                                            ; would misread the 32768 bound as negative)
                jr      z,cmul_inrange
                jr      nc,cmul_overflow    ; HL>DE, no borrow -> over the bound
cmul_inrange:
                ld      de,(MUL32)
                ld      a,(FP_RSIGN)
                or      a
                jr      z,cmul_int_ok
                call    neg_de              ; DE = -DE (float.asm)
cmul_int_ok:
                jp      set_factyp_int_ret
cmul_overflow:
                call    caddsub_widen_both
                jp      fp_mul
cmul_float:
                call    widen_both_operands
                jp      fp_mul

; --- combine_div_float: ev_t's '/' site. ALWAYS float ----------------------
; (spec §10.1: "'/' is always real division, always double").
combine_div_float:
                call    pop_lhs_and_probe   ; ZF result ignored -- '/' is always
                                            ; float regardless (spec §10.1)
                call    widen_both_operands
                jp      fp_div

; =============================================================================
; combine_pow -- ev_pw's `^` site (math pack slice 2c, docs/spec-basic-
; mathpack-slice2.md §13.4). ALWAYS float (like combine_div_float); every
; disposition/classification decision is done MAIN-SIDE (never in the
; tenant): `A` is NOT preserved across CALSLT (the SQR/ATN/EXP/LOG lesson,
; subrom-mathpack §3), so a domain/error status byte can't ride back from
; fp_pow in a register -- only FPERR (a RAM flag) and CF (subrom_call's own
; "sub-ROM absent" signal) are reliable. Classifying y here also means the
; tenant never needs an fp_cmp against literal "32767"/"32768" bounds: this
; routine reads ARGB's own dexp/digit fields directly (pure 16-bit/digit-
; array work, no fp_* calls) and hands the tenant a pre-decided (n, mode)
; pair in MATH_N/MATH_J.
;
; Ladder (§13.1, evaluated in this order -- each rule pinned by capture):
;   1) y==0            -> result 1.0 (double), incl. 0^0=1.
;   2) x==0             -> y>0: 0 ; y<0: Division by zero (FPERR=2).
;   3) y integer-valued AND -32768<=y<=32767 -> INT PATH: n:=|y| (uint16,
;      32768 representable), MATH_N:=n, MATH_J bit0:=(y<0), bit7:=0.
;      "integer-valued" = every digit at index>=dexp is 0, for 1<=dexp<=5
;      (dexp<=0 -> fractional; dexp>5 -> out of int16 -> fractional). At
;      dexp==5 the 5-digit integer part must ALSO clear the asymmetric bound
;      (32767 if y>=0, 32768 if y<0) or it falls through to fractional
;      (pins `(-1)^32768` -> Illegal function call vs `(-1)^-32768`=1, §13.1).
;   4) else (fractional y, or integer-valued y outside int16): x<0 ->
;      Illegal function call (FPERR=3); x>0 -> dispatch the tenant's
;      EXP(y*LOG(x)) path, MATH_J:=$80.
;
; The tenant (sub/fp_pow.asm, SUBROM_IDX_POW) receives x in ARGA, y in ARGB
; (untouched by this classification -- needed verbatim by the frac path),
; n in MATH_N, mode/sign in MATH_J; it is COMPUTE-ONLY (leaves FAC correct,
; errors via FPERR only), so the tail here is evmc_log's exact shape:
; FACTYP:=8 + flt_to_int16, unconditionally, after the CALSLT -- a FPERR set
; inside the tenant is caught by the interpreter's own statement-boundary
; check (D-F2-1), not here.
combine_pow:
                call    pop_lhs_and_probe   ; ZF ignored -- ^ is always float
                call    widen_both_operands ; ARGA := x (lhs), ARGB := y (rhs)

                ; --- 1) y == 0 -> result 1.0 (double), incl. 0^0=1 ---------
                ld      hl,ARGB+FPNUM_DIG
                call    dig15_iszero
                jr      nz,cpow_y_nonzero
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGA := 1.0 (exact)
                jp      round_and_finalize  ; FAC:=1.0 double, FACTYP:=8, DE
cpow_y_nonzero:
                ; --- 2) x == 0: y>0 -> 0 ; y<0 -> Division by zero ---------
                call    arga_dig_iszero
                jr      nz,cpow_x_nonzero
                ld      a,(ARGB+FPNUM_SIGN)
                or      a
                jr      z,cpow_x0_pos
                ld      a,2
                call    penderr_set         ; Division by zero
cpow_x0_pos:
                xor     a
                ld      (FAC),a             ; FAC := 0 (double lead byte)
                call    fac_zero_mantissa   ; D-FACZERO: ...and its mantissa.
                                            ; This label IS `raf_zero_ok`, the
                                            ; shared zero-pack tail every
                                            ; fp_* underflow jumps to.
                ld      a,8
                ld      (FACTYP),a
                jp      ret_de0
cpow_x_nonzero:
                ; --- 3) classify y (ARGB record; no fp_* calls needed) -----
                ld      hl,(ARGB+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,cpow_frac         ; dexp<0 -> fractional
                ld      a,l
                or      a
                jr      z,cpow_frac         ; dexp==0 -> fractional
                cp      6
                jr      nc,cpow_frac        ; dexp>5 -> out of int16 -> frac
                ; 1<=dexp<=5: integer-valued iff dig[dexp..13] are all 0
                ld      c,a                 ; C := dexp (survives the scan)
                ld      e,a
                ld      d,0
                ld      hl,ARGB+FPNUM_DIG
                add     hl,de               ; HL -> dig[dexp]
                ld      a,14
                sub     c
                ld      b,a                 ; B := 14-dexp (fractional digits)
cpow_intscan:
                ld      a,(hl)
                or      a
                jr      nz,cpow_frac        ; a nonzero fractional digit -> frac
                inc     hl
                djnz    cpow_intscan
                ld      a,c
                cp      5
                jr      z,cpow_dexp5
                ; 1<=dexp<=4: n := digits[0..dexp-1] (always <= 9999)
                ld      hl,ARGB+FPNUM_DIG
                ld      b,c
                call    dig_to_word         ; DE := n
                jr      cpow_int_have_n
cpow_dexp5:
                ; dexp==5: asymmetric bound compare vs 32767(y>=0)/32768(y<0)
                ; (own float.asm resident tkf_ref32767/32768 tables, the same
                ; unpacked-digit bound compare domain_convert_core/dcc_bound5
                ; use for POKE/HEX$'s address-domain conversion)
                ld      de,tkf_ref32768
                ld      a,(ARGB+FPNUM_SIGN)
                or      a
                jr      nz,cpow_d5_cmp
                ld      de,tkf_ref32767
cpow_d5_cmp:
                push    de
                ld      hl,ARGB+FPNUM_DIG
                ld      b,5
                call    dig15_cmp           ; A=1(<)/2(=)/4(>)
                pop     de
                cp      4
                jr      z,cpow_frac         ; > bound -> fractional path
                ld      hl,ARGB+FPNUM_DIG
                ld      b,5
                call    dig_to_word         ; DE := n (0..32768)
cpow_int_have_n:
                ld      (MATH_N),de
                ld      a,(ARGB+FPNUM_SIGN)
                or      a
                jr      z,cpow_j_int_pos
                ld      a,1
                jr      cpow_j_int_store
cpow_j_int_pos:
                xor     a
cpow_j_int_store:
                ld      (MATH_J),a          ; bit0 = y negative, bit7 = 0 (int)
                jr      cpow_dispatch
cpow_frac:
                ; --- 4) fractional y (or int-valued y outside int16) -------
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,cpow_frac_ok
                ld      a,3
                ; 🎯 D-PENDTAIL: THE CANONICAL "DEFER CODE A, RETURN DE=0" TAIL.
                ; Four sites had these three instructions verbatim; this one keeps
                ; them and the other three `jp` here, so the shared body costs no
                ; new bytes at all -- it is an existing tail given a name.
                ; ⚠️ THIS IS NOT THE `ev_f_err` SHAPE, WHICH D-EVFERR DECLINED.
                ; There, jumping to the shared tail WOULD HAVE MADE THE DECISION
                ; ("fail with no error code"), and that measured wrong at all seven
                ; sites. Here the decision is the error CODE, it is made by the
                ; `ld a,<code>` that stays at each site, and only the mechanical
                ; call-and-return-zero is shared [[a-shared-tail-is-not-a-decision]].
penderr_de0:
                call    penderr_set         ; illegal function call
                jp      ret_de0
cpow_frac_ok:
                ld      a,$80
                ld      (MATH_J),a          ; bit7 = 1 (frac path)
cpow_dispatch:
                push    ix                  ; save the parser's text-position
                                            ; pointer -- subrom_call/CALSLT
                                            ; clobbers ALL registers, and IX
                                            ; IS the token cursor here (same
                                            ; discipline as evmc_sqr/atn/log)
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_POW
                call    subrom_call         ; CF=1 iff sub-ROM absent. Result
                                            ; in FAC (COMPUTE-ONLY tenant).
                pop     ix
                jp      c,subrom_absent_error
                jp      fac_dbl_int16       ; D-NGRAM14

; --- combine_cmp: ev_rel's numeric-compare site. Both-int -> the EXISTING --
; cmp16_bits (byte-for-byte the same as before, tail-called). Any float ->
; widen both to double + fp_cmp. Result FACTYP is always reset to 2 (a
; relational always yields an int -1/0), and the relation bit is returned in
; A the same way cmp16_bits' caller (ev_rel, expr.asm) already expects.
; PRESERVES BC: ev_rel still holds the REQUESTED relation bits in C across
; this call (its `and c` intersect comes right after) — cmp16_bits leaves BC
; alone so the int path is safe as-is, but the float path's widen/BCD core
; clobbers everything, so it must save/restore BC itself. (Found in F2
; review by the full differential gate: with C trashed to a constant that
; happened to hold the =/> bits, every float `=`/`>` compare passed and
; every float `<`/`<>`/`<=` compare answered wrong — `1.5<1.4` -> -1.)
combine_cmp:
                call    pop_lhs_and_probe
                jr      nz,ccmp_float
                call    set_factyp2
                ld      hl,(FP_LHSVAL)
                jp      cmp16_bits          ; tail call: A = relation bit
ccmp_float:
                push    bc                  ; C = ev_rel's requested relation bits
                call    widen_both_operands
                call    fp_cmp
                ld      e,a                 ; E = relation bit (DE is dead here —
                                            ; ev_rel overwrites DE with the -1/0
                                            ; result right after the intersect)
                call    set_factyp2
                pop     bc
                ld      a,e
                ret

; =============================================================================
; Signed \ and MOD (D-C migration, spec §10.4), repack build only
; =============================================================================

; --- sdivmod_zerocheck: DE=dividend, BC=divisor -> divisor-0 shared gate. --
; Both signed_div_de_bc and signed_mod_de_bc start here: divisor 0 -> FPERR=2
; (division by zero), DE=0, RET (to the CALLER's caller — this "pops" the
; thin entry point too, since there is nothing left for it to do). Otherwise
; falls into sdivmod_mag below. Clobbers A.
sdivmod_zerocheck:
                ld      a,b
                or      c
                ret     nz
                pop     hl                  ; discard the return into signed_div_de_bc/
                                            ; signed_mod_de_bc (own-design early-out; see
                                            ; header)
                ld      a,2
                jr      penderr_de0         ; D-PENDTAIL (-4 B, low region)

; --- sdivmod_mag: DE=dividend, BC=divisor (both SIGNED int16, divisor -----
; already confirmed nonzero) -> DE=quotient magnitude, HL=remainder
; magnitude, (FP_RSIGN)=the DIVIDEND's sign (0/$80) — exactly what
; signed_mod_de_bc needs as its own result sign, and half of what
; signed_div_de_bc needs (XORed with the divisor's sign, computed inline
; where it's used since only one caller needs it). Clobbers A, B, C, D, E,
; H, L.
sdivmod_mag:
                ex      de,hl               ; HL = dividend
                call    abs16               ; HL=|dividend|, A=dividend's sign
                ld      (FP_RSIGN),a
                push    hl                  ; guard |dividend| (abs16 clobbers DE)
                ld      h,b
                ld      l,c                 ; HL = divisor
                call    abs16               ; HL=|divisor|, A=divisor's sign (unused)
                ld      b,h
                ld      c,l                 ; BC = |divisor|
                pop     de                  ; DE = |dividend|
                jp      udiv16              ; tail call: DE=quotient(mag), HL=
                                            ; remainder(mag) (expr.asm)

; --- signed_div_de_bc: DE=dividend, BC=divisor (both SIGNED int16) -------
; -> DE = truncating signed quotient. Divisor 0 -> FPERR=2 (division by
; zero), DE=0. Quirk (spec §10.4): -32768\-1 -> +32768, which escapes int16
; without an error — realised by promoting that one case to a double (FAC :=
; 32768.0, FACTYP=8, DE := silent flt_to_int16 of it). Clobbers A, B, C, D,
; E, H, L.
signed_div_de_bc:
                call    sdivmod_zerocheck
                ld      a,b                 ; B/D (divisor/dividend high bytes) still
                                            ; hold their ORIGINAL signed values here —
                                            ; sdivmod_mag hasn't run yet, so their sign
                                            ; bits are still live
                xor     d
                and     $80
                push    af                  ; stash the quotient's intended sign (XOR)
                                            ; across sdivmod_mag, which overwrites B/D
                                            ; with magnitude values
                call    sdivmod_mag         ; DE=quot(mag), (FP_RSIGN)=dividend sign
                pop     af
                ld      (FP_RSIGN),a        ; overwrite with the quotient's own sign
                or      a
                jr      z,sdiv_applied
                call    neg_de              ; DE = -DE (float.asm)
sdiv_applied:
                ld      a,(FP_RSIGN)
                or      a
                jr      nz,sdiv_ret         ; a negative-signed quotient never escapes
                                            ; int16 this way (min reachable magnitude is
                                            ; 32768 only for the +32768 case below)
                ld      a,d
                cp      $80
                jr      nz,sdiv_ret
                ld      a,e
                or      a
                jr      nz,sdiv_ret
                ; DE == $8000 with the intended sign positive -> the true value
                ; is +32768, which does not fit int16: promote to double.
                jp      flt_ret_32768       ; D-CARVE2 (-10 B, low region)
sdiv_ret:
                ret

; --- signed_mod_de_bc: DE=dividend, BC=divisor (both SIGNED int16) -------
; -> DE = truncating signed remainder (sign = the DIVIDEND's sign, spec
; §10.4). Divisor 0 -> FPERR=2, DE=0. Never escapes int16 (|remainder| <
; |divisor| <= 32768). Clobbers A, B, C, D, E, H, L.
signed_mod_de_bc:
                call    sdivmod_zerocheck
                call    sdivmod_mag         ; HL=remainder(mag), (FP_RSIGN)=dividend sign
                ex      de,hl               ; DE = remainder magnitude
                ld      a,(FP_RSIGN)
                or      a
                ret     z
                jp      neg_de              ; DE = -DE (float.asm)

; --- widen_uint_to: HL = dest FPNUM base, A = sign (0/$80), DE = UNSIGNED --
; magnitude (0..65535) -> fills dest. Same digit-collection technique as
; widen_int_to, but takes an already-separated sign+magnitude pair (needed
; for the -32768\-1 escape quirk above, whose true magnitude is 32768 — a
; value a SIGNED int16 register cannot hold, so widen_int_to's own sign-
; from-bit15 derivation cannot be used here). Clobbers A, B, C, D, E, H, L.
widen_uint_to:
                push    hl
                push    af
                ld      a,d
                or      e
                jr      nz,wu_nz0
                pop     af
                pop     hl                  ; HL = dest base (no caller needs it back
                                            ; after this routine, so no final restore)
                ld      b,18
                jp      zero_fill           ; tail call
wu_nz0:
                ex      de,hl               ; HL = magnitude
                ld      de,WIDIG
                ld      c,0                 ; C = digit count (NOT B: div10, print.asm,
                                            ; clobbers B internally for its own 16-step
                                            ; loop, which would silently reset a B-held
                                            ; counter here every iteration — found live
                                            ; in review, see the F2 close-out report)
wu_digloop:
                call    div10
                ld      (de),a
                inc     de
                inc     c
                ld      a,h
                or      l
                jr      nz,wu_digloop
                ld      a,c
                ld      (MUL_I),a
                pop     af                  ; sign
                pop     hl                  ; dest base
                and     $80
                ld      (hl),a
                inc     hl
                ld      a,(MUL_I)
                ld      e,a
                ld      d,0
                ld      (hl),e
                inc     hl
                ld      (hl),0
                inc     hl
                push    hl
                ld      b,15
                call    zero_fill
                pop     hl
                ld      a,(MUL_I)
                ld      c,a
                dec     a
                ld      e,a
                ld      d,0
                push    hl
                ld      hl,WIDIG
                add     hl,de
                ex      de,hl
                pop     hl
                ld      b,c
wu_rev_lp:
                ld      a,(de)
                ld      (hl),a
                inc     hl
                dec     de
                djnz    wu_rev_lp
                ret

; =============================================================================
; fp_trunc — math pack slice 1a: float->float truncate-toward-zero primitive
; (docs/spec-basic-math-pack.md §9.2). The one new page-0 numeric primitive
; the slice adds; every other slice-1a routine (ABS/SGN/INT/FIX/CINT/CSNG/
; CDBL) lives in expr.asm (page 1) as a thin wrapper, per the spec's home
; decision (§9: "the one new numeric primitive in the page-0 low region
; alongside the other fp_* -- it is a shared leaf").
; =============================================================================

; --- fp_trunc: ARGA (an already-widened FPNUM: sign/dexp/dig[0..13]; guard --
; dig[14] not read) -> zero every mantissa digit at or past the decimal point,
; leaving the integer part untouched -- truncation toward 0. In place on
; ARGA; does NOT pack FAC or touch FACTYP (the expr.asm callers do that once
; they know which precision to preserve -- INT/FIX may return single OR
; double, unlike every other fp_* op here which always promotes to double).
; out: CF set iff at least one nonzero digit was dropped (INT's caller uses
; this to decide its -1 floor adjustment on a negative operand; FIX ignores
; it). Same dexp<=0 "-> |x|<1" classification domain_convert_core already
; uses (own design, same idiom reused). Clobbers A, B, C, D, E, H, L.
fp_trunc:
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,h
                or      a
                jp      m,fpt_allfrac       ; dexp<0 -> |x|<1, whole mantissa is fraction
                ld      a,l
                or      a
                jr      z,fpt_allfrac       ; dexp==0 -> also |x|<1 (dcc_zero's own rule)
                cp      14
                jr      nc,fpt_none         ; dexp>=14 -> already a full-range integer,
                                            ; no fractional digit exists to drop
                ; 1<=dexp<=13: zero dig[dexp..13] (14-dexp digits), reporting
                ; whether any of them was nonzero before clearing
                ld      e,a                 ; E = dexp
                ld      d,0
                ld      hl,ARGA+FPNUM_DIG
                add     hl,de               ; HL = &dig[dexp]
                ld      a,14
                sub     e
                ld      b,a                 ; B = count = 14-dexp
                ld      c,0                 ; C = "any nonzero" accumulator
fpt_lp:
                ld      a,(hl)
                or      c
                ld      c,a
                xor     a
                ld      (hl),a
                inc     hl
                djnz    fpt_lp
                ld      a,c
                or      a
                ret     z
                scf
                ret
fpt_none:
                or      a
                ret
fpt_allfrac:
                call    arga_dig_iszero
                                           ; ZF set iff ARGA was already the canonical
                                            ; zero (0 flags no fraction was dropped)
                push    af
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_zero15
                pop     af
                ret     z
                scf
                ret

