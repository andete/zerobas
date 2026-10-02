; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; sdatex.asm -- SDATE 1999-12-31, then back to the DOS prompt (D-DOSDATEBASIC).
BDOS    equ     $0005
        org     $0100
        ld      hl, 1999
        ld      d, 12
        ld      e, 31
        ld      c, $2B
        call    BDOS
        ld      c, $00
        call    BDOS
        ret
