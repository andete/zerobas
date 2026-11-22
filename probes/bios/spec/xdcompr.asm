; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XDCOMPR -- docs/bios/DCOMPR.md round 1 (2026-11-18): DCOMPR ($0020, RST 20h) over a matrix. H, D, L and E each take
; one of seven values {00, 01, 5A, 7F, 80, FE, FF} -- 7^4 = 2401 cases, every combination -- so "A = H - D when the high
; bytes differ, L - E otherwise" separates from other forms, and unsigned from signed carry. Entry A = $A7 and F = $00;
; BC = $1357, IX = $4321, IY = $8765 on entry, and BC / IX / IY / HL / DE compared after (the record's third byte is 1
; if any of them moved, else 0). Then 4 extra cases with entry F $FF.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdcompr.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case 3 bytes from CAP+1: A after, F after, a "kept" byte (0 = BC / DE /
; HL / IX / IY all kept, else 1); the 2401 matrix cases in order h (outer), d, l, e (inner) over the value list; then
; the 4 entry-F-$FF cases (HL / DE = 1234 / 1234, 1234 / 1235, 1235 / 1234, 0000 / FFFF); then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry only.
;
; @cap C000
; @caplen 1C80
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
ih      equ     $EF02
id      equ     $EF03
il      equ     $EF04
ie      equ     $EF05
ef      equ     $EF06                   ; entry F
vh      equ     $EF08                   ; the values in this case
vd      equ     $EF09
vl      equ     $EF0A
ve      equ     $EF0B

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1C7F
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (ef), a
                ld      (ih), a
lp_h:
                xor     a
                ld      (id), a
lp_d:
                xor     a
                ld      (il), a
lp_l:
                xor     a
                ld      (ie), a
lp_e:
                ld      a, (ih)
                call    val
                ld      (vh), a
                ld      a, (id)
                call    val
                ld      (vd), a
                ld      a, (il)
                call    val
                ld      (vl), a
                ld      a, (ie)
                call    val
                ld      (ve), a
                call    one
                ld      hl, ie
                inc     (hl)
                ld      a, (hl)
                cp      7
                jr      c, lp_e
                ld      hl, il
                inc     (hl)
                ld      a, (hl)
                cp      7
                jr      c, lp_l
                ld      hl, id
                inc     (hl)
                ld      a, (hl)
                cp      7
                jr      c, lp_d
                ld      hl, ih
                inc     (hl)
                ld      a, (hl)
                cp      7
                jr      c, lp_h
                ; the entry-F-$FF cases
                ld      a, $FF
                ld      (ef), a
                ld      hl, extra
x_lp:
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, vh
                ld      bc, 4
                ldir
                push    hl
                call    one
                pop     hl
                jr      x_lp

; one -- call DCOMPR with HL = vh:vl, DE = vd:ve, A = $A7, F = (ef), BC / IX / IY markers; record A, F, kept
one:
                ld      a, (ef)
                ld      c, a
                ld      b, $A7
                push    bc
                ld      a, (vh)
                ld      h, a
                ld      a, (vl)
                ld      l, a
                ld      a, (vd)
                ld      d, a
                ld      a, (ve)
                ld      e, a
                ld      bc, $1357
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                rst     $20
                push    af
                ; kept? BC, IX, IY, HL, DE
                ld      a, b
                xor     $13
                jr      nz, o_moved
                ld      a, c
                xor     $57
                jr      nz, o_moved
                push    ix
                pop     bc
                ld      a, b
                xor     $43
                jr      nz, o_moved
                ld      a, c
                xor     $21
                jr      nz, o_moved
                push    iy
                pop     bc
                ld      a, b
                xor     $87
                jr      nz, o_moved
                ld      a, c
                xor     $65
                jr      nz, o_moved
                ld      a, (vh)
                cp      h
                jr      nz, o_moved
                ld      a, (vl)
                cp      l
                jr      nz, o_moved
                ld      a, (vd)
                cp      d
                jr      nz, o_moved
                ld      a, (ve)
                cp      e
                jr      nz, o_moved
                ld      c, 0
                jr      o_rec
o_moved:
                ld      c, 1
o_rec:
                pop     hl                      ; H = A after, L = F after
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                ld      a, c
                jp      emit

val:
                push    hl
                ld      hl, vals
                add     a, l
                ld      l, a
                jr      nc, v_nc
                inc     h
v_nc:
                ld      a, (hl)
                pop     hl
                ret

vals:
                db      $00, $01, $5A, $7F, $80, $FE, $FF

extra:
                db      $12, $12, $34, $34      ; h, d, l, e: 1234 / 1234
                db      $12, $12, $34, $35      ; 1234 / 1235
                db      $12, $12, $35, $34      ; 1235 / 1234
                db      $00, $FF, $00, $FF      ; 0000 / FFFF
                db      $EE

finish:
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
