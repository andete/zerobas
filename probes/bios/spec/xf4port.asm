; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XF4PORT -- D-MSX2SPEC, docs/msx2/main/RDRES.md / WRRES.md, the port rows (RR-1 / RR-2): I/O port $F4 read and written
; BY HAND (no BIOS call), so it runs on every machine. First thing at INIT: IN $F4 (what the boot left), then for each
; value v of the table: OUT ($F4), v; IN $F4 -- and once more after a second OUT of the same value.
; The capture (CAP = C001): +0 IN $F4 at INIT, +1.. per value: v, IN after; +1+2n $5A.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xf4port.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; an I/O port. No ROM byte read, no BIOS call.
;
; @cap C000
; @caplen 0040

DONE    equ     $C000
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                in      a, ($F4)
                ld      (CAP), a
                ld      hl, vals
                ld      de, CAP+1
lp:
                ld      a, (hl)
                cp      $EE
                jr      z, done
                ld      (de), a
                inc     de
                out     ($F4), a
                in      a, ($F4)
                ld      (de), a
                inc     de
                inc     hl
                jr      lp
done:
                ld      a, $5A
                ld      (de), a
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

vals:
                db      $00, $FF, $A5, $5A, $80, $7F, $01, $FE, $00
                db      $EE

                ds      $8000 - $, $FF
