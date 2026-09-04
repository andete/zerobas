; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — punum.asm  (PRINT USING numeric renderer, D-PUNUM)
; ===========================================================================
; docs/spec-basic-pufloat.md §5. `PRINT USING`'s numeric field was INTEGER-ONLY
; and TRUNCATING: `pu_do_number` evaluates to a 16-bit DE and formats it with
; `pu_fmt_int`, so a value past int16 rendered as **0** -- a silent wrong answer
; -- and a fraction was chopped where both references ROUND HALF-UP.
;
;     PRINT USING"#######";1234567   refs 1234567   was `      0`
;     PRINT USING"#####";1.5         refs `    2`   was `    1`
;     PRINT USING"#####";2.5         refs `    3`   was `    2`
;
; PAGE 1 OF THE SUB-ROM, and that is what makes this possible at all: a page-1
; tenant runs with page 0 still holding slot 0, so main's LOW REGION is callable
; by absolute address -- the rule sub/circleparse.asm already relies on. `flt_fmt`
; ($305E, basic/float.asm) is low-region, and arrives through the GENERATED
; sub/basic-resident-abi.inc so a low-region shift cannot leave us calling a stale
; address. Main page 1 had 32 B free; this body is far larger than that.
;
; 🎯 ROUNDING THE RENDERED TEXT IS EXACT HERE, and that is not a shortcut. MSX
; floats are BCD, so `flt_fmt`'s decimal output is the value -- there is no binary
; representation error to defeat and no tie-breaking to reproduce. `1.5` -> 2 and
; `2.5` -> 3 on both references pin the direction as HALF-UP, not banker's.
;
; CLEAN-ROOM: original code. The rounding DIRECTION is a black-box reading of both
; references (scratchpad/pufloat_probe.py c.round / c.round2); the rendering is
; our own flt_fmt. No disassembly.
; ===========================================================================

; --- pu_num_tenant: the live numeric value -> PU_NUM as PRINT USING wants it -
;   in   FAC / FACTYP hold the evaluated argument (the caller routes FACTYP==2
;        to its own integer path, which is already correct and cheaper)
;   out  PU_NUM = "[-]digits",0 rounded half-up to a whole number
;        A = its length. Clobbers AF, BC, DE, HL.
;
; `flt_fmt` leaves FOUTBUF as: a sign column (`-` or a SPACE), the digits, then
; ONE trailing space. We keep a `-`, drop the space column, copy digits until the
; run ends, and round on the first fraction digit.
; --- pu_num_tenant: the live numeric value -> PU_NUM, to PU_DEC places -------
;   in   FAC / FACTYP hold the evaluated argument
;        PU_FLAGS bit6 = a `.` was scanned; PU_DEC = how many places
;   out  PU_NUM = "[-]digits[.digits]",0 ; A = its length. Clobbers AF, BC, DE, HL.
;
; 🎯 THE DIGITS ARE BUILT CONTIGUOUSLY AND THE POINT IS INSERTED LAST, so rounding
; at N places is ONE carry walk over ONE array -- there is no decimal point in the
; middle for the carry to cross. C carries the INTEGER-digit count throughout, and
; the carry growing the number (9.5 -> 10.) simply increments it.
;
; ⚠️ DIGSTART IS RECOMPUTED, NOT STACKED. The first attempt at this (D-PUDOT,
; reverted) juggled it through push/pop across three branches and crashed. It is
; PU_NUM, or PU_NUM+1 when a `-` leads -- cheaper to derive than to keep, and it
; removes every unbalanced-stack path at once.
;
; ⚠️ `##.` -- a point with ZERO places -- still prints the point (` 2.`, measured).
; The reverted attempt returned early on PU_DEC==0 and lost it.
;
; ⚠️ A format with an EMPTY integer part (`.##`) never reaches here: ptf_num only
; starts a numeric field on a `#`, so a leading `.` is still scanned as a literal.
; `d.lead` stays divergent until that scanner entry point exists.
;
; The algorithm was checked as a model against the eleven measured `d.*` values
; (plus the two carry-growth cases) BEFORE this was written.
pu_num_tenant:
                ld      a,(PU_DEC)
                and     a                   ; bit7 = D-PUEXP's `^^^^` marker
                jp      m,pnt_exp
                call    flt_fmt             ; HL -> FOUTBUF
                ld      de,PU_NUM
                ld      a,(hl)
                cp      '-'
                jr      nz,pnt_nosign
                ld      (de),a              ; keep the minus
                inc     de
