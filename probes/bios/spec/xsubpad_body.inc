; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; The body of XSUBPAD / XSUBPADM / XSUBPADX / XSUBPADB / XSUBPADS / XSUBPADG (D-MSX2SPEC, docs/msx2/sub/NEWPAD.md); the including file sets SEQ (which
; call list) and the @-directives. Per call (the list `seq_*`: the function number, the path 0 = the sub-ROM's NEWPAD
; $01AD through EXTROM, 1 = the main ROM's GTPAD $00DB): interrupts off, PSG R15 := $8F through the ports, BC $1357,
; DE $2468, HL $369C, A := the function, the call; then A, F, the interrupt state (read twice), R15 through the ports,
; BC / DE / HL. The calls follow each other at once (no wait), in the list's order.
; The capture (CAP = C001): +0 $A5 when finished, +1 the call count; per call a 16-byte record from +2: +0 the
; function, +1 the path, +2 A, +3 F, +4 / +5 IFF (P/V of LD A,I, read twice), +6 R15 after, +7 C, +8 B, +9 E, +10 D,
; +11 L, +12 H, +13 $EE (sentinel), +14 / +15 0.

EXTROM  equ     $015F
GTPAD   equ     $00DB
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
fn      equ     $E909
path    equ     $E90A
sv_af   equ     $E910
sv_bc   equ     $E912
sv_de   equ     $E914
sv_hl   equ     $E916
sv_if   equ     $E918

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, seqtab
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                di
                ld      hl, (tp)
        IF SEQ = 3
                inc     hl              ; SEQ 3 measures fn $EE too: the end is a path byte of $EE
                ld      a, (hl)
                dec     hl
                cp      $EE
                jp      z, finish
                ld      a, (hl)
        ELSE
                ld      a, (hl)
                cp      $EE
                jp      z, finish
        ENDIF
                ld      (fn), a
                inc     hl
                ld      a, (hl)
                ld      (path), a
                inc     hl
                ld      (tp), hl
                ld      a, 15
                out     ($A0), a
                ld      a, $8F
                out     ($A1), a
                ld      bc, $1357
                ld      de, $2468
                ld      hl, $369C
                ld      a, (path)
                or      a
                ld      a, (fn)
                jr      nz, c_main
                ld      ix, $01AD
                call    EXTROM
                jr      c_after
c_main:
                call    GTPAD
c_after:
                push    af
                ld      (sv_bc), bc
                ld      (sv_de), de
                ld      (sv_hl), hl
                pop     hl
                ld      (sv_af), hl
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if), a
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if+1), a
                ld      hl, (ptr)
                ld      a, (fn)
                ld      (hl), a
                inc     hl
                ld      a, (path)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af+1)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af)
                ld      (hl), a
                inc     hl
                ld      a, (sv_if)
                rrca
                rrca
                and     1
                ld      (hl), a
                inc     hl
                ld      a, (sv_if+1)
                rrca
                rrca
                and     1
                ld      (hl), a
                inc     hl
                ld      a, 15
                out     ($A0), a
                in      a, ($A2)
                ld      (hl), a
                inc     hl
                ex      de, hl
                ld      hl, sv_bc
                ld      bc, 6
                ldir
                ex      de, hl
                ld      (hl), $EE
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
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
                ei
fin:
                jr      fin

