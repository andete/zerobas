; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBSCAN -- D-MSX2SPEC, docs/msx2/sub/SCANR.md / SCANL.md: the sub-ROM's PAINT scans at $00C1 (SCANR) and $00C5
; (SCANL), through EXTROM, on the MSX2 / MSX2+ references -- entries the handbook does not publish.
; SCREEN 8, line 50: all $00 but the border colour $0F (BRDATR, $FCB2) at X 30 and X 100; MAPXYC ($0091) to (60, 50);
; ATRBYT ($F3F2) $05; interrupts off. Per case (the table `optab`: SCANR B 1 / B 0 with DE 0, SCANL, SCANR B 1 with DE
; 1 and $FFFF): the line re-made,
; the call, the engine waited for; then A / F / HL / DE, CLOC / CMASK, CSAVEA / CSAVEM ($F942 / $F944) and the line
; from X 20, 96 bytes.
; The capture (CAP = C001): +0 $A5 when finished; per case a 112-byte record from +1: +0 the op, +1 A, +2 F, +3/+4 HL,
;   +5/+6 DE, +7/+8 CLOC, +9 CMASK, +10/+11 CSAVEA, +12/+13 CSAVEM, +14 IFF, +15 0, +16..+111 the line.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubscan.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0240
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
op      equ     $E906
rsave   equ     $E910

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $023F
                ld      (hl), 0
                ldir
                ld      a, 8
                call    CHGMOD
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (op), a
c_next:
                ; the line: 256 x $00, then the borders
                ld      hl, 50 * 256
                ld      c, $40
                call    vset
                ld      b, 0
cl:
                xor     a
                out     ($98), a
                djnz    cl
                ld      hl, 50 * 256 + 30
                ld      c, $40
                call    vset
                ld      a, $0F
                out     ($98), a
                ld      hl, 50 * 256 + 100
                ld      c, $40
                call    vset
                ld      a, $0F
                out     ($98), a
                ld      a, $0F
                ld      ($FCB2), a
                ld      a, $05
                ld      ($F3F2), a
                ld      bc, 60
                ld      de, 50
                ld      ix, $0091
                call    EXTROM
                di
                ; op 0 SCANR B 1 DE 0, 1 SCANR B 0 DE 0, 2 SCANL, 3 SCANR B 1 DE 1, 4 SCANR B 1 DE $FFFF
                ld      a, (op)
                ld      hl, optab
                add     a, a
                add     a, a
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      b, (hl)
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      a, (hl)
                ld      ix, $00C1
                or      a
                jr      z, c_go
                ld      ix, $00C5
c_go:
                call    EXTROM
                push    af
                ld      a, i
                di
                push    af
                pop     bc
                ld      a, c
                rrca
                rrca
                and     1
                ld      (rsave+6), a
                pop     bc
                ld      (rsave), bc
                ld      (rsave+2), hl
                ld      (rsave+4), de
                call    cewait
                ld      de, (ptr)
                ld      a, (op)
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
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                push    hl
                ld      hl, 50 * 256 + 20
                ld      c, $00
                call    vset
                pop     de
                ld      b, 96
r_line:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    r_line
                ld      hl, (ptr)
                ld      bc, 112
                add     hl, bc
                ld      (ptr), hl
                ld      a, (op)
                inc     a
                ld      (op), a
                cp      5
                jp      nz, c_next
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

; B, DE, 1 = SCANL
optab:          db      1, $00, $00, 0
                db      0, $00, $00, 0
                db      0, $00, $00, 1
                db      1, $01, $00, 0
                db      1, $FF, $FF, 0

                ds      $8000 - $, $FF
