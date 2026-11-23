; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBDLN4 -- D-MSX2SPEC, docs/msx2/sub/DELLNO.md and INSLNO.md, round 4 (goldfish pass 1): xsubdln3.asm's code with
; BC / DE, the value of the one LINTTB entry the case sets, and an override from the case table:
; - BC / DE other than $B1C1 / $D1E1 on the move, the clear-only and the early-return path;
; - L 128 and L 255 (is the early-return test "L > last + 1", unsigned);
; - CNSDFG $01 (last = CRTCNT - 2 for any non-zero CNSDFG, or CRTCNT - 1 + CNSDFG as a byte);
; - LINTTB[last - 1] := 0 and LINTTB[last] := 0 (are INSLNO's $FB and DELLNO's $AF constants);
; - the override (after CHGMOD): LINLEN, LINL40, LINL32 := three different values, NAMBAS ($F922) and TXTNAM ($F3B3)
;   := two addresses unlike R#2's table, and the rows are filled at NAMBAS; the 16-bit sum of the 27 rows at the
;   table CHGMOD set up is taken before and after the call (is that table touched); and how W is chosen: the 80-column
;   mode with LINLEN 40, the 40-column mode with LINLEN 60, the 40-column mode with LINLEN 29 and SCREEN 1 with LINLEN 40
;   (is W = 32 chosen by SCRMOD or by LINLEN).
; Every case starts with TXTNAM := $0000, T32NAM := $1800 (so an override cannot leak into the next CHGMOD).
; Record additions: +288 the sum before, +290 after, +292 NAMBAS, +294 TXTNAM (after the call), +296 the table
; CHGMOD set up (2).
; Round 2's notes (round 1: xsubdln.asm, the same code):
; the sub-ROM entries $0121 (DELLNO) and $0125 (INSLNO) through EXTROM. Added: $FBCA := the case's value and $FBCB :=
; $77 before the call (round 1 kept $FBCA $5D and saw DELLNO decrement it); the record also keeps $FBCB and rows 4, 5
; and 23 in full (40 bytes each), for the narrow-width cases.
; Per case (the table `cases`): LINL40 / LINL32 := the case's width, CHGMOD (main $005F) into the case's mode; then by
; hand: 27 rows of the name table (base and row length from SCRMOD / RG0SAV) := the row-tagged garbage
; cell(r, c) = $80 | (4 r + (c AND 3)) -- never a space, never a label letter, and its first byte names its row;
; LINTTB ($FBB2, 24) := $C0 + row, one entry := 0 where the case says, $FBCA := $5D; FNKSTR key k := 15 x ('A' + k);
; CNSDFG, CSRY, CSRX, CRTCNT from the table; A from the table, F := $C5 (through the stack), H / L from the table,
; BC $B1C1, DE $D1E1, IY $1A2B; interrupts as the table says; IX := the entry; CALL EXTROM ($015F).
; After it: A F IFF (read twice) BC DE HL IX IY, the cells, LINTTB + $FBCA, and per name-table row (0..26):
; the number of spaces, the first and last byte, the number of cells equal to (first AND $FC) | (c AND 3) -- the row's
; own pattern, so a whole row moved reads `matches = row length`.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 192-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF, +4..+13 C B E D L H IXl IXh IYl IYh, +14 IFF first read,
;   +16 CSRY CSRX CNSDFG SCRMOD LINLEN CRTCNT LINL40 LINL32, +24 LINTTB (24) + $FBCA,
;   +56 27 x (spaces, first, last, matches), +164 row length, +165 name base (2), +191 $5E (sentinel).
; Record additions: +49 $FBCB, +168 row 4 (40), +208 row 5 (40), +248 row 23 (40); RECLEN 320, sentinel +319.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubdln4.asm --row msx2all
; Decode: python3 scratchpad/xsubdln_decode.py --r4 scratchpad/AE_xsubdln4_msx2.out
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 2900
; @timeout 300

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
LINTTB  equ     $FBB2
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     320
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E960                   ; entry (2), mode, width, CNSDFG, CSRY, CSRX, H, L, A, flags, CRTCNT, ltz, FBCA,
                                        ; ltv, BC (2), DE (2), ovr, LINLEN, LINL40, LINL32, NAMBAS (2), TXTNAM (2) = 27