seqtab:
        IF SEQ = 0
                ; 8-23 in order; 13 / 14 / 17 / 18 again without a fetch; 12, 14, 13; 16, 18, 17
                db      8, 0, 9, 0, 10, 0, 11, 0, 12, 0, 13, 0, 14, 0, 15, 0
                db      16, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0, 23, 0
                db      13, 0, 14, 0, 17, 0, 18, 0
                db      12, 0, 14, 0, 13, 0, 16, 0, 18, 0, 17, 0
                ; the same through GTPAD
                db      8, 1, 9, 1, 10, 1, 11, 1, 12, 1, 13, 1, 14, 1, 15, 1
                db      16, 1, 17, 1, 18, 1, 19, 1
        ENDIF
        IF SEQ = 2
                ; which port's reading do the reads return: port 1 empty (reads $01), port 2 a mouse (reads 0)
                db      12, 0, 13, 0, 14, 0, 16, 0, 13, 0, 14, 0, 17, 0, 18, 0
                db      12, 0, 17, 0, 18, 0, 9, 0, 10, 0, 20, 0, 0, 0, 16, 0, 9, 0, 21, 0, 22, 0
        ENDIF
        IF SEQ = 1
                ; out of range: 0-7 through the sub-ROM, then 24, 31, $80, $FF
                db      0, 0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0
                db      24, 0, 31, 0, $80, 0, $FF, 0
        ENDIF
        IF SEQ = 3
                ; (goldfish pass 1, 2026-11-23) a fetch of the EMPTY port 1 ($01 / $01), then every number 0-255 through
                ; the sub-ROM (257 calls: the count byte at +1 wraps to 1; the table ends with a PATH byte of $EE, so $EE is
                ; measured too): the reads now return $01, so the "0" class is told from X / Y by value, and any other
                ; fetch ($FF) or light-pen-like number shows
                db      12, 0
                db      $00, 0, $01, 0, $02, 0, $03, 0, $04, 0, $05, 0, $06, 0, $07, 0, $08, 0, $09, 0, $0A, 0, $0B, 0, $0C, 0, $0D, 0, $0E, 0, $0F, 0
                db      $10, 0, $11, 0, $12, 0, $13, 0, $14, 0, $15, 0, $16, 0, $17, 0, $18, 0, $19, 0, $1A, 0, $1B, 0, $1C, 0, $1D, 0, $1E, 0, $1F, 0
                db      $20, 0, $21, 0, $22, 0, $23, 0, $24, 0, $25, 0, $26, 0, $27, 0, $28, 0, $29, 0, $2A, 0, $2B, 0, $2C, 0, $2D, 0, $2E, 0, $2F, 0
                db      $30, 0, $31, 0, $32, 0, $33, 0, $34, 0, $35, 0, $36, 0, $37, 0, $38, 0, $39, 0, $3A, 0, $3B, 0, $3C, 0, $3D, 0, $3E, 0, $3F, 0
                db      $40, 0, $41, 0, $42, 0, $43, 0, $44, 0, $45, 0, $46, 0, $47, 0, $48, 0, $49, 0, $4A, 0, $4B, 0, $4C, 0, $4D, 0, $4E, 0, $4F, 0
                db      $50, 0, $51, 0, $52, 0, $53, 0, $54, 0, $55, 0, $56, 0, $57, 0, $58, 0, $59, 0, $5A, 0, $5B, 0, $5C, 0, $5D, 0, $5E, 0, $5F, 0
                db      $60, 0, $61, 0, $62, 0, $63, 0, $64, 0, $65, 0, $66, 0, $67, 0, $68, 0, $69, 0, $6A, 0, $6B, 0, $6C, 0, $6D, 0, $6E, 0, $6F, 0
                db      $70, 0, $71, 0, $72, 0, $73, 0, $74, 0, $75, 0, $76, 0, $77, 0, $78, 0, $79, 0, $7A, 0, $7B, 0, $7C, 0, $7D, 0, $7E, 0, $7F, 0
                db      $80, 0, $81, 0, $82, 0, $83, 0, $84, 0, $85, 0, $86, 0, $87, 0, $88, 0, $89, 0, $8A, 0, $8B, 0, $8C, 0, $8D, 0, $8E, 0, $8F, 0
                db      $90, 0, $91, 0, $92, 0, $93, 0, $94, 0, $95, 0, $96, 0, $97, 0, $98, 0, $99, 0, $9A, 0, $9B, 0, $9C, 0, $9D, 0, $9E, 0, $9F, 0
                db      $A0, 0, $A1, 0, $A2, 0, $A3, 0, $A4, 0, $A5, 0, $A6, 0, $A7, 0, $A8, 0, $A9, 0, $AA, 0, $AB, 0, $AC, 0, $AD, 0, $AE, 0, $AF, 0
                db      $B0, 0, $B1, 0, $B2, 0, $B3, 0, $B4, 0, $B5, 0, $B6, 0, $B7, 0, $B8, 0, $B9, 0, $BA, 0, $BB, 0, $BC, 0, $BD, 0, $BE, 0, $BF, 0
                db      $C0, 0, $C1, 0, $C2, 0, $C3, 0, $C4, 0, $C5, 0, $C6, 0, $C7, 0, $C8, 0, $C9, 0, $CA, 0, $CB, 0, $CC, 0, $CD, 0, $CE, 0, $CF, 0
                db      $D0, 0, $D1, 0, $D2, 0, $D3, 0, $D4, 0, $D5, 0, $D6, 0, $D7, 0, $D8, 0, $D9, 0, $DA, 0, $DB, 0, $DC, 0, $DD, 0, $DE, 0, $DF, 0
                db      $E0, 0, $E1, 0, $E2, 0, $E3, 0, $E4, 0, $E5, 0, $E6, 0, $E7, 0, $E8, 0, $E9, 0, $EA, 0, $EB, 0, $EC, 0, $ED, 0, $EE, 0, $EF, 0
                db      $F0, 0, $F1, 0, $F2, 0, $F3, 0, $F4, 0, $F5, 0, $F6, 0, $F7, 0, $F8, 0, $F9, 0, $FA, 0, $FB, 0, $FC, 0, $FD, 0, $FE, 0, $FF, 0
        ENDIF
        IF SEQ = 4
                ; (goldfish pass 1) GTPAD with A = 20-23 and out of range, after a fetch of the empty port 1 through it
                db      12, 1, 20, 1, 21, 1, 22, 1, 23, 1, 24, 1, 31, 1, $80, 1, $FF, 1
        ENDIF
        IF SEQ = 3
                db      $EE, $EE
        ELSE
                db      $EE
        ENDIF

                ds      $8000 - $, $FF
