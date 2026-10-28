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
; every alignment/normalisation shift as a straight memmove. ⚠️ fp_div is the
; exception since D-DIVPACK (2026-10-20): its remainder and divisor are PACKED
; inside the divide (two digits a byte, `sbc`+`daa`, an `rld` for *10) -- its
; inputs and its ARGA answer are the same digit arrays as everyone else's.
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
                jp      m,c16_gt            ; V set  -> less iff S clear
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
                jr      nc,dsi_st           ; no borrow: CF is already 0
                add     a,10                ; A was $F6..$FF: +10 always carries
                                            ; out, so CF=1 IS the borrow
dsi_st:
                ; 🏎️ T5 (2026-09-26): this loop WAS fp_div's inner loop and ~50% of
                ; a SQR's time (PC samples) -- until D-DIVPACK (2026-10-20) gave
                ; fp_div its own packed-BCD loop; fp_add/fp_sub are the callers
                ; now. It carried an `or a` on the no-borrow
                ; path and `scf` + `jr` on the borrow path that set a carry the
                ; `sbc` / `add a,10` had ALREADY set -- 4 bytes, and 70/84 T a
                ; digit down to 66/68. dec/dec/djnz leave CF alone.
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
; 📌 D-BASICINT PIN $3297 (2026-10-15): games (Harry Fox) jump to the reference's
; $3297, which the VG-8020 measured as `pop hl / ret` (scratchpad/basicint_pop.out:
; HL = the pushed word, BC / DE untouched). FIXED ADDRESS -- placed by
; tools/pin_plan.py after an unconditional transfer; the `ds` is the pad, and
; `pin_plan.py --check` fails if it grows (Joost: no growing holes).
    IF BASICINT_PINS
                ds      $3297 - $, $00
basicint_3297:
                pop     hl
                ret
    ENDIF
dshr_allzero:
                jp      dig15_zero15

