; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; b1diag -- D-BIOSLADDER B1 diagnostic: during a cartridge's INIT, does the
; keyboard matrix ever show the typed keys (NEWKEY), and does KEYBUF fill?
; CAP+0..10: OR over ~200 frames of the PRESSED bits (complemented NEWKEY rows);
; CAP+11: 1 if PUTPNT ever left GETPNT; CAP+12/13: JIFFY delta.
; @matrix 2 40
; @timeout 40
NEWKEY  equ     $FBE5
GETPNT  equ     $F3FA
PUTPNT  equ     $F3F8
JIFFY   equ     $FC9E
KILBUF  equ     $0156
DONE    equ     $E000
CAP     equ     $E001
KEYRDY  equ     $E100

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, 31
                ld      (hl), 0
                ldir
                call    KILBUF
                ld      hl, (JIFFY)
                ld      (tmp), hl
                ld      a, 1
                ld      (KEYRDY), a
                ld      b, 200
frame:
                ei
                halt
                push    bc
                ld      hl, NEWKEY
                ld      de, CAP
                ld      b, 11
row:
                ld      a, (hl)
                cpl
                ex      de, hl
                or      (hl)
                ld      (hl), a
                ex      de, hl
                inc     hl
                inc     de
                djnz    row
                ld      hl, (PUTPNT)
                ld      de, (GETPNT)
                or      a
                sbc     hl, de
                jr      z, same
                ld      a, 1
                ld      (CAP+11), a
same:
                pop     bc
                djnz    frame
                ld      hl, (JIFFY)
                ld      de, (tmp)
                or      a
                sbc     hl, de
                ld      (CAP+12), hl
                ld      a, $A5
                ld      (DONE), a
lp:             jr      lp
tmp             equ     $E200
