; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBGPP -- D-MSX2SPEC, docs/msx2/sub/GRPPRT.md: the sub-ROM's GRPPRT ($0089, A = the character) through EXTROM, on the
; MSX2 / MSX2+ references. Per case (the table `cases`: SCRMOD, A, GRPACX, GRPACY, LOGOPR): CHGMOD (main $005F),
; interrupts off; FORCLR ($F3E9) := $05, ATRBYT ($F3F2) := $0A, BAKCLR ($F3EA) := $03 -- all different, so the drawn
; pixels say which colour cell is used and what the glyph's 0 pixels become; the window (Y 9-18 x 16 bytes from X 8:
; SCREEN 8 a byte a pixel, SCREEN 5 two) := $0F; GRPACX ($FCB7) / GRPACY ($FCB9); LOGOPR ($FB02); the call; the
; command engine waited for; then GRPACX / GRPACY, A / F / IFF, the window.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 176-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4/+5 GRPACX after, +6/+7 GRPACY after, +8..+15 0, +16..+175 the window (10 x 16).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubgpp.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0600
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
GRPACX  equ     $FCB7
LOGOPR  equ     $FB02
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920                   ; SCRMOD, A, X (2), Y (2), LOGOPR

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $05FF
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
                ld      bc, 7
                ldir
                ld      (tp), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      a, $05
                ld      ($F3E9), a
                ld      a, $03
                ld      ($F3EA), a
                ld      a, $0A
                ld      ($F3F2), a
                ld      c, $40
                call    win
                ld      hl, cur+2
                ld      de, GRPACX
                ld      bc, 4
                ldir
                ld      a, (cur+6)
                ld      (LOGOPR), a
                ld      a, (cur+1)
                ld      ix, $0089
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
                ld      hl, GRPACX
                ld      bc, 4
                ldir
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ld      (ptr), hl
                ld      c, $00
                call    win
                ld      hl, (ptr)
                ld      bc, 160
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

; the window, Y 9-18 x 16 bytes from X 8 (SCREEN 8: Y x 256 + 8; SCREEN 5 / 2: Y x 128 + 4), write (C $40: $0F) or
; read (C $00: into (ptr) onwards)
win:
                ld      b, 9
                ld      de, (ptr)
w_line:
                push    bc
                ld      a, (cur)
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
                add     hl, hl
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                jr      w_set
w_s8:
                ld      h, a
                ld      l, 8
w_set:
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
w_b:
                ld      a, c
                or      a
                jr      z, w_rd
                ld      a, $0F
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
                cp      19
                jr      nz, w_line
                ret

cases:
                db      8, $41
                dw      10, 10
                db      0   ; 0 'A' PSET
                db      8, $41
                dw      10, 10
                db      8   ; 1 'A' TIMP
                db      5, $41
                dw      10, 10
                db      0   ; 2 'A' SCREEN 5
                db      8, $0D
                dw      10, 10
                db      0   ; 3 CR
                db      8, $41
                dw      250, 10
                db      0   ; 4 'A' at X 250
                db      8, $41
                dw      10, 207
                db      0   ; 5 'A' at Y 207
                db      2, $41
                dw      10, 10
                db      0   ; 6 'A' SCREEN 2
                db      $EE

                ds      $8000 - $, $FF
