; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHPUT3 -- docs/bios/CHPUT.md ROUND 3 (2026-11-17): the five items its second fresh review found
; NOT measured, plus the A after an ESC / prefix call. CHPUT called directly; SCREEN 0 width 40.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput3.asm --row nodisk
; Positions 0-based (row, column); CSRX / CSRY in the records are the BIOS's 1-based cells.
; The capture: CAP+0 LINLEN, +1 $A5 when finished, +2 CRTCNT, +3 CNSDFG; records from CAP+4:
;   G1 ESC Y + byte 1   5 sequences (seqs below), after "xx" CR: CSRX, CSRY after EVERY byte (2 B a
;                       byte; 6 bytes a sequence: 12 B each).                                  @ +4
;   G2 ESC x / ESC y    256 x (ESC y '4', ESC y '5', then ESC x v): ($FCA9), ($FCAA) after; then
;                       256 x (ESC x '4', ESC x '5', then ESC y v): the same.  2 B each.        @ +64
;   G3 DEL / BS wrap    6 cases: a clear; row 9 = 40 'z' printed (it wraps: a continued row), or
;                       only (9, 38) = 'z' (no wrap); the cursor to (10, 0); then 8 / 29 / 127.
;                       8 B: CSRX, CSRY, cells (9, 38) (9, 39) (10, 0) (10, 1), LINTTB[9], [10]. @ +1088
;   G4 ESC A..D edges   key line off / on x the 4 corners x ESC A / B / C / D: a clear, 'a'+r at
;                       (r, 0), the cursor to the corner, the escape. 26 B: CSRX, CSRY, the
;                       cell (r, 0) for r = 0..23.                                             @ +1136
;   G5 edits, key on    DSPFNK; the 8 operations of XCHPUT2's G4 (ESC L, M, J, K, E, j, l, 12) on
;                       rows filled 'a'+r at columns 0..38, the cursor at (10, 20). 53 B: CSRX,
;                       CSRY, cells (r, 0) and (r, 38) for r = 0..23, then (10, 19..21).        @ +1968
;   G6 A after          CHPUT 27, then the A it returned; CHPUT 1, then the A. 1 B each.        @ +2392
; Total 2398 B.
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM read back
; through the published RDVRM.
;
; @cap C000
; @caplen 095E
; @timeout 120

RDVRM   equ     $004A
INITXT  equ     $006C
CHPUT   equ     $00A2
ERAFNK  equ     $00CC
DSPFNK  equ     $00CF
LINL40  equ     $F3AE
LINLEN  equ     $F3B0
CRTCNT  equ     $F3B1
CSRY    equ     $F3DC
CSRX    equ     $F3DD
CNSDFG  equ     $F3DE
LINTTB  equ     $FBB2
CSRSW   equ     $FCA9

DONE    equ     $C000
CAP     equ     $C001
CAPLEN  equ     2398
ptr     equ     $EF00
i1      equ     $EF02
i2      equ     $EF03
i3      equ     $EF04

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, CAPLEN - 1
                ld      (hl), 0
                ldir
                ld      a, 40
                ld      (LINL40), a
                call    INITXT
                call    ERAFNK
                ld      a, (LINLEN)
                ld      (CAP+0), a
                ld      a, (CRTCNT)
                ld      (CAP+2), a
                ld      a, (CNSDFG)
                ld      (CAP+3), a
                ld      hl, CAP+4
                ld      (ptr), hl

; ---- G1: ESC Y with byte 1, the cursor after every byte ------------------------------------
                ld      hl, seqs
g1_seq:
                ld      a, (hl)
                or      a
                jr      z, g1_done
                push    hl
                ld      hl, flush
                call    puts
                pop     hl
                ld      b, 6
g1_byte:
                ld      a, (hl)
                inc     hl
                push    hl
                push    bc
                call    CHPUT
                call    cur
                pop     bc
                pop     hl
                djnz    g1_byte
                jr      g1_seq
g1_done:

; ---- G2: ESC x v from both cells set; ESC y v from both cleared ---------------------------
                ld      a, 'x'
                ld      (i1), a
