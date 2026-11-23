; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBBLT -- D-MSX2SPEC, docs/msx2/sub/{BLTVV,BLTVM,BLTMV}.md and concepts/block-transfer.md: the sub-ROM's block
; transfers within VRAM ($0191 BLTVV), RAM to VRAM ($0195 BLTVM) and VRAM to RAM ($0199 BLTMV), through EXTROM with HL
; = $F562 and the parameter block there, on the MSX2 / MSX2+ references. Per case (the table `cases`: the entry,
; SCRMOD, the 15-byte block -- SX SY DX DY NX NY (words), CDUMMY ARG LOGOP --, the destination window's preset byte,
; the window's X and Y, 1 = the destination is RAM): CHGMOD (main $005F), interrupts off; the source rectangle (8, 8)
; 8 x 4 := distinct bytes ($10 + row x 16 + column; SCREEN 5: $12 $34 $56 $78 per row) and the window (6 lines x 16
; bytes) := the preset, by hand; the array at $D100 := NX 4, NY 2, $A1-$A8; $D200-$D22B := $EE; the call; the engine
; waited for; then A / F / IFF, the block after, and the window (or $D200-$D22B).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 128-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4..+18 the block after, +19..+31 0, +32..+127 the window (6 x 16) or the RAM.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubblt.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
BLK     equ     $F562
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920                   ; entry (2), SCRMOD, block (15), preset, wx (2), wy, ram = 23

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                inc     hl
                or      (hl)
                dec     hl
                jp      z, finish
                ld      de, cur
                ld      bc, 23
                ldir
                ld      (tp), hl
                ld      a, (cur+2)
                call    CHGMOD
                di
                call    src_set
                ld      c, $40
                call    win
                ld      hl, arr
                ld      de, $D100
                ld      bc, 12
                ldir
                ld      hl, $D200
                ld      de, $D201
                ld      bc, 43
                ld      (hl), $EE
                ldir
                ld      hl, cur+3
                ld      de, BLK
                ld      bc, 15
                ldir
                ld      ix, (cur)
                ld      hl, BLK
                call    EXTROM
                push    af
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      (rsave), hl
                call    cewait
                ld      de, (ptr)
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+2)
                ld      (de), a
                inc     de
                ld      hl, BLK
                ld      bc, 15
                ldir
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cur+22)
                or      a
                jr      z, c_vr
                ld      hl, $D200
                ld      de, (ptr)
                ld      bc, 44
                ldir
                jr      c_rec
c_vr:
                ld      c, $00
                call    win
c_rec:
                ld      hl, (ptr)
                ld      bc, 96
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

cewait:
                ld      a, 2
                out     ($99), a
                ld      a, $8F
                out     ($99), a
cw_lp:
                in      a, ($99)
                rrca
                jr      c, cw_lp
                xor     a
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                ret

; the line Y = A's address (HL) at pixel X = DE: SCREEN 8 Y x 256 + X; SCREEN 5 Y x 128 + X / 2
lineaddr:
                ld      b, a
                ld      a, (cur+2)
                cp      8
                jr      nz, la5
                ld      h, b
                ld      l, 0
                add     hl, de
                ret
la5:
                ld      h, 0
                ld      l, b
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                srl     d
                rr      e
                add     hl, de
                ret
; HL for writing (C $40) / reading (C $00), A16 = 0
vset:
                ld      a, h
                rlca
                rlca
                and     3
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      c
                out     ($99), a
                ret

; the source rectangle (8, 8), four lines
src_set:
                ld      a, 8
ss_lp:
                push    af
                ld      de, 8
                call    lineaddr
                ld      c, $40
                call    vset
                pop     af
                push    af
                sub     8
                add     a, a
                add     a, a
                add     a, a
                add     a, a
                add     a, $10
                ld      c, a
                ld      a, (cur+2)
                cp      8
                jr      nz, ss5
                ld      b, 8
ss8:
                ld      a, c
                out     ($98), a
                inc     c
                djnz    ss8
                jr      ss_nx
ss5:
                ld      hl, s5row
                ld      b, 4
ss5b:
                ld      a, (hl)
                out     ($98), a
                inc     hl
                djnz    ss5b
ss_nx:
                pop     af
                inc     a
                cp      12
                jr      nz, ss_lp
                ret
s5row:          db      $12, $34, $56, $78

; the window: 6 lines from wy x 16 bytes from wx; write (C $40) the preset or read (C $00) into (ptr)
win:
                ld      a, (cur+22)
                or      a
                ret     nz
                ld      a, (cur+21)
                ld      b, 6
                ld      ix, (ptr)
w_line:
                push    bc
                push    af
                push    bc
                ld      de, (cur+19)
                call    lineaddr
                pop     bc
                call    vset
                ld      b, 16
w_b:
                ld      a, c
                or      a
                jr      z, w_rd
                ld      a, (cur+18)
                out     ($98), a
                jr      w_nx
w_rd:
                in      a, ($98)
                ld      (ix+0), a
                inc     ix
w_nx:
                djnz    w_b
                pop     af
                inc     a
                pop     bc
                djnz    w_line
                ret

arr:            dw      4, 2
                db      $A1, $A2, $A3, $A4, $A5, $A6, $A7, $A8

cases:
                dw      $0191
                db      8, $08, $00, $08, $00, $28, $00, $08, $00, $08, $00, $04, $00, $00, $00, $00, $00
                dw      36
                db      7, 0   ; 0 BLTVV
                dw      $0191
                db      8, $08, $00, $08, $00, $28, $00, $08, $00, $08, $00, $04, $00, $00, $00, $03, $FF
                dw      36
                db      7, 0   ; 1 BLTVV XOR over $FF
                dw      $0191
                db      8, $08, $00, $08, $00, $28, $00, $08, $00, $08, $00, $04, $00, $00, $04, $00, $00
                dw      28
                db      7, 0   ; 2 BLTVV ARG DIX
                dw      $0199
                db      8, $08, $00, $08, $00, $00, $D2, $00, $00, $08, $00, $04, $00, $00, $00, $00, $00
                dw      0
                db      0, 1   ; 3 BLTMV to $D200
                dw      $0195
                db      8, $00, $D1, $00, $00, $28, $00, $14, $00, $00, $00, $00, $00, $00, $00, $00, $00
                dw      36
                db      19, 0   ; 4 BLTVM from $D100 (4 x 2)
                dw      $0191
                db      5, $09, $00, $08, $00, $28, $00, $08, $00, $04, $00, $04, $00, $00, $00, $00, $00
                dw      36
                db      7, 0   ; 5 BLTVV SCREEN 5 SX 9
                dw      0

                ds      $8000 - $, $FF
