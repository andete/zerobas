; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XGETCPU2 -- D-TRSPEC goldfish pass 1, docs/turbor/main/GETCPU.md: xgetcpu.asm (same code, same record, same decoder:
; scratchpad/xgetcpu_decode.py) with a new case table, on the two turbo R references (--row turbor: FS-A1GT vs
; FS-A1ST): which entry register the R800 modes' undocumented flag bits 5 / 3 come from. xgetcpu changed A and F
; together ($A7 / $00, $FF / $FF); here A and F apart, in both R800 modes, and the Z80 as a control:
;   0-1  R800 ROM, A $00 F $FF / A $FF F $00;  2-3 R800 DRAM, the same;  4-5 R800 ROM, A $00 with F $28 / $08;
;   6    R800 ROM, A $00 F $20;  7 R800 DRAM, A $00 F $28;  8 the Z80, A $00 F $FF.
; No direct R#6 write (no run-on record).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgetcpu2.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM and I/O ports. No ROM byte read.
;
; @cap C000
; @caplen 0C00
; @timeout 200

CHGCPU  equ     $0180
GETCPU  equ     $0183
KILBUF  equ     $0156
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16
RECLEN  equ     $40
WSAVE   equ     $8000
WBASE   equ     $F380
WLEN    equ     $FFFF-WBASE             ; $F380..$FFFE

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E904
CIDX    equ     $E90B
TP      equ     $E90C
ENTBL   equ     $E940
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
                ld      bc, $0BFE
                ld      (hl), 0
                ldir
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, cases
                ld      (TP), hl
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 5
                ldir
                ld      (TP), hl
                ; CUR: mode, A, F, flags, value
                ld      a, (CUR)
                call    CHGCPU
                di
                ld      a, (CUR+3)
                bit     1, a
                jr      z, c_nfc
                ld      a, (CUR+4)
                ld      ($FCB1), a
c_nfc:
                ld      a, (CUR+3)
                bit     2, a
                jr      z, c_nr6
                ld      a, 6
                out     ($E4), a
                ld      a, (CUR+4)
                out     ($E5), a
c_nr6:
                ld      ix, (PTR)
                ld      a, (CIDX)
                ld      (ix+0), a
                ld      hl, CUR
                push    ix
                pop     de
                inc     de
                ld      bc, 5
                ldir
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+6), a
                ld      a, ($FCB1)
                ld      (ix+7), a
                ld      (ix+RECLEN-1), $5A
                ld      hl, WBASE
                ld      de, WSAVE
                ld      bc, WLEN
                ldir
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+2)
                ld      (ENTBL+12), a           ; F
                ld      a, (CUR+1)
                ld      (ENTBL+13), a           ; A
                ld      a, (CUR+3)
                and     1
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
                call    GETCPU
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
                ld      bc, 8
                add     hl, bc
                ex      de, hl
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      ix, (PTR)
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+34), a
                ld      a, ($FCB1)
                ld      (ix+35), a
                call    wdiff
                ld      ix, (PTR)
                out     ($E6), a
                ld      b, 200
g_lp:
                push    bc
                call    GETCPU
                pop     bc
                djnz    g_lp
                di
                call    rdtimer
                ld      (ix+36), l
                ld      (ix+37), h
                out     ($E6), a
                ld      b, 200
k_lp:
                push    bc
                call    KILBUF
                pop     bc
                djnz    k_lp
                di
                call    rdtimer
                ld      (ix+38), l
                ld      (ix+39), h
                ld      hl, (PTR)
                ld      bc, RECLEN
                add     hl, bc
                ld      (PTR), hl
                ld      hl, CIDX
                inc     (hl)
                ld      a, (hl)
                ld      (CAP), a
                jp      c_next

finish:
                ld      a, $82
                call    CHGCPU
                di
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

rdtimer:
                in      a, ($E6)
                ld      l, a
                in      a, ($E7)
                ld      h, a
                ret

; compare $F380..$FFFE with the copy; up to 4 changes to +41, the count to +40
wdiff:
                ld      ix, (PTR)
                push    ix
                pop     hl
                ld      de, 41
                add     hl, de
                ex      de, hl
                ld      hl, WBASE
                ld      bc, WSAVE
                xor     a
                ld      (ix+40), a
w_lp:
                ld      a, (bc)
                cp      (hl)
                jr      z, w_same
                ld      a, (ix+40)
                inc     a
                jr      z, w_same
                ld      (ix+40), a
                cp      5
                jr      nc, w_same
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                ld      a, (bc)
                ld      (de), a
                inc     de
                ld      a, (hl)
                ld      (de), a
                inc     de
w_same:
                inc     hl
                inc     bc
                ld      a, h
                cp      $FF
                jr      nz, w_lp
                ld      a, l
                cp      $FF
                jr      nz, w_lp
                ret

ent_src:        dw      $1A1B, $1C1D            ; IX, IY
                dw      $2829, $2A2B, $2C2D, $2E2F ; AF', BC', DE', HL'
                dw      $3839, $3A3B, $3C3D, $3E3F ; AF (A, F per case), BC, DE, HL

; mode, A, F, flags (bit 0 EI, bit 1 $FCB1 := value, bit 2 S1990 R#6 := value), value
cases:
                db      $81, $00, $FF, 0, 0     ; 0
                db      $81, $FF, $00, 0, 0     ; 1
                db      $82, $00, $FF, 0, 0     ; 2
                db      $82, $FF, $00, 0, 0     ; 3
                db      $81, $00, $28, 0, 0     ; 4
                db      $81, $00, $08, 0, 0     ; 5
                db      $81, $00, $20, 0, 0     ; 6
                db      $82, $00, $28, 0, 0     ; 7
                db      $80, $00, $FF, 0, 0     ; 8: the Z80
                db      $EE

                ds      $8000-$, $FF
