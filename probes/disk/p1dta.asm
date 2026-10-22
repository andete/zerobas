; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; p1dta.asm -- D-P1DOS: an MSX-DOS program reads one 128-byte record of its own
; data file into a DTA in PAGE 1 ($4000) with BDOS $27 RDBLK, then leaves the
; status at $C000 and returns to DOS. The probe compares $4000.. and $C000 on the
; CF-3300 and on zerobas: the record must land in the RAM there.
; Our own code and our own data file (P1DATA.BIN, written by the probe).
BDOS    equ     $0005
        org     $0100
        ld      de, fcb
        ld      c, $0F              ; OPEN
        call    BDOS
        ld      ($C001), a          ; OPEN's answer
        ld      de, $4000
        ld      c, $1A              ; SETDTA -> page 1
        call    BDOS
        ld      hl, 128
        ld      (fcb + 14), hl      ; record size 128
        ld      hl, 0
        ld      (fcb + 33), hl      ; random record 0
        ld      (fcb + 35), hl
        ld      hl, 1               ; one record
        ld      de, fcb
        ld      c, $27              ; RDBLK
        call    BDOS
        ld      ($C000), a          ; RDBLK's answer
        ld      c, $00              ; back to DOS
        call    BDOS
        ret
fcb:    db      0, "P1DATA  BIN"
        ds      25, 0
