; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBDLN -- D-MSX2SPEC, docs/msx2/sub/DELLNO.md and INSLNO.md: the sub-ROM entries $0121 (DELLNO) and $0125
; (INSLNO), names from MAP only, through EXTROM, on the MSX2 / MSX2+ references.
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
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubdln.asm --row msx2all
; Decode: python3 scratchpad/xsubdln_decode.py
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 1A00
; @timeout 300

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
LINTTB  equ     $FBB2
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     192
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E930                   ; entry (2), mode, width, CNSDFG, CSRY, CSRX, H, L, A, flags, CRTCNT, ltz = 13
nbase   equ     $E942
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
                ld      bc, $19FE
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
                ld      bc, 13
                ldir
                ld      (tp), hl
                ld      a, (cur+3)
                ld      ($F3AE), a              ; LINL40
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur+2)
                call    CHGMOD
                di
                call    nsetup
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
                ld      (hl), $5D               ; $FBCA
                ld      a, (cur+12)
                cp      $FF
                jr      z, c_nlt
                ld      e, a
                ld      d, 0
                ld      hl, LINTTB
                add     hl, de
                ld      (hl), 0
c_nlt:
                ld      a, (cur+4)
                ld      ($F3DE), a              ; CNSDFG
                ld      a, (cur+5)
                ld      ($F3DC), a              ; CSRY
                ld      a, (cur+6)
                ld      ($F3DD), a              ; CSRX
                ld      a, (cur+11)
                ld      ($F3B1), a              ; CRTCNT
                ; the call
                ld      hl, (cur)
                push    hl
                pop     ix
                ld      a, (cur+9)
                ld      h, a
                ld      l, $C5
                push    hl
                ld      bc, $B1C1
                ld      de, $D1E1
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
                ld      bc, 25
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

; entry, mode, width, CNSDFG, CSRY, CSRX, H, L, A, flags (b0 EI), CRTCNT, LINTTB index := 0 (FF none)
CASE    macro   ent, mode, wid, fk, cy, cx, hh, ll, aa, fl, crt, ltz
                dw      ent
                db      mode, wid, fk, cy, cx, hh, ll, aa, fl, crt, ltz
        endm
cases:
        irp     ent, $0121, $0125
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $A7, 0, 24, $FF    ;  0 / 17 base: SCREEN 0 w40, L 5
                CASE    ent, 0, 40, $00, 12, 15,  7,  9, $A7, 0, 24, $FF    ;  1 / 18 L 9
                CASE    ent, 0, 40, $00, 12, 15, 20,  5, $A7, 0, 24, $FF    ;  2 / 19 H 20
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $03, 0, 24, $FF    ;  3 / 20 A 3
                CASE    ent, 0, 40, $00, 18,  3,  7,  5, $A7, 0, 24, $FF    ;  4 / 21 cursor (3, 18)
                CASE    ent, 0, 40, $00, 12, 15,  7,  1, $A7, 0, 24, $FF    ;  5 / 22 L 1
                CASE    ent, 0, 40, $00, 12, 15,  7, 24, $A7, 0, 24, $FF    ;  6 / 23 L 24
                CASE    ent, 0, 40, $FF, 12, 15,  7, 24, $A7, 0, 24, $FF    ;  7 / 24 L 24, key line on
                CASE    ent, 0, 40, $FF, 12, 15,  7, 10, $A7, 0, 24, $FF    ;  8 / 25 L 10, key line on
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $A7, 1, 24, $FF    ;  9 / 26 EI
                CASE    ent, 0, 80, $00, 12, 15,  7,  5, $A7, 0, 24, $FF    ; 10 / 27 width 80
                CASE    ent, 1, 32, $00, 12, 15,  7,  5, $A7, 0, 24, $FF    ; 11 / 28 SCREEN 1
                CASE    ent, 0, 37, $00, 12, 15,  7,  5, $A7, 0, 24, $FF    ; 12 / 29 width 37
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $A7, 0, 24, 5      ; 13 / 30 LINTTB[5] = 0
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $A7, 0, 24, 4      ; 14 / 31 LINTTB[4] = 0
                CASE    ent, 0, 40, $00, 12, 15,  7,  5, $A7, 0, 20, $FF    ; 15 / 32 CRTCNT 20
                CASE    ent, 0, 40, $00, 12, 15,  7, 23, $A7, 0, 24, $FF    ; 16 / 33 L 23
        endm
                db      $EE

                ds      $8000 - $, $FF