pnt_nosign:
                inc     hl                  ; past the sign column either way
                ld      c,0                 ; C = integer digits written
pnt_int:
                ld      a,(hl)
                cp      '0'
                jr      c,pnt_intdone
                cp      '9' + 1
                jr      nc,pnt_intdone
                ld      (de),a
                inc     de
                inc     hl
                inc     c
                jr      pnt_int
pnt_intdone:
                ld      a,c
                or      a
                jr      nz,pnt_places
                ld      a,'0'               ; a pure fraction: emit the leading 0
                ld      (de),a              ; the reference shows for `#.##`
                inc     de
                inc     c
pnt_places:
                ld      b,0                 ; B = decimal places wanted
                ld      a,(PU_FLAGS)
                bit     6,a
                jr      z,pnt_atdot
                ld      a,(PU_DEC)
                and     $7F                 ; mask D-PUEXP's marker bit
                ld      b,a
pnt_atdot:
                ld      a,(hl)              ; step past the source `.` so HL walks
                cp      '.'                 ; the fraction digits
                jr      nz,pnt_frac
                inc     hl
pnt_frac:
                ld      a,b
                or      a
                jr      z,pnt_round
pnt_frlp:
                ld      a,(hl)
                cp      '0'
                jr      c,pnt_frpad
                cp      '9' + 1
                jr      nc,pnt_frpad
                inc     hl                  ; a real source digit
                jr      pnt_frput
pnt_frpad:
                ld      a,'0'               ; source exhausted -- pad, and do NOT
                                            ; advance HL, so the rounding digit
                                            ; below stays absent
pnt_frput:
                ld      (de),a
                inc     de
                djnz    pnt_frlp
pnt_round:
                ld      a,(hl)              ; first source digit past the cut
                cp      '5'
                jr      c,pnt_comma         ; below half -> plain truncation
                push    de                  ; the end of the digits
                call    pnt_digstart        ; HL = first digit
pnt_carry:
                dec     de
                ld      a,(de)
                cp      '9'
                jr      z,pnt_nine
                inc     a
                ld      (de),a
                pop     de                  ; back to the end
                jr      pnt_comma
pnt_nine:
                ld      a,'0'
                ld      (de),a              ; 9 -> 0 and keep carrying
                ld      a,d
                cp      h
                jr      nz,pnt_carry
                ld      a,e
                cp      l
                jr      nz,pnt_carry
                ; every digit carried: the number gains a place (9.5 -> 10.).
                ; The run is all '0' now, so growing it is a write, not a move.
                pop     de
                ld      a,'0'
                ld      (de),a
                inc     de
                call    pnt_digstart
                ld      (hl),'1'
                inc     c                   ; one more integer digit
; --- D-PUCOMMA: group the INTEGER digits in threes ---------------------------
; Runs after rounding (so a carry that grows the number regroups correctly) and
; before the point is inserted (so the point still lands at C, which this pass
; widens by the commas it adds).
;
; 🎯 THE GROUPING IS EVERY THREE FROM THE RIGHT, and the format's own `,`
; POSITIONS ARE NOT USED. Those two rules agree on almost every format; row
; `m.pos` separates them loudly -- `USING"####,####";12345678` is `%12,345,678`
; on both references, so the every-three rule OVERFLOWS a 9-wide field where
; placing commas at the format's positions would have fitted in it.
pnt_comma:
                ld      a,(PU_FLAGS)
                bit     7,a
                jp      z,pnt_point
                ld      a,c                 ; K = (integer digits - 1) / 3
                dec     a
                ld      b,0
pnt_ck:
                sub     3
                jr      c,pnt_ckd
                inc     b
                jr      pnt_ck
pnt_ckd:
                ld      a,b
                or      a
                jp      z,pnt_point         ; 3 digits or fewer: no comma at all
                ld      (PU_COMMAS),a
                ld      h,d                 ; HL = the NEW end = old end + K
                ld      l,e
                add     a,l
                ld      l,a
                jr      nc,pnt_cne
                inc     h
