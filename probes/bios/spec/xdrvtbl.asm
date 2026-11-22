; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XDRVTBL -- DRVTBL ($FB21 .. $FB2C, the published disk work area) and H.PHYD ($FFA7 .. $FFAB) as a program sees them
; from H.STKE (every ROM initialised), on every row: the bytes are copied to the capture, nothing is called.
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdrvtbl.asm --row both
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
                ld      hl, $FB21
                ld      de, CAP
                ld      bc, 12
                ldir
                ld      hl, $FFA7
                ld      bc, 5
                ldir
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; rec -- the 30-byte record: A F B C D E H L, the interrupt state, the buffer's 21 bytes
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
                ld      hl, $A400
                ld      bc, 21
                ldir
                ld      (ptr), de
                pop     af
                ret

cases:
                dw      $4019
                db      $00, $00
                dw      $4019
                db      $F9, $F9
                dw      $4019
                db      $FF, $FF
                dw      $401F
                db      $00, $00
                dw      $401F
                db      $FF, $FF
                dw      $401F
                db      $12, $34
                dw      0

                ds      $8000 - $, $FF
