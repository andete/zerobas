; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBGC -- D-MSX2SPEC, docs/msx2/sub/{MAPXYC,SETC,READC,SETATR,SCALXY}.md and concepts/graphics-cursor.md: the
; sub-ROM's graphics-cursor core through EXTROM ($0091 MAPXYC BC = X, DE = Y; $0099 SETATR A; $009D SETC; $0095
; READC -> A; $008D SCALXY BC, DE -> BC, DE, carry) on the MSX2 / MSX2+ references.
; Points (the table `pts`: SCRMOD, X, Y, the byte's address as the mode's layout gives it): CHGMOD (main $005F),
; interrupts off, that byte := $00 by hand, SETATR A $0B, MAPXYC, then CLOC / CMASK recorded, SETC, READC, the byte
; read back. SCALXY (the table `scal`: SCRMOD, X, Y): BC / DE / F after.
; The capture (CAP = C001): +0 $A5 when finished, +1 the point count, +2 the SCALXY count; per point a 16-byte record
; from +3: +0 SCRMOD, +1/+2 X, +3/+4 Y, +5/+6 CLOC ($F92A), +7 CMASK ($F92C), +8 READC's A, +9 the byte, +10 ATRBYT
; ($F3F2) after SETATR, +11 F after MAPXYC, +12..+15 0; then per SCALXY case 8 bytes: SCRMOD, BC (2), DE (2), F, 0, 0.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubgc.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0300
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
CLOC    equ     $F92A
CMASK   equ     $F92C
ATRBYT  equ     $F3F2
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cnt     equ     $E908
cur     equ     $E920                   ; SCRMOD, X (2), Y (2), the address (2)
fsave   equ     $E930

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $02FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+3
                ld      (ptr), hl
                ld      hl, pts
                ld      (tp), hl
                xor     a
                ld      (cnt), a
p_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, p_done
                ld      de, cur
                ld      bc, 7
                ldir
                ld      (tp), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      hl, (cur+5)
                ld      c, $40
                call    vset
                xor     a
                out     ($98), a
                ld      a, $0B
                ld      ix, $0099               ; SETATR
                call    EXTROM
                di
                ld      bc, (cur+1)
                ld      de, (cur+3)
                ld      ix, $0091               ; MAPXYC
                call    EXTROM
                di
                push    af
                pop     hl
                ld      a, l
                ld      (fsave), a
                ld      de, (ptr)
                ld      hl, cur
                ld      bc, 5
                ldir
                ld      hl, (CLOC)
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                ld      a, (CMASK)
                ld      (de), a
                inc     de
                ld      (ptr), de
                ld      ix, $009D               ; SETC
                call    EXTROM
                di
                ld      ix, $0095               ; READC
                call    EXTROM
                di
                ld      de, (ptr)
                ld      (de), a
                inc     de
                push    de
                ld      hl, (cur+5)
                ld      c, $00
                call    vset
                pop     de
                in      a, ($98)
                ld      (de), a
                inc     de
                ld      a, (ATRBYT)
                ld      (de), a
                inc     de
                ld      a, (fsave)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 8
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cnt)
                inc     a
                ld      (cnt), a
                ld      (CAP+1), a
                jp      p_next
p_done:
                ld      hl, scal
                ld      (tp), hl
                xor     a
                ld      (cnt), a
s_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jr      z, finish
                ld      de, cur
                ld      bc, 5
                ldir
                ld      (tp), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      bc, (cur+1)
                ld      de, (cur+3)
                ld      ix, $008D               ; SCALXY
                call    EXTROM
                di
                push    af
                push    de
                push    bc
                ld      de, (ptr)
                ld      a, (cur)
                ld      (de), a
                inc     de
                pop     hl
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                pop     hl
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                pop     hl
                ld      a, l
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 8
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cnt)
                inc     a
                ld      (cnt), a
                ld      (CAP+2), a
                jr      s_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

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

pts:
                db      2
                dw      0, 0, $0000   ; SCREEN 2 (0,0)
                db      2
                dw      1, 0, $0000   ; SCREEN 2 (1,0)
                db      2
                dw      10, 20, $020C   ; SCREEN 2 (10,20)
                db      2
                dw      255, 191, $17FF   ; SCREEN 2 (255,191)
                db      5
                dw      0, 0, $0000   ; SCREEN 5 (0,0)
                db      5
                dw      1, 0, $0000   ; SCREEN 5 (1,0)
                db      5
                dw      10, 20, $0A05   ; SCREEN 5 (10,20)
                db      5
                dw      255, 211, $69FF   ; SCREEN 5 (255,211)
                db      6
                dw      0, 0, $0000   ; SCREEN 6 (0,0)
                db      6
                dw      1, 0, $0000   ; SCREEN 6 (1,0)
                db      6
                dw      3, 0, $0000   ; SCREEN 6 (3,0)
                db      6
                dw      10, 20, $0A02   ; SCREEN 6 (10,20)
                db      6
                dw      511, 211, $69FF   ; SCREEN 6 (511,211)
                db      7
                dw      0, 0, $0000   ; SCREEN 7 (0,0)
                db      7
                dw      1, 0, $0000   ; SCREEN 7 (1,0)
                db      7
                dw      10, 20, $1405   ; SCREEN 7 (10,20)
                db      7
                dw      511, 211, $D3FF   ; SCREEN 7 (511,211)
                db      8
                dw      0, 0, $0000   ; SCREEN 8 (0,0)
                db      8
                dw      1, 0, $0001   ; SCREEN 8 (1,0)
                db      8
                dw      10, 20, $140A   ; SCREEN 8 (10,20)
                db      8
                dw      255, 211, $D3FF   ; SCREEN 8 (255,211)
                db      $EE
scal:
                db      2
                dw      $012C, $00FA
                db      2
                dw      $FFFB, $FFFB
                db      2
                dw      $0064, $0064
                db      5
                dw      $012C, $00FA
                db      5
                dw      $FFFB, $FFFB
                db      5
                dw      $0064, $0064
                db      6
                dw      $012C, $00FA
                db      6
                dw      $FFFB, $FFFB
                db      6
                dw      $0064, $0064
                db      7
                dw      $012C, $00FA
                db      7
                dw      $FFFB, $FFFB
                db      7
                dw      $0064, $0064
                db      8
                dw      $012C, $00FA
                db      8
                dw      $FFFB, $FFFB
                db      8
                dw      $0064, $0064
                db      $EE

                ds      $8000 - $, $FF
