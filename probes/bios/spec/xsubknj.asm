; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBKNJ -- D-MSX2SPEC, docs/msx2/sub/KNJPRT.md: the sub-ROM's KNJPRT ($01BD, BC = the JIS code, A = the mode)
; through EXTROM in SCREEN 5, on the MSX2 / MSX2+ references (the HB-F900 and FS-A1WSX have a kanji ROM -- openMSX's
; device list names one -- the NMS 8250 has none). Per case (the table `cases`: A, BC, LOGOPR, GRPACX, GRPACY, GXPOS,
; GYPOS, the colour at $F3F2, BAKCLR -- the last six added 2026-11-23 by the goldfish pass, with cases 8-16): CHGMOD 5 (main
; $005F), interrupts off; the window -- lines 12-35 x bytes 6-17 (X 12-35), the 16 x 16 cell at (16, 16) and a
; 4-dot margin -- := $33 by hand; FORCLR ($F3E9) $0F, BAKCLR ($F3EA) (the table's; $04 in cases 0-13), $F3F2 (the
; table's; $05), $F3F3 $0A (each a different colour, so the colour drawn names its cell); GRPACX / GRPACY ($FCB7 /
; $FCB9) := the table's (16 / 16 in cases 0-7), GXPOS / GYPOS ($FCB3 / $FCB5) := the table's (40 / 40, outside the
; window, in cases 0-7) (the position's source); LOGOPR ($FB02); DE $2468 HL $369C IY $8765; the call; S#2 read at
; once (its CE bit: is the command engine still busy on return?); the command engine waited for (S#2 CE, by hand);
; then the registers, the interrupt state, the four position cells and the window.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 320-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 C, +4 B, +5 E, +6 D, +7 L, +8 H, +9 IFF, +10..+17 GXPOS GYPOS GRPACX GRPACY after,
;   +18 $EE (sentinel), +19 S#2 at the first read after the return, +20..+31 0, +32..+319 the window (24 lines x
;   12 bytes).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubknj.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports. The kanji ROM is
; never read: only what the call draws.
;
; @cap C000
; @caplen 1600
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
GXPOS   equ     $FCB3
LOGOPR  equ     $FB02
DONE    equ     $C000
CAP     equ     $C001
REC     equ     320
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
sv_af   equ     $E910
sv_bc   equ     $E912
sv_de   equ     $E914
sv_hl   equ     $E916
sv_if   equ     $E918
cur     equ     $E920                   ; A, BC (2), LOGOPR, GRPACX, GRPACY, GXPOS, GYPOS, $F3F2, BAKCLR
s2first equ     $E91A

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $15FF
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
                ld      bc, 10
                ldir
                ld      (tp), hl
                ld      a, 5
                call    CHGMOD
                di
                ; the window := $33
                ld      hl, 12*128 + 6
                ld      b, 24
w_fill:
                push    bc
                push    hl
                ld      c, $40
                call    vset
                ld      b, 12
                ld      a, $33
w_fb:
                out     ($98), a
                djnz    w_fb
                pop     hl
                ld      bc, 128
                add     hl, bc
                pop     bc
                djnz    w_fill
                ld      a, $0F
                ld      ($F3E9), a
                ld      a, (cur+9)
                ld      ($F3EA), a
                ld      a, (cur+8)
                ld      ($F3F2), a
                ld      a, $0A
                ld      ($F3F3), a
                ld      h, 0
                ld      a, (cur+6)
                ld      l, a
                ld      (GXPOS), hl
                ld      a, (cur+7)
                ld      l, a
                ld      (GXPOS+2), hl
                ld      a, (cur+4)
                ld      l, a
                ld      (GXPOS+4), hl
                ld      a, (cur+5)
                ld      l, a
                ld      (GXPOS+6), hl
                ld      a, (cur+3)
                ld      (LOGOPR), a
                ld      bc, (cur+1)
                ld      de, $2468
                ld      hl, $369C
                ld      iy, $8765
                ld      ix, $01BD
                ld      a, (cur)
                call    EXTROM
                push    af
                ld      (sv_bc), bc
                ld      (sv_de), de
                ld      (sv_hl), hl
                pop     hl
                ld      (sv_af), hl
                ld      a, i
                jp      pe, if_on
                ld      a, i
if_on:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (sv_if), a
                ; S#2 once, at once: is the command engine still busy?
                ld      a, 2
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                in      a, ($99)
                ld      (s2first), a
                xor     a
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                ; wait for the command engine (S#2 bit 0)
ce_wait:
                ld      a, 2
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                in      a, ($99)
                ld      b, a
                xor     a
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                bit     0, b
                jr      nz, ce_wait
                ld      de, (ptr)
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (sv_af+1)
                ld      (de), a
                inc     de
                ld      a, (sv_af)
                ld      (de), a
                inc     de
                ld      hl, sv_bc
                ld      bc, 6
                ldir
                ld      a, (sv_if)
                ld      (de), a
                inc     de
                ld      hl, GXPOS
                ld      bc, 8
                ldir
                ld      a, $EE
                ld      (de), a
                inc     de
                ld      a, (s2first)
                ld      (de), a         ; +19
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ex      de, hl
                ld      hl, 12*128 + 6
                ld      b, 24
w_read:
                push    bc
                push    hl
                ld      c, 0
                call    vset
                ld      b, 12
w_rb:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    w_rb
                pop     hl
                ld      bc, 128
                add     hl, bc
                pop     bc
                djnz    w_read
                ld      hl, (ptr)
                ld      bc, REC
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

; the VRAM address HL (< $4000) for a write (C = $40) or a read (C = 0)
vset:
                xor     a
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

cases:          ; A, BC, LOGOPR, GRPACX, GRPACY, GXPOS, GYPOS, $F3F2, BAKCLR (cases 8-16: goldfish pass 1)
                db      $00
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04
                db      $01
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04
                db      $02
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04
                db      $00
                dw      $2422
                db      0, 16, 16, 40, 40, $05, $04
                db      $00
                dw      $4F53
                db      0, 16, 16, 40, 40, $05, $04
                db      $00
                dw      $3021
                db      3, 16, 16, 40, 40, $05, $04
                db      $00
                dw      $0000
                db      0, 16, 16, 40, 40, $05, $04
                db      $03
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04
                db      $00
                dw      $3021
                db      0, 13, 15, 20, 19, $05, $04     ; 8: unaligned (13, 15), GXPOS / GYPOS (20, 19) inside the window
                db      $04
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04     ; 9: mode 4
                db      $05
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04     ; 10: mode 5
                db      $00
                dw      $0021
                db      0, 16, 16, 40, 40, $05, $04     ; 11: B = 0, C <> 0
                db      $00
                dw      $2100
                db      0, 16, 16, 40, 40, $05, $04     ; 12: B <> 0, C = 0
                db      $00
                dw      $2120
                db      0, 16, 16, 40, 40, $05, $04     ; 13: B, C <> 0, below $2121
                db      $00
                dw      $3021
                db      0, 16, 16, 40, 40, $15, $24     ; 14: $F3F2 $15, BAKCLR $24 (upper nibbles set)
                db      $00
                dw      $2220
                db      0, 16, 16, 40, 40, $05, $04     ; 15: C below $21, BC above $2121: per byte or per word
                db      $FF
                dw      $3021
                db      0, 16, 16, 40, 40, $05, $04     ; 16: mode $FF (last: a hang loses only it)
                db      $EE

                ds      $8000 - $, $FF
