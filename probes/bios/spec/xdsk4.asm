; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XDSK4 -- the disk region's BIOS call PHYDIO ($0144) round 4 (2026-11-22): XDSK1's frame and record, new cases
; (38-53) answering review pass 2: which IMAGE sector a read with $F8 / $FF / $FA reaches (sector 9 written from $A400,
; sector 8 from $A500 -- two different 512-byte contents -- sector 18 left zero); the order of a 2-sector read (sector
; 1, the FAT, second: +512 $F9); a WRITE with a refused media byte (and a read back); a refusal with B 2 / B 0; the
; $F8 bound (719); the rule pair "the media byte sets the size" against "the end is track 80, the track number 8 bits"
; ($FF sector 700; $F9 sector $1200 = 4608 = track 256); the error paths with HL $8000. A case's buffer may differ
; from its HL (case 39: the buffer at $A400 holds the pattern, HL $A500 writes its second half). The record's sum is
; the BUFFER's. XDSK1's header follows.
;
; XDSK1 -- the disk region's BIOS call PHYDIO ($0144) round 1 (2026-11-19). A 16 KB "AB" cartridge whose INIT only
; hooks H.STKE (an RST 30h inter-slot call into this cartridge): a disk interface may sit in a later slot and be
; initialised after us, and H.STKE runs once every ROM has been. Then, on both rows (the NODISK row's H.PHYD is a
; bare RET), each case: the buffer's 1 KB filled with $E5 (or, for a write, a pattern), A (drive), F (bit 0 = the
; carry: write), B (sectors), C (media byte), DE (first sector), HL (address) and the interrupt state as the case
; table lists them, CALL PHYDIO, then a 14-byte record: A, F, B, C, D, E, H, L, the interrupt state after (1 on, read
; twice), the 16-bit sum of the buffer's 1 KB (low, high), the buffer's bytes +0 and +512, and a $00 pad.
; Cases:
;   38: write sector 9 from $A400 (PAT): A 0, F $01, B 1, C $F9, DE 9, HL $A400, di, fill PAT
;   39: write sector 8 from $A500 (PAT's second half): A 0, F $01, B 1, C $F9, DE 8, HL $A500, di, fill PAT
;   40: read sector 9 with $F8: A 0, F $00, B 1, C $F8, DE 9, HL $A400, di, fill E5
;   41: read sector 8 with $FF: A 0, F $00, B 1, C $FF, DE 8, HL $A400, di, fill E5
;   42: read sector 8 with $FA: A 0, F $00, B 1, C $FA, DE 8, HL $A400, di, fill E5
;   43: read 2 from 0 (the FAT second): A 0, F $00, B 2, C $F9, DE 0, HL $A400, di, fill E5
;   44: write sector 1437 with C $00: A 0, F $01, B 1, C $00, DE 1437, HL $A400, di, fill PAT
;   45: read sector 1437 after case 44: A 0, F $00, B 1, C $F9, DE 1437, HL $A400, di, fill E5
;   46: media refused, B 2: A 0, F $00, B 2, C $00, DE 0, HL $A400, di, fill E5
;   47: media refused, B 0: A 0, F $00, B 0, C $00, DE 0, HL $A400, di, fill E5
;   48: read sector 719 with $F8: A 0, F $00, B 1, C $F8, DE 719, HL $A400, di, fill E5
;   49: read sector 700 with $FF: A 0, F $00, B 1, C $FF, DE 700, HL $A400, di, fill E5
;   50: read sector $1200 with $F9: A 0, F $00, B 1, C $F9, DE 4608, HL $A400, di, fill E5
;   51: read beyond, HL $8000: A 0, F $00, B 1, C $F9, DE 1440, HL $8000, di, fill E5
;   52: media refused, HL $8000: A 0, F $00, B 1, C $00, DE 0, HL $8000, di, fill E5
;   53: write beyond, HL $8000: A 0, F $01, B 1, C $F9, DE 1440, HL $8000, di, fill PAT
; Drive A is a fresh copy of the generated empty 720 KB disk (@disk), the same image on both machines; sector 1439
; lies outside every file. The disk machine of ours asks the date before BASIC starts (a CR at 20 s, @type-at).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdsk4.asm --row both
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @timeout 60

PHYDIO  equ     $0144
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000           ; @cap A000: below HIMEM -- the disk ROM's work area is live once H.STKE runs
CAP     equ     $A001
ptr     equ     $A200
rsave   equ     $A210
buf     equ     $A212

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h call in H.STKE
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      hl, CAP
                ld      (ptr), hl
                ; case 38: write sector 9 from $A400 (PAT)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $0009
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 39: write sector 8 from $A500 (PAT's second half)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $0008
                ld      hl, $A500
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 40: read sector 9 with $F8
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F8
                ld      de, $0009
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 41: read sector 8 with $FF
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01FF
                ld      de, $0008
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 42: read sector 8 with $FA
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01FA
                ld      de, $0008
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 43: read 2 from 0 (the FAT second)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02F9
                ld      de, $0000
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 44: write sector 1437 with C $00
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $0100
                ld      de, $059D
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 45: read sector 1437 after case 44
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $059D
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 46: media refused, B 2
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $0200
                ld      de, $0000
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 47: media refused, B 0
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $0000
                ld      de, $0000
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 48: read sector 719 with $F8
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F8
                ld      de, $02CF
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 49: read sector 700 with $FF
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01FF
                ld      de, $02BC
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 50: read sector $1200 with $F9
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $1200
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 51: read beyond, HL $8000
                ld      hl, $8000
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $05A0
                ld      hl, $8000
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 52: media refused, HL $8000
                ld      hl, $8000
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $0100
                ld      de, $0000
                ld      hl, $8000
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 53: write beyond, HL $8000
                ld      hl, $8000
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $05A0
                ld      hl, $8000
                pop     af
                di
                call    PHYDIO
                call    rec
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; fill_e5 / fill_pat -- the 1 KB at (buf): $E5, or the pattern $77 + n, n (pairs)
fill_e5:
                ld      hl, (buf)
                ld      bc, $0400
fe:
                ld      (hl), $E5
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, fe
                ret
fill_pat:
                ld      hl, (buf)
                ld      b, 0
                ld      a, $77
fp:
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                inc     a
                djnz    fp
                ld      b, 0
fp2:
                ld      (hl), $E5
                inc     hl
                ld      (hl), $E5
                inc     hl
                djnz    fp2
                ret

; rec -- the 14-byte record
rec:
                ld      (rsave), hl
                push    af
                push    af
                ld      hl, (ptr)
                pop     af
                ld      (hl), a
                inc     hl
                push    hl
                push    af
                pop     hl
                ld      a, l
                pop     hl
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                ld      a, (rsave+1)
                ld      (hl), a
                inc     hl
                ld      a, (rsave)
                ld      (hl), a
                inc     hl
                ld      a, i                    ; P/V := IFF2, read twice
                jp      pe, ion
                ld      a, i
ion:
                ld      a, 0
                jp      po, ioff
                ld      a, 1
ioff:
                ld      (hl), a
                inc     hl
                di
                ld      (ptr), hl
                ld      hl, (buf)               ; the 1 KB sum
                ld      de, 0
                ld      bc, $0400
sm:
                ld      a, (hl)
                add     a, e
                ld      e, a
                jr      nc, sm1
                inc     d
sm1:
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, sm
                ld      hl, (ptr)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                push    hl
                ld      hl, (buf)
                ld      a, (hl)
                ld      de, 512
                add     hl, de
                ld      e, (hl)
                pop     hl
                ld      (hl), a
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (hl), 0
                inc     hl
                ld      (ptr), hl
                pop     af
                ld      hl, (rsave)
                ret