pnt_cne:
                push    hl                  ; ...kept for the finish
                push    hl
                pop     ix                  ; IX = write cursor, walking down
                call    pnt_digstart        ; HL = DIGSTART
                ld      a,e                 ; B = fraction bytes = L - C
                sub     l
                sub     c
                ld      b,a
                or      a
                jr      z,pnt_cint          ; an integer-only field
pnt_cfrac:
                dec     de                  ; the fraction moves right unchanged
                dec     ix
                ld      a,(de)
                ld      (ix+0),a
                djnz    pnt_cfrac
pnt_cint:
                ld      b,c                 ; B = integer digits still to place
                ld      l,3                 ; L = digits left in this group
pnt_clp:
                dec     de
                dec     ix
                ld      a,(de)
                ld      (ix+0),a
                dec     b
                jr      z,pnt_cdone         ; ⚠️ TESTED BEFORE THE GROUP COUNT, so
                                            ; the LEFTMOST group never gets a
                                            ; leading comma: `123` stays `123`.
                dec     l
                jr      nz,pnt_clp
                ld      l,3
                dec     ix
                ld      (ix+0),','
                jr      pnt_clp
pnt_cdone:
                ld      a,(PU_COMMAS)
                add     a,c
                ld      c,a                 ; the point now sits K columns later
                pop     de                  ; DE = the new end
pnt_point:
                ld      a,(PU_FLAGS)
                bit     6,a
                jr      z,pnt_term          ; no `.` in the format at all
                ; fraction length = end - DIGSTART - C. PU_NUM is 8 bytes and the
                ; widest result fits, so neither subtraction borrows across a page.
                call    pnt_digstart
                ld      a,e
                sub     l
                sub     c
                ld      b,a                 ; B = fraction digits (may be 0)
                push    de                  ; the shift moves DE
                ld      h,d
                ld      l,e
                inc     hl                  ; HL = the new end
                ld      a,b
                or      a
                jr      z,pnt_putdot        ; `##.` -- no fraction to move
pnt_shift:
                dec     de
                dec     hl
                ld      a,(de)
                ld      (hl),a
                djnz    pnt_shift
pnt_putdot:
                dec     hl
                ld      (hl),'.'            ; lands where the fraction began
                pop     de
                inc     de                  ; one byte longer overall
pnt_term:
                xor     a
                ld      (de),a              ; 0-terminate
                ld      hl,PU_NUM
                ld      a,e
                sub     l
                ret

; pnt_digstart -- HL = PU_NUM's first DIGIT, stepping past a leading `-`.
; Clobbers AF and HL only, which is why it can be called from inside the carry
; walk without disturbing DE, BC or the count in C.
pnt_digstart:
                ld      hl,PU_NUM
                ld      a,(hl)
                cp      '-'
                ret     nz
                inc     hl
                ret

; --- D-PUEXP: `^^^^`, the exponent form --------------------------------------
; docs/spec-basic-pufloat.md §14. Transcribed from a Python model that passes
; 15/15 against the measured rows -- the same order of work that made D-PUDOT
; land on its second attempt after the first was written straight into Z80.
;
; 🎯 ONE RULE, and two special cases that looked real and are not: the mantissa
; carries (FIELD COLUMNS BEFORE THE POINT) - 1 integer digits, counting `#`, `,`,
; `**` and a leading sign alike. `e.comma` is what makes that unmistakable --
; `#,###` is FIVE columns and the mantissa gets FOUR integer digits, while the
; comma itself is never printed.
;
; It needs no new RAM: n is derived from cells that already exist,
;     n = PU_W - 4 (the `E+dd`) - 1 (the sign column) - (1 + places, if a point)
;
; ⚠️ NO FLOAT SCALING. The value's decimal TEXT comes from flt_fmt and the point
; is shifted symbolically. flt_fmt's text is not uniform and that was measured
; (rows f.big / f.small): `PRINT 1.5E+10` is ` 15000000000 ` but `PRINT 1.5E-10`
; is ` 1.5E-10 ` -- already exponential -- so the parser accepts an `E±dd` on its
; own INPUT.
;
; ⚠️ THE POINT PRINTS ON `##.^^^^` (row e.dot0, ` 2.E+00`), so "has a point" is
; PU_FLAGS bit6 and NOT "places > 0". The model had that wrong until e.dot0 was
; measured.
pnt_exp:
                ; ⚠️ flt_fmt FIRST, then n -- n's inputs are all in RAM, while BC
                ; is NOT preserved across the call. Computing n before it and
                ; reading C after cost two rows (e.big / e.small), and one of the
                ; wrong answers was a plausible 0 that let e.round pass anyway.
                call    flt_fmt             ; HL -> FOUTBUF
                ld      a,(PU_DEC)
                and     $7F
                ld      b,a                 ; B = places
                ld      a,(PU_W)
                sub     5                   ; the `E+dd` and the leading column
                ld      c,a
                ld      a,(PU_FLAGS)
                bit     6,a
                jr      z,pnt_x_n
                ld      a,c
                sub     b
                dec     a                   ; ...and the point's own column
                ld      c,a
