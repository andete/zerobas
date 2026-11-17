; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHPUT -- docs/bios/CHPUT.md, the text-region pilot of docs/spec-method.md (2026-11-17): the
; CHPUT MATRIX on the main-BIOS reference, the VG-8020, against zerobas. CHPUT is CALLED
; DIRECTLY by this cartridge (the page's DRAFT 1 was read through the CF-3300's BDOS).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput.asm --row nodisk
; This directory is spec EVIDENCE: biosl-acceptance's --all does not run it.
;
; INIT: LINL40 := 40, INITXT, CLS -- SCREEN 0, width 40. Before EVERY case:
;   CHPUT 'x' 'x' (completes any escape / prefix the case before left pending), CR,
;   ESC Y to row 10 column 19 (0-based), 'P' 'Q' 'R', ESC Y to row 10 column 20
; -- the cursor on the 'Q' (CSRY 11, CSRX 21, 1-based), P / Q / R in the cells left of, at
; and right of it. Then the case, and 6 bytes: CSRX, CSRY, the A CHPUT returned, and the
; three cells (VRAM, read with RDVRM) at row 10, columns 19 / 20 / 21.
; Modes, 256 cases each, v = 0..255:
;   0  CHPUT v
;   1  CHPUT ESC, then CHPUT v
;   2  CHPUT 1 (the graphic prefix), then CHPUT v
; Case n = mode * 256 + v at CAP + 2 + 6n; CAP+0 = LINLEN, CAP+1 = $A5 when the run finished.
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM read back
; through the published RDVRM.
;
; @cap C000
; @caplen 1202
; @timeout 90

RDVRM   equ     $004A
INITXT  equ     $006C
CHPUT   equ     $00A2
CLS     equ     $00C3
LINL40  equ     $F3AE
LINLEN  equ     $F3B0
CSRY    equ     $F3DC
CSRX    equ     $F3DD

DONE    equ     $C000
CAP     equ     $C001
CELL    equ     10 * 40 + 19            ; row 10, column 19 (0-based): 'P'
mode    equ     $D300                   ; RAM (the cartridge is ROM), clear of CAP..$D202
val     equ     $D301
ptr     equ     $D302

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP                 ; the block starts 0 on both machines
                ld      de, CAP+1
                ld      bc, $1201
                ld      (hl), 0
                ldir
                ld      a, 40
                ld      (LINL40), a
                call    INITXT
                call    CLS
                ld      a, (LINLEN)
                ld      (CAP+0), a
                ld      hl, CAP+2
                ld      (ptr), hl
                xor     a
                ld      (mode), a
mloop:
                xor     a
                ld      (val), a
vloop:
                ld      hl, setseq
                call    puts
                ld      a, (mode)
                or      a
                jr      z, m0
                dec     a
                ld      a, 27                   ; mode 1: ESC first
                jr      z, mpre
                ld      a, 1                    ; mode 2: the graphic prefix first
mpre:
                call    CHPUT
m0:
                ld      a, (val)
                call    CHPUT                   ; A after it: CHPUT's own answer
                call    rec
                ld      a, (val)
                inc     a
                ld      (val), a
                jr      nz, vloop
                ld      a, (mode)
                inc     a
                ld      (mode), a
                cp      3
                jr      c, mloop
                ld      hl, tidy
                call    puts
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; rec -- (ptr) := CSRX, CSRY, A, the cells at CELL, CELL+1, CELL+2; ptr += 6
rec:
                ld      b, a
                ld      hl, (ptr)
                ld      a, (CSRX)
                ld      (hl), a
                inc     hl
                ld      a, (CSRY)
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (ptr), hl
                ld      hl, CELL
                call    cell
                ld      hl, CELL+1
                call    cell
                ld      hl, CELL+2
cell:
                call    RDVRM
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                ret

; puts -- CHPUT each byte of the 0-terminated string at HL
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
tidy:           db      "xx", 13, 10, 0

