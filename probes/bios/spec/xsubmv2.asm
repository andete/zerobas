; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBMV2 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), docs/msx2/sub/{RIGHTC,LEFTC,UPC,DOWNC,TRIGHT,TLEFTC,TUPC,
; TDOWNC}.md: the separating cases xsubmv.asm could not reach. Same method as xsubmv.asm (CHGMOD when the mode
; changes, interrupts off, the start set by MAPXYC ($0091) to (X, Y), then the move through EXTROM), plus per case
; FLAGS: bit 0 = no MAPXYC, CLOC := X and CMASK := Y's low byte planted by hand; bit 1 = R#9 LN cleared (192 lines)
; through WRTVDP ($0047) before the start and restored after; bit 2 = ACPAGE ($FAF6) := 1 for the case, 0 after.
; Entry registers: A = $A7, BC = $B0C1, DE = $D0E1, HL = $4A5B, interrupts off.
; The capture (CAP = C001): +0 $A5 when finished, +1/+2 the case count; per case a 24-byte record from +3:
;   +0 SCRMOD, +1 the entry's low byte, +2 FLAGS, +3/+4 CLOC before, +5 CMASK before, +6/+7 CLOC after,
;   +8 CMASK after, +9 A, +10 F after the move, +11/+12 X, +13/+14 Y, +15 RG9SAV ($FFE8) and +16 ACPAGE at the call,
;   +17/+18 BC, +19/+20 DE, +21/+22 HL after, +23 the F of `ld a, i` right after the return (bit 2 = IFF2).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubmv2.asm --row msx2all
; Decode: python3 scratchpad/xsubmv2_decode.py scratchpad/AE_xsubmv2_msx2.out
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells.
;
; @cap C000
; @caplen 0700
; @timeout 120

WRTVDP  equ     $0047
CHGMOD  equ     $005F
EXTROM  equ     $015F
SCRMOD  equ     $FCAF
ACPAGE  equ     $FAF6
RG9SAV  equ     $FFE8
CLOC    equ     $F92A
CMASK   equ     $F92C
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cnt     equ     $E908
r9old   equ     $E90A
cur     equ     $E920                   ; SCRMOD, FLAGS, X (2), Y (2), the entry (2)

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $06FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+3
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                ld      hl, 0
                ld      (cnt), hl
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
                ld      bc, 8
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                bit     2, a
                jr      z, no_pg
                ld      a, 1
                ld      (ACPAGE), a
no_pg:
                ld      a, (cur+1)
                bit     1, a
                jr      z, no_ln
                ld      a, (RG9SAV)
                ld      (r9old), a
                and     $7F
                ld      b, a
                ld      c, 9
                call    WRTVDP
                di
no_ln:
                ld      a, (cur+1)
                bit     0, a
                jr      nz, plant
                ld      bc, (cur+2)
                ld      de, (cur+4)
                ld      ix, $0091
                call    EXTROM
                di
                jr      started
plant:
                ld      hl, (cur+2)
                ld      (CLOC), hl
                ld      a, (cur+4)
                ld      (CMASK), a
started:
                ld      ix, (ptr)
                ld      a, (cur)
                ld      (ix+0), a
                ld      a, (cur+6)
                ld      (ix+1), a
                ld      a, (cur+1)
                ld      (ix+2), a
                ld      hl, (CLOC)
                ld      (ix+3), l
                ld      (ix+4), h
                ld      a, (CMASK)
                ld      (ix+5), a
                ld      hl, (cur+2)
                ld      (ix+11), l
                ld      (ix+12), h
                ld      hl, (cur+4)
                ld      (ix+13), l
                ld      (ix+14), h
                ld      a, (RG9SAV)
                ld      (ix+15), a
                ld      a, (ACPAGE)
                ld      (ix+16), a
                ld      ix, (cur+6)
                ld      a, $A7
                ld      bc, $B0C1
                ld      de, $D0E1
                ld      hl, $4A5B
                call    EXTROM
                push    af
                ld      a, i
                di
                push    af
                push    bc
                push    de
                push    hl
                ld      ix, (ptr)
                pop     hl
                ld      (ix+21), l
                ld      (ix+22), h
                pop     hl
                ld      (ix+19), l
                ld      (ix+20), h
                pop     hl
                ld      (ix+17), l
                ld      (ix+18), h
                pop     hl
                ld      (ix+23), l
                pop     hl
                ld      (ix+9), h
                ld      (ix+10), l
                ld      hl, (CLOC)
                ld      (ix+6), l
                ld      (ix+7), h
                ld      a, (CMASK)
                ld      (ix+8), a
                ld      a, (cur+1)
                bit     1, a
                jr      z, no_ln2
                ld      a, (r9old)
                ld      b, a
                ld      c, 9
                call    WRTVDP
                di
