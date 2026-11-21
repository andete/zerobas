; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XDSK5 -- the disk region's BIOS call PHYDIO ($0144) round 5 (2026-11-22): XDSK1's frame and record, XDSK4's
; buffer-apart-from-HL, new cases (54-67) answering review pass 3 (scratchpad/PHYDIO_review3.md): three DIFFERENT
; contents written first -- sector 9 from $A400 (P0, +0 $77), 8 from $A500 (P1, +0 $F7), 18 from $A480 (P2, +0 $B7) --
; so every later read names the image sector it reached: a write takes its data from HL (57); $F8 / $FA reach image 18
; (58, 59); $FA is 1 x 8, not 1 x 9 (60); 2-sector reads across a side and a track change (61-63); a write with 2
; sectors past the end (64); track 128 (65: modulo 256 or 128); a good write entered with EI, read back (66, 67);
; track 210 (68, added in run 2: modulo 128 says past, a signed 8-bit compare says on the disk).
; XDSK1's header follows.
;
; XDSK1 -- the disk region's BIOS call PHYDIO ($0144) round 1 (2026-11-19). A 16 KB "AB" cartridge whose INIT only
; hooks H.STKE (an RST 30h inter-slot call into this cartridge): a disk interface may sit in a later slot and be
; initialised after us, and H.STKE runs once every ROM has been. Then, on both rows (the NODISK row's H.PHYD is a
; bare RET), each case: the buffer's 1 KB filled with $E5 (or, for a write, a pattern), A (drive), F (bit 0 = the
; carry: write), B (sectors), C (media byte), DE (first sector), HL (address) and the interrupt state as the case
; table lists them, CALL PHYDIO, then a 14-byte record: A, F, B, C, D, E, H, L, the interrupt state after (1 on, read
; twice), the 16-bit sum of the buffer's 1 KB (low, high), the buffer's bytes +0 and +512, and a $00 pad.
; Cases:
;   54: write sector 9 from $A400 (P0): A 0, F $01, B 1, C $F9, DE 9, HL $A400, di, fill PAT
;   55: write sector 8 from $A500 (P1): A 0, F $01, B 1, C $F9, DE 8, HL $A500, di, fill PAT
;   56: write sector 18 from $A480 (P2): A 0, F $01, B 1, C $F9, DE 18, HL $A480, di, fill PAT
;   57: read sector 8 with $F9 (case 55's write): A 0, F $00, B 1, C $F9, DE 8, HL $A400, di, fill E5
;   58: read sector 9 with $F8: A 0, F $00, B 1, C $F8, DE 9, HL $A400, di, fill E5
;   59: read sector 8 with $FA: A 0, F $00, B 1, C $FA, DE 8, HL $A400, di, fill E5
;   60: read sector 9 with $FA: A 0, F $00, B 1, C $FA, DE 9, HL $A400, di, fill E5
;   61: read 2 from 8 with $F9 (side 0 to 1): A 0, F $00, B 2, C $F9, DE 8, HL $A400, di, fill E5
;   62: read 2 from 17 with $F9 (track 0 to 1): A 0, F $00, B 2, C $F9, DE 17, HL $A400, di, fill E5
;   63: read 2 from 7 with $FF (side 0 to 1): A 0, F $00, B 2, C $FF, DE 7, HL $A400, di, fill E5
;   64: write 3 from 1439 (1 in, 2 beyond): A 0, F $01, B 3, C $F9, DE 1439, HL $A400, di, fill PAT
;   65: read sector $0900 with $F9 (track 128): A 0, F $00, B 1, C $F9, DE 2304, HL $A400, di, fill E5
;   66: write sector 1430, ei: A 0, F $01, B 1, C $F9, DE 1430, HL $A400, ei, fill PAT
;   67: read sector 1430 after case 66: A 0, F $00, B 1, C $F9, DE 1430, HL $A400, di, fill E5
;   68: read sector 3780 with $F9 (track 210): A 0, F $00, B 1, C $F9, DE 3780, HL $A400, di, fill E5
; Drive A is a fresh copy of the generated empty 720 KB disk (@disk), the same image on both machines; sector 1439
; lies outside every file. The disk machine of ours asks the date before BASIC starts (a CR at 20 s, @type-at).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdsk5.asm --row both
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
                ; case 54: write sector 9 from $A400 (P0)
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
                ; case 55: write sector 8 from $A500 (P1)
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
                ; case 56: write sector 18 from $A480 (P2)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $0012
                ld      hl, $A480
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 57: read sector 8 with $F9 (case 55's write)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0008
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 58: read sector 9 with $F8
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
                ; case 59: read sector 8 with $FA
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
                ; case 60: read sector 9 with $FA
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01FA
                ld      de, $0009
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 61: read 2 from 8 with $F9 (side 0 to 1)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02F9
                ld      de, $0008
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 62: read 2 from 17 with $F9 (track 0 to 1)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02F9
                ld      de, $0011
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 63: read 2 from 7 with $FF (side 0 to 1)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02FF
                ld      de, $0007
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 64: write 3 from 1439 (1 in, 2 beyond)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $03F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 65: read sector $0900 with $F9 (track 128)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0900
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 66: write sector 1430, ei
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $0596
                ld      hl, $A400
                pop     af
                ei
                call    PHYDIO
                call    rec
                ; case 67: read sector 1430 after case 66
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0596
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ; case 68: read sector 3780 with $F9 (track 210)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0EC4
                ld      hl, $A400
                pop     af
                di
                call    PHYDIO
                call    rec
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; fill_e5 / fill_pat -- the 1 KB at (buf): $E5, or the pattern $77 + n, -n (pairs: B counts down from 0)
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