obase   equ     $E952
sumb    equ     $E954
nbase   equ     $E950
rlen    equ     $E944
rowc    equ     $E945
first   equ     $E946
fbase   equ     $E947
spc     equ     $E948
mat     equ     $E949
col     equ     $E94A

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $28FE
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
                ld      bc, 27
                ldir
                ld      (tp), hl
                ld      a, (cur+3)
                ld      ($F3AE), a              ; LINL40
                ld      ($F3AF), a              ; LINL32
                ld      hl, $0000
                ld      ($F3B3), hl             ; TXTNAM
                ld      hl, $1800
                ld      ($F3BD), hl             ; T32NAM
                ld      a, (cur+2)
                call    CHGMOD
                di
                call    nsetup
                ld      hl, (nbase)
                ld      (obase), hl
                ld      a, (cur+19)
                or      a
                jr      z, c_novr
                ld      a, (cur+20)
                ld      ($F3B0), a              ; LINLEN
                ld      a, (cur+21)
                ld      ($F3AE), a              ; LINL40
                ld      a, (cur+22)
                ld      ($F3AF), a              ; LINL32
                ld      hl, (cur+23)
                ld      ($F922), hl             ; NAMBAS
                ld      (nbase), hl
                ld      hl, (cur+25)
                ld      ($F3B3), hl             ; TXTNAM
c_novr:
                ; 27 rows of row-tagged garbage
                ld      hl, (nbase)
                call    vwr
                ld      c, 0                    ; row
c_fr:
                ld      a, (rlen)
                ld      b, a
                ld      e, 0                    ; column
c_fc:
                ld      a, c
                add     a, a
                add     a, a
                ld      d, a
                ld      a, e
                and     3
                or      d
                or      $80
                out     ($98), a
                inc     e
                djnz    c_fc
                inc     c
                ld      a, c
                cp      27
                jr      nz, c_fr
                ld      hl, fkeys
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                ld      hl, LINTTB
                ld      b, 24
                ld      a, $C0
c_lt:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_lt
                ld      a, (cur+13)
                ld      (hl), a                 ; $FBCA
                inc     hl
                ld      (hl), $77               ; $FBCB
                ld      a, (cur+12)
                cp      $FF
                jr      z, c_nlt
                ld      e, a
                ld      d, 0
                ld      hl, LINTTB
                add     hl, de
                ld      a, (cur+14)
                ld      (hl), a
c_nlt:
                ld      a, (cur+4)
                ld      ($F3DE), a              ; CNSDFG
                ld      a, (cur+5)
                ld      ($F3DC), a              ; CSRY
                ld      a, (cur+6)
                ld      ($F3DD), a              ; CSRX
                ld      a, (cur+11)
                ld      ($F3B1), a              ; CRTCNT
                call    osum
                ld      (sumb), hl
                ; the call
                ld      hl, (cur)
                push    hl
                pop     ix
                ld      a, (cur+9)
                ld      h, a
                ld      l, $C5
                push    hl
                ld      bc, (cur+15)
                ld      de, (cur+17)
                ld      iy, $1A2B
                ld      a, (cur+8)
                ld      l, a
                ld      a, (cur+7)
                ld      h, a
                ld      a, (cur+10)
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
                ld      bc, 26
                ldir
                ld      hl, (ptr)               ; +56
                ld      bc, 56
                add     hl, bc
                ex      de, hl
                ld      hl, (nbase)
                ld      a, 27
                ld      (rowc), a
c_row:
                push    hl
                call    vrd
                in      a, ($98)
                ld      (first), a
                and     $FC
                ld      (fbase), a
                xor     a
                ld      (spc), a
                ld      (mat), a
                ld      (col), a
                ld      a, (first)
                call    tally
                ld      a, (rlen)
                dec     a
                ld      b, a
