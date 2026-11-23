; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XRDRES -- D-MSX2SPEC, docs/msx2/main/RDRES.md / WRRES.md: the MSX2+ entries RDRES ($017A) and WRRES ($017D) on the
; FS-A1WSX. RUN ON THE MSX2+ ROW ONLY: on an MSX2 these addresses are not entries and what they run is unknown.
; Per case (table `cases`): OUT ($F4), preset by hand and IN $F4 back; every register from the entry table (A, F per
; case; IX / IY / alternates too); DI or EI; CALL the entry; the register dump; IN $F4 by hand after.
; The capture (CAP = C001): +0 case count, +1 $5A; records of 32 bytes from +16: +0 case, +1 kind (0 RDRES, 1 WRRES),
; +2 preset, +3 IN $F4 before the call, +4..+29 the dump (as xextrom.asm: [($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL',
; DE', BC', AF', IY, IX, HL, DE, BC, AF), +30 IN $F4 after, +31 $5A.
; Cases 15-20 (goldfish pass 1, 2026-11-23): WRRES with the port preset to the OTHER bit-7 reading than the one the
; call should leave (cases 5-11 and 13 all ended where they started), and kind 2 = WRRES then RDRES back to back (one
; trampoline, `call WRRES / jp RDRES`; A from the table goes to WRRES, the dump is RDRES's).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xrdres.asm --row msx2p
;
; CLEAN-ROOM: 100% own code; the published-by-MAP entries, an I/O port. No ROM byte read.
;
; @cap C000
; @caplen 0300

RDRES   equ     $017A
WRRES   equ     $017D
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
JVEC    equ     $E9F0
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
                ld      bc, $02FE
                ld      (hl), 0
                ldir
                ld      a, $5A
                ld      (CAP+1), a
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
                ld      bc, 6
                ldir
                ld      (TP), hl
                ; CUR: id, kind, preset, A, F, iff
                ld      a, $C3
                ld      (JVEC), a
                ld      hl, RDRES
                ld      a, (CUR+1)
                or      a
                jr      z, c_k
                ld      hl, WRRES
                cp      1
                jr      z, c_k
                ld      hl, wr_rd
c_k:
                ld      (JVEC+1), hl
                ld      de, (PTR)
                ld      a, (CIDX)
                ld      (de), a
                inc     de
                ld      a, (CUR+1)
                ld      (de), a
                inc     de
                ld      a, (CUR+2)
                ld      (de), a
                inc     de
                out     ($F4), a
                in      a, ($F4)
                ld      (de), a
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+4)
                ld      (ENTBL+12), a
                ld      a, (CUR+3)
                ld      (ENTBL+13), a
                ld      a, (CUR+5)
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
                call    JVEC
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
                in      a, ($F4)
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
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

wr_rd:
                call    WRRES
                jp      RDRES

ent_src:
                dw      $5A6B, $1A2B, $3C4D, $5E6F, $7081, $92A3, $A700, $B1C2, $4E5F, $9876

; id, kind (0 RDRES, 1 WRRES, 2 WRRES then RDRES), preset (OUT by hand), A, F, iff
cases:
                db      0, 0, $00, $A7, $00, 0
                db      1, 0, $80, $A7, $00, 0
                db      2, 0, $FF, $27, $FF, 0
                db      3, 0, $7F, $27, $FF, 0
                db      4, 0, $80, $A7, $00, 1
                db      5, 1, $80, $00, $00, 0
                db      6, 1, $00, $80, $00, 0
                db      7, 1, $00, $FF, $FF, 0
                db      8, 1, $80, $7F, $FF, 0
                db      9, 1, $00, $A5, $00, 0
                db      10, 1, $80, $5A, $00, 0
                db      11, 1, $00, $80, $00, 1
                db      12, 0, $5A, $A7, $00, 0      ; after WRRES's cases: RDRES with the port as set by hand
                db      13, 1, $00, $A5, $00, 0
                db      14, 0, $FF, $27, $00, 0      ; preset overrides: OUT by hand; then RDRES
                db      15, 1, $00, $00, $00, 0      ; port reads $7F before; NOT A = $FF must make it $FF
                db      16, 1, $80, $80, $00, 0      ; port $FF before; NOT A = $7F must make it $7F
                db      17, 1, $00, $7F, $FF, 0      ; port $7F before -> $FF
                db      18, 1, $80, $FF, $FF, 0      ; port $FF before -> $7F
                db      19, 2, $80, $80, $00, 0      ; port $FF; WRRES $80 -> port $7F; RDRES -> A $80
                db      20, 2, $00, $00, $00, 0      ; port $7F; WRRES $00 -> port $FF; RDRES -> A $00
                db      $EE

                ds      $8000 - $, $FF
