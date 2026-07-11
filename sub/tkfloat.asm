; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — tkfloat.asm  (WAVE 1 eviction tenant, docs/spec-basic-subrom.md)
; ===========================================================================
; The float LITERAL CRUNCH (tk_float, FAC-less: ASCII literal -> tokenised BCD
; value bytes), evicted from the repack main ROM's basic/float.asm into sub-ROM
; PAGE 0 as a pure leaf. Reached via the page-0 entry table (index
; SUBROM_IDX_TKFLOAT); a main-ROM stub (basic/float.asm tk_float) dispatches
; here, then acts on the returned disposition.
;
; WHY THE CRUNCH AND NOT THE FORMATTER (user call 2026-07-11): a page-0 sub-ROM
; tenant runs with the BIOS + low region switched out, so it must be pure
; computation. The PRINT formatter is pure-compute too but RUNTIME-HOT (every
; float PRINT), so it stays resident. The crunch runs only at TOKENISE time
; (line edit / program load) — cold — so it is the right thing to page out.
;
; PURE-LEAF DISCIPLINE (§3b). Two changes from the resident original make the
; crunch self-contained (it may touch ONLY page-2/3 RAM + its own body):
;   * its jp-threaded exits back into the tokeniser become a RETURN with a
;     disposition byte in A: A=0 "continue" (the stub does jp tk_loop), A=1
;     "end/overflow" (the stub does jp tk_end; TKOVF is set here first). HL (the
;     advanced source cursor) and DE (the advanced TOKBUF dest) are returned for
;     the tokeniser to resume with — both pass through CALSLT unchanged.
;   * its two page-1 leaf callees `upcase` (basic/interp.asm) and `cmp16_bits`
;     (basic/expr.asm) are duplicated below as byte-identical own-design clones.
; The tkf_ref* bound tables live INSIDE this body (used by tkf_cmp32767); the
; resident float-arith needs them too, so basic/float.asm keeps its OWN copy —
; no cross-ROM reference either way.
;
; RAM cells (TKPOS/TKDIG/TKPC/TKLEAD/TKOVF/TKSRCSAVE/TKFLAGS/...) are the SAME
; addresses as the repack main ROM (shared sysvars.inc, included by sub.asm),
; so no marshalling translation.
;
; CLEAN-ROOM: the crunch algorithm is own-design (copied verbatim from our own
; basic/float.asm); classification/format rules are oracle-pinned + MSX2 TH; the
; token bytes are oracle-pinned. No disassembly.
; ===========================================================================

SGL_DIGITS      equ     6       ; single mantissa digit count (MSX2 TH number format)
DBL_DIGITS      equ     14      ; double mantissa digit count (MSX2 TH number format)

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
                jp      crx_cont            ; sub-crunch: disposition A=0 (continue), HL/DE set
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
                jp      crx_cont            ; sub-crunch: disposition A=0 (continue), HL/DE set
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
                ret                     ; sub-crunch: disposition A=1 (end; TKOVF already set)

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
                jp      crx_cont            ; sub-crunch: disposition A=0 (continue), HL/DE set
tei_b:
                ld      a,INT1_TOKEN
                ld      (de),a
                inc     de
                ld      a,c
                ld      (de),a
                inc     de
                jp      crx_cont            ; sub-crunch: disposition A=0 (continue), HL/DE set
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
                jp      crx_cont            ; sub-crunch: disposition A=0 (continue), HL/DE set

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

; --- crx_cont: the "continue" disposition return (A=0) --------------------
; Every normal crunch exit reaches here with HL = advanced source cursor and
; DE = advanced TOKBUF dest already set; the main-ROM stub resumes tk_loop.
crx_cont:
                xor     a
                ret

; --- sub-local neg_de (byte-identical clone of basic/float.asm neg_de) ------
; DE = -DE (two's complement); used by the exponent-sign path (tke_esdone). The
; resident copy stays with float-arith/flt_out in the low region (invisible
; here). Clobbers A.
neg_de:
                xor     a
                sub     e
                ld      e,a
                ld      a,0
                sbc     a,d
                ld      d,a
                ret

; --- sub-local upcase (byte-identical clone of basic/interp.asm upcase) ----
; A -> uppercase if 'a'..'z'. Resident copy is in page 1 (invisible here).
upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     $20
                ret

; --- sub-local cmp16_bits (byte-identical clone of basic/expr.asm cmp16_bits) -
; Signed 16-bit compare HL?DE -> A: 2 equal / 1 less / 4 greater.
cmp16_bits:
                ld      a,h
                cp      d
                jr      nz,c16_ne
                ld      a,l
                cp      e
                jr      nz,c16_ne
                ld      a,2
                ret
c16_ne:
                or      a
                sbc     hl,de
                jp      pe,c16_vset
                jp      m,c16_lt
                jr      c16_gt
c16_vset:
                jp      p,c16_lt
                jr      c16_gt
c16_lt:
                ld      a,1
                ret
c16_gt:
                ld      a,4
                ret
