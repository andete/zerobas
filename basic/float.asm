; float.asm — math float pack, slice F1: literal crunch + PRINT formatter
; (repack build only — the whole file is included only inside
; `IF ROM_BASE < $4000`, basic/main.asm). docs/spec-basic-float-core.md.
;
; Representation (§9.1, MSX2 Technical Handbook number-format chapter, cross-
; checked byte-exact against basic_probe_floatlit.py / VG-8020): a float value
; is a lead byte (bit7 = sign, bits6-0 = excess-64 decimal exponent; the whole
; byte 0 means value 0) followed by 3 (single) / 7 (double) bytes of packed
; BCD mantissa digits, 2 digits/byte, left-justified, normalised so the first
; digit is the ones-place of 0.dddd * 10^dec_exp (0.1 <= mantissa < 1).
;
; `tk_float` (tokeniser side) replaces `tk_number` in the repack build: one
; pass over the literal collects significant digits + shape flags, then
; classifies (int / single / double, §9.2) and encodes, rounding half-up to
; the target precision with the single-precision non-renormalising carry
; quirk (§9.2 rule 6, oracle-pinned: `9999995!` -> 1000000, not a re-exponented
; 1E7). `flt_out` (PRINT side) is the inverse: FAC/FACTYP -> the MSX number
; display format (§9.3) -> FOUTBUF -> print_string.
;
; All classification/rounding/formatting RULES were captured black-box by
; basic_probe_floatlit.py and basic_probe_float_fmt.py against the Philips
; VG-8020 (2026-07-11; docs/spec-basic-float-core.md §9 is the distillation).
; One rule was NOT in the original matrix and was pinned by an extra targeted
; capture during S2 (same probe machinery, `--only` not used — see
; tkf_try_exponent's header for the exact literals/bytes): a type suffix
; (!/#/%) is only recognised when NO exponent (E/e/D/d) was parsed; after an
; exponent, the suffix character is left UNCONSUMED (verbatim ASCII), which is
; why `PRINT 1e10#` diverges to <no capture> on both sides in
; basic_probe_float_fmt.py (pre-authorised "[both rejected]" pass) — the
; trailing '#' derails the evaluator on both the reference and zerobas
; identically once it is left in the token stream. All algorithms (BCD pack/
; unpack, rounding, formatting layout) are own-design; the number FORMAT
; (byte layout) is MSX2 TH; token bytes are oracle-pinned (sysvars.inc). No
; disassembly.

SGL_DIGITS      equ     6       ; single mantissa digit count (MSX2 TH number format)
DBL_DIGITS      equ     14      ; double mantissa digit count (MSX2 TH number format)

; =============================================================================
; tk_float: crunch a decimal float/int literal (spec §9.2)
; =============================================================================
; in:  HL = source cursor (on the first digit, or on '.' when tk_loop routed a
;      '.'+digit lead here), DE = TOKBUF destination cursor.
; out: token(s) + value bytes emitted at the original DE; HL advanced past the
;      whole literal (digits, dot, exponent, suffix); control passes to
;      tk_loop (int/float forms) or, on a crunch-time overflow (dec_exp>63 or
;      a %-suffixed value>32767, §9.2 rules 1/6), TKOVF is set and control
;      passes to tk_end, ending the line's crunch there (own design, D-F1-1 —
;      dispatch_line, program.asm, reports it and skips execute/store).
; Classification (§9.2): %  -> int forms, error if >32767; # or a D/d exponent
; -> double always; ! -> single always; otherwise no dot/no exponent with
; D<=5 digits and value<=32767 -> int forms; D<=6 -> single; D>=7 -> double
; (D = significant digit count, leading zeros excluded, trailing zeros AND
; post-'.' digits included -- counts CHARACTERS, not numeric significance).
tk_float:
                push    de                  ; save the TOKBUF destination cursor
                xor     a
                ld      (TKPOS),a
                ld      (TKHAVESIG),a
                ld      (TKDCOUNT),a
                ld      (TKSTORED),a
                ld      (TKFLAGS),a
                ld      (TKINTLEN),a
                ld      (TKNZPOS),a
                ld      (TKEXP),a
                ld      (TKEXP+1),a
                ld      ix,TKDIG            ; TKDIG write cursor (own scratch)
                call    tkf_scan_digits     ; integer-part digits
                ld      a,(TKPOS)
                ld      (TKINTLEN),a        ; P = integer-part digit count
                ld      a,(hl)
                cp      '.'
                jr      nz,tkf_nodot
                inc     hl
                ld      a,(TKFLAGS)
                or      1                   ; bit0 = has_dot
                ld      (TKFLAGS),a
                call    tkf_scan_digits     ; fractional-part digits (pos continues)
tkf_nodot:
                call    tkf_try_exponent    ; consumes E/D exponent if well-formed
                ld      a,(TKFLAGS)
                bit     1,a                 ; has_exp?
                jr      nz,tkf_classify     ; exponent present -> no suffix check (oracle)
                call    tkf_try_suffix      ; consumes !/#/% if present
tkf_classify:
                ld      (TKSRCSAVE),hl      ; scanning is done -- park the source cursor;
                                             ; tkf_int_value/tkf_calc_and_round/
                                             ; tkf_emit_mantissa below all use HL as
                                             ; scratch (see sysvars.inc TKSRCSAVE)
                ld      a,(TKFLAGS)
                bit     5,a                 ; percent?
                jp      nz,tkf_check_percent
                bit     4,a                 ; hash?
                jp      nz,tkf_double
                bit     2,a                 ; expD?
                jp      nz,tkf_double
                bit     3,a                 ; bang?
                jp      nz,tkf_single
                bit     0,a                 ; dot?
                jp      nz,tkf_bydcount
                bit     1,a                 ; exponent (E, non-D)?
                jp      nz,tkf_bydcount
                ; plain literal, no forcing suffix/dot/exponent: maybe int
                ld      a,(TKDCOUNT)
                cp      5
                jp      c,tkf_go_int        ; D<=4 -> always int
                jp      nz,tkf_bydcount     ; D>5 -> not int-eligible
                call    tkf_cmp32767        ; D==5: CF set iff TKDIG[0..4] <= 32767
                jp      c,tkf_go_int
                jp      tkf_bydcount
tkf_check_percent:
                ld      a,(TKDCOUNT)
                cp      5
                jp      c,tkf_go_int
                jp      nz,tkf_overflow
                call    tkf_cmp32767
                jp      c,tkf_go_int
                jp      tkf_overflow
tkf_bydcount:
                ld      a,(TKDCOUNT)
                cp      7
                jp      nc,tkf_double
                ; falls through: D<=6 -> single
tkf_single:
                ld      a,SGL_DIGITS
                ld      (TKPC),a
                call    tkf_calc_and_round  ; -> TKLEAD + TKDIG[0..PC-1]; may not return
                                             ; (jp tkf_overflow on dec_exp>63); clobbers HL
                pop     de
                ld      a,SNG_TOKEN
                ld      (de),a
                inc     de
                ld      a,(TKLEAD)
                ld      (de),a
                inc     de
                call    tkf_emit_mantissa   ; also clobbers HL (own TKDIG walk)
                ld      hl,(TKSRCSAVE)      ; restore the source cursor for tk_loop
                jp      tk_loop
tkf_double:
                ld      a,DBL_DIGITS
                ld      (TKPC),a
                call    tkf_calc_and_round
                pop     de
                ld      a,DBL_TOKEN
                ld      (de),a
                inc     de
                ld      a,(TKLEAD)
                ld      (de),a
                inc     de
                call    tkf_emit_mantissa
                ld      hl,(TKSRCSAVE)
                jp      tk_loop
tkf_go_int:
                call    tkf_int_value       ; DE = value (0..32767); clobbers HL
                ld      b,d
                ld      c,e                 ; BC = value
                pop     de                  ; DE = TOKBUF destination cursor
                ld      hl,(TKSRCSAVE)      ; restore the source cursor for tk_loop
                jp      tkf_emit_int_bc
tkf_overflow:
                pop     de                  ; nothing of this literal was emitted yet,
                                             ; so DE is exactly the line-truncation point
                ld      a,1
                ld      (TKOVF),a
                jp      tk_end              ; stop crunching the line (own design, D-F1-1)

; --- tkf_scan_digits: consume a run of ASCII digits at (HL) -----------------
; Shared by the integer-part and fractional-part scans (pos is continuous
; across the '.'), so intlen (P) and the first-nonzero position (f) come out
; right regardless of which side of the dot they fall on (own-design, derived
; from the oracle captures: dec_exp = P - f + explicit_exp exactly reproduces
; every §9.2 example, `.000001`'s dec_exp=-5 included). Leading zeros are
; skipped (not stored, not counted in D); once the first nonzero digit is
; seen, every digit from there on (incl. trailing zeros) is stored into TKDIG
; (capped at 24 bytes; TKDCOUNT keeps counting past the cap for correct
; single/double classification even on a very long literal). IX = TKDIG write
; cursor (free during tokenise; no conflict with the evaluator's IX use).
; Clobbers A, B.
tkf_scan_digits:
                ld      a,(hl)
                cp      '0'
                ret     c
                cp      '9'+1
                ret     nc
                sub     '0'
                ld      b,a                 ; B = digit value 0..9
                ld      a,(TKHAVESIG)
                or      a
                jr      nz,tksd_have
                ld      a,b
                or      a
                jr      nz,tksd_first
                jr      tksd_advance        ; leading zero: not stored, not counted
tksd_first:
                ld      a,1
                ld      (TKHAVESIG),a
                ld      a,(TKPOS)
                ld      (TKNZPOS),a         ; f = position of the first nonzero digit
tksd_have:
                ld      a,(TKDCOUNT)
                cp      200
                jr      nc,tksd_dsat
                inc     a
                ld      (TKDCOUNT),a        ; D += 1 (saturating)
tksd_dsat:
                ld      a,(TKSTORED)
                cp      24
                jr      nc,tksd_advance     ; TKDIG full -> still counted in D, not stored
                ld      (ix+0),b
                inc     ix
                inc     a
                ld      (TKSTORED),a
tksd_advance:
                ld      a,(TKPOS)
                inc     a
                ld      (TKPOS),a
                inc     hl
                jr      tkf_scan_digits

; --- tkf_try_exponent: consume an optional E/D exponent (§9.2 rule 6) ------
; HL -> the char right after the mantissa digits. If E/e/D/d is followed by
; an optional sign then at least one digit, it is consumed: TKFLAGS bit1
; (has_exp) [+bit2 (expD), forces double] is set, the signed magnitude is
; accumulated into TKEXP (16-bit, saturated at +-9999 -- far outside the
; legal +-63 dec_exp range, so the saturation never affects a correctly
; classified literal), and HL advances past it. Otherwise HL is left
; UNCHANGED (own-design lookahead: a malformed "5E" or "5EX" leaves 'E' for
; the ordinary tokeniser to process as a separate token/identifier).
;
; Oracle-pinned quirk (S2 extra capture, 2026-07-11, same probe machinery as
; basic_probe_floatlit.py's --machine mode): once an exponent IS consumed, a
; trailing !/#/% is NOT treated as a suffix -- it is left as a raw verbatim
; byte. Captures (VG-8020, `bload"cas:",r:a=<lit>`, KBUF tail):
;   1e10# -> 1D 4B 10 00 00 23 00...   ($23 = '#', uneaten)
;   1e5#  -> 1D 46 10 00 00 23 00...
;   1e1#  -> 1D 42 10 00 00 23 00...
;   1d5!  -> 1F 46 10 00 00 00 00 00 00 21 00...   ($21 = '!', uneaten)
; i.e. the classification is exactly as if no suffix were present (E doesn't
; force a precision; D forces double); tk_loop's caller in tk_float enforces
; this by skipping tkf_try_suffix whenever TKFLAGS bit1 is set. Clobbers
; A, B, C, DE.
tkf_try_exponent:
                ld      a,(hl)
                call    upcase
                cp      'E'
                jr      z,tke_mark_e
                cp      'D'
                jr      z,tke_mark_d
                ret
tke_mark_d:
                ld      a,1
                ld      (TKEXPD),a
                jr      tke_go
tke_mark_e:
                xor     a
                ld      (TKEXPD),a
tke_go:
                push    hl                  ; save the marker position (rollback)
                inc     hl                  ; past E/D
                xor     a
                ld      (TKEXPSIGN),a       ; 0 = positive
                ld      a,(hl)
                cp      '+'
                jr      z,tke_skipsign
                cp      '-'
                jr      nz,tke_checkdig
                ld      a,1
                ld      (TKEXPSIGN),a       ; 1 = negative
tke_skipsign:
                inc     hl
tke_checkdig:
                ld      a,(hl)
                cp      '0'
                jr      c,tke_fail
                cp      '9'+1
                jr      nc,tke_fail
                ; valid exponent: commit
                pop     de                  ; discard the rollback position
                ld      a,(TKFLAGS)
                or      2                   ; bit1 = has_exp
                ld      (TKFLAGS),a
                ld      a,(TKEXPD)
                or      a
                jr      z,tke_accum
                ld      a,(TKFLAGS)
                or      4                   ; bit2 = expD (forces double)
                ld      (TKFLAGS),a
tke_accum:
                ld      de,0                ; DE = exponent magnitude accumulator
tke_dloop:
                ld      a,(hl)
                cp      '0'
                jr      c,tke_ddone
                cp      '9'+1
                jr      nc,tke_ddone
                sub     '0'
                ld      c,a
                push    hl                  ; save source cursor
                ld      h,d
                ld      l,e
                add     hl,hl
                add     hl,hl
                add     hl,de
                add     hl,hl
                ld      e,c
                ld      d,0
                add     hl,de               ; HL = DE_old*10 + digit
                ld      de,9999
                or      a
                sbc     hl,de
                jr      nc,tke_clamp
                add     hl,de
                ex      de,hl
                jr      tke_dnext
tke_clamp:
                ld      de,9999
tke_dnext:
                pop     hl                  ; restore source cursor
                inc     hl
                jr      tke_dloop
tke_ddone:
                ld      a,(TKEXPSIGN)
                or      a
                jr      z,tke_esdone
                call    neg_de              ; DE = -DE; HL is the SOURCE CURSOR here
                                             ; (unlike flt_out's use of neg_de) -- must
                                             ; NOT be touched, so this (not an HL-based
                                             ; negate) is deliberate
tke_esdone:
                ld      (TKEXP),de
                ret
tke_fail:
                pop     hl                  ; rollback to the marker position
                ret

; --- tkf_try_suffix: consume an optional !/#/% type suffix -----------------
; Only called when tkf_try_exponent found none (see its header). Sets TKFLAGS
; bit3 (!) / bit4 (#) / bit5 (%) and advances HL past the char.
tkf_try_suffix:
                ld      a,(hl)
                cp      '!'
                jr      z,tks_bang
                cp      '#'
                jr      z,tks_hash
                cp      '%'
                jr      z,tks_pct
                ret
tks_bang:
                ld      a,(TKFLAGS)
                or      8
                ld      (TKFLAGS),a
                inc     hl
                ret
tks_hash:
                ld      a,(TKFLAGS)
                or      16
                ld      (TKFLAGS),a
                inc     hl
                ret
tks_pct:
                ld      a,(TKFLAGS)
                or      32
                ld      (TKFLAGS),a
                inc     hl
                ret

; --- tkf_cmp32767: are the 5 stored digits TKDIG[0..4] <= 32767? -----------
; out: CF set iff <=32767. Clobbers A, B, C, D, E, HL.
tkf_cmp32767:
                ld      de,tkf_ref32767
                ; falls through into the general 5-digit comparator
; --- tkf_cmp5: are the 5 stored digits TKDIG[0..4] <= the bound at (DE)? ---
; DE -> a 5-entry unpacked-digit bound table. out: CF set iff <= bound.
; Clobbers A, B, C, D, E, HL.
tkf_cmp5:
                ld      hl,TKDIG
                ld      b,5
tkf_cmp_lp:
                ld      a,(de)
                ld      c,a
                ld      a,(hl)
                cp      c
                jr      c,tkf_cmp_small     ; stored < ref -> <=32767 -> CF set
                jr      nz,tkf_cmp_big      ; stored > ref -> >32767 -> CF clear
                inc     hl
                inc     de
                djnz    tkf_cmp_lp
                scf                         ; all equal -> ==32767 -> <=
                ret
tkf_cmp_small:
                scf
                ret
tkf_cmp_big:
                or      a
                ret
tkf_ref32767:
                db      3,2,7,6,7
; flt_to_int16's sign-dependent bounds (D-F1-2 address domain, see its header)
tkf_ref65535:
                db      6,5,5,3,5           ; positive ceiling: unsigned 16-bit
tkf_ref32768:
                db      3,2,7,6,8           ; negative magnitude ceiling (-32768)

; --- tkf_int_value: TKDIG[0..D-1] (D=TKDCOUNT, <=5 here) -> DE = value -----
; Same *10+digit accumulation idiom as tk_number (interp.asm); safe from
; 16-bit overflow because every caller has already confirmed D<=5 and, for
; D==5, value<=65535 at most (tkf_cmp5 against a caller-chosen bound: 32767
; in tk_float's int classification, 65535/32768 in flt_to_int16).
; Clobbers A, B, C, HL.
tkf_int_value:
                ld      de,0
                ld      a,(TKDCOUNT)
                or      a
                ret     z
                ld      b,a
                ld      hl,TKDIG
tiv_lp:
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
                djnz    tiv_lp
                ret

; --- tkf_emit_int_bc: BC = value (0..32767) -> int token(s) at (DE) --------
; Same encoding as tk_number's tail (interp.asm): $11+n / $0F,<byte> /
; $1C,<word LE>. Tail-calls tk_loop.
tkf_emit_int_bc:
                ld      a,b
                or      a
                jr      nz,tei_w
                ld      a,c
                cp      10
                jr      nc,tei_b
                add     a,INT_DIGIT_BASE
                ld      (de),a
                inc     de
                jp      tk_loop
tei_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      tk_loop
tei_w:
                ld      a,INT2_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                ld      a,b
                ld      (de),a
                inc     de
                jp      tk_loop

; --- tkf_calc_and_round: dec_exp + rounded mantissa -> TKLEAD/TKDIG --------
; in: TKPC = target precision (6/14), TKHAVESIG/TKINTLEN/TKNZPOS/TKEXP/
; TKDCOUNT/TKDIG (raw significant digits) from the scan.
; out: TKLEAD = final lead byte (0..127); TKDIG[0..TKPC-1] = the rounded/
; padded mantissa digit VALUES (0-9 each, not yet packed). On dec_exp>63
; (post-rounding) jumps to tkf_overflow and does not return.
; dec_exp = TKINTLEN - TKNZPOS + TKEXP (signed); dec_exp<=-64 -> TKLEAD=0
; with the mantissa still computed/retained (§9.2 rule 6, the "1e-65" case:
; reads as value 0, no error). Clobbers A, B, C, HL, DE.
tkf_calc_and_round:
                ld      a,(TKHAVESIG)
                or      a
                jr      nz,tcr_go
                ; value 0: lead=0, mantissa all zero (14 covers both PC cases)
                xor     a
                ld      (TKLEAD),a
                ld      hl,TKDIG
                ld      b,14
tcr_zero_lp:
                ld      (hl),a
                inc     hl
                djnz    tcr_zero_lp
                ret
tcr_go:
                ld      a,(TKINTLEN)
                ld      l,a
                ld      h,0
                ld      a,(TKNZPOS)
                ld      e,a
                ld      d,0
                or      a
                sbc     hl,de               ; HL = P - f
                ld      de,(TKEXP)
                add     hl,de               ; HL = dec_exp (pre-round)
                ld      (TKDEXP),hl
                call    tkf_round_mantissa  ; may bump TKDEXP by +1 (double carry-out)
                ld      hl,(TKDEXP)
                push    hl
                ld      de,63
                call    cmp16_bits          ; A=1/2/4 (lt/eq/gt); HL clobbered inside
                pop     hl
                cp      4
                jp      z,tkf_overflow      ; dec_exp > 63
                push    hl
                ld      de,$FFC0            ; -64
                call    cmp16_bits
                pop     hl
                cp      1
                jr      nz,tcr_leadok
                xor     a
                ld      (TKLEAD),a          ; dec_exp <= -64 -> forced lead 0
                ret
tcr_leadok:
                ld      de,64
                add     hl,de
                ld      a,l
                ld      (TKLEAD),a
                ret

; --- tkf_round_mantissa: round/pad TKDIG to TKPC digits, half-up -----------
; D<=PC: pad TKDIG[D..PC-1] with zeros, no rounding. D>PC: keep TKDIG[0..PC-1],
; round on TKDIG[PC] (>=5 rounds up, carrying through the kept digits). A full
; carry-out (every kept digit was 9) does NOT renormalise for single (TKDEXP
; unchanged -- the oracle-pinned `9999995!` -> 1000000 quirk) but DOES for
; double (TKDEXP += 1); either way the carried mantissa is "1" + (PC-1) zeros.
; Clobbers A, B, C, HL, DE.
tkf_round_mantissa:
                ld      a,(TKPC)
                ld      b,a
                ld      a,(TKDCOUNT)
                cp      b
                jp      c,trm_pad
                jp      z,trm_pad
                ; D > PC: round using TKDIG[PC]
                ld      hl,TKDIG
                ld      c,b
                ld      b,0
                add     hl,bc
                ld      a,(hl)
                cp      5
                ret     c                   ; rounding digit < 5 -> truncate as-is
                call    trm_increment       ; CF set iff it carried out of all PC digits
                ret     nc
                call    trm_set_carried_mantissa
                ld      a,(TKPC)
                cp      14
                ret     nz                  ; single: quirk -- dec_exp unchanged
                ld      hl,(TKDEXP)
                inc     hl
                ld      (TKDEXP),hl
                ret
trm_pad:
                ld      a,(TKDCOUNT)
                ld      l,a
                ld      h,0
                ld      de,TKDIG
                add     hl,de               ; HL -> first pad slot
                ld      a,(TKPC)
                ld      b,a
                ld      a,(TKDCOUNT)
                ld      c,a
                ld      a,b
                sub     c                   ; A = PC - D
                ret     z
                ld      b,a
trm_pad_lp:
                ld      (hl),0
                inc     hl
                djnz    trm_pad_lp
                ret

; --- trm_increment: TKDIG[0..PC-1] += 1 (big-decimal) ----------------------
; out: CF set iff the increment carried out of the leftmost (index-0) digit.
; Clobbers A, B, HL.
trm_increment:
                ld      a,(TKPC)
                ld      b,a
                ld      hl,TKDIG
                dec     a
                ld      e,a
                ld      d,0
                add     hl,de               ; HL -> TKDIG[PC-1] (rightmost kept digit)
trm_inc_lp:
                ld      a,(hl)
                inc     a
                cp      10
                jr      c,trm_inc_done
                ld      (hl),0
                dec     hl
                djnz    trm_inc_lp
                scf                         ; carried past index 0
                ret
trm_inc_done:
                ld      (hl),a
                or      a
                ret

; --- trm_set_carried_mantissa: TKDIG = "1" + (PC-1) zeros ------------------
trm_set_carried_mantissa:
                ld      a,(TKPC)
                ld      b,a
                ld      hl,TKDIG
                ld      (hl),1
                inc     hl
                dec     b
trm_scm_lp:
                ld      a,b
                or      a
                ret     z
                ld      (hl),0
                inc     hl
                dec     b
                jr      trm_scm_lp

; --- tkf_emit_mantissa: TKDIG[0..PC-1] -> PC/2 packed-BCD bytes at (DE) ----
; 2 digits/byte, left-justified (MSX2 TH §9.1). Clobbers A, B, HL.
tkf_emit_mantissa:
                ld      a,(TKPC)
                ld      b,a
                srl     b                   ; B = PC/2 byte count
                ld      hl,TKDIG
tem_lp:
                ld      a,(hl)
                add     a,a
                add     a,a
                add     a,a
                add     a,a                 ; A = digit<<4 (digit<=9, no wraparound)
                inc     hl
                or      (hl)                ; | next digit (0..9)
                inc     hl
                ld      (de),a
                inc     de
                djnz    tem_lp
                ret

; =============================================================================
; flt_out: FAC/FACTYP -> formatted string -> print_string (spec §9.3)
; =============================================================================
; Sign space/'-' + digits + ONE trailing space; E notation for BOTH
; precisions (never D on this reference); FIXED form iff -1<=dec_exp<=14,
; else E form. Value 0 (lead byte 0; also the dec_exp<=-64 crunch-time
; underflow case, mantissa retained but unprinted per §9.2 rule 6) -> "0".
; Clobbers A, B, C, D, E, H, L.
flt_out:
                ld      a,(FACTYP)
                cp      8
                jr      z,flo_dblsz
                ld      a,6
                ld      (TKPC),a
                ld      a,3
                ld      (FOMBYTES),a
                jr      flo_unpackgo
flo_dblsz:
                ld      a,14
                ld      (TKPC),a
                ld      a,7
                ld      (FOMBYTES),a
flo_unpackgo:
                ld      a,(FAC)
                or      a
                jp      z,flo_zero
                ld      (FOSIGN),a          ; stash the raw lead byte (sign in bit7)
                and     $7F
                sub     64                  ; A = dec_exp (signed, -64..63)
                ld      l,a
                ld      h,0
                bit     7,a
                jr      z,flo_dexp_ok
                ld      h,$FF
flo_dexp_ok:
                ld      (TKDEXP),hl
                ; unpack the mantissa bytes into TKDIG (one digit value per byte)
                ld      a,(FOMBYTES)
                ld      b,a
                ld      hl,FAC+1
                ld      de,TKDIG
flo_unpack:
                ld      a,(hl)
                ld      c,a
                and     $F0
                rrca
                rrca
                rrca
                rrca
                ld      (de),a
                inc     de
                ld      a,c
                and     $0F
                ld      (de),a
                inc     de
                inc     hl
                djnz    flo_unpack
                ; strip trailing zeros -> s (>=1: lead<>0 guarantees a nonzero digit)
                ld      a,(TKPC)
                ld      c,a
flo_strip:
                ld      a,c
                dec     a
                ld      l,a
                ld      h,0
                ld      de,TKDIG
                add     hl,de
                ld      a,(hl)
                or      a
                jr      nz,flo_strip_done
                dec     c
                ld      a,c
                or      a
                jr      nz,flo_strip
flo_strip_done:
                ld      a,c
                ld      (FOSIGCOUNT),a
                ; --- sign char, then dispatch fixed vs E form ---
                ld      hl,FOUTBUF
                ld      a,(FOSIGN)
                and     $80
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
                jp      print_string
flo_zero:
                ld      hl,FOUTBUF
                ld      (hl),' '
                inc     hl
                ld      (hl),'0'
                inc     hl
                ld      (hl),' '
                inc     hl
                xor     a
                ld      (hl),a
                ld      hl,FOUTBUF
                jp      print_string

; --- flo_is_fixed: CF set iff -1 <= dec_exp <= 14. Preserves HL. -----------
; Clobbers A, DE.
flo_is_fixed:
                push    hl
                ld      hl,(TKDEXP)
                ld      de,14
                call    cmp16_bits
                pop     hl
                cp      4
                jr      z,flo_notfixed
                push    hl
                ld      hl,(TKDEXP)
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
                ld      hl,(TKDEXP)
                ld      de,0
                call    cmp16_bits
                pop     hl
                cp      4
                jr      z,flo_fx_bc
                ld      (hl),'.'
                inc     hl
                ld      de,(TKDEXP)
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
                jp      flo_write_digits
flo_fx_bc:
                ld      a,(FOSIGCOUNT)
                push    hl
                ld      hl,(TKDEXP)
                ld      c,l
                pop     hl
                cp      c
                jr      c,flo_fx_case_b
                jr      z,flo_fx_case_b
                ; case (c): 0 < dec_exp < s
                push    hl
                ld      hl,(TKDEXP)
                ld      a,l
                pop     hl
                ld      b,a
                ld      c,0
                call    flo_write_digits_range   ; digits[0..dec_exp)
                ld      (hl),'.'
                inc     hl
                push    hl
                ld      hl,(TKDEXP)
                ld      a,l
                pop     hl
                ld      c,a
                ld      a,(FOSIGCOUNT)
                sub     c
                ld      b,a
                jp      flo_write_digits_range   ; digits[dec_exp..s)
flo_fx_case_b:
                ld      a,(FOSIGCOUNT)
                ld      b,a
                ld      c,0
                call    flo_write_digits_range   ; all s digits
                push    hl
                ld      hl,(TKDEXP)
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

; --- flo_write_digits: write all FOSIGCOUNT digits from TKDIG[0..] --------
flo_write_digits:
                ld      a,(FOSIGCOUNT)
                ld      b,a
                ld      c,0
                jp      flo_write_digits_range

; --- flo_write_digits_range: write B ASCII digits from TKDIG[C..] at (HL) -
; out: HL advanced past the written digits. Clobbers A, B, D, E.
flo_write_digits_range:
                ld      a,b
                or      a
                ret     z
                push    hl
                ld      hl,TKDIG
                ld      d,0
                ld      e,c
                add     hl,de
                ex      de,hl               ; DE = TKDIG[C] read cursor
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
                ld      a,(TKDIG)
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
                ld      hl,(TKDEXP)
                ld      de,$FFFF            ; -1
                add     hl,de               ; HL = dec_exp - 1
                ld      a,h
                and     $80
                ld      d,a                 ; D = sign flag (0 pos / $80 neg)
                jr      z,flo_e_magpos
                xor     a
                sub     l
                ld      l,a
                ld      a,0
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
neg_de:
                xor     a
                sub     e
                ld      e,a
                ld      a,0
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
flt_int_result:
                ld      a,2
                ld      (FACTYP),a
                ret

; flt_guard (F1's sticky-FACTYP combine guard, interim divergence D-F1-3) is
; REMOVED — F2 replaces every one of its 12 call sites in expr.asm with real
; float-aware combine logic (float-arith.asm's combine_add/combine_sub/
; combine_mul/combine_div_float/combine_cmp, plus fac_to_int_strict at the
; logical/\/MOD sites), so no site is left that needs "float arithmetic
; isn't implemented yet" as its fallback.
