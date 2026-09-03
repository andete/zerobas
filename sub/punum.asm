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

; --- pu_num_tenant: the live numeric value -> NUMBUF as PRINT USING wants it -
;   in   FAC / FACTYP hold the evaluated argument (the caller routes FACTYP==2
;        to its own integer path, which is already correct and cheaper)
;   out  NUMBUF = "[-]digits",0 rounded half-up to a whole number
;        A = its length. Clobbers AF, BC, DE, HL.
;
; `flt_fmt` leaves FOUTBUF as: a sign column (`-` or a SPACE), the digits, then
; ONE trailing space. We keep a `-`, drop the space column, copy digits until the
; run ends, and round on the first fraction digit.
; --- pu_num_tenant: the live numeric value -> NUMBUF, to PU_DEC places -------
;   in   FAC / FACTYP hold the evaluated argument
;        PU_FLAGS bit6 = a `.` was scanned; PU_DEC = how many places
;   out  NUMBUF = "[-]digits[.digits]",0 ; A = its length. Clobbers AF, BC, DE, HL.
;
; 🎯 THE DIGITS ARE BUILT CONTIGUOUSLY AND THE POINT IS INSERTED LAST, so rounding
; at N places is ONE carry walk over ONE array -- there is no decimal point in the
; middle for the carry to cross. C carries the INTEGER-digit count throughout, and
; the carry growing the number (9.5 -> 10.) simply increments it.
;
; ⚠️ DIGSTART IS RECOMPUTED, NOT STACKED. The first attempt at this (D-PUDOT,
; reverted) juggled it through push/pop across three branches and crashed. It is
; NUMBUF, or NUMBUF+1 when a `-` leads -- cheaper to derive than to keep, and it
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
                call    flt_fmt             ; HL -> FOUTBUF
                ld      de,NUMBUF
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
                jr      c,pnt_point         ; below half -> plain truncation
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
                jr      pnt_point
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
pnt_point:
                ld      a,(PU_FLAGS)
                bit     6,a
                jr      z,pnt_term          ; no `.` in the format at all
                ; fraction length = end - DIGSTART - C. NUMBUF is 8 bytes and the
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
                ld      hl,NUMBUF
                ld      a,e
                sub     l
                ret

; pnt_digstart -- HL = NUMBUF's first DIGIT, stepping past a leading `-`.
; Clobbers AF and HL only, which is why it can be called from inside the carry
; walk without disturbing DE, BC or the count in C.
pnt_digstart:
                ld      hl,NUMBUF
                ld      a,(hl)
                cp      '-'
                ret     nz
                inc     hl
                ret
