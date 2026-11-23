; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XEXTROM0 -- D-MSX2SPEC, docs/msx2/main/EXTROM.md case EX-11: EXTROM ($015F) with EXBRSA ($FAF8) := $00, the
; "no sub-ROM" value, and IX = RSLREG ($0138), the main ROM's published "read port $A8" entry -- so if EXTROM makes an
; inter-slot call to slot 0 anyway, A comes back as port $A8 DURING the call (page 0's bits = 00), and the main ROM's
; own RSLREG cannot do harm. Entry A $A7, F $00, BC $B1C2, DE $4E5F, HL $9876, IY $1A2B, DI.
; The capture (CAP = C001): +0 $01 when the call returned, +1 port $A8 before, +2 ($FFFF) cpl before, +3 A after,
; +4 F after, +5/6 BC, +7/8 DE, +9/10 HL, +11/12 IX, +13/14 IY, +15 port $A8 after, +16 ($FFFF) cpl after,
; +17 I/IFF F read twice (bit 2 each: +17 first, +18 second), +19 EXBRSA after, +20 $5A.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xextrom0.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells. No ROM byte read.
;
; @cap C000
; @caplen 0040
; @timeout 60

EXTROM  equ     $015F
EXBRSA  equ     $FAF8
DONE    equ     $C000
CAP     equ     $C001
SVSP    equ     $E900
SVEX    equ     $E902

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $003E
                ld      (hl), 0
                ldir
                ld      a, (EXBRSA)
                ld      (SVEX), a
                in      a, ($A8)
                ld      (CAP+1), a
                ld      a, ($FFFF)
                cpl
                ld      (CAP+2), a
                xor     a
                ld      (EXBRSA), a
                ld      iy, $1A2B
                ld      ix, $0138
                ld      bc, $B1C2
                ld      de, $4E5F
                ld      hl, $A700
                push    hl
                pop     af
                ld      hl, $9876
                call    EXTROM
                ld      (SVSP), sp
                ld      sp, CAP+15
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      sp, (SVSP)
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (CAP+17), a
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (CAP+18), a
                di
                ; AF was pushed F then A: CAP+3 = F, CAP+4 = A -- swap to the documented A, F
                ld      a, (CAP+3)
                ld      b, a
                ld      a, (CAP+4)
                ld      (CAP+3), a
                ld      a, b
                ld      (CAP+4), a
                in      a, ($A8)
                ld      (CAP+15), a
                ld      a, ($FFFF)
                cpl
                ld      (CAP+16), a
                ld      a, (EXBRSA)
                ld      (CAP+19), a
                ld      a, (SVEX)
                ld      (EXBRSA), a
                ld      a, 1
                ld      (CAP), a
                ld      a, $5A
                ld      (CAP+20), a
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

                ds      $8000 - $, $FF
