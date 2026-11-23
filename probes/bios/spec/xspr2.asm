; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSPR2 -- D-MSX2SPEC, docs/msx2/sub/{CLRSPR,CALPAT,CALATR,GSPSIZ,GETPAT}.md: the sub-ROM sprite calls through EXTROM
; ($00F5 CLRSPR, $00F9 CALPAT, $00FD CALATR, $0101 GSPSIZ, $0105 GETPAT) on the MSX2 / MSX2+ references.
; Per case (the table `cases`: op 0 CLRSPR 1 CALPAT 2 CALATR 3 GSPSIZ 4 GETPAT, A, SCRMOD, the sprite size): CHGMOD
; (main $005F), then RG1SAV's bit 1 (the size) set or cleared in RAM only; the sprite attribute table's first 16
; bytes := $5A and PATWRK ($FC40-$FC47) := $A5 by hand; the call with A, BC $1357, DE $9BDF, HL $2468.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 32-byte record from +2:
;   +0 op, +1 A in, +2 SCRMOD, +3 size, +4 A, +5 F, +6 H, +7 L after, +8..+15 PATWRK, +16..+31 the attribute table's
;   first 16 bytes (ATRBAS, $F928) after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xspr2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0500
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
RG1SAV  equ     $F3E0
ATRBAS  equ     $F928
PATWRK  equ     $FC40
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $04FF
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
                ld      bc, 4
                ldir
                ld      (tp), hl
                ld      a, (cur+2)
                call    CHGMOD
                di
                ld      a, (RG1SAV)
                and     $FD
                ld      b, a
                ld      a, (cur+3)
                add     a, a
                or      b
                ld      (RG1SAV), a
                ld      hl, PATWRK
                ld      b, 8
pw:
                ld      (hl), $A5
                inc     hl
                djnz    pw
                ld      c, $40
                call    atr_set
                ld      b, 16
aw:
                ld      a, $5A
                out     ($98), a
                djnz    aw
                ld      a, (cur)
                ld      ix, $00F5
                or      a
                jr      z, go
                ld      ix, $00F9
                dec     a
                jr      z, go
                ld      ix, $00FD
                dec     a
                jr      z, go
                ld      ix, $0101
                dec     a
                jr      z, go
                ld      ix, $0105
go:
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      a, (cur+1)
                call    EXTROM
                di
                push    af
                pop     bc
                ld      (rsave), bc
                ld      (rsave+2), hl
                ld      de, (ptr)
                ld      hl, cur
                ld      bc, 4
                ldir
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+3)
                ld      (de), a
                inc     de
                ld      a, (rsave+2)
                ld      (de), a
                inc     de
                ld      hl, PATWRK
                ld      bc, 8
                ldir
                push    de
                ld      c, $00
                call    atr_set
                pop     de
                ld      b, 16
ar:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    ar
                ld      (ptr), de
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                jp      c_next
finish:
                ld      a, (cidx)
                ld      (CAP+1), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; ATRBAS (16-bit; A16 = 0 in SCREEN 1 / 5) for writing (C $40) or reading (C $00) through the VDP's ports
atr_set:
                ld      hl, (ATRBAS)
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

; op, A, SCRMOD, sprite size (RG1SAV bit 1)
cases:
                db      1, $00, 1, 0
                db      1, $01, 1, 0
                db      1, $1F, 1, 0
                db      1, $FF, 1, 0
                db      1, $00, 1, 1
                db      1, $01, 1, 1
                db      1, $1F, 1, 1
                db      1, $FF, 1, 1
                db      1, $00, 5, 1
                db      1, $01, 5, 1
                db      1, $1F, 5, 1
                db      1, $FF, 5, 1
                db      1, $00, 5, 0
                db      1, $01, 5, 0
                db      1, $1F, 5, 0
                db      1, $FF, 5, 0
                db      2, $00, 1, 0
                db      2, $01, 1, 0
                db      2, $1F, 1, 0
                db      2, $FF, 1, 0
                db      2, $00, 5, 0
                db      2, $01, 5, 0
                db      2, $1F, 5, 0
                db      2, $FF, 5, 0
                db      3, $00, 1, 0
                db      3, $00, 1, 1
                db      3, $00, 5, 0
                db      3, $00, 5, 1
                db      4, $41, 1, 0
                db      4, $00, 1, 0
                db      4, $FF, 1, 0
                db      0, $00, 1, 0
                db      0, $00, 1, 1
                db      0, $00, 5, 0
                db      0, $00, 5, 1
                db      $EE

                ds      $8000 - $, $FF
