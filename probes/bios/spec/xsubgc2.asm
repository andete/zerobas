; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBGC2 -- D-MSX2SPEC goldfish pass 1 (test writer), the separating cases for docs/msx2/sub/{MAPXYC,SETC,READC,
; SETATR,SCALXY}.md that xsubgc.asm could not tell apart. Sub-ROM entries through EXTROM: $0091 MAPXYC (BC = X,
; DE = Y), $0099 SETATR (A), $009D SETC, $0095 READC (-> A), $008D SCALXY (BC, DE -> BC, DE, carry).
; Four sections, each case after its own CHGMOD (main $005F) and DI:
;   STATE   per SCRMOD 2-8: LOGOPR ($FB02), ACPAGE ($FAF6), DPPAGE ($FAF5), GRPCGP ($F3CB), MLTCGP ($F3D5) as CHGMOD
;           leaves them, then the whole VDP state (@vdpfull: R#0-R#63, S#0-S#15, VRAM pointer, palette) -- R#9's LN
;           and S#2's CE are the cells the pages' preconditions need.
;   SETATR  FORCLR ($F3E9) := 7, ATRBYT ($F3F2) := 5 by hand, then SETATR A: ATRBYT and F after (the carry).
;   POINTS  GRPCGP / MLTCGP planted when the table says so, ATRBYT and LOGOPR ($FB02) planted, entry A $5A and F from the table, MAPXYC;
;           CLOC / CMASK / F recorded; the byte at the table's address (or at CLOC when the address is $FFFF; no VRAM
;           access at all when it is $FFFE) planted, READC (no SETC before it: the planted pixel), the byte re-read,
;           SETC, the byte read, READC again, ATRBYT.
;   SCALXY  entry A $5A and F from the table: BC / DE / F / A after. A table SCRMOD with bit 7 set: after CHGMOD,
;           R#9 := $00 through WRTVDP (main $0047) -- LN 0, 192 lines (and NTSC on the NMS 8250, irrelevant here).
; NOTE: the POINTS table plants GRPCGP $0800 / MLTCGP $1000 in its 16th case, and CHGMOD does not reset either cell:
; every later SCREEN 2 / 3 / 4 point runs with those values (the CLOCs show MLTCGP's $1000 as the base).
; The capture (CAP = C001; @cap names DONE = C000): +0 $A5 when finished, +1 / +2 / +3 / +4 the STATE / SETATR /
; POINTS / SCALXY counts; the records from +5 in that order:
;   STATE  122 bytes: SCRMOD, LOGOPR, ACPAGE, DPPAGE, GRPCGP (2), MLTCGP (2), then the 114-byte @vdpfull block.
;   SETATR 4 bytes: SCRMOD, A in, ATRBYT after, F after.
;   POINT  16 bytes: SCRMOD, CLOC (2), CMASK, F after MAPXYC, READC #1 (planted pixel), the byte after SETC, READC #2,
;          ATRBYT at the end, the address used (2), the byte after READC #1 (before SETC), LOGOPR at the end, 0 x 3.
;   SCALXY 8 bytes: SCRMOD (bit 7 = LN forced 0), BC (2), DE (2), F, A, F in.
; Decoder: scratchpad/xsubgc2_decode.py RUNFILE [--side ref|ours].
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubgc2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0A00
; @vdpfull E8F0 E900
; @timeout 180

CHGMOD  equ     $005F
WRTVDP  equ     $0047
EXTROM  equ     $015F
CLOC    equ     $F92A
CMASK   equ     $F92C
ATRBYT  equ     $F3F2
FORCLR  equ     $F3E9
GRPCGP  equ     $F3CB
MLTCGP  equ     $F3D5
LOGOPR  equ     $FB02
ACPAGE  equ     $FAF6
DPPAGE  equ     $FAF5
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
addr    equ     $E90A
rec     equ     $E90C
cur     equ     $E920                   ; the current table entry (up to 14 bytes)

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $09FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      hl, CAP+5
                ld      (ptr), hl

; ---------------------------------------------------------------- STATE
                ld      hl, modes
                ld      (tp), hl
st_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, st_done
                inc     hl
                ld      (tp), hl
                ld      (cur), a
                call    CHGMOD
                di
                ld      de, (ptr)
                ld      a, (cur)
                ld      (de), a
                inc     de
                ld      a, (LOGOPR)
                ld      (de), a
                inc     de
                ld      a, (ACPAGE)
                ld      (de), a
                inc     de
                ld      a, (DPPAGE)
                ld      (de), a
                inc     de
                ld      hl, (GRPCGP)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ex      de, hl
                ld      hl, (MLTCGP)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (SNAPP), hl
                ld      bc, 114
                add     hl, bc
                ld      (ptr), hl
                call    SNAPFN
                ld      hl, CAP+1
                inc     (hl)
                jr      st_next
st_done:

; ---------------------------------------------------------------- SETATR
                ld      hl, satab
                ld      (tp), hl
sa_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, sa_done
                ld      de, cur
                ld      bc, 2
                ldir
                ld      (tp), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      a, 7
                ld      (FORCLR), a
                ld      a, 5
                ld      (ATRBYT), a
                ld      a, (cur+1)
                ld      ix, $0099               ; SETATR
                call    EXTROM
                di
                push    af
                pop     bc                      ; C = F
                ld      hl, (ptr)
                ld      a, (cur)
                ld      (hl), a
                inc     hl
                ld      a, (cur+1)
                ld      (hl), a
                inc     hl
                ld      a, (ATRBYT)
                ld      (hl), a
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (ptr), hl
                ld      hl, CAP+2
                inc     (hl)
                jr      sa_next
sa_done:

; ---------------------------------------------------------------- POINTS
                ld      hl, pts
                ld      (tp), hl
p_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, p_done
                ld      de, cur
                ld      bc, 15
                ldir
                ld      (tp), hl
                ld      hl, (ptr)
                ld      (rec), hl
                ld      a, (cur)
                call    CHGMOD
                di
                ld      hl, (cur+10)            ; GRPCGP plant
                ld      a, h
                and     l
                inc     a
                jr      z, p_nog
                ld      (GRPCGP), hl
p_nog:
                ld      hl, (cur+12)            ; MLTCGP plant
                ld      a, h
                and     l
                inc     a
                jr      z, p_nom
                ld      (MLTCGP), hl
p_nom:
                ld      a, (cur+8)
                ld      (ATRBYT), a
                ld      a, (cur+14)
                ld      (LOGOPR), a
                ld      bc, (cur+1)
                ld      de, (cur+3)
                ld      ix, $0091               ; MAPXYC
                ld      a, (cur+9)
                ld      l, a
                ld      h, $5A
                push    hl
                pop     af
                call    EXTROM
                di
                push    af
                pop     bc                      ; C = F
                ld      hl, (rec)
                ld      a, (cur)
                ld      (hl), a                 ; +0
                inc     hl
                ld      de, (CLOC)
                ld      (hl), e                 ; +1
                inc     hl
                ld      (hl), d                 ; +2
                inc     hl
                ld      a, (CMASK)
                ld      (hl), a                 ; +3
                inc     hl
                ld      (hl), c                 ; +4
                ; the address
                ld      hl, (cur+5)
                ld      a, l
                and     h
                inc     a
                jr      nz, p_ad
                ld      hl, (CLOC)              ; $FFFF: at CLOC
p_ad:
                ld      (addr), hl
                ex      de, hl
                ld      hl, (rec)
                ld      bc, 9
                add     hl, bc
                ld      (hl), e                 ; +9
                inc     hl
                ld      (hl), d                 ; +10
                call    novram
                jr      z, p_np
                ld      hl, (addr)
                ld      c, $40
                call    vset
                ld      a, (cur+7)
                out     ($98), a
p_np:
                ld      ix, $0095               ; READC #1
                call    EXTROM
                di
                ld      hl, (rec)
                ld      bc, 5
                add     hl, bc
                ld      (hl), a                 ; +5
                ld      bc, 11 - 5
                add     hl, bc
                call    rdbyte
                ld      (hl), a                 ; +11
                ld      ix, $009D               ; SETC
                call    EXTROM
                di
                ld      hl, (rec)
                ld      bc, 6
                add     hl, bc
                call    rdbyte
                ld      (hl), a                 ; +6
                ld      ix, $0095               ; READC #2
                call    EXTROM
                di
                ld      hl, (rec)
                ld      bc, 7
                add     hl, bc
                ld      (hl), a                 ; +7
                inc     hl
                ld      a, (ATRBYT)
                ld      (hl), a                 ; +8
                ld      bc, 12 - 8
                add     hl, bc
                ld      a, (LOGOPR)
                ld      (hl), a                 ; +12
                ld      hl, (rec)
                ld      bc, 16
                add     hl, bc
                ld      (ptr), hl
                ld      hl, CAP+3
                inc     (hl)
                jp      p_next
p_done:

; ---------------------------------------------------------------- SCALXY
                ld      hl, scal
                ld      (tp), hl
s_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 6
                ldir
                ld      (tp), hl
                ld      a, (cur)
                and     $7F
                call    CHGMOD
                di
                ld      a, (cur)
                bit     7, a
                jr      z, s_ln
                ld      bc, $0009               ; SCRMOD bit 7: R#9 := $00 (LN 0) through WRTVDP
                call    WRTVDP
                di
s_ln:
                ld      bc, (cur+1)
                ld      de, (cur+3)
                ld      ix, $008D               ; SCALXY
                ld      a, (cur+5)
                ld      l, a
                ld      h, $5A
                push    hl
                pop     af
                call    EXTROM
                di
                push    af
                push    de
                ld      hl, (ptr)
                ld      a, (cur)
                ld      (hl), a
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (hl), b
                inc     hl
                pop     de
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                pop     de                      ; D = A, E = F
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      a, (cur+5)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                ld      hl, CAP+4
                inc     (hl)
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

; Z set when the case's table address is $FFFE (no VRAM access)
novram:
                ld      hl, (cur+5)
                ld      a, l
                cp      $FE
                ret     nz
                ld      a, h
                cp      $FF
                ret

; A := the byte at (addr), or 0 when the case has no VRAM access; HL kept
rdbyte:
                push    hl
                call    novram
                pop     hl
                ld      a, 0
                ret     z
                push    hl
                ld      hl, (addr)
                ld      c, $00
                call    vset
                pop     hl
                in      a, ($98)
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

modes:
                db      2, 3, 4, 5, 6, 7, 8, $EE

satab:                                  ; SCRMOD, A
                db      6, $03,  6, $04,  6, $0B,  6, $0F,  6, $10
                db      5, $0F,  5, $10,  5, $FF
                db      7, $10
                db      8, $10,  8, $80,  8, $FF
                db      2, $0F,  2, $10
                db      6, $01,  6, $02,  6, $0E          ; (appended after the first run) the S6 transform
                db      $EE

; SCRMOD, X, Y, address ($FFFF = CLOC, $FFFE = none), the byte planted, ATRBYT, entry F, GRPCGP, MLTCGP ($FFFF = left)
pt              macro   pm, px, py, pad, ppre, patr, pf, pgc, pmc, plop
                db      pm
                dw      px, py, pad
                db      ppre, patr, pf
                dw      pgc, pmc
                db      plop
                endm
pts:
                ; READC on a planted pixel / SETC replace vs OR (SCREEN 5)
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      5, 11, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      5, 11, 7, $0385, $45, $1A, $FF, $FFFF, $FFFF, 0
                ; SCREEN 6: each 2-bit field of $1B; ATRBYT 5 over the field
                pt      6, 0, 7, $0380, $1B, $01, $FF, $FFFF, $FFFF, 0
                pt      6, 1, 7, $0380, $1B, $01, $FF, $FFFF, $FFFF, 0
                pt      6, 2, 7, $0380, $1B, $01, $FF, $FFFF, $FFFF, 0
                pt      6, 3, 7, $0380, $1B, $01, $FF, $FFFF, $FFFF, 0
                pt      6, 1, 7, $0380, $00, $05, $FF, $FFFF, $FFFF, 0
                ; SCREEN 7 past X 255; SCREEN 8 the byte
                pt      7, 300, 7, $0796, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      7, 301, 7, $0796, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      8, 9, 9, $0909, $C3, $5A, $FF, $FFFF, $FFFF, 0
                ; SCREEN 2 at CLOC away from $0000; entry F 00 / FF
                pt      2, 10, 20, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 255, 191, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 0, $FFFF, $A5, $09, $00, $FFFF, $FFFF, 0
                pt      2, 0, 0, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                ; SCREEN 2 base: GRPCGP and MLTCGP planted apart
                pt      2, 0, 0, $FFFF, $A5, $09, $FF, $0800, $1000, 0
                pt      2, 10, 20, $FFFF, $A5, $09, $FF, $0800, $1000, 0
                ; SCREEN 2 layout steps and wraps
                pt      2, 2, 0, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 1, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 4, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 8, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 64, 0, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 128, 0, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 48, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      2, 0, 64, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                ; SCREEN 3 / 4
                pt      3, 10, 20, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      3, 0, 0, $FFFF, $A5, $09, $FF, $0800, $1000, 0
                pt      4, 10, 20, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 0
                pt      4, 0, 0, $FFFF, $A5, $09, $FF, $0800, $1000, 0
                ; MAPXYC's F: entry F 00 / FF
                pt      5, 10, 20, $0A05, $00, $0B, $00, $FFFF, $FFFF, 0
                pt      5, 10, 20, $0A05, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      6, 10, 20, $0A02, $00, $03, $00, $FFFF, $FFFF, 0
                pt      6, 10, 20, $0A02, $00, $03, $FF, $FFFF, $FFFF, 0
                pt      8, 10, 20, $140A, $00, $0B, $00, $FFFF, $FFFF, 0
                pt      8, 10, 20, $140A, $00, $0B, $FF, $FFFF, $FFFF, 0
                ; MAPXYC out of range (CLOC / CMASK only)
                pt      5, 300, 7, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      5, 511, 211, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      5, 10, $0107, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      5, 10, 255, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      8, 300, 7, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                pt      7, 600, 7, $FFFE, $00, $0B, $FF, $FFFF, $FFFF, 0
                ; appended after the second run: LOGOPR planted (SETC SC-05 / SC-06 / SC-13)
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 1
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 2
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 3
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 4
                pt      5, 10, 7, $0385, $A5, $00, $FF, $FFFF, $FFFF, 8
                pt      5, 10, 7, $0385, $A5, $09, $FF, $FFFF, $FFFF, 8
                pt      8, 9, 9, $0909, $C3, $5A, $FF, $FFFF, $FFFF, 3
                pt      2, 10, 20, $FFFF, $A5, $09, $FF, $FFFF, $FFFF, 3
                db      $EE

; SCRMOD, X, Y, entry F
sc              macro   sm, sx, sy, sf
                db      sm
                dw      sx, sy
                db      sf
                endm
scal:
                sc      5, 511, 5, $00
                sc      5, 256, 5, $00
                sc      5, 600, 5, $00
                sc      5, 5, 300, $00
                sc      5, -5, 5, $00
                sc      5, 5, -5, $00
                sc      5, 600, 300, $00
                sc      5, 5, 5, $00
                sc      5, 255, 211, $00
                sc      5, 255, 212, $00
                sc      5, $7FFF, 5, $00
                sc      5, 5, 191, $00
                sc      5, 5, 192, $00
                sc      5, 5, 5, $FF
                sc      5, 600, 5, $FF
                sc      6, 511, 5, $00
                sc      6, 512, 5, $00
                sc      6, $7FFF, 5, $00
                sc      6, 600, 5, $00
                sc      6, 5, 300, $00
                sc      6, -5, 5, $00
                sc      6, 5, -5, $00
                sc      6, 5, 5, $00
                sc      7, 511, 5, $00
                sc      7, 512, 5, $00
                sc      7, $7FFF, 5, $00
                sc      7, 600, 5, $00
                sc      8, 256, 5, $00
                sc      8, 600, 5, $00
                sc      8, 5, 300, $00
                sc      8, -5, 5, $00
                sc      2, 254, 5, $00
                sc      2, 256, 5, $00
                sc      2, 5, 191, $00
                sc      2, 5, 192, $00
                sc      2, -5, 5, $00
                sc      2, 5, -5, $00
                sc      2, 5, 5, $00
                sc      2, 300, 250, $00
                sc      3, 300, 250, $00
                sc      3, 100, 100, $00
                sc      3, 254, 5, $00
                sc      4, 300, 250, $00
                sc      4, 100, 100, $00
                ; appended after the first run: the divide / clip order (-3 rounds to 0 or to -1); LN 0
                sc      2, -3, 5, $00
                sc      2, 5, -3, $00
                sc      3, -3, 5, $00
                sc      5, -3, 5, $00
                sc      $85, 5, 191, $00
                sc      $85, 5, 192, $00
                sc      $85, 5, 212, $00
                sc      $86, 5, 192, $00
                db      $EE

                ds      $8000 - $, $FF
