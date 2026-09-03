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
                push    de                  ; remember where the DIGITS start --
                                            ; the carry walk must not run into the
                                            ; minus sign
pnt_copy:
                ld      a,(hl)
                cp      '.'
                jr      z,pnt_frac
                cp      '0'
                jr      c,pnt_end           ; not a digit (space, 0, or `E`) -> done
                cp      '9' + 1
                jr      nc,pnt_end
                ld      (de),a
                inc     de
                inc     hl
                jr      pnt_copy
pnt_frac:
                ; round half-up on the FIRST fraction digit, then drop the rest
                inc     hl
                ld      a,(hl)
                cp      '5'
                jr      c,pnt_end           ; below half -> plain truncation
                ; --- carry the increment back through the digits ---------------
                pop     bc                  ; BC = first digit position
                push    bc
pnt_carry:
                dec     de
                ld      a,(de)
                cp      '9'
                jr      z,pnt_nine
                inc     a
                ld      (de),a
                jr      pnt_carry_done
pnt_nine:
                ld      a,'0'
                ld      (de),a              ; 9 -> 0 and keep carrying
                ld      a,d
                cp      b
                jr      nz,pnt_carry
                ld      a,e
                cp      c
                jr      nz,pnt_carry
                ; ran off the front: every digit was a 9, so the number grows by
                ; one place (9.5 -> 10). Shift right and write the leading 1.
                call    pnt_grow
pnt_carry_done:
                pop     de                  ; DE = first digit position
                call    pnt_end_of           ; DE -> the terminator position
                jr      pnt_term
pnt_end:
                pop     bc                  ; discard the remembered start
pnt_term:
                xor     a
                ld      (de),a              ; 0-terminate
                ; A = length
                ld      hl,NUMBUF
                ld      a,e
                sub     l
                ret

; pnt_end_of -- DE points at the first digit; advance it past the digit run.
pnt_end_of:
                ld      a,(de)
                cp      '0'
                ret     c
                cp      '9' + 1
                ret     nc
                inc     de
                jr      pnt_end_of

; pnt_grow -- every digit carried, so the run gains a place. BC = the first digit
; position; DE is at it. Shift the run one right and write '1' at the front.
; The run is all '0' by now, so "shifting" is just writing one more '0' at the
; end and putting the '1' in front -- no block move is needed.
pnt_grow:
                push    de
                call    pnt_end_of
                ld      a,'0'
                ld      (de),a              ; extend the run by one place
                inc     de
                pop     de
                ld      a,'1'
                ld      (de),a
                ret
