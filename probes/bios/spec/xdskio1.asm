; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XDSKIO1 -- the disk ROM's DSKIO ($4010) called DIRECTLY, round 1 (2026-11-22): XDSK1's eleven PHYDIO cases
; (probes/bios/spec/xdsk1.asm, docs/bios/PHYDIO.md) with `CALL PHYDIO` replaced by CALSLT ($001C) to $4010 in the disk
; interface's slot -- DRVTBL's first slot byte ($FB22, IY high), IX $4010 -- with the same A, F, B, C, DE, HL. CALSLT
; leaves interrupts off on its way in (case 08's `ei` reaches DSKIO as di). The NODISK row has no disk interface ($FB22
; 0): the call is skipped and the record holds the registers as entered. Everything else is XDSK1's: the buffer, the
; 14-byte record (A, F, B, C, D, E, H, L, the interrupt state after, the buffer's 16-bit sum, +0, +512, a pad).
; Cases:
;   00: read boot: A 0, F $00, B 1, C $F9, DE 0, HL $A400, di, fill E5
;   01: read 2 FAT: A 0, F $00, B 2, C $F9, DE 1, HL $A400, di, fill E5
;   02: read last: A 0, F $00, B 1, C $F9, DE 1439, HL $A400, di, fill E5
;   03: read beyond: A 0, F $00, B 1, C $F9, DE 1440, HL $A400, di, fill E5
;   04: read B=0 from the last sector: A 0, F $00, B 0, C $F9, DE 1439, HL $A400, di, fill E5 (run 1 had DE 0:
;       the VG-8020 + NMS 1200 never returned -- B 0 read on, 256 sectors, over this probe)
;   05: read media F8: A 0, F $00, B 1, C $F8, DE 0, HL $A400, di, fill E5
;   06: write last: A 0, F $01, B 1, C $F9, DE 1439, HL $A400, di, fill PAT
;   07: read last back: A 0, F $00, B 1, C $F9, DE 1439, HL $A400, di, fill E5
;   08: read boot, F $FE, ei: A 0, F $FE, B 1, C $F9, DE 0, HL $A400, ei, fill E5
;   09: read boot to $8000: A 0, F $00, B 1, C $F9, DE 0, HL $8000, di, fill E5
;   10: read 2 across 1439: A 0, F $00, B 2, C $F9, DE 1439, HL $A400, di, fill E5
; Drive A is a fresh copy of the generated empty 720 KB disk (@disk), the same image on both machines; sector 1439
; lies outside every file. The disk machine of ours asks the date before BASIC starts (a CR at 20 s, @type-at).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdskio1.asm --row both
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @timeout 60

PHYDIO  equ     $0144
CALSLT  equ     $001C
DRVSLT  equ     $FB22
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
                ; case 00: read boot
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0000
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 01: read 2 FAT
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02F9
                ld      de, $0001
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 02: read last
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 03: read beyond
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $05A0
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 04: read B=0, from the LAST sector (run 1 read from sector 0 and the VG-8020 + NMS 1200
                ; never came back: B 0 is 256 sectors there, 128 KB over this probe; from 1439 a count that
                ; large stops at 1440 after 512 bytes)
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $00F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 05: read media F8
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F8
                ld      de, $0000
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 06: write last
                ld      hl, $A400
                ld      (buf), hl
                call    fill_pat
                ld      bc, $0001
                push    bc
                ld      bc, $01F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 07: read last back
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    dskio
                call    rec
                ; case 08: read boot, F $FE, ei
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $00FE
                push    bc
                ld      bc, $01F9
                ld      de, $0000
                ld      hl, $A400
                pop     af
                ei
                call    dskio
                call    rec
                ; case 09: read boot to $8000
                ld      hl, $8000
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $01F9
                ld      de, $0000
                ld      hl, $8000
                pop     af
                di
                call    dskio
                call    rec
                ; case 10: read 2 across 1439
                ld      hl, $A400
                ld      (buf), hl
                call    fill_e5
                ld      bc, $0000
                push    bc
                ld      bc, $02F9
                ld      de, $059F
                ld      hl, $A400
                pop     af
                di
                call    dskio
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
dskio:                                  ; CALSLT to DSKIO ($4010) in the disk interface's slot; none: return
                push    af
                ld      a, (DRVSLT)
                or      a
                jr      z, nodsk
                pop     af
                ld      iy, (DRVSLT - 1)        ; IY high = the slot
                ld      ix, $4010
                jp      CALSLT
nodsk:
                pop     af
                ret
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
