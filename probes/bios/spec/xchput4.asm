; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHPUT4 -- docs/bios/CHPUT.md ROUND 4 (2026-11-17): the third fresh review's findings.
;   - A NEUTRAL SETUP. Rounds 2 / 3 placed the cursor with ESC Y and wrote the markers with CHPUT, so
;     where the two machines' ESC Y differs (the key line on) every case STARTED somewhere else and the
;     differences were the setup's. Here every case: "xx" CR 12 (clears any pending escape, then the
;     screen; with the key line on the key row stays), the markers written straight into VRAM
;     (WRTVRM), the cursor-display cells $FCA9 / $FCAA := 0, and CSRY / CSRX written DIRECTLY.
;   - Column 40 (0-based 39) is filled, so a blank there is evidence.
; CHPUT called directly; SCREEN 0 width 40. Positions 0-based (row, col); CSRX / CSRY 1-based.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput4.asm --row nodisk
;
; Markers: row r, column 0 = 'a'+r, column 38 = 'A'+r, column 39 = '0'+r (G2 also 19, 20, 21 =
; 'P', 'Q', 'R'); every other cell blank.
; The capture: CAP+0 LINLEN, +1 $A5 when finished, +2 CRTCNT, +3 CNSDFG; records from CAP+4:
;   G1 EDGES  key line off: starts (0,0) (0,39) (23,0) (23,39); key line on: (0,0) (0,39) (22,0) (22,39)
;             (23,0) (23,39) -- the last two ON the key row. x 14 sequences: 8, 29, 127, 28, 30, 31, 10,
;             13, 9, 'A', ESC A, ESC B, ESC C, ESC D.  140 cases x 42 B: CSRX, CSRY, A, LINTTB (24),
;             then columns 0 / 38 / 39 of rows 0, s-1, s, s+1, 23 (s = the start row; clamped to 0..23).
;                                                                                     @ +4
;   G2 EDITS  key line off, then on: ESC L, M, J, K, E, j, l, 12 with the cursor at (10, 20).
;             16 cases x 170 B: CSRX, CSRY, LINTTB (24), then columns 0, 19, 20, 21, 38, 39 of every
;             row 0..23 (row-major).                                                   @ +5884
;   G3 SEPARATE  12 cases x 9 B: CSRX, CSRY, A, row 10 columns 18..22, the cell (9, 39). The cursor at
;             (10, 20) (cases 0..7, 11) or (10, 0) (8: DEL onto a row that does NOT continue), key
;             line off but for 9..10:
;              0 ESC Z A   1 ESC ~ A   2 ESC DEL A   3 ESC x 1 A   4 ESC x ESC A   5 ESC y 1 A
;              6 ESC y ESC A   7 prefix DEL A   8 DEL from (10,0)   9 key on: ESC Y 55 52
;             10 key on: ESC Y 200 52   11 ESC Y 54 52 (key off)                       @ +8604
; Total 8712 B.
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM / WRTVRM.
;
; @cap C000
; @caplen 2208
; @timeout 240

RDVRM   equ     $004A
WRTVRM  equ     $004D
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
CAPLEN  equ     8712
ptr     equ     $EF00
i1      equ     $EF02
i2      equ     $EF03
i3      equ     $EF04
srow    equ     $EF05
scol    equ     $EF06
rows5   equ     $EF08                   ; 5 row numbers for a G1 record
keyst   equ     $EF10

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

; ---- G1: the edges ---------------------------------------------------------------------------
                ld      hl, g1starts
                ld      (gstart), hl
g1_start:
                ld      hl, (gstart)
                ld      a, (hl)
                cp      $FF
                jp      z, g1_done
                ld      (keyst), a
                inc     hl
                ld      a, (hl)
                ld      (srow), a
                inc     hl
                ld      a, (hl)
                ld      (scol), a
                inc     hl
                ld      (gstart), hl
                ld      a, (keyst)
                or      a
                call    z, ERAFNK
                ld      a, (keyst)
                or      a
                call    nz, DSPFNK
                ld      hl, g1seqs
                ld      (gseq), hl
