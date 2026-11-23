; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XMODE -- D-MSX2SPEC, docs/msx2/sub/{CHGMOD,INITXT,INIT32,INIGRP,INIMLT,SETTXT,SETT32,SETGRP,SETMLT,SETPAG,CHGMDP}.md
; and concepts/screen-modes.md: the sub-ROM screen-mode calls through EXTROM, on the MSX2 / MSX2+ references.
; Per case (the table `cases`: the entry, A, DPPAGE, ACPAGE, 1 = run in SCREEN 5 first): interrupts off; CHGMOD
; (main $005F) to SCREEN 0 (or 5); RG0SAV-RG7SAV ($F3DF-$F3E6) := $A5 (bits 4 / 6 of RG0SAV clear: no line
; interrupt); DPPAGE / ACPAGE where given; the call with A, BC $1357, DE $9BDF, HL $2468; then the record.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 96-byte record from +2:
;   +0 A, +1 F after, +2 IFF after (1 on), +3 the case, +4..+31 VDP R#0-R#27 (the debugger), +32..+39 $F3DF-$F3E6,
;   +40..+61 $FFE7-$FFFC, +62 SCRMOD ($FCAF), +63 OLDSCR ($FCB0), +64 LINLEN ($F3B0), +65 CRTCNT ($F3B1),
;   +66..+75 NAMBAS CGPBAS PATBAS ATRBAS (and the 5th word) $F922-$F92B, +76 DPPAGE, +77 ACPAGE, +78..+95 0.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xmode.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's registers read by the debugger.
;
; @cap C000
; @caplen 0B00
; @vdpfull E8F0 E900
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
DPPAGE  equ     $FAF5
ACPAGE  equ     $FAF6
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920
SNAPB   equ     $E000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0AFF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                inc     hl
                or      (hl)
                dec     hl
                jp      z, finish
                ld      de, cur
                ld      bc, 6
                ldir
                ld      (tp), hl
                ld      a, (cur+5)
                or      a
                ld      a, 0
                jr      z, c_m
                ld      a, 5
c_m:
                call    CHGMOD
                di
                ld      hl, $F3DF
                ld      b, 8
c_g:
                ld      (hl), $A5
                inc     hl
                djnz    c_g
                ld      a, (cur+3)
                ld      (DPPAGE), a
                ld      a, (cur+4)
                ld      (ACPAGE), a
                ld      ix, (cur)
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      a, (cur+2)
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
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ld      de, (ptr)
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+2)
                ld      (de), a
                inc     de
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      hl, SNAPB
                ld      bc, 28
                ldir
                ld      hl, $F3DF
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      bc, 22
                ldir
                ld      a, ($FCAF)
                ld      (de), a
                inc     de
                ld      a, ($FCB0)
                ld      (de), a
                inc     de
                ld      a, ($F3B0)
                ld      (de), a
                inc     de
                ld      a, ($F3B1)
                ld      (de), a
                inc     de
                ld      hl, $F922
                ld      bc, 10
                ldir
                ld      a, (DPPAGE)
                ld      (de), a
                inc     de
                ld      a, (ACPAGE)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 96
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a              ; progress, so a run that dies still says how far it got
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

; the entry (sub-ROM), A, DPPAGE, ACPAGE, 1 = SCREEN 5 first
cases:
                dw      $00D1
                db      $00, 0, 0, 0   ;  0 CHGMOD 0
                dw      $00D1
                db      $01, 0, 0, 0   ;  1 CHGMOD 1
                dw      $00D1
                db      $02, 0, 0, 0   ;  2 CHGMOD 2
                dw      $00D1
                db      $03, 0, 0, 0   ;  3 CHGMOD 3
                dw      $00D1
                db      $04, 0, 0, 0   ;  4 CHGMOD 4
                dw      $00D1
                db      $05, 0, 0, 0   ;  5 CHGMOD 5
                dw      $00D1
                db      $06, 0, 0, 0   ;  6 CHGMOD 6
                dw      $00D1
                db      $07, 0, 0, 0   ;  7 CHGMOD 7
                dw      $00D1
                db      $08, 0, 0, 0   ;  8 CHGMOD 8
                dw      $00D1
                db      $09, 0, 0, 0   ;  9 CHGMOD 9
                dw      $00D1
                db      $FF, 0, 0, 0   ; 10 CHGMOD 255
                dw      $00D5
                db      $00, 0, 0, 0   ; 11 INITXT 0
                dw      $00D9
                db      $00, 0, 0, 0   ; 12 INIT32 0
                dw      $00DD
                db      $00, 0, 0, 0   ; 13 INIGRP 0
                dw      $00E1
                db      $00, 0, 0, 0   ; 14 INIMLT 0
                dw      $00E5
                db      $00, 0, 0, 0   ; 15 SETTXT 0
                dw      $00E9
                db      $00, 0, 0, 0   ; 16 SETT32 0
                dw      $00ED
                db      $00, 0, 0, 0   ; 17 SETGRP 0
                dw      $00F1
                db      $00, 0, 0, 0   ; 18 SETMLT 0
                dw      $013D
                db      $00, 1, 0, 1   ; 19 SETPAG 0
                dw      $013D
                db      $00, 0, 1, 1   ; 20 SETPAG 0
                dw      $013D
                db      $00, 3, 2, 1   ; 21 SETPAG 0
                dw      $01B5
                db      $05, 0, 0, 0   ; 22 CHGMDP 5
                dw      $00D1
                db      $0A, 0, 0, 0   ; 23 CHGMOD 10
                dw      $00D1
                db      $0B, 0, 0, 0   ; 24 CHGMOD 11
                dw      $00D1
                db      $0C, 0, 0, 0   ; 25 CHGMOD 12
                dw      0

                ds      $8000 - $, $FF