no_ln2:
                ld      a, (cur+1)
                bit     2, a
                jr      z, no_pg2
                xor     a
                ld      (ACPAGE), a
no_pg2:
                ld      ix, (ptr)
                ld      de, 24
                add     ix, de
                ld      (ptr), ix
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
                db      2, 0
                dw      10, 184, $00B1   ; TDOWNC S2 bottom rows (1.7)
                db      2, 0
                dw      10, 188, $00B1   ; TDOWNC S2 bottom rows (1.7)
                db      2, 0
                dw      10, 190, $00B1   ; TDOWNC S2 bottom rows (1.7)
                db      2, 0
                dw      10, 191, $00B1   ; TDOWNC S2 bottom rows (1.7)
                db      2, 0
                dw      255, 191, $00B1   ; TDOWNC S2 right of the bottom row
                db      2, 0
                dw      8, 0, $00B9   ; TUPC S2 stop: CLOC $0008? (1.6)
                db      2, 0
                dw      4, 0, $00B9   ; TUPC S2 (4,0)
                db      2, 0
                dw      0, 4, $00B9   ; TUPC S2 (0,4)
                db      2, 0
                dw      252, 20, $00A1   ; TRIGHT S2 X 252 (2.7)
                db      2, 0
                dw      251, 20, $00A1   ; TRIGHT S2 X 251
                db      2, 0
                dw      248, 20, $00A1   ; TRIGHT S2 X 248
                db      2, 0
                dw      3, 20, $00A9   ; TLEFTC S2 X 3 (2.7)
                db      2, 0
                dw      4, 20, $00A9   ; TLEFTC S2 X 4
                db      2, 0
                dw      0, 20, $00A9   ; TLEFTC S2 X 0, Y 20
                db      5, 0
                dw      10, 211, $00B1   ; control: old record 72
                db      5, 0
                dw      10, 190, $00B1   ; TDOWNC S5 the bottom: 191 vs 211 (2.1)
                db      5, 0
                dw      10, 191, $00B1   ; TDOWNC S5 the bottom: 191 vs 211 (2.1)
                db      5, 0
                dw      10, 210, $00B1   ; TDOWNC S5 the bottom: 191 vs 211 (2.1)
                db      5, 2
                dw      10, 190, $00B1   ; TDOWNC S5 with R#9 LN 0
                db      5, 2
                dw      10, 191, $00B1   ; TDOWNC S5 with R#9 LN 0
                db      5, 2
                dw      10, 211, $00B1   ; TDOWNC S5 with R#9 LN 0
                db      5, 4
                dw      10, 211, $00B1   ; TDOWNC S5 under ACPAGE 1
                db      5, 0
                dw      10, 0, $00B9   ; TUPC S5 (10,0): Y vs X/CLOC (2.4)
                db      5, 0
                dw      0, 3, $00B9   ; TUPC S5 (0,3)
                db      5, 4
                dw      10, 0, $00B9   ; TUPC S5 (10,0) under ACPAGE 1
                db      5, 0
                dw      0, 3, $00A9   ; TLEFTC S5 (0,3): X vs Y (2.3)
                db      5, 0
                dw      5, 0, $00A9   ; TLEFTC S5 (5,0)
                db      5, 0
                dw      254, 3, $00A1   ; TRIGHT S5 (254,3): equality vs pass (2.6)
                db      5, 0
                dw      250, 20, $00A1   ; TRIGHT S5 (250,20)
                db      5, 0
                dw      248, 20, $00A1   ; TRIGHT S5 (248,20)
                db      5, 0
                dw      247, 20, $00A1   ; TRIGHT S5 (247,20)
                db      5, 0
                dw      255, 200, $00A1   ; TRIGHT S5 (255,200): CMASK bit 7 set at the edge
                db      5, 1
                dw      511, 20, $00A1   ; TRIGHT S5 planted CLOC $01FF (2.5)
                db      5, 1
                dw      10, 128, $00A5   ; RIGHTC S5 planted CMASK $80 (2.2)
                db      5, 1
                dw      10, 64, $00A5   ; RIGHTC S5 planted CMASK $40
                db      5, 1
                dw      10, 128, $00AD   ; LEFTC S5 planted CMASK $80 (2.2)
                db      5, 1
                dw      10, 64, $00AD   ; LEFTC S5 planted CMASK $40
                db      5, 1
                dw      10, 128, $00A1   ; TRIGHT S5 planted CMASK $80 (2.2)
                db      5, 1
                dw      10, 64, $00A1   ; TRIGHT S5 planted CMASK $40
                db      5, 1
                dw      10, 128, $00A9   ; TLEFTC S5 planted CMASK $80 (2.2)
                db      5, 1
                dw      10, 64, $00A9   ; TLEFTC S5 planted CMASK $40
                db      5, 0
                dw      8, 20, $00BD   ; UPC S5 (8,20): AND 7 = 0 with CLOC != 0 (1.5)
                db      5, 0
                dw      16, 20, $00BD   ; UPC S5 (16,20)
                db      5, 0
                dw      0, 200, $00AD   ; LEFTC S5 (0,200): CLOC - 8 wraps (4.3)
                db      6, 0
                dw      255, 20, $00A1   ; TRIGHT S6 X 255 (2.5)
                db      6, 0
                dw      10, 191, $00B1   ; TDOWNC S6 (10,191)
                db      8, 0
                dw      10, 211, $00B1   ; TDOWNC S8 (10,211): old record 128 re-measured (1.3)
                db      8, 0
                dw      10, 191, $00B1   ; TDOWNC S8 (10,191)
                db      8, 0
                dw      10, 210, $00B1   ; TDOWNC S8 (10,210)
                db      5, 1
                dw      10, 212, $00B1   ; TDOWNC S5 planted CMASK $D4: stop at = 211 vs >= 211
                db      5, 1
                dw      10, 255, $00B1   ; TDOWNC S5 planted CMASK $FF
                db      2, 1
                dw      1839, 240, $00B1   ; TDOWNC S2 planted $072F/F0 (control)
                db      2, 1
                dw      1583, 240, $00B1   ; TDOWNC S2 planted $062F/F0: CLOC's high byte in the stop test?
                db      2, 1
                dw      3887, 240, $00B1   ; TDOWNC S2 planted $0F2F/F0
                db      2, 1
                dw      256, 240, $00B9   ; TUPC S2 planted $0100/F0: high byte 0 in the stop test?
                db      2, 1
                dw      768, 240, $00B9   ; TUPC S2 planted $0300/F0
                db      2, 1
                dw      508, 15, $00A1   ; TRIGHT S2 planted $01FC/0F: the low-byte carry rule
                db      2, 1
                dw      768, 240, $00A9   ; TLEFTC S2 planted $0300/F0: the low-byte borrow rule
                db      2, 1
                dw      772, 240, $00A9   ; TLEFTC S2 planted $0304/F0
                db      2, 0
                dw      10, 7, $00B1   ; TDOWNC S2 (10,7): a band's last row -- stop at CLOC AND 7 = 7 vs at the bottom
                db      2, 0
                dw      10, 15, $00B1   ; TDOWNC S2 (10,15)
                db      2, 1
                dw      47, 240, $00B1   ; TDOWNC S2 planted $002F/F0
                db      2, 1
                dw      46, 240, $00B1   ; TDOWNC S2 planted $002E/F0
                db      5, 0
                dw      10, 7, $00B1   ; TDOWNC S5 (10,7): the bitmap rule at a band's last row
                db      2, 1
                dw      1327, 240, $00B1   ; TDOWNC S2 planted $052F/F0: the band-step bound ($0600?)
                db      2, 1
                dw      1071, 240, $00B1   ; TDOWNC S2 planted $042F/F0
                db      5, 1
                dw      256, 20, $00A9   ; TLEFTC S5 planted $0100/14: stop at CLOC = 0 vs low byte 0; A = old vs new high byte
                db      6, 1
                dw      256, 20, $00A9   ; TLEFTC S6 planted $0100/14
                db      2, 1
                dw      516, 15, $00A9   ; TLEFTC S2 planted $0204/0F: column 0 right nibble -- stop vs the in-cell step
                db      $EE

                ds      $8000 - $, $FF