g1_seq:
                ld      hl, (gseq)
                ld      a, (hl)
                or      a
                jp      z, g1_start
                call    neutral
                call    mark3
                call    place
                ld      hl, (gseq)
                call    sendseq
                ld      (gseq), hl
                ld      (lasta), a
                call    cur
                ld      a, (lasta)
                call    emit
                call    lt24
                ; rows 0, s-1, s, s+1, 23
                ld      a, (srow)
                ld      b, a
                xor     a
                ld      (rows5+0), a
                ld      a, b
                or      a
                jr      z, g1_r1
                dec     a
g1_r1:
                ld      (rows5+1), a
                ld      a, b
                ld      (rows5+2), a
                cp      23
                jr      nc, g1_r3
                inc     a
g1_r3:
                ld      (rows5+3), a
                ld      a, 23
                ld      (rows5+4), a
                ld      hl, rows5
                ld      b, 5
g1_rows:
                ld      d, (hl)
                push    hl
                push    bc
                ld      e, 0
                call    vr
                call    emit
                ld      e, 38
                call    vr
                call    emit
                ld      e, 39
                call    vr
                call    emit
                pop     bc
                pop     hl
                inc     hl
                djnz    g1_rows
                jp      g1_seq
g1_done:

; ---- G2: the edits, key line off then on ----------------------------------------------------
                xor     a
                ld      (i1), a
g2_kl:
                ld      a, (i1)
                or      a
                call    z, ERAFNK
                ld      a, (i1)
                or      a
                call    nz, DSPFNK
                xor     a
                ld      (i2), a
g2_op:
                call    neutral
                call    mark3
                call    markpqr
                ld      a, 10
                ld      (srow), a
                ld      a, 20
                ld      (scol), a
                call    place
                ld      a, (i2)
                ld      hl, g2ops
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
                call    lt24
                ld      d, 0
g2_row:
                ld      hl, g2cols
                ld      b, 6
g2_col:
                ld      e, (hl)
                push    hl
                push    bc
                call    vr
                call    emit
                pop     bc
                pop     hl
                inc     hl
                djnz    g2_col
                inc     d
                ld      a, d
                cp      24
                jr      nz, g2_row
                ld      a, (i2)
                inc     a
                ld      (i2), a
                cp      8
                jr      nz, g2_op
                ld      a, (i1)
                inc     a
                ld      (i1), a
                cp      2
                jp      nz, g2_kl
                call    ERAFNK

; ---- G3: the separating cases ------------------------------------------------------------------
                ld      hl, g3cases
                ld      (gseq), hl
g3_case:
                ld      hl, (gseq)
                ld      a, (hl)                 ; key line, $FF = the end
                cp      $FF
                jp      z, g3_done
                or      a
                call    z, ERAFNK
                ld      hl, (gseq)
                ld      a, (hl)
                or      a
                call    nz, DSPFNK
                ld      hl, (gseq)
                inc     hl
                ld      a, (hl)                 ; the start column (row 10)
                ld      (scol), a
                inc     hl
                ld      (gseq), hl
                ld      a, 10
                ld      (srow), a
                call    neutral
                call    markpqr
                ld      de, 9*256 + 39
                ld      a, 'z'
                call    vw
                call    place
                ld      hl, (gseq)
                call    sendseq
                ld      (gseq), hl
                ld      (lasta), a
                call    cur
                ld      a, (lasta)
                call    emit
                ld      d, 10
                ld      e, 18
g3_cells:
                call    vr
                call    emit
                inc     e
                ld      a, e
                cp      23
                jr      nz, g3_cells
                ld      de, 9*256 + 39
                call    vr
                call    emit
                jp      g3_case
g3_done:
                call    ERAFNK
                ld      hl, tidy
                call    puts
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; neutral -- "xx" CR 12 (any pending escape completed, then the clear), the cursor-display cells 0
neutral:
                ld      hl, flush
                call    puts
                xor     a
                ld      (CSRSW), a
                ld      (CSRSW+1), a
                ret

