; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHPUT2 -- docs/bios/CHPUT.md ROUND 2 (2026-11-17): the separating cases its first fresh review
; asked for (docs/spec-method.md §5). CHPUT is called directly; SCREEN 0, width 40 (LINL40 := 40,
; INITXT at INIT). Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput2.asm --row nodisk
; This directory is spec EVIDENCE: biosl-acceptance's --all does not run it.
;
; Positions below are 0-based (row, column); CSRY / CSRX in the records are the BIOS's 1-based cells.
; The capture: CAP+0 LINLEN, +1 $A5 when finished, +2 CRTCNT, +3 CNSDFG at INIT; records from CAP+4:
;   G1 TAB     40 cases (c = 0..39): row 10 filled with 'o', the cursor at (10, c), TAB.
;              42 B: CSRX, CSRY, row 10's 40 cells.                                 @ +4
;   G2 EDGES   2 key-line states (0 ERAFNK, 1 DSPFNK) x 4 corners ((0,0) (0,39) (23,0) (23,39)) x 10
;              bytes (8, 29, 127, 28, 30, 31, 10, 13, 9, 'A'): a clear, 'a'+r at (r, 0) for every
;              row r, the cursor to the corner, the byte. 50 B: CSRX, CSRY, the cell at (r, 0) for
;              r = 0..23, LINTTB's 24 bytes ($FBB2).                                 @ +1684
;   G3 PENDING 2 kinds (ESC, the graphic prefix 1) x c = 0..31: the usual setup (P Q R at
;              (10, 19..21), the cursor on the Q), the kind, c, then 'A'. 5 B: CSRX, CSRY, the
;              three cells.                                                           @ +5684
;   G4 EDITS   8 operations (ESC L, ESC M, ESC J, ESC K, ESC E, ESC j, ESC l, 12), key line off:
;              every row r filled at columns 0..38 with 'a'+r, the cursor at (10, 20), the op.
;              53 B: CSRX, CSRY, the cells (r, 0) and (r, 38) for r = 0..23, then (10, 19..21). @ +6004
;   G5 ESC Y   v = 0..255 as the ROW parameter (column 32+5), then as the COLUMN parameter (row
;              32+5), each after "xx" CR. 2 B: CSRX, CSRY.                            @ +6428
;   G6 ESC x/y v = 0..255 after ESC x, then after ESC y, each after the usual setup; the state
;              CARRIES from case to case. 4 B: CSRX, CSRY, ($FCA9) CSRSW, ($FCAA).   @ +7452
; Total 9500 B (CAP+0 .. CAP+$251B).
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM read back
; through the published RDVRM.
;
; @cap C000
; @caplen 251C
; @timeout 240

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
CAPLEN  equ     9500
ptr     equ     $EF00                   ; RAM (the cartridge is ROM), clear of CAP's block
i1      equ     $EF02
i2      equ     $EF03
i3      equ     $EF04
i4      equ     $EF05

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP                 ; the block starts 0 on both machines
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

; ---- G1: TAB from every column ------------------------------------------------------------
                xor     a
                ld      (i1), a
g1_lp:
                ld      a, 12
                call    CHPUT
                ld      de, 10*256 + 0
                call    pos
                ld      b, 40
g1_fill:
                push    bc
                ld      a, 'o'
                call    CHPUT
                pop     bc
                djnz    g1_fill
                ld      d, 10
                ld      a, (i1)
                ld      e, a
                call    pos
                ld      a, 9
                call    CHPUT
                call    cur
                ld      d, 10
                ld      e, 0
g1_rd:
                call    vr
                call    emit
                inc     e
                ld      a, e
                cp      40
                jr      nz, g1_rd
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      40
                jr      nz, g1_lp

; ---- G2: the edges -------------------------------------------------------------------------
                xor     a
                ld      (i1), a                 ; key line: 0 off, 1 on
g2_kl:
                ld      a, (i1)
                or      a
                jr      nz, g2_on
                call    ERAFNK
                jr      g2_kset
g2_on:
                call    DSPFNK
g2_kset:
                xor     a
                ld      (i2), a                 ; corner 0..3
g2_corner:
                xor     a
                ld      (i3), a                 ; byte index 0..9
g2_byte:
                ld      a, 12
                call    CHPUT
                ld      d, 0
g2_mark:
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
                jr      nz, g2_mark
                ld      a, (i2)                 ; the corner
                ld      hl, corners
                add     a, a
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      d, (hl)
                inc     hl
                ld      e, (hl)
                call    pos
                ld      a, (i3)
                ld      hl, g2bytes
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, (hl)
                call    CHPUT
                call    cur
                ld      d, 0
                ld      e, 0
g2_rd:
                call    vr
                call    emit
                inc     d
                ld      a, d
                cp      24
                jr      nz, g2_rd
                ld      hl, LINTTB
                ld      b, 24
