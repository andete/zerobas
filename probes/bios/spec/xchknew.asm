; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCHKNEW -- D-MSX2SPEC, docs/msx2/main/CHKNEW.md: the main ROM's CHKNEW ($0165), unpublished, on the MSX2 / MSX2+
; references. Per case (table `cases`): LINL40 := the width, CHGMOD ($005F) to the mode (or none), DI; then the
; overrides: SCRMOD ($FCAF) := a value, and / or RG0SAV / RG1SAV ($F3DF / $F3E0) := the values CHGMOD left in SCREEN 5
; (or in SCREEN 1) -- saved at INIT -- only the save cells, the VDP itself keeps the mode CHGMOD set; every register
; from the entry table (A $A7, F per case, IX / IY / alternates too); DI or EI; CALL $0165.
; The capture (CAP = C001): +0 case count, +1 RG0SAV / +2 RG1SAV after CHGMOD 5, +3 / +4 after CHGMOD 1, +5 $5A;
; records of 32 bytes from +16: +0 case, +1 SCRMOD at the call, +2 RG0SAV, +3 RG1SAV at the call, +4..+29 the dump (as
; xextrom.asm: [($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL', DE', BC', AF', IY, IX, HL, DE, BC, AF), +30 SCRMOD after,
; +31 $5A.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchknew.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells. No ROM byte read.
;
; @cap C000
; @caplen 0500
; @timeout 120

CHGMOD  equ     $005F
CHKNEW  equ     $0165
SCRMOD  equ     $FCAF
RG0SAV  equ     $F3DF
RG1SAV  equ     $F3E0
LINL40  equ     $F3AE
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E906
CIDX    equ     $E90B
TP      equ     $E90C
ENTBL   equ     $E910
RDUMP   equ     $E960
RDEND   equ     $E97A
CUR     equ     $E9E0

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $04FE
                ld      (hl), 0
                ldir
                ld      a, 40
                ld      (LINL40), a
                ld      a, 5
                call    CHGMOD
                di
                ld      a, (RG0SAV)
                ld      (CAP+1), a
                ld      a, (RG1SAV)
                ld      (CAP+2), a
                ld      a, 1
                call    CHGMOD
                di
                ld      a, (RG0SAV)
                ld      (CAP+3), a
                ld      a, (RG1SAV)
                ld      (CAP+4), a
                ld      a, $5A
                ld      (CAP+5), a
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, cases
                ld      (TP), hl
                xor     a
                ld      (CIDX), a
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 7
                ldir
                ld      (TP), hl
                ; CUR: id, mode (FF none), width, SCRMOD override (FF none), RG save override (0 none, 5, 1), F, iff
                ld      a, (CUR+2)
                ld      (LINL40), a
                ld      a, (CUR+1)
                cp      $FF
                jr      z, c_nm
                call    CHGMOD
c_nm:
                di
                ld      a, (CUR+3)
                cp      $FF
                jr      z, c_ns
                ld      (SCRMOD), a
c_ns:
                ld      a, (CUR+4)
                or      a
                jr      z, c_nr
                ld      hl, (CAP+1)
                cp      5
                jr      z, c_r
                ld      hl, (CAP+3)
c_r:
                ld      (RG0SAV), hl            ; RG0SAV, RG1SAV
c_nr:
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+5)
                ld      (ENTBL+12), a
                ld      de, (PTR)
                ld      a, (CIDX)
                ld      (de), a
                inc     de
                ld      a, (SCRMOD)
                ld      (de), a
                inc     de
                ld      a, (RG0SAV)
                ld      (de), a
                inc     de
                ld      a, (RG1SAV)
                ld      (de), a
                ld      a, (CUR+6)
                or      a
                jr      z, c_di
                ei
c_di:
                ld      (E_SP), sp
                ld      sp, ENTBL
                pop     ix
                pop     iy
                pop     af
                ex      af, af'
                pop     bc
                pop     de
                pop     hl
                exx
                pop     af
                pop     bc
                pop     de
                pop     hl
                ld      sp, (E_SP)
                call    CHKNEW
                ld      (R_SP), sp
                ld      sp, RDEND
                push    af
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ex      af, af'
                push    af
                ex      af, af'
                exx
                push    bc
                push    de
                push    hl
                exx
                ld      a, i
                push    af
                ld      a, i
                push    af
                in      a, ($A8)
                ld      h, a
                ld      a, ($FFFF)
                cpl
                ld      l, a
                push    hl
                ld      sp, (R_SP)
                di
                ld      hl, (PTR)
                ld      bc, 4
                add     hl, bc
                ex      de, hl
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      a, (SCRMOD)
                ld      (de), a
                inc     de
                ld      a, $5A
                ld      (de), a
                ld      hl, (PTR)
                ld      bc, 32
                add     hl, bc
                ld      (PTR), hl
                ld      a, (CIDX)
                inc     a
                ld      (CIDX), a
                ld      (CAP), a
                jp      c_next
finish:
                ld      a, 40
                ld      (LINL40), a
                xor     a
                call    CHGMOD
                di
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

ent_src:
                dw      $5A6B, $1A2B, $3C4D, $5E6F, $7081, $92A3, $A700, $B1C2, $4E5F, $9876

; id, mode, width, SCRMOD override, RG save override, F, iff
cases:
                db      0, 0, 40, $FF, 0, $00, 0
                db      1, 1, 40, $FF, 0, $00, 0
                db      2, 2, 40, $FF, 0, $00, 0
                db      3, 3, 40, $FF, 0, $00, 0
                db      4, 4, 40, $FF, 0, $00, 0
                db      5, 5, 40, $FF, 0, $00, 0
                db      6, 6, 40, $FF, 0, $00, 0
                db      7, 7, 40, $FF, 0, $00, 0
                db      8, 8, 40, $FF, 0, $00, 0
                db      9, 0, 40, $FF, 0, $FF, 0
                db      10, 1, 40, $FF, 0, $FF, 0
                db      11, 2, 40, $FF, 0, $FF, 0
                db      12, 3, 40, $FF, 0, $FF, 0
                db      13, 4, 40, $FF, 0, $FF, 0
                db      14, 5, 40, $FF, 0, $FF, 0
                db      15, 6, 40, $FF, 0, $FF, 0
                db      16, 7, 40, $FF, 0, $FF, 0
                db      17, 8, 40, $FF, 0, $FF, 0
                db      18, 0, 80, $FF, 0, $00, 0       ; SCREEN 0 width 80
                db      19, 1, 40, 5, 0, $00, 0         ; VDP SCREEN 1, SCRMOD 5
                db      20, 5, 40, 1, 0, $00, 0         ; VDP SCREEN 5, SCRMOD 1
                db      21, 1, 40, $FF, 5, $00, 0       ; SCREEN 1, the save cells in SCREEN 5's
                db      22, 5, 40, $FF, 1, $00, 0       ; SCREEN 5, the save cells in SCREEN 1's
                db      23, 1, 40, 9, 0, $00, 0
                db      24, 1, 40, $10, 0, $00, 0
                db      25, 1, 40, $FF, 0, $00, 0       ; (SCRMOD override $FF = none: SCREEN 1 again)
                db      26, 1, 40, 10, 0, $00, 0
                db      27, 1, 40, 11, 0, $00, 0
                db      28, 1, 40, 12, 0, $00, 0
                db      29, 5, 40, $FF, 0, $00, 1       ; SCREEN 5, EI
                db      30, 1, 40, $FF, 0, $00, 1       ; SCREEN 1, EI
                db      31, 1, 40, 4, 0, $00, 0         ; VDP SCREEN 1, SCRMOD 4
                db      32, 1, 40, $80, 0, $00, 0
                db      $EE

                ds      $8000 - $, $FF