; --- dig15_shl: shift the 15-byte digit array at (HL) left by -------------
; (FP_SHIFTAMT) positions, zero-filling the vacated high end (used by the
; leading-zero normalise after subtract-cancellation; fp_div's "remainder
; *= 10" used it too until D-DIVPACK's nibble rotate). HL NOT preserved (same
; rationale as dig15_shr).
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
                ret     nc                  ; (was `jr nc,ai14_done`, a bare ret)
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
arga_dexp_inc:                              ; D-TAILMERGE: ARGA's decimal exponent + 1
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
fac_typ_int16:                              ; D-TAILIX2 (2026-10-03): FACTYP := A, then
                ld      (FACTYP),a          ; the int16 tail -- shared by the single
                jp      flt_to_int16        ; tail call: sets DE, returns to our caller
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to cpow_x0_pos,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
; (raf_zero_ok = cpow_x0_pos: its equ is in basic/aliases-early.inc -- pasmo 0.5.3, D-PASMO053)

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
                ret     nc                  ; (was `jr nc,ai6_done`, a bare ret)
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
                jp      arga_dexp_inc       ; D-TAILMERGE: the same 4-instruction tail

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
                jr      fac_typ_int16       ; D-TAILIX2: FACTYP := 4, DE := the int
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
                                            ; (low MULPROD) plus the max offset (27) never
                                            ; carries past $FF, so the low-byte-only
                                            ; add stays correct and H is always MULPROD's page
                ld      l,a
                ld      h,high MULPROD      ; MULPROD's page -- was the literal $F0, which no idiom scan sees (D-WSZERO s6 moved it)
    IF (MULPROD & $FF) + 14 + 27 > $FF
                db      MULPROD_TOO_CLOSE_TO_A_PAGE_END__LOW_BYTE_ADD_WOULD_CARRY
    ENDIF
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
; --- fpd_pack: HL -> a 14-digit unpacked array (MSD first), DE -> 8 bytes ---
; (no page crossing). Writes the digits PACKED, one nibble each, at nibbles
; 1..14 of the 16: (0,d0)(d1,d2)..(d11,d12)(d13,0). Reads d0..d13 only (the
; guard digit d14 is ignored, as the unpacked divide always ignored it).
; out: C = low byte of the address of the LAST nonzero packed byte (the
; first byte's own if all are zero). Clobbers A, B, C, E, HL.
fpd_pack:
                ld      c,e
                ld      b,7
                xor     a
fpk_lp:
                or      (hl)                ; A = (d[2i-1] << 4) | d[2i]
                inc     hl
                ld      (de),a
                jr      z,fpk_z
                ld      c,e
fpk_z:
                inc     e
                ld      a,(hl)
                inc     hl
                add     a,a
                add     a,a
                add     a,a
                add     a,a
                djnz    fpk_lp
                ld      (de),a              ; byte 7 = (d13,0)
                or      a
                ret     z
                ld      c,e
                ret

; --- fp_div: ARGA / ARGB -> ARGA -> round_and_finalize. Divisor 0 ---------
; -> Division-by-zero (FPERR=2). Overflow PRE-CHECK on stored dec_exps: e(a)-
; e(b)+1 > 63 -> Overflow (even when the true quotient would fit, spec
; §10.2); < -63 -> silent 0. Long division producing 15 quotient digits
; (14 + guard): per digit, remainder *= 10, then count how many times the
; divisor still goes in, subtracting it each time (own design: the classic
; restoring long division). Clobbers A, B, C, D, E, H, L.
;
; 🏎️ D-DIVPACK (2026-10-20, TIER 5): THE SAME COUNTS, FOUND OVER PACKED BCD.
; Division was 3.7x the VG-8020 (`A=I/7` x300: 614 TIME ticks vs 163), and a
; PC-sample profile had ~50% of a SQR in the unpacked digit-subtract loop. The
; remainder R (DIVREM) and the divisor B (DIVPAD) now hold two digits a byte,
; at nibbles 1..14 of 16 (fpd_pack): a trial subtract is `sbc`+`daa` per BYTE,
; *10 is one `rld` per byte, and both run only over the bytes that can matter --
; the subtract over 0..LB (B's last nonzero byte: B is 0 past it, so no borrow
; reaches past it), the *10 over 0..max(LA,LB) (R is 0 past both, always). The
; compare still runs over all 8 bytes, MSB first, early out -- past LB it reads
; B's zeros, which decide R >= B exactly as stopping there would.
; A ONE-DIGIT DIVISOR (LB = 0: B = (0,b0) -- I/7, X/2 in SQR, /10) takes
; fpd_one instead: the digit is R's byte 0 read as 0..99, divided by b0 in
; binary (the bytes past it are a fraction below 1 and cannot change it).
; WHY IT IS THE SAME ANSWER: every digit is the same integer count of the same
; two integers -- R and B are the unpacked arrays' values (the *10 drops a top
; nibble that is 0 because R < B), the count is the same 8-bit C the old
; MUL_CARRY was, and the dividend < divisor decision (one less exponent, digit 0
; after a shift) is still dig15_cmp over the UNPACKED 14 digits, so even an
; unnormalised operand (a POKEd variable; counts above 9 can happen) divides as
; it did. tests/test_fpdiv_fast.py runs the old image against this one: FAC,
; FACTYP, FPERR, ARGA, ARGB, registers and all RAM but this routine's own
; scratch, over 200000 random pairs + the walls, and through SQR/LOG/ATN/TAN/^.
; Host T-states: 300/7 110837 -> 12101, a 14-digit divisor ~2.2-2.5x.
; Scratch: DIVREM+0..7, DIVPAD+0..7, FPD_PB/FPD_SH/FPD_SLOT in DIVREM's spare
; bytes -- all inside the blocks the unpacked divide already owned; it no
; longer writes MUL_CARRY, FP_LHSVAL, FP_SHIFTAMT or FP_RSIGN (each is written
; by its every reader first). The sign goes straight to ARGA (xor_sign has
; read it; nothing reads ARGA's sign again before round_and_finalize).
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
                ld      (ARGA+FPNUM_SIGN),a
                ld      hl,ARGA+FPNUM_DIG
                ld      de,DIVREM
                call    fpd_pack            ; C = low (DIVREM + LA)
                ld      a,c
                ld      (FPD_SH),a
                ld      hl,ARGB+FPNUM_DIG
                ld      de,DIVPAD
                call    fpd_pack            ; C = low (DIVPAD + LB)
                ld      l,c
                ld      h,high DIVPAD
                ld      (FPD_PB),hl
                ld      a,c
                add     a,(low DIVREM) - (low DIVPAD)
                ld      hl,FPD_SH
                cp      (hl)
                jr      c,fpd_shok
                ld      (hl),a              ; FPD_SH = low (DIVREM + max(LA,LB))
fpd_shok:
                ld      hl,ARGA+FPNUM_DIG
                ld      de,ARGB+FPNUM_DIG
                ld      b,14
                call    dig15_cmp           ; A = 1 iff dividend < divisor
                ld      hl,(FP_TMP_B)
                dec     a
                jr      nz,fpd_ge
                dec     hl                  ; quotient < 1: one less, digit 0 shifts
fpd_ge:
                ld      (ARGA+FPNUM_DEXP),hl
                ld      a,low (ARGA+FPNUM_DIG)
                ld      (FPD_SLOT),a
                jr      nz,fpd_trial        ; (flags still from the `dec a`)
fpd_digit:
                ld      a,(FPD_SH)          ; R *= 10: one nibble left over bytes
                ld      l,a                 ; 0..max(LA,LB) -- past both, R is 0
                ld      h,high DIVREM
                sub     (low DIVREM) - 1
                ld      b,a
                xor     a
fps_lp:
                rld
                dec     l
                djnz    fps_lp
fpd_trial:
                ld      h,high DIVPAD
                ld      a,(FPD_PB)
                cp      low DIVPAD
                jr      z,fpd_one           ; a one-digit divisor: one binary divide
                ld      d,high DIVREM
                ld      c,0
ftr_lp:
                ld      l,low DIVPAD
                ld      e,low DIVREM
                ld      b,8
ftr_cmp:
                ld      a,(de)
                cp      (hl)                ; R - B, MSB first
                jr      c,ftr_done          ; R < B
                jr      nz,ftr_sub          ; R > B
                inc     l
                inc     e
                djnz    ftr_cmp             ; all equal: R = B, subtract
ftr_sub:
                ld      hl,(FPD_PB)
                ld      a,l
                add     a,(low DIVREM) - (low DIVPAD)
                ld      e,a
                sub     (low DIVREM) - 1    ; B = LB+1, and no borrow: CF = 0
                ld      b,a
ftr_slp:
                ld      a,(de)
                sbc     a,(hl)
                daa
                ld      (de),a
                dec     l
                dec     e
                djnz    ftr_slp
                inc     c
                jr      ftr_lp
fpd_one:
                ; B = (0,b0), b0 = 1..9, and R < 10*B: the digit is (R's byte 0,
                ; read as the number 0..99) / b0 -- the bytes past it are a
                ; fraction below 1 and cannot change the quotient -- and the
                ; remainder (< b0 <= 9) is that byte's new value, already BCD.
                ld      a,(DIVREM)
                ld      c,a
                and     $F0                 ; 16 * hi
                rrca
                ld      b,a                 ; 8 * hi
                rrca
                rrca
                add     a,b                 ; 10 * hi
                ld      b,a
                ld      a,c
                and     $0F
                add     a,b                 ; byte 0 as a binary number
                ld      l,low DIVPAD        ; (HL) = b0
                ld      c,$FF
fpo_lp:
                inc     c
                sub     (hl)
                jr      nc,fpo_lp
                add     a,(hl)
                ld      (DIVREM),a
ftr_done:
                ld      a,(FPD_SLOT)
                ld      l,a                 ; H = high DIVPAD = high ARGA (guarded)
                ld      (hl),c
                inc     a
                ld      (FPD_SLOT),a
                cp      low (ARGA+FPNUM_DIG+15)
                jr      nz,fpd_digit
                jp      round_and_finalize
    IF (high DIVPAD) != (high (ARGA+FPNUM_DIG)) || (high DIVPAD) != (high (ARGA+FPNUM_DIG+14))
                db      FPD_SLOT_NOT_IN_DIVPADS_PAGE
    ENDIF
    IF (high DIVPAD) != (high (DIVPAD+7)) || (high DIVREM) != (high (DIVREM+7))
                db      FPD_PACKED_ARRAY_CROSSES_A_PAGE
    ENDIF

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
                ld      a,1                 ; D-DEFERRSTUDY family 2: CINT, `\`, AND / OR
                jp      raise_now           ; / XOR / NOT operands raise AT ONCE, before
                                            ; FACTYP := 2 (CINT's VALTYP 4: herro3_run.out)

; --- eval_addr: HL(cursor) -> DE = a checked ADDRESS-domain int value, ----
; HL(cursor advanced). Thin wrapper combining eval + fac_to_int_addr — the
; shared shape POKE/VPOKE's argument parses both need (basic/poke.asm,
; basic/vdpio.asm). Clobbers as eval + fac_to_int_addr.
    IF BASICINT_PINS
                                            ; (eval_addr lives in basic/input.asm in
                                            ; the shipping build: it REFILLS the 9 B
                                            ; S10.C freed ahead of the pinned $3297,
                                            ; 2026-10-15 -- no growing holes)
    ELSE
eval_addr:
                call    eval
                push    hl
                call    fac_to_int_addr
                pop     hl
                ret
    ENDIF

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
; equally-shaped [lead+mantissa byte][type byte] sources — (WSRC) holds the
; source's mantissa address, and its TYPE rides in a register, as the reference
; passes the operand type in A (D-WSZERO S14g-b: WSRC_TYP, the type byte's
; ADDRESS in zerobas's own workspace, read twice through it, is gone). Fills dest:
; sign, dexp (signed -64..63), dig[0..13] (zero-padded to 14 for a single;
; dig[14]=0, meaningless for a freshly-unpacked operand). A source lead byte
; of 0 -> canonical zero (sign=0, dexp=0, all digits 0). Own design: same
; nibble-split technique as flt_out/flt_to_int16 (basic/float.asm), applied
; to a caller-chosen destination. Clobbers A, B, C, D, E, H, L.
widen_fac_to:
                ld      a,(FACTYP)          ; A = the type (2/4/8)
                ld      de,FAC
                jr      wsrc_go
widen_lhsframe_to:
                ld      a,(LHS_FACTYP)
                ld      de,LHS_FAC
wsrc_go:
                ld      (WSRC),de
                ld      b,a                 ; B = the type until the mantissa count:
                                            ; nothing below touches B before then
                push    hl                  ; dest base
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
                ld      a,b
                cp      8
                ld      b,7
                jr      z,wsrc_mbytes_ok
                ld      b,3
wsrc_mbytes_ok:
                push    af                  ; Z = double, kept across the loop
                                            ; (it makes no call)
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
                pop     af                  ; Z = double
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

; --- push_lhs_frame: DE = the lhs -> push the lhs frame, sized by its TYPE --
; (D-EVALSLOPE's typed-frame step, 2026-10-20) and FACTYP := 2. The frame the
; matching combine_* pops (pop_lhs_and_probe, basic/input.asm) is, top first:
;
;     [FACTYP]  then  int16 (2): the lhs DE                       -> 4 B
;                     single (4, or 3: < 5): FAC+0, FAC+2          -> 6 B
;                     double (8: > 5): FAC+0, +2, +4, +6           -> 10 B
;
; It used to be ONE fixed 12-byte shape for every type -- the caller's `push de`
; under FACTYP + all eight FAC bytes -- so a pending `1+(` held 20 B a level
; where the VG-8020 holds 16 (spec-basic-deepexpr-guard.md §5.3: 8 + the
; operand's width), and an arithmetic nest near the memory edge refused levels
; earlier than the reference (scratchpad/arithnest_run.out: depth 13 against 16
; with 400 B left). Each type now keeps only what its readers read:
;   * an int16 lhs is its DE -- FP_LHSVAL, the only cell combine_*'s int paths and
;     widen_lhs_operand read for it; LHS_FAC is never read when LHS_FACTYP = 2;
;   * a float lhs is its FAC bytes. Its DE was never read (FP_LHSVAL is read only
;     under LHS_FACTYP = 2: widen_lhs_operand, and the int paths after
;     pop_lhs_and_probe's Z), so it is no longer pushed at all;
;   * a single needs FAC+0..3 alone: widen_lhsframe_to (wsrc_go) reads the lead
;     byte and 3 mantissa bytes for ANY type but 8, and 7 for 8. The split is
;     `cp 5` on both sides, so 3 (and 0..4) take the short frame and 8 the long
;     one, exactly as wsrc_go reads them. No type is 5 (2 3 4 8 are the only
;     values FACTYP ever holds): pop_lhs_and_probe's NZ relies on it.
; So `1+(` holds 6 + 6 = 12 B a level, `1.5+(` 6 + 8 = 14 and `1#+(` 6 + 12 = 18
; (the climber's [entry] word included) -- the VG-8020's 16 / 18 / 22, or less.
;
; THE RETURN ADDRESS is popped into HL first, because the frame must stay ON the
; stack after this routine returns (it is the persistent frame combine_* pops
; later): pushes made on top of our own return address would bury it. The int
; path returns with `jp (hl)` (FACTYP is already 2); the float path moves the
; return address to DE (the float lhs's DE is dead, above), pushes the FAC words
; through HL, and resets FACTYP inline -- a `push de / jp set_factyp2` tail costs
; 23 T more, which the double path cannot pay (TIER 5: no path slower).
; ⛔ THE CALL ITSELF MUST STAY OPEN-CODED (`call push_lhs_frame`) at all four
; sites (the climber's two shifts, basic/expr.asm; NEXT's two, basic/program.asm):
; a helper wrapping it would land its own return address INSIDE the frame (the
; D-NGRAM8 hazard). Clobbers A, DE, HL; BC is kept (the climber's relational
; shift holds the relation bits in C across this call). Returns A = 2.
; GA-LHSTYP2 (2026-10-03): the reset to FACTYP 2 happens HERE, after the capture;
; FOR's two sites get the store for free (their very next call is slot_load).
push_lhs_frame:
                pop     hl                  ; HL = our own return address
                ld      a,(FACTYP)
                cp      2
                jr      nz,plf_fac
                push    de                  ; an int16 lhs: its value ...
                push    af                  ; ... under [FACTYP]
                jp      (hl)                ; FACTYP is already 2
plf_fac:
                ex      de,hl               ; DE = the return address
                cp      5
                jr      c,plf_sgl           ; single: FAC+0..3 only
                ld      hl,(FAC+6)
                push    hl
                ld      hl,(FAC+4)
                push    hl
plf_sgl:
                ld      hl,(FAC+2)
                push    hl
                ld      hl,(FAC+0)
                push    hl
                push    af                  ; [FACTYP] on top
                ld      a,2
                ld      (FACTYP),a          ; FACTYP := 2 AFTER the capture
                ex      de,hl
                jp      (hl)

; (pop_lhs_and_probe lives in basic/input.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)

; --- set_factyp_int_ret: FACTYP := 2, ret. Shared tail for combine_add/sub/
; mul's int-fast-path success returns (the result value is already in DE).
; Clobbers A. GA-LHSTYP2 (2026-10-03): an alias of expr.asm's set_factyp2 --
; it was a 3 B jump-to-jump (low -> page 1); the name is kept for its two
; `jp` users below and for the docs.
set_factyp_int_ret equ set_factyp2

; --- widen_lhs_operand: HL = dest FPNUM base. Dispatches on LHS_FACTYP to --
; either widen_int_to(FP_LHSVAL) or widen_lhsframe_to. Clobbers as whichever
; it calls.
; D-INTFAST (2026-10-20) carve: the `push hl` / `pop hl` that bracketed the type
; test here and in widen_rhs_operand guarded nothing -- `ld a,(nn)`, `cp n` and
; factyp_is2 (`ld a,(FACTYP)` / `cp 2`) never write HL -- and the `jr nz` to a
; `jp` is one `jp nz`. -6 B, the same registers out.
widen_lhs_operand:
                ld      a,(LHS_FACTYP)
                cp      2
                jp      nz,widen_lhsframe_to
                ld      de,(FP_LHSVAL)
                jr      widen_int_to

; --- widen_rhs_operand: HL = dest FPNUM base, DE = the RHS's plain int -----
; value (used iff FACTYP==2). Dispatches on the CURRENT (live) FACTYP.
; Clobbers as whichever it calls.
widen_rhs_operand:
                call    factyp_is2
                jr      z,widen_int_to
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
                call    neg_de_hl           ; D-NEGDE: HL = -DE
                pop     af
                ret

; (mul16x16_32 lives in basic/input.asm since D-WSZERO S16: it refills bytes the stack
; parameter block freed in front of a pinned address)

; =============================================================================
; combine_* — expr.asm binary-operator dispatch entry points (spec §1
; bullet 4)
; =============================================================================
; Called with: the LHS frame already pushed via push_lhs_frame -- [FACTYP] on
; top, then the lhs DE (an int16 lhs) or its 4 / 8 FAC bytes (a single / a
; double), sized by the type since D-EVALSLOPE's typed-frame step -- and
; DE/FACTYP/FAC holding the just-evaluated RHS. Each pops the frame (into
; LHS_FACTYP and FP_LHSVAL or LHS_FAC: pop_lhs_and_probe), decides int-fast-
; path vs BCD-widen-and-combine, and returns DE=result with FACTYP set
; (2 for the int paths, 8 — via round_and_finalize — for any float path).

; (caddsub_widen_both -- widen FP_LHSVAL / FP_TMP_B to ARGA / ARGB, the int
; paths' overflow prelude -- is GONE, D-INTFAST 2026-10-20: an int path that
; overflows now widens through widen_both_operands, which for two int16
; operands does exactly the same two widen_int_to calls (LHS_FACTYP = FACTYP = 2,
; FP_LHSVAL = the lhs, DE = the rhs), and which for the float path's exact-int16
; detour below widens the ORIGINAL float operands -- the old float path to the
; byte. -20 B, and the overflow tails shrank with it.)

; --- arga_dig_iszero: HL := ARGA+FPNUM_DIG, then dig15_iszero (D-PAIRCARVE2) ----
; 💰 The pair stood at SEVEN sites, 6 B each against 3 for a call. dig15_iszero
; preserves HL, so the caller sees HL = ARGA+FPNUM_DIG and Z exactly as the
; open-coded pair left them. Low region, not page 1: two of the sites are in the
; resident closure sub page-1 tenants reach (check_tenant_closure).
; MOVED HERE (D-EVALSLOPE's typed-frame step, 2026-10-20) from basic/str-engine.asm,
; whole and self-contained (entered only by label, ends in a `jp`): it was in front
; of the $3297 pin, and pop_lhs_and_probe (basic/input.asm, also in front) grew by
; exactly its 6 B -- tools/pin_plan.py's exact fill, no pad change.
arga_dig_iszero:
                ld      hl,ARGA+FPNUM_DIG
                jp      dig15_iszero

; 🏎️ D-INTFAST (D-LOOPPROF lever 1, 2026-10-20, TIER 5): A FLOAT `+ - *` WHOSE
; OPERANDS BOTH HOLD EXACT INT16 VALUES RUNS ON THE INT PATH. `A=I+7` with I a
; default-type (double) loop counter is a BCD add -- widen both (~3100 T), fp_add
; (~5100 T) -- of two integers, and `A=I*7`'s fp_mul alone was ~14 100 T
; (scratchpad/loopprof_host.out). The float arms below (caddsub_float, cmul_float)
; first ask fx_cvt whether each operand is an exact int16 (nx_pki over its packed
; bytes; an int16 operand is one already); if both are, they CALL the int path
; (caddsub_int / cmul_int) on those values and fx_tail turns its answer into what
; the BCD path would have left:
;   * the int path's own exact answer (FACTYP = 2, DE): a nonzero one is packed by
;     nx_pack into FAC+0..3 over a zeroed FAC+1..7 -- the bytes round_and_finalize's
;     arga_pack_fac writes for an exact integer of at most five digits (guard digit
;     0, no rounding) -- and leaves through fac_dbl_int16, the BCD path's own tail,
;     so FACTYP = 8, CVT_MODE / CVT / WSRC and every register come out of the same
;     flt_to_int16 over the same FAC. A ZERO answer leaves through raf_zero_ok, the
;     BCD path's zero tail, with C = 0 -- the C every int-valued zero reaches it with
;     (dig15_cmp / dig15_add_inplace end on digit 14 = 0, fp_mul's ldir on BC = 0);
;   * an int path that OVERFLOWED has already run the BCD op itself, through
;     widen_both_operands on the original operands (FACTYP = 8): the old float
;     path to the byte, which fx_tail hands back as it stands.
; Never taken: a fraction, past int16, -32768 as a float (nx_pki), a zero lead byte
; over a nonzero mantissa or a "negative zero" ($80 lead), and an int16 rhs of
; $8000 -- for '-' the int path keeps that one int16 (the measured no-promotion
; quirk), which a float operand must not inherit. Then the float arm runs as it
; always did; the cost of asking is fx_cvt's (an nx_pki per float operand).
; ⚠️ CANONICAL OPERANDS ONLY, AS FOR nx_fast: a mantissa with a leading 0 digit
; ($42 $05 = 5) or a nibble above 9 -- which no producer here makes; only POKE or
; CVS / CVD of foreign bytes can -- is read by nx_pki as the integer its digits
; spell and gets the canonical answer, where the BCD add could keep the odd form
; (`0+CVS(CHR$(&H42)+CHR$(5)+...)`: $42 $05 before, $41 $50 now). Guarding the
; lead digit is +9 B; the nibble is not guardable cheaply.
; Page 1 is mapped here: combine_* are reached only from main page-1 code (the
; climber's cl_leaf, NEXT), never from a tenant, and they already call
; set_factyp2 / factyp_is2 there.
; tests/test_intfast.py holds old image against new: FAC, FACTYP, FPERR, DE, A/F/
; BC/HL and all RAM but the float scratch, over every type pairing, the int16
; walls, a seeded random corpus and whole statements through the interpreter.
; Host profile (scratchpad/loopprof_host.py, machine model T a pass): `A=I+7`
; 29116 -> 24999, `A=I*7` 38033 -> 28696.

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
                ld      hl,(FP_LHSVAL)
caddsub_int:                                ; D-INTFAST: HL = the lhs, DE = the rhs
                ld      a,(FP_OPMODE)       ; (the `ld (FP_TMP_B),de` that stood here
                                            ; fed caddsub_widen_both only)
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
                jr      z,caddsub_old       ; '+' -> always promote
                ld      a,d
                xor     $80
                or      e
                jr      nz,caddsub_old      ; '-' promotes, unless the RHS is $8000
caddsub_ok:
                ex      de,hl
                jp      set_factyp_int_ret
caddsub_float:
                call    fx_cvt              ; NC: HL = the lhs, DE = the rhs, both
                jr      c,caddsub_old       ; exact int16s (D-INTFAST, above)
                call    caddsub_int
                jr      fx_tail
caddsub_old:                                ; the float path, and the int path's
                call    widen_both_operands ; promotion (DE = the rhs either way)
caddsub_disp:
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
                ld      hl,(FP_LHSVAL)
cmul_int:                                   ; D-INTFAST: HL = the lhs, DE = the rhs
                ld      (FP_TMP_B),de
                call    abs16               ; HL=|lhs|, A=lhs sign (0/$80)
                ld      (FP_RSIGN),a
                push    hl                  ; |lhs|
                ld      hl,(FP_TMP_B)
                call    abs16               ; HL=|rhs|, A=rhs sign
                ex      de,hl               ; DE = |rhs|
                ld      hl,FP_RSIGN         ; D-INTFAST carve: the product's sign is
                xor     (hl)                ; lhs XOR rhs -- one `xor (hl)` where an
                ld      (hl),a              ; `or a` / `jr z` / flip took 11 B (-6)
                pop     hl                  ; HL = |lhs|
                call    mul16x16_32         ; -> MUL32 (32-bit unsigned product)
                ld      hl,(MUL32+2)
                ld      a,h
                or      l
                jr      nz,cmul_overflow    ; high word nonzero -> definitely > 32768
                ld      hl,(MUL32)
                ld      a,(FP_RSIGN)
                ld      de,32768
                or      a                   ; (and CF = 0 for the sbc below: the
                jr      nz,cmul_boundcmp    ; second `or a` that stood there was
                dec     de                  ; redundant, D-INTFAST carve -1 B)
cmul_boundcmp:
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
                ld      de,(FP_TMP_B)       ; DE = the rhs, as widen_both_operands
cmul_old:                                   ; wants it (the float path's is live)
                call    widen_both_operands
                jp      fp_mul_raise        ; overflow at once (D-DEFERRSTUDY, expr.asm)
cmul_float:
                call    fx_cvt              ; NC: HL = the lhs, DE = the rhs, both
                jr      c,cmul_old          ; exact int16s (D-INTFAST)
                call    cmul_int
; --- fx_tail: the int path came back from a float arm's exact-int16 detour ------
; (D-INTFAST, above). FACTYP = 2: DE is its exact answer -> the BCD path's FAC and
; tail. Otherwise it overflowed into the BCD op, whose answer -- FAC, DE and every
; register -- is final: AF, the one pair the test below takes, is put back. (Re-
; running the idempotent flt_to_int16 tail instead is 4 B smaller and ~1700 T
; dearer on every overflow.)
fx_tail:
                push    af
                call    factyp_is2
                jr      z,fxt_int
                pop     af
                ret
fxt_int:
                pop     hl                  ; (the int path's AF: dead)
                push    de
                xor     a
                call    fac_zero_mantissa   ; FAC+1..7 := 0 (A = 0)
                pop     hl                  ; HL = the answer
                ld      a,h
                or      l
                ld      c,a                 ; a zero: C = 0, as the BCD path's
                jp      z,raf_zero_ok       ; zero tail is reached with it
                ld      de,FAC
                call    nx_pack             ; FAC+0..3: lead + three BCD pairs
                jp      fac_dbl_int16       ; FACTYP := 8, DE := flt_to_int16

; --- fx_cvt: are both operands of a float `+ - *` exact int16s? (D-INTFAST) ------
; In: the popped lhs (LHS_FACTYP; FP_LHSVAL or LHS_FAC), the rhs (FACTYP; DE or
; FAC). Out: NC, HL = the lhs, DE = the rhs; or CF (one is not, or the rhs is the
; int16 $8000), DE then still the rhs's own DE when that rhs is an int16 -- the
; only case widen_rhs_operand reads it. Clobbers A, BC, HL (and DE on a float
; rhs, whose DE nothing reads: widen_both_operands only parks it in FP_TMP_B).
fx_cvt:
                call    factyp_is2
                jr      z,fxc_rint          ; an int16 rhs is its DE
                ld      b,a                 ; B = the type = the byte count (4 / 8)
                ld      hl,FAC
                call    nx_pki              ; NC: DE = its exact value
                ret     c
fxc_rint:
                ld      a,d
                xor     $80
                or      e
                scf
                ret     z                   ; $8000 (only an int16 can be): the int path's
                                            ; '-' would keep it int16, the BCD path not
                ld      hl,(FP_LHSVAL)
                ld      a,(LHS_FACTYP)
                cp      2
                ret     z                   ; NC: an int16 lhs is FP_LHSVAL
                push    de
                ld      b,a
                ld      hl,LHS_FAC
                call    nx_pki              ; NC: DE = the lhs's exact value
                ex      de,hl
                pop     de
                ret

; --- combine_div_float: ev_t's '/' site. ALWAYS float ----------------------
; (spec §10.1: "'/' is always real division, always double").
combine_div_float:
                call    pop_lhs_and_probe   ; ZF result ignored -- '/' is always
                                            ; float regardless (spec §10.1)
                call    widen_both_operands
                ld      hl,ARGB+FPNUM_DIG   ; D-DEFERRSTUDY: a zero divisor is raised
                call    dig15_iszero        ; HERE, at once (the VG-8020 never evaluates
                ld      a,2                 ; past it: scratchpad/deferr_side_run.out);
                jp      z,raise_now8        ; VALTYP 8, as there; fp_div's own test stays
                jp      fp_div_raise        ; overflow at once (D-DEFERRSTUDY, expr.asm)

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
                jp      raise_now           ; Division by zero, at once (D-DEFERRSTUDY)
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
                                            ; DE = n rides to the tenant in DE
                                            ; (D-WSZERO S14e: MATH_N is math_wrap's)
                ld      a,(ARGB+FPNUM_SIGN)
                or      a
                jr      z,cpow_j_int_pos
                ld      a,1
                jr      cpow_j_int_store
cpow_j_int_pos:
                xor     a
cpow_j_int_store:
                                            ; A = j: bit0 = y negative, bit7 = 0 (int)
                jr      cpow_dispatch
cpow_frac:
                ; --- 4) fractional y (or int-valued y outside int16) -------
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,cpow_frac_ok
                ld      a,3
                jp      raise_now8          ; (-x)^frac: at once, VALTYP 8 (D-DEFERRSTUDY)
                ; (penderr_de0, D-PENDTAIL's shared "defer code A, return DE=0" tail,
                ; stood here: D-DEFERRSTUDY families 1 and 2 converted all four of its
                ; sites to an immediate raise, the last one EXP, so it went -- 6 B.)
cpow_frac_ok:
                ld      a,$80               ; j: bit7 = 1 (frac path)
cpow_dispatch:
                ld      l,a                 ; D-WSZERO S14e: j rides to the tenant in L
                push    ix                  ; save the parser's text-position
                                            ; pointer -- subrom_call/CALSLT
                                            ; clobbers ALL registers, and IX
                                            ; IS the token cursor here (same
                                            ; discipline as evmc_sqr/atn/log)
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_POW
; cpow_tail -- a ZERO-BYTE label: evmc_dispatch (basic/expr.asm) ended in these
; exact 11 bytes and jumps here now (D-SAVECOLON carve, -8 B main page 1). The
; entry contract is the one both sites had: IX = the tenant entry, the text cursor
; pushed once beneath the return address.
cpow_tail:
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
; this call (its `and c` intersect comes right after; since D-EVALSLOPE that
; caller is expr.asm's cl_red_rel) — cmp16_bits leaves BC
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
                jp      raise_now           ; `\` / MOD by 0, at once (D-DEFERRSTUDY)

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
                ret     nz                  ; a negative-signed quotient never escapes
                                            ; int16 this way (min reachable magnitude is
                                            ; 32768 only for the +32768 case below)
                ld      a,d
                cp      $80
                ret     nz
                ld      a,e
                or      a
                ; DE == $8000 with the intended sign positive -> the true value
                ; is +32768, which does not fit int16: promote to double.
                jp      z,flt_ret_32768     ; D-CARVE2 (-10 B, low region)
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

; --- neg_de_hl: HL = 0 - DE, with `sbc hl,de`'s flags (P/V = int16 overflow,
; the one ev_f_neg reads) -- D-NEGDE (2026-09-27). NOT float.asm's neg_de,
; which negates DE IN PLACE and keeps HL: the two sites that wanted that
; (INPUT's sign, pu_fmt_int) call it now. `ld hl,0 / or a / sbc hl,de` stood
; open-coded at THREE sites that want the result in HL (unary minus, the
; number renderer, and this file's own). SITED IN THE LOW REGION so the page-1
; sites reach it, and LAST in this file on purpose: subromcall.asm's header
; rests on this file ENDING in `ret` (nothing may fall forward into
; subrom_call). A untouched.
neg_de_hl:
                ld      hl,0
                or      a
                sbc     hl,de
                ret