g2_lt:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    g2_lt
                ld      a, (i3)
                inc     a
                ld      (i3), a
                cp      10
                jr      nz, g2_byte
                ld      a, (i2)
                inc     a
                ld      (i2), a
                cp      4
                jr      nz, g2_corner
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      2
                jp      nz, g2_kl
                call    ERAFNK

; ---- G3: ESC / the prefix, a control code, then 'A' ----------------------------------------
                ld      a, 27
                ld      (i1), a                 ; the kind: 27, then 1
g3_kind:
                xor     a
                ld      (i2), a
g3_lp:
                call    setup
                ld      a, (i1)
                call    CHPUT
                ld      a, (i2)
                call    CHPUT
                ld      a, 'A'
                call    CHPUT
                call    cur
                call    cells3
                ld      a, (i2)
                inc     a
                ld      (i2), a
                cp      32
                jr      nz, g3_lp
                ld      a, (i1)
                cp      27
                ld      a, 1
                ld      (i1), a
                jr      z, g3_kind

; ---- G4: line / screen edits on a full pattern ---------------------------------------------
                xor     a
                ld      (i1), a
g4_lp:
                ld      a, 12
                call    CHPUT
                ld      d, 0
g4_fill:
                ld      e, 0
                call    pos
                ld      b, 39
g4_row:
                push    bc
                push    de
                ld      a, d
                add     a, 'a'
                call    CHPUT
                pop     de
                pop     bc
                djnz    g4_row
                inc     d
                ld      a, d
                cp      24
                jr      nz, g4_fill
                ld      de, 10*256 + 20
                call    pos
                ld      a, (i1)
                ld      hl, g4ops
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
g4_rd:
                ld      e, 0
                call    vr
                call    emit
                ld      e, 38
                call    vr
                call    emit
                inc     d
                ld      a, d
                cp      24
                jr      nz, g4_rd
                call    cells3
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      8
                jr      nz, g4_lp

; ---- G5: every byte as ESC Y's row, then as its column ------------------------------------
                xor     a
                ld      (i1), a                 ; 0: row parameter, 1: column parameter
g5_kind:
                xor     a
                ld      (i2), a
g5_lp:
                ld      hl, flush
                call    puts
                ld      a, 27
                call    CHPUT
                ld      a, 'Y'
                call    CHPUT
                ld      a, (i1)
                or      a
                jr      nz, g5_col
                ld      a, (i2)
                call    CHPUT
                ld      a, 32+5
                call    CHPUT
                jr      g5_rec
g5_col:
                ld      a, 32+5
                call    CHPUT
                ld      a, (i2)
                call    CHPUT
g5_rec:
                call    cur
                ld      a, (i2)
                inc     a
                ld      (i2), a
                jr      nz, g5_lp
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      2
                jr      nz, g5_kind

; ---- G6: ESC x v, then ESC y v -------------------------------------------------------------
                ld      a, 'x'
                ld      (i1), a
g6_kind:
                xor     a
                ld      (i2), a
g6_lp:
                call    setup
                ld      a, 27
                call    CHPUT
                ld      a, (i1)
                call    CHPUT
                ld      a, (i2)
                call    CHPUT
                call    cur
                ld      a, (CSRSW)
                call    emit
                ld      a, (CSRSW+1)
                call    emit
                ld      a, (i2)
                inc     a
                ld      (i2), a
                jr      nz, g6_lp
                ld      a, (i1)
                cp      'x'
                ld      a, 'y'
                ld      (i1), a
                jr      z, g6_kind

                ld      hl, tidy
                call    puts
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

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
                add     hl, hl              ; row * 8
                push    hl
                add     hl, hl
                add     hl, hl              ; row * 32
                pop     bc
                add     hl, bc              ; row * 40
                ld      d, 0
                add     hl, de              ; + column
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

; cur -- emit CSRX, CSRY
cur:
                ld      a, (CSRX)
                call    emit
                ld      a, (CSRY)
                jp      emit

; cells3 -- emit the cells (10, 19), (10, 20), (10, 21)
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

; setup -- "xx" CR, P Q R at (10, 19..21), the cursor on the Q
setup:
                ld      hl, setseq
puts:
                ld      a, (hl)
                or      a
                ret     z
                push    hl
                call    CHPUT
                pop     hl
                inc     hl
                jr      puts

setseq:         db      "xx", 13, 27, "Y", 32+10, 32+19, "PQR", 27, "Y", 32+10, 32+20, 0
flush:          db      "xx", 13, 0
tidy:           db      "xx", 13, 10, 0
corners:        db      0, 0,  0, 39,  23, 0,  23, 39
g2bytes:        db      8, 29, 127, 28, 30, 31, 10, 13, 9, 'A'
g4ops:          db      27, 'L',  27, 'M',  27, 'J',  27, 'K',  27, 'E',  27, 'j',  27, 'l',  12, 0
