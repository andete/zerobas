; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBCTX -- D-MSX2SPEC, docs/msx2/sub/CLRTXT.md: the sub-ROM entry $0119 (CLRTXT in other open implementations;
; not in the handbook's listing) through EXTROM, on the MSX2 / MSX2+ references.
; Per case (the table `cases`): LINL40 / LINL32 := the case's width, CHGMOD (main $005F) into the case's mode; then by
; hand: 27 rows of the name table (base and row length from SCRMOD / RG0SAV) and three 16-byte windows := the
; address-dependent garbage g(a) = ((a.lo + 3 a.hi) & $7F) | $80 (never a space, never a label letter); LINTTB
; ($FBB2, 24) := $A0 + row; FNKSTR key k := 15 x ('A' + k); CNSDFG, CSRY, CSRX from the table, CRTCNT 24; A / F from
; the table through the stack (so Z and A are separate inputs), BC DE HL := $B1C1 $D1E1 $4151; interrupts as the
; table says; the call. After it: A F IFF (read twice) BC DE HL IX IY, the cells, LINTTB, RG0SAV-RG7SAV, per name-table
; row (0..26) the number of spaces and its first and last byte, rows 0 and 23 in full, the three windows.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 384-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF, +4..+13 C B E D L H IXl IXh IYl IYh, +14 IFF first read,
;   +16 CSRY CSRX CNSDFG SCRMOD LINLEN CRTCNT LINL40 LINL32, +24 LINTTB (24), +48 RG0SAV-RG7SAV,
;   +56 27 x (spaces, first, last), +140 row 0 (80), +220 row 23 (80), +300 three windows (3 x 16),
;   +348 row length, +349 name base (2), +383 $5E (sentinel).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubctx.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 1300
; @timeout 240

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
LINTTB  equ     $FBB2
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     384
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E930                   ; mode, width, CNSDFG, CSRY, CSRX, A, F, flags, 3 windows (6) = 14
nbase   equ     $E942
rlen    equ     $E944
rowc    equ     $E945
cc      equ     $E946

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $12FF
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
                ld      bc, 14
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                ld      ($F3AE), a              ; LINL40
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur)
                call    CHGMOD
                di
                call    nsetup
                ; 27 rows of garbage
                ld      hl, (nbase)
                ld      a, (rlen)
                ld      c, a
                ld      b, 0
                push    hl
                ld      hl, 0
                ld      a, 27
c_m:
                add     hl, bc
                dec     a
                jr      nz, c_m
                ld      b, h
                ld      c, l                    ; BC = 27 rows
                pop     hl
                call    gfill
                ld      ix, cur+8
                ld      b, 3
c_w:
                push    bc
                ld      l, (ix+0)
                ld      h, (ix+1)
                ld      bc, 16
                call    gfill
                inc     ix
                inc     ix
                pop     bc
                djnz    c_w
                ld      hl, fkeys
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                ld      hl, LINTTB
                ld      b, 24
                ld      a, $A0
c_lt:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_lt
                ld      a, (cur+2)
                ld      ($F3DE), a              ; CNSDFG
                ld      a, (cur+3)
                ld      ($F3DC), a              ; CSRY
                ld      a, (cur+4)
                ld      ($F3DD), a              ; CSRX
                ld      a, 24
                ld      ($F3B1), a              ; CRTCNT
                ; the call
                ld      ix, $0119
                ld      a, (cur+6)
                ld      l, a
                ld      a, (cur+5)
                ld      h, a
                push    hl
                ld      bc, $B1C1
                ld      de, $D1E1
                ld      hl, $4151
                ld      a, (cur+7)
                bit     0, a
                jr      z, c_di
                pop     af
                ei
                jr      c_go
c_di:
                pop     af
c_go:
                call    EXTROM
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                push    af
                jp      pe, c_ion
                ld      a, i                    ; an "off" is read again (the NMOS ld a,i erratum)
c_ion:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      a, l
                ld      (rsave+13), a
                pop     hl
                ld      (rsave), hl
                pop     hl
                ld      (rsave+3), hl
                pop     hl
                ld      (rsave+5), hl
                pop     hl
                ld      (rsave+7), hl
                pop     hl
                ld      (rsave+9), hl
                pop     hl
                ld      (rsave+11), hl
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
                ld      hl, rsave+3
                ld      bc, 10
                ldir
                ld      a, (rsave+13)
                rrca
                rrca
                and     1
                ld      (de), a
                inc     de
                inc     de                      ; +16
                ld      hl, cells
                ld      b, 8
c_cell:
                push    hl
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ld      a, (hl)
                ld      (de), a
                inc     de
                pop     hl
                inc     hl
                inc     hl
                djnz    c_cell
                ld      hl, LINTTB              ; +24
                ld      bc, 24
                ldir
                ld      hl, $F3DF               ; +48
                ld      bc, 8
                ldir
                ; +56: per row (spaces, first, last); the base / row length as before the call
                ld      hl, (nbase)
                ld      a, 27
                ld      (rowc), a
c_row:
                push    hl
                call    vrd
                ld      a, (rlen)
                ld      b, a
                ld      c, 0
                in      a, ($98)
                ld      (de), a                 ; first, stored at +1 below
                push    af
                cp      $20
                jr      nz, c_r1
                inc     c
c_r1:
                dec     b
c_rb:
                in      a, ($98)
                cp      $20
                jr      nz, c_r2
                inc     c
