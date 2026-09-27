; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; =============================================================================
; Clean-room: own design. Where this tenant is reference-IDENTICAL it is so BY
; CONSTRUCTION and BLACK-BOX CONFIRMED -- our own reference-identical multiply
; composed in a loop shape pinned by observed outputs, never by reading the
; reference's code. Coefficients: tools/gen_math_coeffs.py, our own fit. Nothing
; here is derived from a disassembly or byte-copy of any reference ROM.
; ---------------------------------------------------------------------------
; fp_pow -- math pack slice 2c: `^` (power operator) primitive
; (docs/spec-basic-mathpack-slice2.md §13.5). Two dispositions, chosen
; MAIN-SIDE by combine_pow (basic/float-arith.asm) and handed in via
; MATH_N/MATH_J:
;
;   INT PATH (MATH_J bit7 clear): y is integer-valued, -32768<=y<=32767.
;   LSB-first square-and-multiply over |y| (n in MATH_N), REFERENCE-IDENTICAL
;   BIT-FOR-BIT by construction (§13.2: a composition of our own reference-
;   identical fp_mul in the reference's own pinned loop shape, black-box
;   confirmed 2026-07-14 -- char_pow rounds 1-5). Negative y: compute the
;   forward power first, THEN reciprocate (fp_div, correctly rounded) --
;   pinned order (`.1^63`=1E-63 but `10^-63`->Overflow: reciprocal-FIRST
;   would make them equal, which the reference does NOT do).
;
;   FRAC PATH (MATH_J bit7 set): y is fractional (or integer-valued outside
;   int16). EXP(y*LOG(x)) -- bit-for-bit the reference's own derivation
;   (math-pack spec §5.1) -- x>0 already guaranteed by combine_pow's own
;   x<0 domain check (Illegal function call, main-side). fp_log/fp_exp are
;   DIRECT in-page calls (same assembly unit, sub/sub.asm includes
;   fp_atan.asm then fp_exp.asm then fp_log.asm before this file) -- the
;   first tenant-to-tenant composition, NO nested subrom_call.
;
; ACCURACY (§13.2, pre-proven by tools/sim_math_chain.py BEFORE this asm was
; written, 7f3f31f -- all 32 captured reference anchors reproduce bit-for-
; bit in the sim's model): the positive-y int path is reference-identical;
; vs mathematical truth it inherits the reference's OWN squaring-
; amplification error (each s:=s*s doubles accumulated relative error, so
; the sim's per-row structural cap is `3*2^bitlen(n)` ulp, HELD, worst
; measured 353 ulp @ 1.0392660791291^176 = 0.46 of cap -- the reference's
; own error, not ours to fix, per [[bug-for-bug-compat-over-accuracy]]).
; Negative-y adds one correctly-rounded fp_div (same caps). The fractional
; path's deviation scales with |t|=|y*log x|: per-row cap
; `12*max(1,|t|)+10` ulp, HELD (worst measured 91 ulp @ t~=11.3 = 0.62 of
; cap). Documented bounded deviation, ATN-shape gate (truth-bound caps +
; informational reference report, no per-input never-worse claim, §2
; relaxation).
;
; HOME: the sub-ROM PAGE-1 island (sub/sub.asm), dispatched from combine_pow
; (basic/float-arith.asm) via subrom_call/SUBROM_ENTRY_BASE_P1+
; SUBROM_IDX_POW. Fifth page-1 tenant (after fp_sqrt/fp_atan/fp_exp/fp_log).
; COMPUTE-ONLY (leaves FAC correct; every disposition, including the frac
; path's own huge-|t| overflow/underflow replica of evmc_exp's §12.6 coarse
; check, is via FPERR only -- combine_pow reads only CF, per the CALSLT
; A-not-preserved lesson). Every exit is a plain `ret`.
;
; RAM (§13.5 -- NO new claims beyond the slice-2a/2b MATH_*/HORNER_* and
; SQR-precedent SQRT_* aliases, basic/sysvars.inc):
;   int path: SQRT_X := s (the running square), SQRT_Y := acc stash across
;   the squaring mul, MATH_N := n (consumed bit-by-bit, dead once 0),
;   MATH_J bit0 read once at fpw_done (y-negative). fp_mul/fp_div touch none
;   of these -- SQR/ATN/EXP/LOG/POW never run concurrently (one factor
;   evaluated at a time), the same argument every prior slice's header makes.
;
;   frac path: y (ARGB at entry) must survive the ENTIRE `call fp_log` --
;   but fp_log/fp_exp's own internal `call fp_poly_horner` clobbers
;   HORNER_ACC, which ALIASES the only spare persistent FPNUM cell this
;   tenant cluster has (MATH_R/SQRT_R/FOUTBUF). **DEVIATION from the literal
;   §13.5 pseudocode** (flagged, not hidden -- the 2b-precedent class of
;   finding): the contract's own text ("y is copied to the FOUTBUF FPNUM
;   cell ... SQRT_X/SQRT_Y are CLOBBERED by fp_log/fp_exp internals") never
;   accounts for fp_log/fp_exp ALSO clobbering FOUTBUF itself (=SQRT_R=
;   HORNER_ACC) via their own internal Horner call -- there is in fact NO
;   free persistent FPNUM cell left to stash y in across `call fp_log`; all
;   three (SQRT_X, SQRT_Y, SQRT_R/FOUTBUF) are used internally by fp_log AND
;   fp_exp. Fixed by stashing y on the Z80 MACHINE STACK instead (18 bytes =
;   9 word push/pop pairs) -- zero new RAM, and provably safe: fp_log's own
;   call/ret discipline is stack-balanced, so the pushed bytes sit
;   untouched beneath its frames for the whole call. MATH_J is read ONCE at
;   entry (fp_exp/fp_log clobber it too: MATH_J aliases their own m/j).
;
; CANONICAL-OPERAND DISCIPLINE: the int path chains ONLY fp_mul/fp_div,
; neither of which ever READS its operands' guard digit (index 14; only
; fp_add/fp_sub's alignment does, via dig15_shr/dig15_shl) -- so §13.5's
; literal pseudocode (raw copy18 straight from ARGA, no widen_fac_to) looked
; safe by that argument alone. **A SECOND, MORE FUNDAMENTAL reason forces a
; widen_fac_to after every fp_mul in this loop anyway (found live, flagged
; as a contract gap): fp_mul's own UNDERFLOW disposition is a silent PRE-
; check abort (check_preexp_bounds' cpb_abort -> raf_zero_ok, no FPERR) that
; sets FAC:=0 correctly but never touches ARGA at all -- so a raw copy18
; straight from ARGA after an underflowing fp_mul propagates the STALE
; PRE-multiply operand, not the zero the true result is.** `0.5^2000`
; (mathematically 0, per the sim) printed `2.4308653429145E-63` -- an
; intermediate partial product frozen in place because a later squaring
; step's underflow silently failed to update `s`, so the multiply chain
; kept reusing its last-good nonzero value forever instead of collapsing to
; 0. Every fp_mul call in the int loop is followed by `ld hl,ARGA / call
; widen_fac_to`, which re-derives ARGA from FAC (always correct, even on
; the abort path) before it is used as a copy source. The frac path already
; follows the full discipline (fp_log/fp_exp are opaque compound ops, and
; the one fp_mul between them is re-widened before its dexp is read, for
; the same class of reason -- see fp_pow_frac's own comment).
;
; Resident-ABI surface: fp_mul, fp_div, widen_fac_to, widen_uint_to,
; dig15_iszero (+ transitively whatever fp_log/fp_exp already import) -- a
; SUBSET of the existing imports, NO new page-0 relocation; `make
; subrom-closure-check` re-audits mechanically.
; =============================================================================

; --- fp_pow: ARGA=x (widened, x!=0, x>0 if MATH_J bit7 set -- both --------
; guaranteed by combine_pow's own main-side classification), ARGB=y (widened,
; y!=0), MATH_N/MATH_J as combine_pow set them -> FAC (double). Every exit is
; a plain `ret`. COMPUTE-ONLY.
fp_pow:
                ld      a,(MATH_J)
                bit     7,a
                jp      nz,fp_pow_frac

; --- int path: LSB-first square-and-multiply (§13.1 rule 3, sim-proven) ----
                ld      hl,ARGA
                ld      de,SQRT_X
                call    fat_copy18          ; s := x
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; acc := 1.0 (a REAL one -- the
                                            ; 1D62^1 anchor needs acc=1*x)
fpw_lp:
                ld      hl,(MATH_N)
                bit     0,l
                jr      z,fpw_no_mul
                ld      hl,SQRT_X
                ld      de,ARGB
                call    fat_copy18          ; ARGB := s; acc := acc*s
                call    fp_mul
                ld      a,(FPERR)
                or      a
                ret     nz                  ; overflow -- FPERR/FAC already
                                            ; set by fp_mul's own tail
                ld      hl,ARGA
                call    widen_fac_to        ; re-derive ARGA from FAC --
                                            ; REQUIRED (found live, 0.5^2000):
                                            ; fp_mul's own UNDERFLOW abort
                                            ; (silent, no FPERR -- check_
                                            ; preexp_bounds' cpb_abort ->
                                            ; raf_zero_ok) sets FAC:=0
                                            ; correctly but leaves ARGA
                                            ; COMPLETELY untouched (still the
                                            ; PRE-multiply operand, not the
                                            ; zero the true result is) --
                                            ; without this, acc*s "gets
                                            ; stuck" at a stale nonzero value
                                            ; instead of becoming 0 whenever
                                            ; it underflows (0.5^2000
                                            ; printed 2.4308653429145E-63, an
                                            ; intermediate partial product,
                                            ; instead of the correct 0)
fpw_no_mul:
                ld      hl,(MATH_N)
                srl     h                   ; MATH_N is 16-bit -- a genuine
                rr      l                   ; 16-bit logical shift (srl high,
                                            ; rr low), not an 8-bit srl
                ld      (MATH_N),hl
                ld      a,h
                or      l
                jr      z,fpw_done
                ld      hl,ARGA
                ld      de,SQRT_Y
                call    fat_copy18          ; stash acc
                ld      hl,SQRT_X
                ld      de,ARGA
                call    fat_copy18
                ld      hl,SQRT_X
                ld      de,ARGB
                call    fat_copy18          ; ARGA/ARGB := s; s := s*s
                call    fp_mul
                ld      a,(FPERR)
                or      a
                ret     nz                  ; overflow -- FPERR/FAC already set
                call    widen_to_arga
                                            ; re-derive (same underflow
                                            ; reason as the acc*s site above)
                ld      de,SQRT_X           ; s := s*s
                call    fat_copy18
                ld      hl,SQRT_Y
                ld      de,ARGA             ; ARGA := acc (restored)
                call    fat_copy18
                jr      fpw_lp
fpw_done:
                ld      a,(MATH_J)
                bit     0,a
                ret     z                   ; positive y: FAC is ALREADY the
                                            ; correct result -- no further
                                            ; pack needed. The loop's own
                                            ; structure guarantees the LAST
                                            ; fp_mul call before ANY exit was
                                            ; the acc-multiply (the only n
                                            ; value that shifts to the
                                            ; exiting 0 is n==1, whose bit0
                                            ; is definitionally set), so FAC
                                            ; already reflects acc, kept in
                                            ; lockstep with ARGA by the
                                            ; widen_fac_to fix above.
                                            ; **DEVIATION from the literal
                                            ; §13.5 pseudocode** (which shows
                                            ; "arga_pack_fac, ret" here):
                                            ; arga_pack_fac blindly packs
                                            ; sign|(dexp+64) from ARGA
                                            ; regardless of whether the
                                            ; mantissa is actually all-zero
                                            ; -- round_and_finalize's own
                                            ; header explicitly documents
                                            ; this precondition ("caller has
                                            ; already verified ... ARGA_DIG
                                            ; isn't the all-zero case"),
                                            ; which a genuinely-zero acc
                                            ; (e.g. underflow, `0.5^2000`)
                                            ; violates -- producing a
                                            ; non-canonical "$40" lead byte
                                            ; instead of the "0" the zero
                                            ; convention needs (found live:
                                            ; `0.5^2000` printed "." instead
                                            ; of "0").
                ld      hl,ARGA+FPNUM_DIG
                call    dig15_iszero
                jr      z,fpw_recip_zero
                ld      hl,ARGA
                ld      de,ARGB
                call    fat_copy18          ; ARGB := p (acc)
                ld      hl,ARGA
                xor     a
                ld      de,1
                call    widen_uint_to       ; ARGA := 1.0
                jp      fp_div              ; tail: FAC/ARGA := 1/p, correctly
                                            ; rounded. fp_div's OWN
                                            ; round_and_finalize disposes a
                                            ; genuine reciprocal overflow
                                            ; (e.g. a p just above the
                                            ; underflow floor, 1/p past the
                                            ; ceiling) via its own bound
                                            ; check. DEVIATION from the
                                            ; literal §13.5 pseudocode (which
                                            ; shows an explicit "arga_pack_
                                            ; fac, ret" after this call):
                                            ; that would be WRONG on
                                            ; fp_div's own overflow-abort
                                            ; path (check_preexp_bounds's
                                            ; cpb_abort -> raf_zero_ok sets
                                            ; FAC:=0 directly WITHOUT
                                            ; touching ARGA, which still
                                            ; holds the pre-div numerator
                                            ; 1.0) -- re-deriving FAC from
                                            ; that stale ARGA would silently
                                            ; overwrite the correct FPERR=1/
                                            ; FAC=0 Overflow result with 1.0.
                                            ; A tail-jp lets fp_div's own
                                            ; tail be the sole authority.
fpw_recip_zero:
                ld      a,1
                call    penderr_set         ; reciprocal of underflowed 0 =
                                            ; Overflow (pinned .5^-2000)
                ret

; --- frac path: EXP(y*LOG(x)) (§13.1 rule 4) --------------------------------
; y (ARGB, untouched by combine_pow's classification) must survive the
; ENTIRE `call fp_log` below -- stashed on the machine stack, see this
; file's header for why (a RAM-cell stash, as §13.5 literally shows, is NOT
; safe: fp_log's own internal Horner call clobbers the only spare
; persistent FPNUM cell).
fp_pow_frac:
                ld      hl,ARGB+17
                ld      b,9
fpwf_save:
                ld      e,(hl)
                dec     hl
                ld      d,(hl)
                dec     hl
                push    de
                djnz    fpwf_save
                call    fp_log              ; ARGA/FAC := ln(x) (x>0
                                            ; guaranteed by combine_pow's own
                                            ; domain check)
                ld      hl,ARGB
                ld      b,9
fpwf_restore:
                pop     de
                ld      (hl),d
                inc     hl
                ld      (hl),e
                inc     hl
                djnz    fpwf_restore        ; ARGB := y (restored, byte-exact)
                call    fp_mul              ; FAC/ARGA := ln(x)*y = t (the
                                            ; pre-check on a huge-magnitude y
                                            ; IS the right disposition: a
                                            ; genuinely overflowing |t| must
                                            ; abort here)
                ld      a,(FPERR)
                or      a
                ret     nz                  ; FAC/FPERR already set by fp_mul
                ld      hl,ARGA
                call    widen_fac_to        ; canonical t -- REQUIRED here
                                            ; (found live, `1^123456789`):
                                            ; fp_mul's own zero-PRODUCT path
                                            ; (fpm_after's ".1 branch", taken
                                            ; whenever either factor is 0)
                                            ; adjusts ARGA's dexp field by -1
                                            ; as part of its normal mantissa-
                                            ; window shift, then round_and_
                                            ; finalize's raf_zero_ok tail
                                            ; packs FAC:=0 WITHOUT resetting
                                            ; that stale dexp back to 0 --
                                            ; e.g. ln(1)*123456789=0 (dexp 9)
                                            ; left ARGA_DEXP=8, which the
                                            ; unwidened dexp>=4 test below
                                            ; misread as "huge" and wrongly
                                            ; raised Overflow for `1^y` on
                                            ; any y past dexp 4. widen_fac_to
                                            ; re-derives a true dexp=0 from
                                            ; FAC's own canonical zero.
                ld      a,(ARGA+FPNUM_DEXP) ; low byte -- signed, safe (every
                                            ; canonical FPNUM's dexp fits
                                            ; -64..63, so the high byte is
                                            ; pure sign-extension; same idiom
                                            ; as evmc_exp's own coarse check)
                sub     4
                jp      p,fpwf_huge         ; dexp-4>=0 <=> dexp>=4 <=>
                                            ; |t|>=1000: replicate evmc_exp's
                                            ; own coarse disposition (§12.6)
                                            ; TENANT-side (fp_exp's own
                                            ; |x|<1000 precondition)
                jp      fp_exp              ; tail: FAC := e^t (fp_exp packs
                                            ; FAC itself)
fpwf_huge:
                ld      a,(ARGA+FPNUM_SIGN)
                or      a
                jr      z,fpwf_overflow
                xor     a
                ld      (FAC),a             ; t <= -1000: e^t underflows to 0
                ret                         ; (no error -- matches EXP(-huge))
fpwf_overflow:
                ld      a,1
                call    penderr_set         ; t >= 1000: e^t overflows
                ret