; mark3 -- columns 0 / 38 / 39 of every TEXT row r: 'a'+r, 'A'+r, '0'+r (VRAM directly)
mark3:
                ld      a, (CNSDFG)
                or      a
                ld      b, 24
                jr      z, m3_n
                ld      b, 23
m3_n:
                ld      d, 0
m3_lp:
                push    bc
                ld      e, 0
                ld      a, d
                add     a, 'a'
                call    vw
                ld      e, 38
                ld      a, d
                add     a, 'A'
                call    vw
                ld      e, 39
                ld      a, d
                add     a, '0'
                call    vw
                pop     bc
                inc     d
                djnz    m3_lp
                ret

; markpqr -- P Q R at (10, 19..21)
markpqr:
                ld      de, 10*256 + 19
                ld      a, 'P'
                call    vw
                inc     e
                ld      a, 'Q'
                call    vw
                inc     e
                ld      a, 'R'
                jp      vw

; place -- CSRY := srow + 1, CSRX := scol + 1, directly
place:
                ld      a, (srow)
                inc     a
                ld      (CSRY), a
                ld      a, (scol)
                inc     a
                ld      (CSRX), a
                ret

; sendseq -- HL -> a length byte then the bytes: CHPUT each; out HL past it, A = the last CHPUT's A
sendseq:
                ld      b, (hl)
                inc     hl
ss_lp:
                ld      a, (hl)
                inc     hl
                push    hl
                push    bc
                call    CHPUT
                pop     bc
                pop     hl
                djnz    ss_lp
                ret

; lt24 -- emit LINTTB's 24 bytes
lt24:
                ld      hl, LINTTB
                ld      b, 24
lt_lp:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    lt_lp
                ret

; vw -- the VRAM cell at (D = row, E = column) := A. Keeps DE.
vw:
                push    af
                call    vaddr
                pop     af
                push    de
                call    WRTVRM
                pop     de
                ret

; vr -- A := the VRAM cell at (D = row, E = column). Keeps DE.
vr:
                call    vaddr
                push    de
                call    RDVRM
                pop     de
                ret

; vaddr -- HL := D * 40 + E. Keeps DE.
vaddr:
                push    de
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
                pop     de
                ret

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

puts:
                ld      a, (hl)
                or      a
                ret     z
                push    hl
                call    CHPUT
                pop     hl
                inc     hl
                jr      puts

gstart:         equ     $EF12
gseq:           equ     $EF14
lasta:          equ     $EF16

flush:          db      "xx", 13, 12, 0
tidy:           db      "xx", 13, 10, 0
; G1 starts: key, row, col; $FF ends
g1starts:       db      0, 0, 0,   0, 0, 39,   0, 23, 0,   0, 23, 39
                db      1, 0, 0,   1, 0, 39,   1, 22, 0,   1, 22, 39,   1, 23, 0,   1, 23, 39
                db      $FF
; G1 sequences: length, bytes; 0 ends
g1seqs:         db      1, 8,  1, 29,  1, 127,  1, 28,  1, 30,  1, 31,  1, 10,  1, 13,  1, 9,  1, "A"
                db      2, 27, "A",  2, 27, "B",  2, 27, "C",  2, 27, "D"
                db      0
g2ops:          db      27, 'L',  27, 'M',  27, 'J',  27, 'K',  27, 'E',  27, 'j',  27, 'l',  12, 0
g2cols:         db      0, 19, 20, 21, 38, 39
; G3 cases: key, start column (row 10), length, bytes
g3cases:        db      0, 20, 3, 27, "Z", "A"
                db      0, 20, 3, 27, "~", "A"
                db      0, 20, 3, 27, 127, "A"
                db      0, 20, 4, 27, "x", 1, "A"
                db      0, 20, 5, 27, "x", 27, "A", "A"
                db      0, 20, 4, 27, "y", 1, "A"
                db      0, 20, 5, 27, "y", 27, "A", "A"
                db      0, 20, 3, 1, 127, "A"
                db      0, 0, 1, 127
                db      1, 20, 4, 27, "Y", 55, 52
                db      1, 20, 4, 27, "Y", 200, 52
                db      0, 20, 4, 27, "Y", 54, 52
                db      $FF
