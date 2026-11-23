; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; The body of XSUBPAD / XSUBPADM / XSUBPADX (D-MSX2SPEC, docs/msx2/sub/NEWPAD.md); the including file sets SEQ (which
; call list) and the @-directives. Per call (the list `seq_*`: the function number, the path 0 = the sub-ROM's NEWPAD
; $01AD through EXTROM, 1 = the main ROM's GTPAD $00DB): interrupts off, PSG R15 := $8F through the ports, BC $1357,
; DE $2468, HL $369C, A := the function, the call; then A, F, the interrupt state (read twice), R15 through the ports,
; BC / DE / HL. The calls follow each other at once (no wait), in the list's order.
; The capture (CAP = C001): +0 $A5 when finished, +1 the call count; per call a 16-byte record from +2: +0 the
; function, +1 the path, +2 A, +3 F, +4 / +5 IFF (P/V of LD A,I, read twice), +6 R15 after, +7 C, +8 B, +9 E, +10 D,
; +11 L, +12 H, +13 $EE (sentinel), +14 / +15 0.

EXTROM  equ     $015F
GTPAD   equ     $00DB
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
fn      equ     $E909
path    equ     $E90A
sv_af   equ     $E910
sv_bc   equ     $E912
sv_de   equ     $E914
sv_hl   equ     $E916
sv_if   equ     $E918

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, seqtab
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      (fn), a
                inc     hl
                ld      a, (hl)
                ld      (path), a
                inc     hl
                ld      (tp), hl
                ld      a, 15
                out     ($A0), a
                ld      a, $8F
                out     ($A1), a
                ld      bc, $1357
                ld      de, $2468
                ld      hl, $369C
                ld      a, (path)
                or      a
                ld      a, (fn)
                jr      nz, c_main
                ld      ix, $01AD
                call    EXTROM
                jr      c_after
c_main:
                call    GTPAD
c_after:
                push    af
                ld      (sv_bc), bc
                ld      (sv_de), de
                ld      (sv_hl), hl
                pop     hl
                ld      (sv_af), hl
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if), a
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if+1), a
                ld      hl, (ptr)
                ld      a, (fn)
                ld      (hl), a
                inc     hl
                ld      a, (path)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af+1)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af)
                ld      (hl), a
                inc     hl
                ld      a, (sv_if)
                rrca
                rrca
                and     1
                ld      (hl), a
                inc     hl
                ld      a, (sv_if+1)
                rrca
                rrca
                and     1
                ld      (hl), a
                inc     hl
                ld      a, 15
                out     ($A0), a
                in      a, ($A2)
                ld      (hl), a
                inc     hl
                ex      de, hl
                ld      hl, sv_bc
                ld      bc, 6
                ldir
                ex      de, hl
                ld      (hl), $EE
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

seqtab:
        IF SEQ = 0
                ; 8-23 in order; 13 / 14 / 17 / 18 again without a fetch; 12, 14, 13; 16, 18, 17
                db      8, 0, 9, 0, 10, 0, 11, 0, 12, 0, 13, 0, 14, 0, 15, 0
                db      16, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0, 23, 0
                db      13, 0, 14, 0, 17, 0, 18, 0
                db      12, 0, 14, 0, 13, 0, 16, 0, 18, 0, 17, 0
                ; the same through GTPAD
                db      8, 1, 9, 1, 10, 1, 11, 1, 12, 1, 13, 1, 14, 1, 15, 1
                db      16, 1, 17, 1, 18, 1, 19, 1
        ENDIF
        IF SEQ = 2
                ; which port's reading do the reads return: port 1 empty (reads $01), port 2 a mouse (reads 0)
                db      12, 0, 13, 0, 14, 0, 16, 0, 13, 0, 14, 0, 17, 0, 18, 0
                db      12, 0, 17, 0, 18, 0, 9, 0, 10, 0, 20, 0, 0, 0, 16, 0, 9, 0, 21, 0, 22, 0
        ENDIF
        IF SEQ = 1
                ; out of range: 0-7 through the sub-ROM, then 24, 31, $80, $FF
                db      0, 0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0
                db      24, 0, 31, 0, $80, 0, $FF, 0
        ENDIF
                db      $EE

                ds      $8000 - $, $FF