pnt_x_n:
                ; --- the leading column ---------------------------------------
                ; ⚠️ EMIT NOTHING FOR A POSITIVE VALUE THAT HAS INTEGER DIGITS.
                ; The fixed-point path writes no sign either, and pu_sign_tenant
                ; PREPENDS its `+` rather than overwriting a blank -- a space here
                ; made `+##.##^^^^` overflow its own field, and stopped `**`
                ; filling. The `0` of `0.1E+04` is a different thing: with no
                ; integer digit it IS the column (rows e.big / e.negtight).
                ld      de,PU_NUM
                ld      a,(hl)
                cp      '-'
                jr      nz,pnt_x_pos
                ld      a,'-'
                jr      pnt_x_put
pnt_x_pos:
                ld      a,c
                or      a
                jr      nz,pnt_x_sgnd
                ld      a,'0'
pnt_x_put:
                ld      (de),a
                inc     de
pnt_x_sgnd:
                inc     hl                  ; past flt_fmt's own sign column
                push    de
                pop     ix                  ; IX = the first mantissa digit, and
                                            ; the floor the carry walk stops at
                push    bc                  ; n, places
                ; --- the significant digits -> PU_DIG, B = P ------------------
                ; The value is 0.<digits> x 10^P.
                ld      de,PU_DIG
                ld      b,0
pnt_x_ip:
                ld      a,(hl)
                cp      '0'
                jr      c,pnt_x_ipd
                cp      '9' + 1
                jr      nc,pnt_x_ipd
                ld      (de),a
                inc     de
                inc     hl
                inc     b                   ; P counts the INTEGER digits
                jr      pnt_x_ip
pnt_x_ipd:
                ld      a,(hl)
                cp      '.'
                jr      nz,pnt_x_ex
                inc     hl
pnt_x_fp:
                ld      a,(hl)
                cp      '0'
                jr      c,pnt_x_ex
                cp      '9' + 1
                jr      nc,pnt_x_ex
                ld      (de),a
                inc     de
                inc     hl
                jr      pnt_x_fp
pnt_x_ex:
                xor     a
                ld      (de),a              ; terminate PU_DIG -- "exhausted" is
                                            ; then a byte test, not a compare
                ld      a,(hl)
                cp      'E'
                jr      nz,pnt_x_strip
                inc     hl
                ld      a,(hl)
                cp      '-'
                jr      nz,pnt_x_eplus
                inc     hl
                call    pnt_x_e2
                ld      c,a
                ld      a,b
                sub     c
                ld      b,a
                jr      pnt_x_strip
pnt_x_eplus:
                cp      '+'
                jr      nz,pnt_x_e2go
                inc     hl
pnt_x_e2go:
                call    pnt_x_e2
                add     a,b
                ld      b,a
pnt_x_strip:
                ; leading zeros are not significant; each one lowers P
                ld      hl,PU_DIG
pnt_x_sl:
                ld      a,(hl)
                cp      '0'
                jr      nz,pnt_x_have
                inc     hl
                dec     b
                jr      pnt_x_sl
