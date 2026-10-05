; float.asm — math float pack: RESIDENT half (repack build only, included inside
; basic/main.asm. docs/spec-basic-float-core.md.
;
; The float LITERAL CRUNCH (tk_float) was evicted to the sub-ROM as a cold,
; pure-computation page-0 tenant (subrom S2b, sub/tkfloat.asm). WAVE 1 kept a thin
; main-side dispatch STUB here (a per-literal CALSLT); WAVE 2 evicted the WHOLE
; tokeniser to the sub-ROM too, so the crunch is now reached by an in-slot
; `jp tk_float` from the co-located tk_loop and the main-side stub is GONE (spec
; §5 — `tokenise` in basic/interp.asm is the sole sub-ROM entry now). What stays
; HERE is the runtime-hot / resident float code that must not pay a per-call
; CALSLT:
;   * flt_out   — the PRINT formatter (FAC/FACTYP -> FOUTBUF -> print_string).
;     RUNTIME-HOT (every float PRINT), so it stays resident (it is NOT paged out
;     — the user's "never evict a hot path" rule, spec §WAVE-1 AMENDMENT);
;   * flt_to_int16 / flt_neg / flt_int_result — the hot per-factor glue;
;   * a RESIDENT copy of the tkf_ref* bound tables, because float-arith.asm's
;     domain_convert_core reads them and the crunch (which owns the originals)
;     now lives in the sub-ROM, invisible from the low region.
;
; Representation and all format/classification RULES are unchanged and live with
; their code (crunch rules in sub/tkfloat.asm; format rules below). Own-design
; algorithms; number FORMAT is MSX2 TH; token bytes oracle-pinned. No disassembly.

; --- tkf_ref*: RESIDENT copy of the 5-digit bound tables -------------------
; Byte-identical to the copy inside sub/tkfloat.asm. float-arith.asm's
; domain_convert_core (dcc_bound5) reads these; keeping a resident copy avoids a
; cross-ROM reference now that the crunch lives in the sub-ROM. Unpacked digits,
; one per byte (MSX2 TH number format; oracle-pinned bounds).
; tkf_ref32767 / tkf_ref65535 / tkf_ref32768 -- MOVED to basic/islands.asm (D-ISLDATA2, 2026-10-03): pure data,
; read only by absolute `ld` from main; now in the font island.

; =============================================================================
; Sign space/'-' + digits + ONE trailing space; E notation for BOTH
; precisions (never D on this reference); FIXED form iff -1<=dec_exp<=14,
; else E form. Value 0 (lead byte 0; also the dec_exp<=-64 crunch-time
; underflow case, mantissa retained but unprinted per §9.2 rule 6) -> "0".
; Clobbers A, B, C, D, E, H, L.
; --- D-STRFLT: flt_out is now a two-liner over flt_fmt ---------------------
; STR$ needs the TEXT, not the printing. `flt_fmt` builds FOUTBUF and returns
; HL pointing at it; `flt_out` is what PRINT has always called.
; 🟢 THE SPLIT COSTS ~2 BYTES, because the two `jp print_string` tails below
; become `ret`. FOUTBUF is safe across STR$'s own temp allocation: the only
; writers are this file and the math pack (via the SQRT_R / MATH_R aliases),
; and neither is on `str_temp_alloc`'s path.
flt_out:
                call    flt_fmt
                jp      print_string
flt_fmt:
                ; --- C8 (2026-10-03): the unpack IS widen_fac_to -----------------
                ; This used to open-code what float-arith.asm's widen_fac_to already
                ; does -- lead byte -> sign / signed dec_exp / one digit per byte --
                ; into TKDEXP/TKDIG, with its own FACTYP->TKPC/FOMBYTES dispatch and
                ; its own nibble loop (a byte-for-byte twin of wsrc_unpack). Now the
                ; value is widened into ARGA, the FPNUM record the float pack already
                ; owns, and the flo_* readers below read the record's fields.
                ; WHY ARGA IS DEAD HERE (space plan B-10 rewrote this; the first
                ; draft said domain_convert_core "already widens into it" -- it
                ; widens into CVT, $F0C8, not ARGA). Checked at every ARGA writer:
                ; each one either packs ARGA straight back (arga_widen followed by
                ; round_and_finalize / round_single_and_pack / fp_trunc+pack) or
                ; hands it to a leaf that never evaluates (the evmc_* math tenants,
                ; the combine_* operators -- whose LHS lives in the push_lhs_frame
                ; stack frame, never in ARGA, while the RHS is evaluated). The one
                ; writer that RESUMES parsing with ARGA loaded is CIRCLE's DREQ 3
                ; (basic/graphics.asm), and its tenant copies ARGA out
                ; (cpt_angle_from_arga / the aspect) on resume, before it requests
                ; the next argument. So when STR$ formats mid-expression, PRINT
                ; formats an evaluated item, or the PRINT USING tenant runs after
                ; round_and_finalize packed ARGA into FAC, nothing still reads it.
                ; ⚠️ A NEW ARGA WRITER THAT EVALUATES BEFORE CONSUMING IT BREAKS
                ; THIS -- `VAL(STR$(x))` as that argument would overwrite it here.
                ; The precision dispatch is gone too: widen_fac_to zero-pads the
                ; record to 15 digits, so the trailing-zero strip simply starts at
                ; 15 and lands on the same last nonzero digit for either precision.
                ; Cost: the pad (9 B for a single, 1 for a double) and up to nine
                ; extra strip iterations for a SINGLE -- on the PRINT path only, the
                ; wsrc_unpack loop itself is untouched.
                ld      a,(FAC)
                or      a
                jr      z,flo_zero
                ld      hl,ARGA
                call    widen_fac_to        ; ARGA := sign / dec_exp / 15 digits
                ; strip trailing zeros -> s (>=1: lead<>0 guarantees a nonzero digit)
                ; 🎯 A POINTER WALK DOWN FROM THE LAST DIGIT (space plan B-10). C8
                ; made every value strip from 15 (widen_fac_to pads a single), and
                ; the loop this replaces recomputed ARGA+FPNUM_DIG+c-1 on every
                ; pass (~82 cycles): `PRINT VAL("1E3")` paid 9 extra passes and its
                ; whole-row time went 1.8x -> 2.2x the VG-8020's. ~40 cycles a pass
                ; here, so 14 passes cost about what the old 5 did, and 7 B less.
                ; DE is no longer written; flo_is_fixed sets it before any read.
                ld      hl,ARGA+FPNUM_DIG+14
                ld      c,15
flo_strip:
                ld      a,(hl)
                or      a
                jr      nz,flo_strip_done
                dec     hl
                dec     c
                jr      nz,flo_strip
flo_strip_done:
                ld      a,c
                ld      (FOSIGCOUNT),a
                ; --- sign char, then dispatch fixed vs E form ---
                ld      hl,FOUTBUF
                ld      a,(ARGA+FPNUM_SIGN) ; 0 / $80 -- widen_fac_to masked it
                or      a
                jr      z,flo_possign
                ld      a,'-'
                jr      flo_signwr
flo_possign:
                ld      a,' '
flo_signwr:
                ld      (hl),a
                inc     hl
                call    flo_is_fixed
                jr      c,flo_do_fixed
                call    flo_emit_e
                jr      flo_finish
flo_do_fixed:
                call    flo_emit_fixed
flo_finish:
                ld      (hl),' '            ; trailing space (MSX number format)
                inc     hl
                xor     a
                ld      (hl),a              ; 0-terminate
                ld      hl,FOUTBUF
                ret                         ; D-STRFLT: HL = the formatted text
flo_zero:
                ld      hl,FOUTBUF
                ld      (hl),' '
                inc     hl
                ld      (hl),'0'
                inc     hl
                jr      flo_finish          ; its trailing space + terminator +
                                            ; HL = FOUTBUF, verbatim (D-SEQEOF
                                            ; funding carve, -7 B)

; --- flo_is_fixed: CF set iff -1 <= dec_exp <= 14. Preserves HL. -----------
; Clobbers A, DE.
flo_is_fixed:
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,14
                call    cmp16_bits
                pop     hl
                cp      4
                jr      z,flo_notfixed
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,$FFFF            ; -1
                call    cmp16_bits
                pop     hl
                cp      1
                jr      z,flo_notfixed
                scf
                ret
flo_notfixed:
                or      a
                ret

; --- flo_emit_fixed: write the FIXED-form digits at (HL), HL advanced -----
; dec_exp<=0: '.' + (-dec_exp) zeros + digits. dec_exp>0 & s<=dec_exp:
; digits + (dec_exp-s) zeros, no point. Else: digits[0..dec_exp) + '.' +
; digits[dec_exp..s). Clobbers A, B, C, D, E.
flo_emit_fixed:
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,0
                call    cmp16_bits
                pop     hl
                cp      4
                jr      z,flo_fx_bc
                ld      (hl),'.'
                inc     hl
                ld      de,(ARGA+FPNUM_DEXP)
                call    neg_de              ; DE = -dec_exp (>=0)
                ld      a,d
                or      e
                jr      z,flo_fx_a_digits
                ld      b,e
flo_fx_a_zloop:
                ld      (hl),'0'
                inc     hl
                djnz    flo_fx_a_zloop
flo_fx_a_digits:
                jr      flo_write_digits
flo_fx_bc:
                ld      a,(FOSIGCOUNT)
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      c,l
                pop     hl
                cp      c
                jr      c,flo_fx_case_b
                jr      z,flo_fx_case_b
                ; case (c): 0 < dec_exp < s
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,l
                pop     hl
                ld      b,a
                ld      c,0
                call    flo_write_digits_range   ; digits[0..dec_exp)
                ld      (hl),'.'
                inc     hl
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,l
                pop     hl
                ld      c,a
                ld      a,(FOSIGCOUNT)
                sub     c
                ld      b,a
                jr      flo_write_digits_range   ; digits[dec_exp..s)
flo_fx_case_b:
                ld      a,(FOSIGCOUNT)
                ld      b,a
                ld      c,0
                call    flo_write_digits_range   ; all s digits
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      a,l
                pop     hl
                ld      c,a
                ld      a,(FOSIGCOUNT)
                ld      b,a
                ld      a,c
                sub     b                   ; A = dec_exp - s
                ret     z
                ld      b,a
flo_fx_b_zloop:
                ld      (hl),'0'
                inc     hl
                djnz    flo_fx_b_zloop
                ret

; --- flo_write_digits: write all FOSIGCOUNT digits from ARGA's digits[0..] (C8)
flo_write_digits:
                ld      a,(FOSIGCOUNT)
                ld      b,a
                ld      c,0
                ; ...and FALLS THROUGH into flo_write_digits_range (the `jr` here
                ; was to the very next instruction: -2 B, GA-CROSS-ROMSCAN)

; --- flo_write_digits_range: write B ASCII digits from ARGA's digits[C..] at (HL) (C8)
; out: HL advanced past the written digits. Clobbers A, B, D, E.
flo_write_digits_range:
                ld      a,b
                or      a
                ret     z
                push    hl
                ld      hl,ARGA+FPNUM_DIG
                ld      d,0
                ld      e,c
                add     hl,de
                ex      de,hl               ; DE = ARGA digit[C] read cursor
                pop     hl                  ; HL = write cursor
fwdr_lp:
                ld      a,(de)
                add     a,'0'
                ld      (hl),a
                inc     hl
                inc     de
                djnz    fwdr_lp
                ret

; --- flo_emit_e: write the E-FORM digits at (HL), HL advanced -------------
; digit0 [+ '.' + digits[1..s) if s>1] + 'E' + sign + 2-digit |dec_exp-1|.
; Clobbers A, B, C, D, E.
flo_emit_e:
                ld      a,(ARGA+FPNUM_DIG)
                add     a,'0'
                ld      (hl),a
                inc     hl
                ld      a,(FOSIGCOUNT)
                cp      1
                jr      z,flo_e_nodp
                ld      (hl),'.'
                inc     hl
                dec     a
                ld      b,a
                ld      c,1
                call    flo_write_digits_range
flo_e_nodp:
                ld      (hl),'E'
                inc     hl
                push    hl
                ld      hl,(ARGA+FPNUM_DEXP)
                ld      de,$FFFF            ; -1
                add     hl,de               ; HL = dec_exp - 1
                ld      a,h
                and     $80
                ld      d,a                 ; D = sign flag (0 pos / $80 neg)
                jr      z,flo_e_magpos
                xor     a
                sub     l
                ld      l,a
                ld      a,0                 ; 🔴 NOT `xor a`: this is a 16-bit
                                            ; NEGATE and the borrow from `sub l`
                                            ; must reach the `sbc a,h` below.
                                            ; xor would clear it (D-PEEPHOLE).
                sbc     a,h
                ld      h,a
flo_e_magpos:
                ld      a,l                 ; A = |dec_exp-1| (fits a byte)
                pop     hl
                push    af
                ld      a,d
                or      a
                jr      z,flo_e_signpos
                ld      a,'-'
                jr      flo_e_signwr
flo_e_signpos:
                ld      a,'+'
flo_e_signwr:
                ld      (hl),a
                inc     hl
                pop     af
                ld      b,0
flo_e_tens:
                cp      10
                jr      c,flo_e_havetens
                sub     10
                inc     b
                jr      flo_e_tens
flo_e_havetens:
                push    af
                ld      a,b
                add     a,'0'
                ld      (hl),a
                inc     hl
                pop     af
                add     a,'0'
                ld      (hl),a
                inc     hl
                ret

; --- neg_de: DE = -DE (two's complement). Clobbers A. ----------------------
; --- neg_de: DE = -DE (two's complement). Clobbers A. ----------------------
neg_de:
                xor     a
                sub     e
                ld      e,a
                ld      a,0                 ; 🔴 NOT `xor a`: 16-bit negate, the
                                            ; borrow from `sub e` must reach the
                                            ; `sbc a,d` below (D-PEEPHOLE).
                sbc     a,d
                ld      d,a
                ret

; =============================================================================
; flt_to_int16 / flt_neg (spec §9.4, corrected per §10.3 — see below)
; =============================================================================

; --- flt_to_int16: FAC/FACTYP -> DE, TRUNCATING toward zero, address domain
; (-32769<x<65536, a value >=32768 wraps by -65536 first — spec §10.3). Runs
; EAGERLY on every float factor (ev_f_float, expr.asm), including inside
; pure-float expressions that must not abort, so it stays SILENT: out of
; domain -> DE=0, no error flag (this is the fallback value unwired int
; consumers see; wired ones dispatch on FACTYP instead).
;
; F1 shipped this routine with HALF-UP rounding, reasoned from the published
; POKE/HEX$ -32768..65535 argument range but not oracle-pinned (see the
; superseded header this replaces, kept in git history). F2's oracle capture
; (basic_probe_float_arith.py, spec §10.3) corrected that: the reference
; TRUNCATES. The body is now a thin wrapper over float-arith.asm's
; domain_convert_core (the same domain/wrap/truncate logic fac_to_int_addr
; uses for POKE/VPOKE/HEX$'s CHECKED conversion, in its ADDRESS-domain mode)
; — this call site just ignores the CF (out-of-domain) signal instead of
; turning it into FPERR, which is exactly the silent-vs-checked distinction
; the two callers need. tests/test_float.py's flt_to_int16 matrix was
; updated to the truncating contract in the same review that made this
; change.
flt_to_int16:
                ld      a,1
                ld      (CVT_MODE),a
                jp      domain_convert_core

; --- flt_neg: flip FAC's sign bit (value-0 lead byte is exempt) -----------
flt_neg:
                ld      a,(FAC)
                or      a
                ret     z
                xor     $80
                ld      (FAC),a
                ret

; --- flt_int_result: FACTYP := 2 (int). Clobbers A only. -------------------
; Called at the tail of every FUNCTION factor that returns an int after its
; argument eval may have set FACTYP (PEEK/VPEEK/INP/EOF/LOF/DSKF via
; ev_ff_arg, USR, BASE, CVI, INSTR, LEN/ASC/VAL via ev_str_arg, and the
; string-relational result) — without this, `PRINT PEEK(40000.)` would print
; the STICKY FAC (40000) instead of the function's int result (caught live in
; F1 review; the fmt matrix had no function-over-float case). Parens and
; unary minus deliberately do NOT reset — `PRINT (1.5)` stays a float.
; D-XREG: an ALIAS across the low <-> page-1 boundary. Byte-identical to
; evsgn_settype and POSITION-INDEPENDENT (tools/dupspan_indep.py), and the
; REGION question -- is this label reached from a tenant whose mapping
; switches the target page OUT? -- is answered by scratchpad/crossreg_probe.py
; and GATED by check_tenant_closure.py, whose K-XR1 knife proves it can see an
; `equ` (it resolves addresses from the sym, not from the source form).
flt_int_result  equ     evsgn_settype

; flt_guard (F1's sticky-FACTYP combine guard, interim divergence D-F1-3) is
; REMOVED — F2 replaces every one of its 12 call sites in expr.asm with real
; float-aware combine logic (float-arith.asm's combine_add/combine_sub/
; combine_mul/combine_div_float/combine_cmp, plus fac_to_int_strict at the
; logical/\/MOD sites), so no site is left that needs "float arithmetic
; isn't implemented yet" as its fallback.