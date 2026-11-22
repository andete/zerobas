; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XDENT5 -- GETDPB ($4016) and DSKCHG ($4013) with drive A EMPTY (no @disk), round 5 (2026-11-22, review pass 2,
; scratchpad/DENT_review2.md): does GETDPB touch the drive at all (its block is B's either way), and does DSKCHG's first
; call READ the disk or answer from a byte it keeps. XDENT1's frame and 30-byte record (probes/bios/spec/xdent1.asm).
; Steps (the entry, B, C):
;   0: GETDPB, drive A EMPTY: B $F9, C $F9
;   1: DSKCHG, first, drive A EMPTY: B $00, C $F9
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdent5.asm --row both
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @type-at 20 \r
; @cap A000
; @timeout 90

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
                jr      z, fin
                ld      (entry), de
                ld      a, (hl)
                ld      (cb), a
                inc     hl
                ld      a, (hl)
                ld      (cc), a
                inc     hl
                ld      (tptr), hl
                ld      hl, (entry)
                dec     hl
                ld      a, h
                or      l
                jr      nz, notwait
                ld      a, (cb)             ; WAIT: B x 8 frames
                ld      b, a
wt1:
                push    bc
                ld      b, 8
wt2:
                ei
                halt
                djnz    wt2
                pop     bc
                djnz    wt1
                jr      nxt
notwait:
                ld      hl, $A400           ; the DPB buffer: $E5 x 32
                ld      b, 32
fl:
                ld      (hl), $E5
                inc     hl
                djnz    fl
                ld      a, (DRVSLT)
                or      a
                jr      z, skip             ; no disk interface (the NODISK row)
                ld      iyh, a
                ld      ix, (entry)
                ld      a, (cb)
                ld      b, a
                ld      a, (cc)
                ld      c, a
                ld      de, 0
                ld      hl, $A400
                push    bc
                ld      bc, 0
                push    bc
                pop     af                  ; A 0, F 0
                pop     bc
                di
                call    CALSLT
                call    rec
                jr      nxt
skip:
                ld      hl, (ptr)
                ld      de, 30
                add     hl, de
                ld      (ptr), hl
                jr      nxt
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
                dw      $4016
                db      $F9, $F9
                dw      $4013
                db      $00, $F9
                dw      0

                ds      $8000 - $, $FF
