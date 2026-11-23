; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XLIN -- docs/bios/PINLIN.md round 1 (2026-11-17): the line-input calls PINLIN ($00AE), QINLIN ($00B4) and INLIN
; ($00B1) on the VG-8020 against zerobas, fed by ONE typed burst (@type-ready: Tcl turns \r / \b into Enter / BS; typed once
; INITXT has returned and the probe sets KEYREADY -- D-MSX1ON2: a fixed @type-at 4 fired before the NMS 8250 /
; FS-A1WSX reached the program) that
; waits in the key buffer; six calls in a row consume it, each on its own screen row:
;   1 PINLIN at (1, 3), an empty row             "AB" Enter
;   2 QINLIN at (1, 5), an empty row             "CD" Enter
;   3 PINLIN at (4, 7), "XYZ" written in cols 1-3 "Q" Enter
;   4 INLIN  at (4, 9), "XYZ" written in cols 1-3 "Q" Enter
;   5 PINLIN at (1, 11), an empty row            "AB" BS "C" Enter
;   6 PINLIN at (1, 13), "XYZ" written in cols 1-3, Enter alone
; The screen: CNSDFG 0, LINL40 40, INITXT (docs/bios/INITXT.md), CSRSW 0; the pre-written cells through WRTVRM.
; The capture (CAP = C001): +0 STAGE (the number of calls returned), then per call 29 bytes from +1: HL (2), F,
; CSRX, CSRY, BUF ($F55E) 12 bytes, the call's row's first 12 cells; then the sentinel $C3.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xlin.asm --row nodisk
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM / WRTVRM.
;
; @cap C000
; @type-ready AB\rCD\rQ\rQ\rAB\bC\r\r
; @timeout 60

RDVRM   equ     $004A
WRTVRM  equ     $004D
INITXT  equ     $006C
PINLIN  equ     $00AE
INLIN   equ     $00B1
QINLIN  equ     $00B4
LINL40  equ     $F3AE
CSRY    equ     $F3DC
CSRX    equ     $F3DD
CNSDFG  equ     $F3DE
CSRSW   equ     $FCA9
BUF     equ     $F55E

DONE    equ     $C000
CAP     equ     $C001
STAGE   equ     CAP
ptr     equ     $EF00
crow    equ     $EF02
rHL     equ     $EF04
rF      equ     $EF06

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
                xor     a
                ld      (CNSDFG), a
                ld      (CSRSW), a
                ld      a, 40
                ld      (LINL40), a
                call    INITXT
                ld      a, 1                    ; KEYREADY: the harness types the burst now (@type-ready)
                ld      ($C100), a
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      ix, calls
c_lp:
                ld      a, (ix+0)
                cp      $FF
                jr      z, c_done
                ld      a, (ix+2)               ; the row
                ld      (crow), a
                ld      a, (ix+3)               ; pre-write "XYZ" in cols 1-3?
                or      a
                call    nz, xyz
                ld      a, (ix+1)
                ld      (CSRX), a
                ld      a, (crow)
                ld      (CSRY), a
                ld      l, (ix+4)
                ld      h, (ix+5)
                push    ix
                call    jphl
                push    af
                pop     bc
                ld      (rHL), hl
                ld      a, c
                ld      (rF), a
                pop     ix
                call    record
                ld      a, (STAGE)
                inc     a
                ld      (STAGE), a
                ld      de, 6
                add     ix, de
                jr      c_lp
c_done:
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

jphl:
                jp      (hl)

; rowaddr -- HL := the name-table address of (crow)'s column 1
rowaddr:
                ld      a, (crow)
                ld      b, a
                ld      hl, 0
                ld      de, 40
                dec     b
                ret     z
ra_lp:
                add     hl, de
                djnz    ra_lp
                ret

xyz:
                call    rowaddr
                ld      a, 'X'
                call    WRTVRM
                inc     hl
                ld      a, 'Y'
                call    WRTVRM
                inc     hl
                ld      a, 'Z'
                jp      WRTVRM

record:
                ld      hl, (rHL)
                ld      a, l
                call    emit
                ld      a, h
                call    emit
                ld      a, (rF)
                call    emit
                ld      a, (CSRX)
                call    emit
                ld      a, (CSRY)
                call    emit
                ld      hl, BUF
                ld      b, 12
rb_lp:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    rb_lp
                call    rowaddr
                ld      b, 12
rr_lp:
                push    bc
                push    hl
                call    RDVRM
                call    emit
                pop     hl
                pop     bc
                inc     hl
                djnz    rr_lp
                ret

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; per call: kind (unused, 0), CSRX, CSRY, pre-write XYZ, the entry (2); $FF ends
calls:
                db      0, 1, 3, 0
                dw      PINLIN
                db      0, 1, 5, 0
                dw      QINLIN
                db      0, 4, 7, 1
                dw      PINLIN
                db      0, 4, 9, 1
                dw      INLIN
                db      0, 1, 11, 0
                dw      PINLIN
                db      0, 1, 13, 1
                dw      PINLIN
                db      $FF
