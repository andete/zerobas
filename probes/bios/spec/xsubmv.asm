; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBMV -- D-MSX2SPEC, docs/msx2/sub/{RIGHTC,LEFTC,UPC,DOWNC,TRIGHT,TLEFTC,TUPC,TDOWNC}.md: the sub-ROM's graphics
; cursor moves through EXTROM, on the MSX2 / MSX2+ references. Per case (the table `cases`: SCRMOD, X, Y, the entry):
; CHGMOD (main $005F) when the mode changes, interrupts off, MAPXYC ($0091) to (X, Y), then CLOC ($F92A) / CMASK
; ($F92C) recorded, the move, CLOC / CMASK / A / F recorded. The points: an interior one, (0, 0), the right edge, the
; bottom edge, per mode (SCREEN 2, 5, 6, 8).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count (low), +2 (high); per case a 12-byte record from
;   +3: +0 SCRMOD, +1 the entry's low byte, +2/+3 CLOC before, +4 CMASK before, +5/+6 CLOC after, +7 CMASK after,
;   +8 A, +9 F after the move, +10 X low, +11 Y low.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubmv.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells.
;
; @cap C000
; @caplen 0600
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
SCRMOD  equ     $FCAF
CLOC    equ     $F92A
CMASK   equ     $F92C
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cnt     equ     $E908
cur     equ     $E920                   ; SCRMOD, X (2), Y (2), the entry (2)

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
                ld      hl, CAP+3
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                ld      hl, 0
                ld      (cnt), hl
                ld      a, $FF
                ld      (cur), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      b, a
                ld      a, (SCRMOD)
                cp      b
                ld      a, b
                push    hl
                call    nz, CHGMOD
                pop     hl
                di
                ld      de, cur
                ld      bc, 7
                ldir
                ld      (tp), hl
                ld      bc, (cur+1)
                ld      de, (cur+3)
                ld      ix, $0091
                call    EXTROM
                di
                ld      de, (ptr)
                ld      a, (cur)
                ld      (de), a
                inc     de
                ld      a, (cur+5)
                ld      (de), a
                inc     de
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
                ld      ix, (cur+5)
                ld      a, $A7
                call    EXTROM
                di
                push    af
                ld      de, (ptr)
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
                pop     bc
                ld      a, b
                ld      (de), a
                inc     de
                ld      a, c
                ld      (de), a
                inc     de
                ld      a, (cur+1)
                ld      (de), a
                inc     de
                ld      a, (cur+3)
                ld      (de), a
                inc     de
                ld      (ptr), de
                ld      hl, (cnt)
                inc     hl
                ld      (cnt), hl
                ld      (CAP+1), hl
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

