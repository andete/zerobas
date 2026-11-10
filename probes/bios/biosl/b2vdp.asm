; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B2VDP -- D-BIOSLADDER rung B2 (TODO.md): the VDP as a ROM program drives it
; through the main BIOS. A 16 KB "AB" cartridge; INIT runs it.
;   1. CHGMOD 1 (SCREEN 1): RG0SAV..RG7SAV (CAP+0) and T32NAM..T32PAT (CAP+8);
;   2. FILVRM 32 x '.' at the name table, LDIRVM a word into it, RDVRM / WRTVRM /
;      RDVRM, LDIRMV of the row back (CAP+$40..$5F);
;   3. CHGCLR with FORCLR 15 / BAKCLR 4 / BDRCLR 7, then WRTVDP R#7 := $F1: RG7SAV
;      after each (CAP+20, 21);
;   4. sprites: GSPSIZ at 8 x 8, R#1 bit 1 set by WRTVDP, GSPSIZ at 16 x 16;
;      CALPAT 5 and CALATR 5 (HL); CLRSPR, then sprite 0's attribute bytes;
;   5. CHGMOD 2 (SCREEN 2): the shadows (CAP+32) and GRPNAM..GRPPAT (CAP+40), and a
;      byte of the name table INIGRP filled; CHGMOD 3: the shadows (CAP+51) and
;      MLTNAM..MLTPAT (CAP+59);
;   6. CHGMOD 1 again: the shadows (CAP+69); VRAM compared: the name table, the
;      sprite attribute table and the first colour bytes. NOT the pattern table:
;      the font is C-BIOS's own glyphs, not the reference's (never copied -- clean
;      room), so every glyph differs by design (scratchpad/biosl_b2_run1.out).
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @vram 1800:300
; @vram 1B00:80
; @vram 2000:20
; @timeout 40

WRTVDP  equ     $0047
RDVRM   equ     $004A
WRTVRM  equ     $004D
FILVRM  equ     $0056
LDIRMV  equ     $0059
LDIRVM  equ     $005C
CHGMOD  equ     $005F
CHGCLR  equ     $0062
CLRSPR  equ     $0069
CALPAT  equ     $0084
CALATR  equ     $0087
GSPSIZ  equ     $008A
T32NAM  equ     $F3BD
T32ATR  equ     $F3C3
GRPNAM  equ     $F3C7
MLTNAM  equ     $F3D1
RG0SAV  equ     $F3DF
RG1SAV  equ     $F3E0
RG7SAV  equ     $F3E6
FORCLR  equ     $F3E9
BAKCLR  equ     $F3EA
BDRCLR  equ     $F3EB

DONE    equ     $E000
CAP     equ     $E001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ; --- 1: SCREEN 1 ---------------------------------------------------------
                ld      a, 1
                call    CHGMOD
                ld      de, CAP+0
                call    shadows
                ld      hl, T32NAM
                ld      de, CAP+8
                ld      bc, 10
                ldir
                ; --- 2: VRAM traffic -----------------------------------------------------
                ld      hl, (T32NAM)
                ld      bc, 32
                ld      a, '.'
                call    FILVRM
                ld      hl, (T32NAM)
                ld      de, 4
                add     hl, de
                ex      de, hl              ; DE = name table + 4
                ld      hl, word
                ld      bc, 6
                call    LDIRVM
                ld      hl, (T32NAM)
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                call    RDVRM               ; the word's second letter
                ld      (CAP+18), a
                ld      hl, (T32NAM)
                ld      de, 31
                add     hl, de
                ld      a, '!'
                call    WRTVRM
                call    RDVRM
                ld      (CAP+19), a
                ld      hl, (T32NAM)
                ld      de, CAP+$40
                ld      bc, 32
                call    LDIRMV
                ; --- 3: colours ----------------------------------------------------------
                ld      a, 15
                ld      (FORCLR), a
                ld      a, 4
                ld      (BAKCLR), a
                ld      a, 7
                ld      (BDRCLR), a
                call    CHGCLR
                ld      a, (RG7SAV)
                ld      (CAP+20), a
                ld      bc, $F107           ; B = $F1, C = R#7
                call    WRTVDP
                ld      a, (RG7SAV)
                ld      (CAP+21), a
                ; --- 4: sprites ----------------------------------------------------------
                call    GSPSIZ
                ld      (CAP+22), a
                ld      a, (RG1SAV)
                or      2
                ld      b, a
                ld      c, 1
                call    WRTVDP
                call    GSPSIZ
                ld      (CAP+23), a
                ld      a, 5
                call    CALPAT
                ld      (CAP+24), hl
                ld      a, 5
                call    CALATR
                ld      (CAP+26), hl
                call    CLRSPR
                ld      hl, (T32ATR)
                call    RDVRM
                ld      (CAP+28), a         ; sprite 0: Y
                inc     hl
                inc     hl
                call    RDVRM
                ld      (CAP+29), a         ; pattern number
                inc     hl
                call    RDVRM
                ld      (CAP+30), a         ; colour
                ld      a, (RG1SAV)
                ld      (CAP+31), a
                ; --- 5: SCREEN 2 and 3 ---------------------------------------------------
                ld      a, 2
                call    CHGMOD
                ld      de, CAP+32
                call    shadows
                ld      hl, GRPNAM
                ld      de, CAP+40
                ld      bc, 10
                ldir
                ld      hl, (GRPNAM)
                ld      de, $0101
                add     hl, de
                call    RDVRM
                ld      (CAP+50), a
                ld      a, 3
                call    CHGMOD
                ld      de, CAP+51
                call    shadows
                ld      hl, MLTNAM
                ld      de, CAP+59
                ld      bc, 10
                ldir
                ; --- 6: SCREEN 1 again --------------------------------------------------
                ld      a, 1
                call    CHGMOD
                ld      de, CAP+69
                call    shadows
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; shadows -- (DE..DE+7) := RG0SAV..RG7SAV
shadows:
                ld      hl, RG0SAV
                ld      bc, 8
                ldir
                ret

word:           db      "ZEROBA"