pnt_x_have:
                ld      a,b
                ld      (PU_COMMAS),a       ; P -- PU_COMMAS is free here, and
                                            ; measurably so: `e.comma` shows the
                                            ; exponent form never groups
                pop     bc                  ; C = n, B = places
                ld      a,(hl)
                or      a
                jr      nz,pnt_x_pnz
                ld      a,c                 ; a ZERO value: force the exponent to
                ld      (PU_COMMAS),a       ; 0 by taking P as n (row e.zero)
pnt_x_pnz:
                ld      a,(PU_COMMAS)
                sub     c
                ld      (PU_COMMAS),a       ; the displayed exponent = P - n
                ld      a,b
                add     a,c
                ld      b,a                 ; B = wanted significant digits
                ; --- copy that many digits, padding when the source runs out ---
                push    ix
                pop     de                  ; DE = where the mantissa begins
                or      a
                jr      z,pnt_x_round
pnt_x_cl:
                ld      a,(hl)
                or      a
                jr      z,pnt_x_cpad
                inc     hl                  ; a real digit: advance the source so
                jr      pnt_x_cput          ; the rounding digit below is right
pnt_x_cpad:
                ld      a,'0'
pnt_x_cput:
                ld      (de),a
                inc     de
                djnz    pnt_x_cl
pnt_x_round:
                ld      a,(hl)              ; first digit past the cut (0 when the
                cp      '5'                 ; source was exhausted -> no rounding)
                jr      c,pnt_x_pt
                push    ix
                pop     hl                  ; HL = the carry floor
                push    de
pnt_x_cw:
                dec     de
                ld      a,(de)
                cp      '9'
                jr      z,pnt_x_c9
                inc     a
                ld      (de),a
                pop     de
                jr      pnt_x_pt
pnt_x_c9:
                ld      a,'0'
                ld      (de),a
                ld      a,d
                cp      h
                jr      nz,pnt_x_cw
                ld      a,e
                cp      l
                jr      nz,pnt_x_cw
                ld      (hl),'1'            ; 999 -> 100: one more integer digit,
                ld      a,(PU_COMMAS)       ; which the EXPONENT absorbs rather
                inc     a                   ; than the field (row e.round)
                ld      (PU_COMMAS),a
                pop     de
pnt_x_pt:
                ; --- the point, if the format carries one ----------------------
                ld      a,(PU_FLAGS)
                bit     6,a
                jr      z,pnt_x_e
                ld      a,(PU_DEC)
                and     $7F
                ld      b,a                 ; the fraction moves right by one
                push    de
                ld      h,d
                ld      l,e
                inc     hl
                ld      a,b
                or      a
                jr      z,pnt_x_dot
pnt_x_sh:
                dec     de
                dec     hl
                ld      a,(de)
                ld      (hl),a
                djnz    pnt_x_sh
pnt_x_dot:
                dec     hl
                ld      (hl),'.'
                pop     de
                inc     de
pnt_x_e:
                ; --- `E`, the sign, and two exponent digits --------------------
                ld      a,'E'
                ld      (de),a
                inc     de
                ld      a,(PU_COMMAS)
                ld      c,a
                or      a
                jp      p,pnt_x_epl
                ld      a,'-'
                ld      (de),a
                inc     de
                xor     a
                sub     c
                ld      c,a                 ; C = the magnitude
                jr      pnt_x_ed
pnt_x_epl:
                ld      a,'+'
                ld      (de),a
                inc     de
pnt_x_ed:
                ld      b,'0' - 1
pnt_x_tens:
                inc     b
                ld      a,c
                sub     10
                ld      c,a
                jr      nc,pnt_x_tens
                ld      a,c
                add     a,10
                add     a,'0'
                ld      c,a
                ld      a,b
                ld      (de),a              ; tens
                inc     de
                ld      a,c
                ld      (de),a              ; units
                inc     de
                xor     a
                ld      (de),a
                ld      hl,PU_NUM
                ld      a,e
                sub     l
                ret

; pnt_x_e2 -- the two exponent digits at HL as a binary value in A; HL advances.
; Clobbers C, which the caller has already spilled.
pnt_x_e2:
                ld      a,(hl)
                sub     '0'
                ld      c,a
                add     a,a
                add     a,a
                add     a,c
                add     a,a                 ; A = 10 * the first digit
                inc     hl
                ld      c,a
                ld      a,(hl)
                sub     '0'
                add     a,c
                inc     hl
                ret