c_rb:
                in      a, ($98)
                call    tally
                djnz    c_rb
                ld      c, a                    ; last
                ld      a, (spc)
                ld      (de), a
                inc     de
                ld      a, (first)
                ld      (de), a
                inc     de
                ld      a, c
                ld      (de), a
                inc     de
                ld      a, (mat)
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
                ld      a, (rlen)
                ld      (de), a                 ; +164
                inc     de
                ld      hl, (nbase)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ld      hl, (ptr)               ; +168 rows 4, 5, 23
                ld      bc, 168
                add     hl, bc
                ex      de, hl
                ld      a, 4
                call    rowdump
                ld      a, 5
                call    rowdump
                ld      a, 23
                call    rowdump
                call    osum
                ex      de, hl
                ld      hl, (ptr)
                ld      bc, 288
                add     hl, bc
                ld      bc, (sumb)
                ld      (hl), c
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (hl), e                 ; +290 the sum after
                inc     hl
                ld      (hl), d
                inc     hl
                ld      bc, ($F922)
                ld      (hl), c                 ; +292 NAMBAS
                inc     hl
                ld      (hl), b
                inc     hl
                ld      bc, ($F3B3)
                ld      (hl), c                 ; +294 TXTNAM
                inc     hl
                ld      (hl), b
                inc     hl
                ld      bc, (obase)
                ld      (hl), c                 ; +296 the table CHGMOD set up
                inc     hl
                ld      (hl), b
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
                ld      a, 40
                ld      ($F3AE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; HL := the 16-bit sum of 27 rows (rlen each) at obase; A, BC, DE changed
osum:
                ld      hl, (obase)
                call    vrd
                ld      hl, 0
                ld      e, 27
os_r:
                ld      a, (rlen)
                ld      b, a
os_c:
                in      a, ($98)
                add     a, l
                ld      l, a
                jr      nc, os_n
                inc     h
os_n:
                djnz    os_c
                dec     e
                jr      nz, os_r
                ret

; 40 bytes of name-table row A to DE..
rowdump:
                ld      hl, (nbase)
                ld      b, a
                or      a
                jr      z, rd_go
                ld      a, (rlen)
                ld      c, a
                ld      a, b
                ld      b, 0
rd_m:
                add     hl, bc
                dec     a
                jr      nz, rd_m
rd_go:
                call    vrd
                ld      b, 40
rd_lp:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    rd_lp
                ret

; count A (a cell, column (col)) into spaces / matches; A, B, DE kept
tally:
                push    af
                push    bc
                ld      c, a
                cp      $20
                jr      nz, t1
                ld      hl, spc
                inc     (hl)
t1:
                ld      a, (col)
                and     3
                ld      b, a
                ld      a, (fbase)
                or      b
                cp      c
                jr      nz, t2
                ld      hl, mat
                inc     (hl)
t2:
                ld      hl, col
                inc     (hl)
                pop     bc
                pop     af
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

; entry, mode, width, CNSDFG, CSRY, CSRX, H, L, A, flags (b0 EI), CRTCNT, LINTTB index (FF none), $FBCA, the value for
; that LINTTB entry, BC, DE, override (0 none), LINLEN, LINL40, LINL32, NAMBAS, TXTNAM
CASE    macro   ent, mode, wid, fk, cy, cx, hh, ll, aa, fl, crt, ltz, fs, ltv, rbc, rde, ov, lin, l40, l32, nb, tn
                dw      ent
                db      mode, wid, fk, cy, cx, hh, ll, aa, fl, crt, ltz, fs, ltv
                dw      rbc, rde
                db      ov, lin, l40, l32
                dw      nb, tn
        endm
cases:
        irp     ent, $0121, $0125
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $2468, $9ABC, 0, 0, 0, 0, 0, 0              ;  0 / 16 L 5, BC 2468 DE 9ABC
                CASE    ent, 0, 40, $00, 12, 15, 7,  24, $A7, 0, 24, $FF, 30, 0, $2468, $9ABC, 0, 0, 0, 0, 0, 0              ;  1 / 17 L 24 (clear only)
                CASE    ent, 0, 40, $00, 12, 15, 7,  25, $A7, 0, 24, $FF, 30, 0, $2468, $9ABC, 0, 0, 0, 0, 0, 0              ;  2 / 18 L 25 (early)
                CASE    ent, 0, 40, $00, 12, 15, 7, 128, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  3 / 19 L 128
                CASE    ent, 0, 40, $00, 12, 15, 7, 255, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  4 / 20 L 255
                CASE    ent, 0, 40, $01, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  5 / 21 CNSDFG 1
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24,  22, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  6 / 22 LINTTB[22] = 0
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24,  23, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  7 / 23 LINTTB[23] = 0
                CASE    ent, 0, 40, $00, 12, 15, 7,  24, $A7, 0, 24,  23, 30, 0, $B1C1, $D1E1, 0, 0, 0, 0, 0, 0              ;  8 / 24 L 24, LINTTB[23] = 0
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 37, 33, 29, $2000, $3000  ;  9 / 25 w40 override
                CASE    ent, 1, 32, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 29, 33, 25, $3000, $2400  ; 10 / 26 SCREEN 1 override
                CASE    ent, 0, 80, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 72, 75, 29, $2000, $3000  ; 11 / 27 w80 override
                CASE    ent, 0, 80, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 40, 80, 32, $0000, $0000  ; 12 / 28 80 columns, LINLEN 40
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 60, 40, 32, $0000, $0000  ; 13 / 29 40 columns, LINLEN 60
                CASE    ent, 0, 40, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 29, 40, 32, $0000, $0000  ; 14 / 30 40 columns, LINLEN 29
                CASE    ent, 1, 32, $00, 12, 15, 7,   5, $A7, 0, 24, $FF, 30, 0, $B1C1, $D1E1, 1, 40, 40, 32, $1800, $0000  ; 15 / 31 SCREEN 1, LINLEN 40
        endm
                db      $EE

                ds      $8000 - $, $FF
