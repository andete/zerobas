; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBBOX -- D-MSX2SPEC, docs/msx2/sub/{NVBXLN,NVBXFL,DOGRPH}.md: the sub-ROM's box ($00C9 NVBXLN), filled box ($00CD
; NVBXFL) and line ($0085 DOGRPH) through EXTROM, on the MSX2 / MSX2+ references. Per case (the table `cases`: the
; entry, SCRMOD, BC, DE, GXPOS, GYPOS, GRPACX, GRPACY, LOGOPR, the window's preset byte): CHGMOD (main $005F),
; interrupts off; the window -- 8 lines (Y 9-16) x 16 bytes from X 8 (SCREEN 8: one byte a pixel; SCREEN 5: from X 8
; / 2, two pixels a byte) -- := the preset by hand; $F3F2 := $05 and $F3F3 := $0A (the handbook names ATRBYT $F3F3:
; the colour drawn says which cell is read); GXPOS ($FCB3), GYPOS ($FCB5), GRPACX ($FCB7), GRPACY ($FCB9), LOGOPR
; ($FB02); the call; the command engine waited for (S#2 CE, by hand); then the window, the four cells, R#36-R#45.
; DOGRPH's three point pairs are all different, so the line drawn says which two it joins.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 160-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 0, +4..+11 GXPOS GYPOS GRPACX GRPACY after, +12..+21 R#36-R#45, +22..+31 0,
;   +32..+159 the window (8 x 16).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubbox.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger.
;
; @cap C000
; @caplen 0500
; @vdpfull E8F0 E900
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
GXPOS   equ     $FCB3
LOGOPR  equ     $FB02
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920                   ; entry (2), SCRMOD, 6 words, LOGOPR, preset = 17
SNAPB   equ     $E000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $04FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
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
                ld      bc, 17
                ldir
                ld      (tp), hl
                ld      a, (cur+2)
                call    CHGMOD
                di
                ; the window := the preset
                ld      c, $40
                call    win
                ; the cells
                ld      a, $05
                ld      ($F3F2), a
                ld      a, $0A
                ld      ($F3F3), a
                ld      hl, cur+7
                ld      de, GXPOS
                ld      bc, 8
                ldir
                ld      a, (cur+15)
                ld      (LOGOPR), a
                ld      bc, (cur+3)
                ld      de, (cur+5)
                ld      ix, (cur)
                call    EXTROM
                di
                push    af
                pop     hl
                ld      (rsave), hl
                call    cewait
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
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
                inc     de
                ld      hl, GXPOS
                ld      bc, 8
                ldir
                ld      hl, SNAPB+36
                ld      bc, 10
                ldir
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ld      (ptr), hl
                ld      c, $00
                call    win
                ld      hl, (ptr)
                ld      bc, 128
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

; wait for the VDP's command engine: S#2 bit 0 (CE), by hand
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

; the window, 8 lines x 16 bytes, write (C $40: the preset) or read (C $00: into (ptr) onwards)
win:
                ld      b, 9                    ; Y 9 .. 16
                ld      de, (ptr)
w_line:
                push    bc
                ; the line's address: SCREEN 8 Y x 256 + 8; SCREEN 5 Y x 128 + 4
                ld      a, (cur+2)
                cp      8
                ld      a, b
                jr      z, w_s8
                ld      h, 0
                ld      l, a
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl                  ; x 128
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                jr      w_set
w_s8:
                ld      h, a
                ld      l, 8
w_set:
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
                pop     de
                ld      b, 16
w_b:
                ld      a, c
                or      a
                jr      z, w_rd
                ld      a, (cur+16)
                out     ($98), a
                jr      w_nx
w_rd:
                in      a, ($98)
                ld      (de), a
                inc     de
w_nx:
                djnz    w_b
                pop     bc
                inc     b
                ld      a, b
                cp      17
                jr      nz, w_line
                ret

cases:
                dw      $00C9
                db      8
                dw      10, 10, 20, 15, 0, 0
                db      0, $00   ; 0 NVBXLN
                dw      $00C9
                db      8
                dw      20, 15, 10, 10, 0, 0
                db      0, $00   ; 1 NVBXLN reversed
                dw      $00CD
                db      8
                dw      10, 10, 20, 15, 0, 0
                db      0, $00   ; 2 NVBXFL
                dw      $00CD
                db      8
                dw      20, 15, 10, 10, 0, 0
                db      0, $00   ; 3 NVBXFL reversed
                dw      $0085
                db      8
                dw      20, 15, 23, 9, 10, 10
                db      0, $00   ; 4 DOGRPH
                dw      $00C9
                db      8
                dw      10, 10, 20, 15, 0, 0
                db      3, $0F   ; 5 NVBXLN XOR over $0F
                dw      $00CD
                db      5
                dw      10, 10, 20, 15, 0, 0
                db      0, $00   ; 6 NVBXFL SCREEN 5
                dw      0

                ds      $8000 - $, $FF
