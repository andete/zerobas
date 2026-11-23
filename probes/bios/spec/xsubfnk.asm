; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBFNK -- D-MSX2SPEC, docs/msx2/sub/DSPFNK.md: the sub-ROM's DSPFNK ($011D) through EXTROM, on the MSX2 / MSX2+
; references. FNKSTR ($F87F, 10 x 16) := key k's string = 15 x ('A' + k) -- so the screen says which keys and how many
; characters. Per case (the table `cases`: SCRMOD, LINL40 / LINL32, the VRAM address read back, its length): CHGMOD
; (main $005F) with the width set first, CNSDFG ($F3DE) := 0, CRTCNT 24, interrupts off, the call, then CNSDFG, A / F /
; IFF and the VRAM span (the key row of the text modes; SCREEN 5's line 204, in case it draws on the bitmap).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 112-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4 CNSDFG after, +5..+15 0, +16..+111 the span (up to 96 bytes).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubfnk.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0200
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
CNSDFG  equ     $F3DE
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920                   ; SCRMOD, width, address (2), length

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $01FF
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
                ld      bc, 5
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                ld      ($F3AE), a              ; LINL40
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur)
                call    CHGMOD
                di
                ld      hl, fkeys
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                xor     a
                ld      (CNSDFG), a
                ld      a, 24
                ld      ($F3B1), a              ; CRTCNT
                ld      ix, $011D
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
                ld      a, (CNSDFG)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ex      de, hl
                ld      hl, (cur+2)
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
                out     ($99), a
                ld      a, (cur+4)
                ld      b, a
c_rd:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    c_rd
                ld      hl, (ptr)
                ld      bc, 112
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

fkeys:
                db      "AAAAAAAAAAAAAAA", 0
                db      "BBBBBBBBBBBBBBB", 0
                db      "CCCCCCCCCCCCCCC", 0
                db      "DDDDDDDDDDDDDDD", 0
                db      "EEEEEEEEEEEEEEE", 0
                db      "FFFFFFFFFFFFFFF", 0
                db      "GGGGGGGGGGGGGGG", 0
                db      "HHHHHHHHHHHHHHH", 0
                db      "IIIIIIIIIIIIIII", 0
                db      "JJJJJJJJJJJJJJJ", 0

cases:
                db      0, 40
                dw      $0398
                db      40   ; 0 SCREEN 0 width 40, row 23
                db      0, 80
                dw      $0730
                db      80   ; 1 SCREEN 0 width 80, row 23
                db      1, 32
                dw      $1AE0
                db      32   ; 2 SCREEN 1, row 23
                db      5, 40
                dw      $6600
                db      96   ; 3 SCREEN 5, line 204
                db      $EE

                ds      $8000 - $, $FF
