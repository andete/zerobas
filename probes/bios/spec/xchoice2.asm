; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHOICE2 -- CHOICE ($4019) and MTOFF ($401F), round 2 (2026-11-22), answering review pass 1 (scratchpad/
; BCHO_review1.md): every entry register from the table (AF, BC with B not C, DE, HL), so "kept" and "set" separate;
; the whole 32-byte buffer recorded; MTOFF and CHOICE right after a DSKIO read (the motor running). XCHOICE1's slot
; set-up and skip (H.PHYD a bare RET, then DRVTBL); each case: the 32 bytes at the case's HL filled with $E5, CALSLT
; to the entry with AF, BC, DE, HL from the table (di), then a 41-byte record: A, F, B, C, D, E, H, L, the interrupt
; state after, the 32 bytes at the case's HL.
; Cases (the entry; AF, BC, DE, HL):
;   0: CHOICE ($4019); $5AD7, $F800, $1234, $C000
;   1: CHOICE; $0000, $00F9, $0000, $A400
;   2: MTOFF ($401F); $5AD7, $1234, $5678, $C000
;   3: DSKIO ($4010) read sector 0 to $A800; $0000, $01F9, $0000, $A800 (the buffer: the image's boot sector)
;   4: MTOFF right after it; $0000, $0000, $0000, $A400
;   5: CHOICE right after; $0000, $0000, $0000, $A400
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchoice2.asm --row both
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @timeout 60

CALSLT  equ     $001C
DRVSLT  equ     $FB22
tptr    equ     $A202
entry   equ     $A204
cb      equ     $A206
cc      equ     $A207
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $A001
ptr     equ     $A200
rsave   equ     $A210
cregs   equ     $A220
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
                ld      hl, cases
                ld      (tptr), hl
nxt:
                ld      hl, (tptr)
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      a, d
                or      e
                jp      z, fin
                ld      (entry), de
                ld      de, cregs           ; AF, BC, DE, HL: 8 bytes
                ld      bc, 8
                ldir
                ld      (tptr), hl
                ld      hl, (cregs + 6)     ; the buffer at the case's HL: $E5 x 32
                ld      b, 32
fl:
                ld      (hl), $E5
                inc     hl
                djnz    fl
                ld      a, ($FFA7)          ; H.PHYD a bare RET: no disk interface (checked FIRST, as a ROM does)
                cp      $C9
                jr      z, skip
                ld      a, (DRVSLT)
                or      a
                jr      z, skip
                ld      iyh, a
                ld      ix, (entry)
                ld      bc, (cregs + 2)
                ld      de, (cregs + 4)
                ld      hl, (cregs)
                push    hl
                ld      hl, (cregs + 6)
                pop     af
                di
                call    CALSLT
                call    rec
                jp      nxt
skip:
                ld      hl, (ptr)
                ld      de, 41
                add     hl, de
                ld      (ptr), hl
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; rec -- the 41-byte record: A F B C D E H L, the interrupt state, the 32 bytes at the case's HL
rec:
                ld      (rsave), hl
                push    af
                ld      hl, (ptr)
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
                ex      de, hl
                ld      hl, (cregs + 6)
                ld      bc, 32
                ldir
                ld      (ptr), de
                pop     af
                ret

cases:
                dw      $4019, $5AD7, $F800, $1234, $C000
                dw      $4019, $0000, $00F9, $0000, $A400
                dw      $401F, $5AD7, $1234, $5678, $C000
                dw      $4010, $0000, $01F9, $0000, $A800
                dw      $401F, $0000, $0000, $0000, $A400
                dw      $4019, $0000, $0000, $0000, $A400
                dw      0

                ds      $8000 - $, $FF
