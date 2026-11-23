; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBGPP2 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), docs/msx2/sub/GRPPRT.md: the cases xsubgpp.asm could not
; separate -- the line feed at the bottom edge, the glyph at the right-edge wrap, SCREEN 2's pattern / colour bytes,
; an odd X in SCREEN 5, XOR and TIMP-with-BAKCLR-0, ATRBYT / FORCLR / BAKCLR after, and the registers after.
; Per case (the table `cases`, 18 bytes: SCRMOD, A, GRPACX, GRPACY, LOGOPR, FORCLR, BAKCLR, the windows' preset, then
; two VRAM windows as (address, stride)): CHGMOD (main $005F), interrupts off; FORCLR ($F3E9), BAKCLR ($F3EA), ATRBYT
; ($F3F2) := $0A; both windows (20 rows x 16 bytes, row r at address + r x stride) := the preset; GRPACX ($FCB7) /
; GRPACY ($FCB9); LOGOPR ($FB02); BC $B1C2, DE $D3E4, HL $A5F6, IY $9786 (garbage); the call (IX = $0089); then the
; registers at once, the command engine waited for, the cells, the windows.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 672-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4/+5 GRPACX after, +6/+7 GRPACY after, +8 ATRBYT after, +9/+10 BC, +11/+12 DE,
;   +13/+14 HL, +15/+16 IX, +17/+18 IY, +19 FORCLR after, +20 BAKCLR after, +21..+31 0, +32..+351 window A,
;   +352..+671 window B.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubgpp2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 2200
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
GRPACX  equ     $FCB7
LOGOPR  equ     $FB02
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910                   ; AF (2), BC, DE, HL, IX, IY, IFF
cur     equ     $E930                   ; the 18-byte case
wrow    equ     $E950

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $F000
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $21FF
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
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 18
                ldir
                ld      (tp), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      a, (cur+7)
                ld      ($F3E9), a
                ld      a, (cur+8)
                ld      ($F3EA), a
                ld      a, $0A
                ld      ($F3F2), a
                ld      c, $40
                call    wins
                ld      hl, cur+2
                ld      de, GRPACX
                ld      bc, 4
                ldir
                ld      a, (cur+6)
                ld      (LOGOPR), a
                ld      a, (cur+1)
                ld      bc, $B1C2
                ld      de, $D3E4
                ld      hl, $A5F6
                ld      iy, $9786
                ld      ix, $0089
                call    EXTROM
                ld      (rsave+2), bc
                ld      (rsave+4), de
                ld      (rsave+6), hl
                ld      (rsave+8), ix
                ld      (rsave+10), iy
                push    af
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+12), a
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
                ld      a, (rsave+12)
                ld      (de), a
                inc     de
                ld      hl, GRPACX
                ld      bc, 4
                ldir
                ld      a, ($F3F2)
                ld      (de), a
                inc     de
                ld      hl, rsave+2
                ld      bc, 10
                ldir
                ld      a, ($F3E9)
                ld      (de), a
                inc     de
                ld      a, ($F3EA)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ld      (ptr), hl
                ld      c, $00
                call    wins
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

; both windows: C $40 write the preset, C $00 read into (ptr) onwards (ptr advanced)
wins:
                ld      hl, (cur+10)
                ld      de, (cur+12)
                call    win
                ld      hl, (cur+14)
                ld      de, (cur+16)
                ; fall through
; one window: HL the address, DE the stride, 20 rows x 16 bytes
win:
                ld      b, 20
w_row:
                push    bc
                push    hl
                push    de
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
                ld      b, 16
                ld      a, c
                or      a
                jr      z, w_rd
                ld      a, (cur+9)
w_wr:
                out     ($98), a
                djnz    w_wr
                jr      w_nx
w_rd:
                ld      hl, (ptr)
w_rl:
                in      a, ($98)
                ld      (hl), a
                inc     hl
                djnz    w_rl
                ld      (ptr), hl
w_nx:
                pop     de
                pop     hl
                add     hl, de
                pop     bc
                djnz    w_row
                ret

cases:
                db      8, $41
                dw      250, 10
                db      0, $05, $03, $0F
                dw      $08F0, 256, $0800, 256          ; 0 'A' at X 250: X 240-255 / X 0-15, Y 8-27
                db      8, $41
                dw      250, 207
                db      0, $05, $03, $0F
                dw      $C4F0, 256, $0000, 256          ; 1 'A' at (250, 207): X 240-255 Y 196-215 / X 0-15 Y 0-19
                db      8, $0D
                dw      10, 207
                db      0, $05, $03, $0F
                dw      $C400, 256, $0000, 256          ; 2 CR at Y 207: X 0-15 Y 196-215 / Y 0-19
                db      8, $0D
                dw      10, 203
                db      0, $05, $03, $0F
                dw      $C400, 256, $0000, 256          ; 3 CR at Y 203
                db      8, $0D
                dw      10, 204
                db      0, $05, $03, $0F
                dw      $C400, 256, $0000, 256          ; 4 CR at Y 204
                db      8, $41
                dw      2, 204
                db      0, $05, $03, $0F
                dw      $C400, 256, $0000, 256          ; 5 'A' at (2, 204): rows 212+ ?
                db      2, $41
                dw      10, 10
                db      0, $05, $03, $0F
                dw      $0100, 16, $2100, 16            ; 6 'A' SCREEN 2: pattern $0100-$023F / colour $2100-$223F
                db      5, $41
                dw      11, 10
                db      0, $05, $03, $0F
                dw      $0404, 128, $0414, 128          ; 7 'A' SCREEN 5 at X 11: X 8-39 / 40-71, Y 8-27
                db      8, $41
                dw      10, 10
                db      3, $05, $03, $0F
                dw      $0808, 256, $0818, 256          ; 8 'A' XOR over $0F: X 8-23 / 24-39, Y 8-27
                db      8, $41
                dw      10, 10
                db      8, $05, $00, $0F
                dw      $0808, 256, $0818, 256          ; 9 'A' TIMP, BAKCLR 0
                db      8, $41
                dw      10, 10
                db      0, $05, $03, $0F
                dw      $0808, 256, $0818, 256          ; 10 'A' PSET (the registers / cells baseline)
                db      8, $41
                dw      10, 10
                db      8, $00, $03, $0F
                dw      $0808, 256, $0818, 256          ; 11 'A' TIMP, FORCLR 0
                db      $EE

                ds      $8000 - $, $FF