c_r2:
                djnz    c_rb
                ld      h, a                    ; last
                ld      a, c
                ld      (de), a                 ; spaces
                inc     de
                pop     af
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                pop     hl
                ld      a, (rlen)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (rowc)
                dec     a
                ld      (rowc), a
                jr      nz, c_row
                ; +140 row 0, +220 row 23
                ld      hl, (ptr)
                ld      bc, 140
                add     hl, bc
                ex      de, hl
                ld      hl, (nbase)
                call    vrd
                ld      b, 80
                call    rdb
                ld      hl, (nbase)
                ld      a, (rlen)
                ld      c, a
                ld      b, 0
                ld      a, 23
c_23:
                add     hl, bc
                dec     a
                jr      nz, c_23
                call    vrd
                ld      b, 80
                call    rdb
                ; +300 the windows
                ld      ix, cur+8
                ld      b, 3
c_wr:
                push    bc
                ld      l, (ix+0)
                ld      h, (ix+1)
                call    vrd
                ld      b, 16
                call    rdb
                inc     ix
                inc     ix
                pop     bc
                djnz    c_wr
                ld      a, (rlen)
                ld      (de), a                 ; +348
                inc     de
                ld      hl, (nbase)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ld      hl, (ptr)
                ld      bc, RECLEN-1
                add     hl, bc
                ld      (hl), $5E
                inc     hl
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

; B bytes from the VDP to DE..
rdb:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    rdb
                ret

; BC bytes of g(a) from HL (VRAM, 16-bit, page 0 of 128 KB)
gfill:
                push    bc
                call    vwr
                pop     bc
gf:
                ld      a, h
                add     a, a
                add     a, h
                add     a, l
                and     $7F
                or      $80
                out     ($98), a
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, gf
                ret

; the name base / row length from SCRMOD and RG0SAV
nsetup:
                ld      a, ($FCAF)
                ld      hl, ($F3B3)             ; TXTNAM
                ld      c, 40
                or      a
                jr      nz, ns1
                ld      a, ($F3DF)
                and     4
                jr      z, nsset
                ld      c, 80
                jr      nsset
ns1:
                ld      hl, ($F3BD)             ; T32NAM
                ld      c, 32
                dec     a
                jr      z, nsset
                ld      hl, ($F3C7)             ; GRPNAM
                dec     a
                jr      z, nsset
                ld      hl, 0
                ld      c, 80
nsset:
                ld      (nbase), hl
                ld      a, c
                ld      (rlen), a
                ret

; VRAM write / read address HL (A16-A14 from H's top bits, A16 = 0)
vwr:
                ld      c, $40
                jr      vset
vrd:
                ld      c, $00
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

cells:
                dw      $F3DC, $F3DD, $F3DE, $FCAF, $F3B0, $F3B1, $F3AE, $F3AF

fkeys:
                db      "AAAAAAAAAAAAAAA", 0
                db      "BBBBBBBBBBBBBBB", 0
                db      "CCCCCCCCCCCCCCC", 0
                db      "DDDDDDDDDDDDDDD", 0
                db      "EEEEEEEEEEEEEEE", 0
                db      "FFFFFFFFFFFFFFF", 0
                db      "GGGGGGGGGGGGGGG", 0
                db      "HHHHHHHHHHHHHHH", 0
                db      "IIIIIIIIIIIIIII", 0
                db      "JJJJJJJJJJJJJJJ", 0

; mode, width, CNSDFG, CSRY, CSRX, A, F, flags (b0 EI), three windows
cases:
                db      0, 40, $00, 12, 10, $00, $40, 0
                dw      $0800, $0438, $1000     ;  0 SCREEN 0 w40, Z set, A 0
                db      0, 40, $00, 12, 10, $00, $40, 1
                dw      $0800, $0438, $1000     ;  1 the same, EI
                db      0, 40, $00, 12, 10, $00, $00, 0
                dw      $0800, $0438, $1000     ;  2 Z clear, A 0
                db      0, 40, $00, 12, 10, $FF, $40, 0
                dw      $0800, $0438, $1000     ;  3 Z set, A $FF
                db      0, 40, $FF, 12, 10, $00, $40, 0
                dw      $0800, $0438, $1000     ;  4 key line on (CNSDFG $FF)
                db      0, 37, $00, 12, 10, $00, $40, 0
                dw      $0800, $0438, $1000     ;  5 width 37
                db      0, 80, $00, 12, 10, $00, $40, 0
                dw      $0800, $0870, $1000     ;  6 width 80 (TEXT 2; $0800 = the blink table)
                db      0, 80, $FF, 12, 10, $00, $40, 0
                dw      $0800, $0870, $1000     ;  7 width 80, key line on
                db      1, 29, $00, 12, 10, $00, $40, 0
                dw      $2000, $0000, $1C00     ;  8 SCREEN 1 (colour table, patterns, past rows)
                db      1, 29, $FF, 12, 10, $00, $40, 0
                dw      $2000, $0000, $1C00     ;  9 SCREEN 1, key line on
                db      2, 32, $00, 12, 10, $00, $40, 0
                dw      $2000, $0000, $1C00     ; 10 SCREEN 2
                db      5, 32, $00, 12, 10, $00, $40, 0
                dw      $6A00, $7000, $7600     ; 11 SCREEN 5 (bitmap rows from 0; past line 212)
                db      $EE

                ds      $8000 - $, $FF