g2_kind:
                xor     a
                ld      (i2), a
g2_lp:
                ld      hl, flush
                call    puts
                ld      a, (i1)                 ; the OTHER command first, '4' then '5'
                xor     1                       ; 'x' <-> 'y'
                ld      (i3), a
                call    esc_k4
                ld      a, (i3)
                ld      c, '5'
                call    esc_kv
                ld      a, (i1)
                ld      hl, i2
                ld      c, (hl)
                call    esc_kv
                ld      a, (CSRSW)
                call    emit
                ld      a, (CSRSW+1)
                call    emit
                ld      a, (i2)
                inc     a
                ld      (i2), a
                jr      nz, g2_lp
                ld      a, (i1)
                cp      'x'
                ld      a, 'y'
                ld      (i1), a
                jr      z, g2_kind
                ld      a, 'x'                  ; the cursor display OFF: with it on, the cell
                ld      c, '5'                  ; under the cursor reads 255 (the cursor glyph),
                call    esc_kv                  ; which hid G3's blank (first run, XCH3_run1.out)
                ld      a, 'x'
                ld      c, '4'
                call    esc_kv

; ---- G3: DEL / BS wrapping onto a row's end -------------------------------------------------
                xor     a
                ld      (i1), a                 ; 0..5: (wrapped?) x (8, 29, 127)
g3_lp:
                ld      a, 12
                call    CHPUT
                ld      a, (i1)
                cp      3
                jr      nc, g3_nowrap
                ld      de, 9*256 + 0
                call    pos
                ld      b, 40
g3_fill:
                push    bc
                ld      a, 'z'
                call    CHPUT
                pop     bc
                djnz    g3_fill
                jr      g3_go
g3_nowrap:
                ld      de, 9*256 + 38
                call    pos
                ld      a, 'z'
                call    CHPUT
g3_go:
                ld      de, 10*256 + 0
                call    pos
                ld      a, (i1)
                ld      hl, g3bytes
g3_mod:
                cp      3
                jr      c, g3_pick
                sub     3
                jr      g3_mod
g3_pick:
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, (hl)
                call    CHPUT
                call    cur
                ld      de, 9*256 + 38
                call    vr
                call    emit
                inc     e
                call    vr
                call    emit
                ld      de, 10*256 + 0
                call    vr
                call    emit
                inc     e
                call    vr
                call    emit
                ld      a, (LINTTB+9)
                call    emit
                ld      a, (LINTTB+10)
                call    emit
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      6
                jr      nz, g3_lp

; ---- G4: ESC A / B / C / D at the corners, key line off then on ---------------------------
                xor     a
                ld      (i1), a
g4_kl:
                ld      a, (i1)
                or      a
                jr      nz, g4_on
                call    ERAFNK
                jr      g4_set
g4_on:
                call    DSPFNK
g4_set:
                xor     a
                ld      (i2), a                 ; corner
g4_corner:
                xor     a
                ld      (i3), a                 ; A..D
g4_cmd:
                ld      a, 12
                call    CHPUT
                ld      d, 0
g4_mark:
                ld      e, 0
                call    pos
                ld      a, d
                add     a, 'a'
                push    de
                call    CHPUT
                pop     de
                inc     d
                ld      a, d
                cp      24
                jr      nz, g4_mark
                ld      a, (i2)
                ld      hl, corners
                add     a, a
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      d, (hl)
                inc     hl
                ld      e, (hl)
                call    pos
                ld      a, 27
                call    CHPUT
                ld      a, (i3)
                add     a, 'A'
                call    CHPUT
                call    cur
                ld      d, 0
                ld      e, 0
g4_rd:
                call    vr
                call    emit
                inc     d
                ld      a, d
                cp      24
                jr      nz, g4_rd
                ld      a, (i3)
                inc     a
                ld      (i3), a
                cp      4
                jr      nz, g4_cmd
                ld      a, (i2)
                inc     a
                ld      (i2), a
                cp      4
                jr      nz, g4_corner
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      2
                jp      nz, g4_kl

