; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBSCAN2 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), docs/msx2/sub/SCANR.md / SCANL.md: the cases xsubscan.asm
; could not separate -- SCANR's B gate at a DE that does not return at once, the border skip (DE counted down), DE
; $7FFF / $8000 / 2, a non-border non-zero pixel inside the run, a run of a non-zero colour, SCANL's CSAVEA / CSAVEM
; against non-zero markers, and the commands each call issues (every OUT to $99 and $9B logged, @portlog).
; SCREEN 8, line 50; BRDATR ($FCB2) $0F, ATRBYT ($F3F2) $05; interrupts off. Per case (the table `cases`, 19 bytes:
; the op (0 SCANR $00C1, 1 SCANL $00C5), B, DE, the start X, the line's base colour, then up to 6 (X, colour) pixels,
; colour $FF ending the list): the line := the base colour, then the pixels; CSAVEA ($F942) := $1357, CSAVEM ($F944)
; := $2468 (markers); MAPXYC ($0091) to (start X, 50); the logs armed; B, DE; the call; the logs disarmed; the engine
; waited for; then A / F / HL / DE, CLOC / CMASK, CSAVEA / CSAVEM and the line from X 20, 96 bytes.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 128-byte record from +2: +0 the case,
;   +1 A, +2 F, +3/+4 HL, +5/+6 DE, +7/+8 CLOC, +9 CMASK, +10/+11 CSAVEA, +12/+13 CSAVEM, +14 IFF, +15 0,
;   +16/+17 the $99 log's start, +18/+19 its end, +20/+21 the $9B log's start, +22/+23 its end, +24..+31 0,
;   +32..+127 the line X 20-115. The $99 log runs from $CA00, the $9B log from $D800.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubscan2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; BIOS entries and work-area cells, the VDP's published ports, the probe's own OUTs to the
; VDP observed by the debugger's I/O watch.
;
; @cap C000
; @caplen 1F00
; @portlog 99 E90A E8F4
; @portlog 9B E90C E8F4
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
ARMFN   equ     $E8F4
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
LP99    equ     $E90A
LP9B    equ     $E90C
rsave   equ     $E910                   ; AF (2), HL, DE, IFF
sv99    equ     $E918
sv9B    equ     $E91A
st99    equ     $E91C
st9B    equ     $E91E
cur     equ     $E930                   ; the 19-byte case

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
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LP99), hl
                ld      (LP9B), hl
                ld      hl, $CA00
                ld      (sv99), hl
                ld      hl, $D800
                ld      (sv9B), hl
                call    ARMFN
                ld      a, 8
                call    CHGMOD
                di
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
                ld      bc, 19
                ldir
                ld      (tp), hl
                ; the line: 256 x the base colour, then the pixels
                ld      hl, 50 * 256
                ld      c, $40
                call    vset
                ld      b, 0
                ld      a, (cur+6)
cl:
                out     ($98), a
                djnz    cl
                ld      ix, cur+7
px:
                ld      a, (ix+1)
                cp      $FF
                jr      z, px_end
                ld      l, (ix+0)
                ld      h, 50
                ld      c, $40
                call    vset
                ld      a, (ix+1)
                out     ($98), a
                inc     ix
                inc     ix
                jr      px
px_end:
                ld      a, $0F
                ld      ($FCB2), a
                ld      a, $05
                ld      ($F3F2), a
                ld      hl, $1357
                ld      ($F942), hl
                ld      hl, $2468
                ld      ($F944), hl
                ld      bc, (cur+4)
                ld      de, 50
                ld      ix, $0091
                call    EXTROM
                di
                ld      hl, (sv99)
                ld      (st99), hl
                ld      (LP99), hl
                ld      hl, (sv9B)
                ld      (st9B), hl
                ld      (LP9B), hl
                ld      a, (cur+1)
                ld      b, a
                ld      de, (cur+2)
                ld      ix, $00C1
                ld      a, (cur)
                or      a
                jr      z, c_go
                ld      ix, $00C5
c_go:
                call    EXTROM
                push    af
                ld      a, i
                di
                ld      (rsave+2), hl
                ld      (rsave+4), de
                push    af
                pop     bc
                ld      a, c
                rrca
                rrca
                and     1
                ld      (rsave+6), a
                pop     bc
                ld      (rsave), bc
                ld      hl, (LP99)
                ld      (sv99), hl
                ld      hl, (LP9B)
                ld      (sv9B), hl
                ld      hl, 0
                ld      (LP99), hl
                ld      (LP9B), hl
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
                ld      hl, rsave+2
                ld      bc, 4
                ldir
                ld      hl, $F92A
                ld      bc, 3
                ldir
                ld      hl, $F942
                ld      bc, 4
                ldir
                ld      a, (rsave+6)
                ld      (de), a
                inc     de
                inc     de
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
                ld      hl, 50 * 256 + 20
                ld      c, $00
                call    vset
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ex      de, hl
                ld      b, 96
r_line:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    r_line
                ld      (ptr), de
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

; op, B, DE, start X, base colour, (X, colour) x 6 ($FF ends)
cases:
                db      0, 0
                dw      1, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 0 SCANR B 0 DE 1
                db      0, 1
                dw      1, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 1 SCANR B 1 DE 1
                db      0, $80
                dw      1, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 2 SCANR B $80 DE 1
                db      0, 1
                dw      2, 60
                db      0, 30, $0F, 60, $0F, 61, $0F, 62, $0F, 100, $0F, 0, $FF     ; 3 SCANR DE 2, 3 borders at the start
                db      0, 1
                dw      3, 60
                db      0, 30, $0F, 60, $0F, 61, $0F, 62, $0F, 100, $0F, 0, $FF     ; 4 SCANR DE 3, the same
                db      0, 1
                dw      4, 60
                db      0, 30, $0F, 60, $0F, 61, $0F, 62, $0F, 100, $0F, 0, $FF     ; 5 SCANR DE 4, the same
                db      0, 1
                dw      $7FFF, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 6 SCANR DE $7FFF
                db      0, 1
                dw      $8000, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 7 SCANR DE $8000
                db      0, 1
                dw      2, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 8 SCANR DE 2
                db      0, 1
                dw      1, 60
                db      0, 30, $0F, 80, $07, 100, $0F, 0, $FF, 0, $FF, 0, $FF       ; 9 SCANR, a $07 pixel at X 80
                db      1, 1
                dw      $5A5A, 60
                db      0, 30, $0F, 45, $07, 100, $0F, 0, $FF, 0, $FF, 0, $FF       ; 10 SCANL, a $07 pixel at X 45
                db      1, 1
                dw      $5A5A, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 11 SCANL (DE $5A5A in)
                db      0, 1
                dw      1, 60
                db      $07, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF      ; 12 SCANR, the line $07
                db      1, 1
                dw      $5A5A, 60
                db      $07, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF      ; 13 SCANL, the line $07
                db      0, 1
                dw      0, 60
                db      0, 30, $0F, 60, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF       ; 14 SCANR DE 0 on a border pixel
                db      1, 0
                dw      $5A5A, 60
                db      0, 30, $0F, 100, $0F, 0, $FF, 0, $FF, 0, $FF, 0, $FF        ; 15 SCANL B 0
                db      $EE

                ds      $8000 - $, $FF
