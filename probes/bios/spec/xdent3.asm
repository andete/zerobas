; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XDENT3 -- DSKCHG ($4013) and GETDPB ($4016) round 3 (2026-11-22), answering review pass 1 (scratchpad/
; DENT_review1.md): does DSKCHG's B 0 path READ the disk (C $F8 against the $F9 disk); does GETDPB take B or C (B $F9,
; C $F8); does a B 1 answer restart the clock (DSKCHG once a second); is GETDPB an access (after 3.5 s idle, GETDPB,
; then DSKCHG); the motor or a timer (MTOFF, then DSKCHG); seconds or timer interrupts (a 3.5 s wait with interrupts
; OFF). XDENT1's frame and 30-byte record (probes/bios/spec/xdent1.asm), XDENT2's WAIT step (entry $0001: B x 8 timer
; interrupts, EI / HALT) and a BUSY step (entry $0002: B x 65536 loops of DEC BC / LD A,B / OR C / JR NZ with
; interrupts off -- ~0.5 s each at 3.58 MHz). The capture is 11 records (330 bytes, @caplen 180).
; Steps (the entry, B, C):
;   0: DSKCHG, C $F8 (the disk is $F9): B $00, C $F8
;   1: GETDPB, B $F9, C $F8: B $F9, C $F8
;   --: wait 48 frames (~1 s): B 6
;   2: DSKCHG at ~1 s: B $00, C $F9
;   --: wait ~1 s: B 6
;   3: DSKCHG at ~2 s: B $00, C $F9
;   --: wait ~1 s: B 6
;   4: DSKCHG at ~3 s: B $00, C $F9
;   --: wait ~1 s: B 6
;   5: DSKCHG at ~4 s: B $00, C $F9
;   --: wait 176 frames (~3.5 s): B 22
;   6: GETDPB after ~3.5 s idle: B $F9, C $F9
;   7: DSKCHG right after it: B $00, C $F9
;   8: MTOFF: B $00, C $00
;   9: DSKCHG right after MTOFF: B $00, C $F9
;   --: busy wait, interrupts OFF, 7 x 65536 loops (~3.5 s): B 7
;   10: DSKCHG after it: B $00, C $F9
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdent3.asm --row both
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 180
; @timeout 120

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
                ld      bc, $17F
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
                jr      z, iswait
                dec     hl
                ld      a, h
                or      l
                jr      nz, notwait
                ld      a, (cb)             ; BUSY: B x 65536 loops, interrupts off
                di
bz1:
                push    af
                ld      bc, 0
bz2:
                dec     bc
                ld      a, b
                or      c
                jr      nz, bz2
                pop     af
                dec     a
                jr      nz, bz1
                jp      nxt
iswait:
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
                jp      nxt
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
                jp      nxt
skip:
                ld      hl, (ptr)
                ld      de, 30
                add     hl, de
                ld      (ptr), hl
                jp      nxt
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
                dw      $4013
                db      $00, $F8
                dw      $4016
                db      $F9, $F8
                dw      $0001
                db      $06, $00
                dw      $4013
                db      $00, $F9
                dw      $0001
                db      $06, $00
                dw      $4013
                db      $00, $F9
                dw      $0001
                db      $06, $00
                dw      $4013
                db      $00, $F9
                dw      $0001
                db      $06, $00
                dw      $4013
                db      $00, $F9
                dw      $0001
                db      $16, $00
                dw      $4016
                db      $F9, $F9
                dw      $4013
                db      $00, $F9
                dw      $401F
                db      $00, $00
                dw      $4013
                db      $00, $F9
                dw      $0002
                db      $07, $00
                dw      $4013
                db      $00, $F9
                dw      0

                ds      $8000 - $, $FF