; ---- G5: the line and screen edits with the key line ON -----------------------------------
                call    DSPFNK
                xor     a
                ld      (i1), a
g5_lp:
                ld      a, 12
                call    CHPUT
                ld      d, 0
g5_fill:
                ld      e, 0
                call    pos
                ld      b, 39
g5_row:
                push    bc
                push    de
                ld      a, d
                add     a, 'a'
                call    CHPUT
                pop     de
                pop     bc
                djnz    g5_row
                inc     d
                ld      a, d
                cp      24
                jr      nz, g5_fill
                ld      de, 10*256 + 20
                call    pos
                ld      a, (i1)
                ld      hl, g5ops
                add     a, a
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, (hl)
                call    CHPUT
                inc     hl
                ld      a, (hl)
                or      a
                call    nz, CHPUT
                call    cur
                ld      d, 0
g5_rd:
                ld      e, 0
                call    vr
                call    emit
                ld      e, 38
                call    vr
                call    emit
                inc     d
                ld      a, d
                cp      24
                jr      nz, g5_rd
                call    cells3
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      8
                jp      nz, g5_lp
                call    ERAFNK

; ---- G6: the A an ESC / prefix call returns -------------------------------------------------
                ld      hl, flush
                call    puts
                ld      a, 27
                call    CHPUT
                call    emit
                ld      a, 'K'                  ; complete it
                call    CHPUT
                ld      a, 1
                call    CHPUT
                call    emit
                ld      a, 'Q'                  ; complete it
                call    CHPUT

                ld      hl, tidy
                call    puts
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; esc_k4 -- ESC (A) '4';  esc_kv -- ESC (A) (C)
esc_k4:
                ld      c, '4'
esc_kv:
                push    bc
                push    af
                ld      a, 27
                call    CHPUT
                pop     af
                call    CHPUT
                pop     bc
                ld      a, c
                jp      CHPUT

; pos -- ESC Y to (D = row, E = column), 0-based. Keeps DE.
pos:
                push    de
                ld      a, 27
                call    CHPUT
                ld      a, 'Y'
                call    CHPUT
                pop     de
                push    de
                ld      a, d
                add     a, 32
                call    CHPUT
                pop     de
                push    de
                ld      a, e
                add     a, 32
                call    CHPUT
                pop     de
                ret

; vr -- A := the VRAM cell at (D = row, E = column), name table at 0, 40 a row. Keeps DE.
vr:
                push    de
                push    hl
                ld      l, d
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                push    hl
                add     hl, hl
                add     hl, hl
                pop     bc
                add     hl, bc
                ld      d, 0
                add     hl, de
                call    RDVRM
                pop     hl
                pop     de
                ret

; emit -- (ptr) := A, ptr += 1. Keeps every register but F.
emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

cur:
                ld      a, (CSRX)
                call    emit
                ld      a, (CSRY)
                jp      emit

cells3:
                ld      de, 10*256 + 19
                call    vr
                call    emit
                inc     e
                call    vr
                call    emit
                inc     e
                call    vr
                jp      emit

puts:
                ld      a, (hl)
                or      a
                ret     z
                push    hl
                call    CHPUT
                pop     hl
                inc     hl
                jr      puts

; G1's sequences: 6 bytes each, a 0 ends the list
seqs:           db      27, "Y", 1, 32+5, "A", "B"
                db      27, "Y", 32+5, 1, "A", "B"
                db      27, "Y", 1, 1, 32+5, 32+5
                db      1, 27, "Y", 32+5, 32+5, "A"
                db      27, "Y", 1, "A", 32+5, "B"
                db      0
flush:          db      "xx", 13, 0
tidy:           db      "xx", 13, 10, 0
corners:        db      0, 0,  0, 39,  23, 0,  23, 39
g3bytes:        db      8, 29, 127
g5ops:          db      27, 'L',  27, 'M',  27, 'J',  27, 'K',  27, 'E',  27, 'j',  27, 'l',  12, 0
