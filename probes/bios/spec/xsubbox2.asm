; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBBOX2 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), docs/msx2/sub/{NVBXLN,NVBXFL,DOGRPH}.md: the cases xsubbox.asm
; could not separate. The same per-case procedure and record as xsubbox.asm (the table `cases`: the entry, SCRMOD, BC,
; DE, GXPOS, GYPOS, GRPACX, GRPACY, LOGOPR, the window's preset; $F3F2 := $05, $F3F3 := $0A; the window Y 9-16 x 16
; bytes from X 8), plus: GRPACX / GRPACY preset to non-zero markers, and every OUT to $99 and to $9B during the call
; logged (@portlog), so the commands issued -- their count, registers and order -- are read, not inferred from the
; residue.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 160-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 0, +4..+11 GXPOS GYPOS GRPACX GRPACY after, +12..+21 R#36-R#45,
;   +22/+23 the $99 log's start, +24/+25 its end, +26/+27 the $9B log's start, +28/+29 its end, +30/+31 0,
;   +32..+159 the window (8 x 16). The $99 log runs from $CC00, the $9B log from $DA00 (inside the capture).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubbox2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger, the probe's own OUTs to the VDP observed by the debugger's I/O watch.
;
; @cap C000
; @caplen 1F00
; @vdpfull E8F0 E900
; @portlog 99 E90A E8F4
; @portlog 9B E90C E8F4
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
GXPOS   equ     $FCB3
LOGOPR  equ     $FB02
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ARMFN   equ     $E8F4
LP99    equ     $E90A
LP9B    equ     $E90C
sv99    equ     $E912
sv9B    equ     $E914
st99    equ     $E916
st9B    equ     $E918
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
                ld      bc, $1EFF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LP99), hl
                ld      (LP9B), hl
                ld      hl, $CC00
                ld      (sv99), hl
                ld      hl, $DA00
                ld      (sv9B), hl
                call    ARMFN
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
                ld      hl, (sv99)
                ld      (st99), hl
                ld      (LP99), hl
                ld      hl, (sv9B)
                ld      (st9B), hl
                ld      (LP9B), hl
                ld      ix, (cur)
                call    EXTROM
                di
                push    af
                pop     hl
                ld      (rsave), hl
                ld      hl, (LP99)
                ld      (sv99), hl
                ld      hl, (LP9B)
                ld      (sv9B), hl
                ld      hl, 0
                ld      (LP99), hl
                ld      (LP9B), hl
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
                ld      hl, st99
                ld      bc, 2
                ldir
                ld      hl, sv99
                ld      bc, 2
                ldir
                ld      hl, st9B
                ld      bc, 2
                ldir
                ld      hl, sv9B
                ld      bc, 2
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
                dw      20, 10, 10, 15, 77, 33
                db      0, $00   ; 0 NVBXLN anti-diagonal (20,10)-(10,15); GRPAC markers
                dw      $00C9
                db      8
                dw      10, 15, 20, 10, 77, 33
                db      0, $00   ; 1 NVBXLN anti-diagonal reversed (10,15)-(20,10)
                dw      $00C9
                db      8
                dw      12, 11, 19, 14, 44, 55
                db      0, $00   ; 2 NVBXLN asymmetric (12,11)-(19,14)
                dw      $00C9
                db      8
                dw      19, 14, 12, 11, 44, 55
                db      0, $00   ; 3 NVBXLN asymmetric reversed (19,14)-(12,11)
                dw      $00C9
                db      8
                dw      10, 10, 20, 15, 77, 33
                db      3, $0C   ; 4 NVBXLN XOR over $0C ($0C^$05 = $09, not $F3F3's $0A)
                dw      $00C9
                db      8
                dw      10, 10, 20, 15, 77, 33
                db      2, $08   ; 5 NVBXLN OR over $08
                dw      $00C9
                db      8
                dw      10, 10, 20, 15, 77, 33
                db      8, $0C   ; 6 NVBXLN TIMP over $0C
                dw      $00CD
                db      8
                dw      10, 10, 20, 15, 77, 33
                db      0, $00   ; 7 NVBXFL (10,10)-(20,15)
                dw      $00CD
                db      8
                dw      20, 15, 10, 10, 77, 33
                db      0, $00   ; 8 NVBXFL (20,15)-(10,10)
                dw      $00CD
                db      5
                dw      11, 10, 20, 15, 77, 33
                db      0, $00   ; 9 NVBXFL SCREEN 5 (11,10)-(20,15): odd left edge
                dw      $0085
                db      8
                dw      11, 14, 21, 11, 77, 33
                db      0, $00   ; 10 DOGRPH BC/DE (11,14) GX/GY (21,11): both ends inside the window
                dw      $0085
                db      8
                dw      21, 11, 11, 14, 77, 33
                db      0, $00   ; 11 DOGRPH swapped: BC/DE (21,11) GX/GY (11,14)
                dw      $0085
                db      8
                dw      11, 14, 21, 11, 77, 33
                db      2, $08   ; 12 DOGRPH OR over $08
                dw      $00CD
                db      8
                dw      10, 10, 20, 15, 77, 33
                db      3, $0C   ; 13 NVBXFL XOR over $0C
                dw      $0085
                db      8
                dw      11, 11, 21, 14, 77, 33
                db      0, $00   ; 14 DOGRPH BC/DE (11,11) GX/GY (21,14): down-right, so "start at the top" and
                                 ;    "start at the right" disagree
                dw      $0085
                db      8
                dw      21, 14, 11, 11, 77, 33
                db      0, $00   ; 15 DOGRPH swapped: BC/DE (21,14) GX/GY (11,11)
                dw      0

                ds      $8000 - $, $FF
