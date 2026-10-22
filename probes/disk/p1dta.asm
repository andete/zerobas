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
        ; --- SEQRD ($14) into $4100: the same record, sequentially ----------------
        ld      de, $4100
        ld      c, $1A
        call    BDOS
        ld      de, fcb3            ; a FRESH FCB: the first one's position has moved
        ld      c, $0F              ; OPEN
        call    BDOS
        xor     a
        ld      (fcb3 + 32), a      ; current record 0
        ld      de, fcb3
        ld      c, $14              ; SEQRD
        call    BDOS
        ld      ($C002), a
        ; --- SFIRST ($11) into $4200: the directory entry -------------------------
        ; $55 in both DTAs first: does SFIRST WRITE every byte of its 33?
        ld      hl, $4200
        ld      (hl), $55
        ld      de, $4201
        ld      bc, 40
        ldir
        ld      hl, $C100
        ld      (hl), $55
        ld      de, $C101
        ld      bc, 40
        ldir
        ld      de, $4200
        ld      c, $1A
        call    BDOS
        ld      de, fcb2
        ld      c, $11              ; SFIRST
        call    BDOS
        ld      ($C003), a
        ; --- and SFIRST into $C100 (page 3), the layout without page 1 in it --------
        ld      de, $C100
        ld      c, $1A
        call    BDOS
        ld      de, fcb4
        ld      c, $11
        call    BDOS
        ld      c, $00              ; back to DOS
        call    BDOS
        ret
fcb:    db      0, "P1DATA  BIN"
        ds      25, 0
fcb2:   db      0, "P1DATA  BIN"
        ds      25, 0
fcb3:   db      0, "P1DATA  BIN"
        ds      25, 0
fcb4:   db      0, "P1DATA  BIN"
        ds      25, 0
