; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — fltout.asm  (WAVE 1 eviction tenant, docs/spec-basic-subrom.md)
; ===========================================================================
; The float PRINT formatter (FAC/FACTYP -> FOUTBUF), evicted from the repack
; main ROM's basic/float.asm into sub-ROM PAGE 0 as a ZERO-LINKAGE PURE LEAF.
; Reached via the page-0 entry table (index SUBROM_IDX_FLTOUT); a main-ROM stub
; (basic/print.asm exp_num_float) marshals FAC in RAM, CALSLTs here to format
; into FOUTBUF, then prints FOUTBUF itself.
;
; PURE-LEAF DISCIPLINE (§3b): while this runs, slot-0 page 0 (BIOS + low region)
; is switched OUT, so it may touch ONLY page-3/2 RAM and its own page-0 body.
; Two changes from the resident original make that hold:
;   * its two tail `jp print_string` become `ret` — print_string reaches
;     CHPUT (BIOS, switched out here), so the STUB does the printing;
;   * its two page-1/resident leaf callees, `cmp16_bits` (basic/expr.asm) and
;     `neg_de` (the resident half of basic/float.asm, still needed by
;     float-arith), are DUPLICATED below as sub-local copies. The bodies are
;     byte-identical own-design clones — see those files for the authoritative
;     source; they are tiny (11 B / 8 B) and stable.
; Every RAM cell (FAC/FACTYP/FOUTBUF/TKDIG/TKPC/FOMBYTES/TKDEXP/FOSIGN/
; FOSIGCOUNT) is the SAME address as the repack main ROM (shared sysvars.inc,
; included by sub.asm under ROM_BASE<$4000), so no marshalling translation.
;
; CLEAN-ROOM: the formatting algorithm is own-design (copied verbatim from our
; own basic/float.asm); the number FORMAT layout is MSX2 TH. No disassembly.
; ===========================================================================

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
                ret                     ; sub-ROM: return to the main-ROM stub, which prints FOUTBUF
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
                ret                     ; sub-ROM: return to the main-ROM stub, which prints FOUTBUF

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

; --- sub-local cmp16_bits (byte-identical clone of basic/expr.asm cmp16_bits) -
; Signed 16-bit compare HL?DE -> A: 2 equal / 1 less / 4 greater. Resident copy
; lives in page 1 (invisible here), so the formatter carries its own.
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

; --- sub-local neg_de (byte-identical clone of basic/float.asm neg_de) --------
; DE = -DE (two's complement). Resident copy stays with float-arith in page 0
; low region (invisible here). Clobbers A.
neg_de:
                xor     a
                sub     e
                ld      e,a
                ld      a,0
                sbc     a,d
                ld      d,a
                ret