cases:
                db      2
                dw      10, 20, $00A5   ; S2 (10,20) RIGHTC
                db      2
                dw      10, 20, $00AD   ; S2 (10,20) LEFTC
                db      2
                dw      10, 20, $00BD   ; S2 (10,20) UPC
                db      2
                dw      10, 20, $00B5   ; S2 (10,20) DOWNC
                db      2
                dw      10, 20, $00A1   ; S2 (10,20) TRIGHT
                db      2
                dw      10, 20, $00A9   ; S2 (10,20) TLEFTC
                db      2
                dw      10, 20, $00B9   ; S2 (10,20) TUPC
                db      2
                dw      10, 20, $00B1   ; S2 (10,20) TDOWNC
                db      2
                dw      0, 0, $00A5   ; S2 (0,0) RIGHTC
                db      2
                dw      0, 0, $00AD   ; S2 (0,0) LEFTC
                db      2
                dw      0, 0, $00BD   ; S2 (0,0) UPC
                db      2
                dw      0, 0, $00B5   ; S2 (0,0) DOWNC
                db      2
                dw      0, 0, $00A1   ; S2 (0,0) TRIGHT
                db      2
                dw      0, 0, $00A9   ; S2 (0,0) TLEFTC
                db      2
                dw      0, 0, $00B9   ; S2 (0,0) TUPC
                db      2
                dw      0, 0, $00B1   ; S2 (0,0) TDOWNC
                db      2
                dw      255, 20, $00A5   ; S2 (255,20) RIGHTC
                db      2
                dw      255, 20, $00AD   ; S2 (255,20) LEFTC
                db      2
                dw      255, 20, $00BD   ; S2 (255,20) UPC
                db      2
                dw      255, 20, $00B5   ; S2 (255,20) DOWNC
                db      2
                dw      255, 20, $00A1   ; S2 (255,20) TRIGHT
                db      2
                dw      255, 20, $00A9   ; S2 (255,20) TLEFTC
                db      2
                dw      255, 20, $00B9   ; S2 (255,20) TUPC
                db      2
                dw      255, 20, $00B1   ; S2 (255,20) TDOWNC
                db      2
                dw      10, 191, $00A5   ; S2 (10,191) RIGHTC
                db      2
                dw      10, 191, $00AD   ; S2 (10,191) LEFTC
                db      2
                dw      10, 191, $00BD   ; S2 (10,191) UPC
                db      2
                dw      10, 191, $00B5   ; S2 (10,191) DOWNC
                db      2
                dw      10, 191, $00A1   ; S2 (10,191) TRIGHT
                db      2
                dw      10, 191, $00A9   ; S2 (10,191) TLEFTC
                db      2
                dw      10, 191, $00B9   ; S2 (10,191) TUPC
                db      2
                dw      10, 191, $00B1   ; S2 (10,191) TDOWNC
                db      5
                dw      10, 20, $00A5   ; S5 (10,20) RIGHTC
                db      5
                dw      10, 20, $00AD   ; S5 (10,20) LEFTC
                db      5
                dw      10, 20, $00BD   ; S5 (10,20) UPC
                db      5
                dw      10, 20, $00B5   ; S5 (10,20) DOWNC
                db      5
                dw      10, 20, $00A1   ; S5 (10,20) TRIGHT
                db      5
                dw      10, 20, $00A9   ; S5 (10,20) TLEFTC
                db      5
                dw      10, 20, $00B9   ; S5 (10,20) TUPC
                db      5
                dw      10, 20, $00B1   ; S5 (10,20) TDOWNC
                db      5
                dw      0, 0, $00A5   ; S5 (0,0) RIGHTC
                db      5
                dw      0, 0, $00AD   ; S5 (0,0) LEFTC
                db      5
                dw      0, 0, $00BD   ; S5 (0,0) UPC
                db      5
                dw      0, 0, $00B5   ; S5 (0,0) DOWNC
                db      5
                dw      0, 0, $00A1   ; S5 (0,0) TRIGHT
                db      5
                dw      0, 0, $00A9   ; S5 (0,0) TLEFTC
                db      5
                dw      0, 0, $00B9   ; S5 (0,0) TUPC
                db      5
                dw      0, 0, $00B1   ; S5 (0,0) TDOWNC
                db      5
                dw      255, 20, $00A5   ; S5 (255,20) RIGHTC
                db      5
                dw      255, 20, $00AD   ; S5 (255,20) LEFTC
                db      5
                dw      255, 20, $00BD   ; S5 (255,20) UPC
                db      5
                dw      255, 20, $00B5   ; S5 (255,20) DOWNC
                db      5
                dw      255, 20, $00A1   ; S5 (255,20) TRIGHT
                db      5
                dw      255, 20, $00A9   ; S5 (255,20) TLEFTC
                db      5
                dw      255, 20, $00B9   ; S5 (255,20) TUPC
                db      5
                dw      255, 20, $00B1   ; S5 (255,20) TDOWNC
                db      5
                dw      10, 211, $00A5   ; S5 (10,211) RIGHTC
                db      5
                dw      10, 211, $00AD   ; S5 (10,211) LEFTC
                db      5
                dw      10, 211, $00BD   ; S5 (10,211) UPC
                db      5
                dw      10, 211, $00B5   ; S5 (10,211) DOWNC
                db      5
                dw      10, 211, $00A1   ; S5 (10,211) TRIGHT
                db      5
                dw      10, 211, $00A9   ; S5 (10,211) TLEFTC
                db      5
                dw      10, 211, $00B9   ; S5 (10,211) TUPC
                db      5
                dw      10, 211, $00B1   ; S5 (10,211) TDOWNC
                db      6
                dw      10, 20, $00A5   ; S6 (10,20) RIGHTC
                db      6
                dw      10, 20, $00AD   ; S6 (10,20) LEFTC
                db      6
                dw      10, 20, $00BD   ; S6 (10,20) UPC
                db      6
                dw      10, 20, $00B5   ; S6 (10,20) DOWNC
                db      6
                dw      10, 20, $00A1   ; S6 (10,20) TRIGHT
                db      6
                dw      10, 20, $00A9   ; S6 (10,20) TLEFTC
                db      6
                dw      10, 20, $00B9   ; S6 (10,20) TUPC
                db      6
                dw      10, 20, $00B1   ; S6 (10,20) TDOWNC
                db      6
                dw      0, 0, $00A5   ; S6 (0,0) RIGHTC
                db      6
                dw      0, 0, $00AD   ; S6 (0,0) LEFTC
                db      6
                dw      0, 0, $00BD   ; S6 (0,0) UPC
                db      6
                dw      0, 0, $00B5   ; S6 (0,0) DOWNC
                db      6
                dw      0, 0, $00A1   ; S6 (0,0) TRIGHT
                db      6
                dw      0, 0, $00A9   ; S6 (0,0) TLEFTC
                db      6
                dw      0, 0, $00B9   ; S6 (0,0) TUPC
                db      6
                dw      0, 0, $00B1   ; S6 (0,0) TDOWNC
                db      6
                dw      511, 20, $00A5   ; S6 (511,20) RIGHTC
                db      6
                dw      511, 20, $00AD   ; S6 (511,20) LEFTC
                db      6
                dw      511, 20, $00BD   ; S6 (511,20) UPC
                db      6
                dw      511, 20, $00B5   ; S6 (511,20) DOWNC
                db      6
                dw      511, 20, $00A1   ; S6 (511,20) TRIGHT
                db      6
                dw      511, 20, $00A9   ; S6 (511,20) TLEFTC
                db      6
                dw      511, 20, $00B9   ; S6 (511,20) TUPC
                db      6
                dw      511, 20, $00B1   ; S6 (511,20) TDOWNC
                db      6
                dw      10, 211, $00A5   ; S6 (10,211) RIGHTC
                db      6
                dw      10, 211, $00AD   ; S6 (10,211) LEFTC
                db      6
                dw      10, 211, $00BD   ; S6 (10,211) UPC
                db      6
                dw      10, 211, $00B5   ; S6 (10,211) DOWNC
                db      6
                dw      10, 211, $00A1   ; S6 (10,211) TRIGHT
                db      6
                dw      10, 211, $00A9   ; S6 (10,211) TLEFTC
                db      6
                dw      10, 211, $00B9   ; S6 (10,211) TUPC
                db      6
                dw      10, 211, $00B1   ; S6 (10,211) TDOWNC
                db      8
                dw      10, 20, $00A5   ; S8 (10,20) RIGHTC
                db      8
                dw      10, 20, $00AD   ; S8 (10,20) LEFTC
                db      8
                dw      10, 20, $00BD   ; S8 (10,20) UPC
                db      8
                dw      10, 20, $00B5   ; S8 (10,20) DOWNC
                db      8
                dw      10, 20, $00A1   ; S8 (10,20) TRIGHT
                db      8
                dw      10, 20, $00A9   ; S8 (10,20) TLEFTC
                db      8
                dw      10, 20, $00B9   ; S8 (10,20) TUPC
                db      8
                dw      10, 20, $00B1   ; S8 (10,20) TDOWNC
                db      8
                dw      0, 0, $00A5   ; S8 (0,0) RIGHTC
                db      8
                dw      0, 0, $00AD   ; S8 (0,0) LEFTC
                db      8
                dw      0, 0, $00BD   ; S8 (0,0) UPC
                db      8
                dw      0, 0, $00B5   ; S8 (0,0) DOWNC
                db      8
                dw      0, 0, $00A1   ; S8 (0,0) TRIGHT
                db      8
                dw      0, 0, $00A9   ; S8 (0,0) TLEFTC
                db      8
                dw      0, 0, $00B9   ; S8 (0,0) TUPC
                db      8
                dw      0, 0, $00B1   ; S8 (0,0) TDOWNC
                db      8
                dw      255, 20, $00A5   ; S8 (255,20) RIGHTC
                db      8
                dw      255, 20, $00AD   ; S8 (255,20) LEFTC
                db      8
                dw      255, 20, $00BD   ; S8 (255,20) UPC
                db      8
                dw      255, 20, $00B5   ; S8 (255,20) DOWNC
                db      8
                dw      255, 20, $00A1   ; S8 (255,20) TRIGHT
                db      8
                dw      255, 20, $00A9   ; S8 (255,20) TLEFTC
                db      8
                dw      255, 20, $00B9   ; S8 (255,20) TUPC
                db      8
                dw      255, 20, $00B1   ; S8 (255,20) TDOWNC
                db      8
                dw      10, 211, $00A5   ; S8 (10,211) RIGHTC
                db      8
                dw      10, 211, $00AD   ; S8 (10,211) LEFTC
                db      8
                dw      10, 211, $00BD   ; S8 (10,211) UPC
                db      8
                dw      10, 211, $00B5   ; S8 (10,211) DOWNC
                db      8
                dw      10, 211, $00A1   ; S8 (10,211) TRIGHT
                db      8
                dw      10, 211, $00A9   ; S8 (10,211) TLEFTC
                db      8
                dw      10, 211, $00B9   ; S8 (10,211) TUPC
                db      8
                dw      10, 211, $00B1   ; S8 (10,211) TDOWNC
                db      $EE

                ds      $8000 - $, $FF
