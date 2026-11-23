; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK2C -- D-TRSPEC (2026-11-23, tr6): DSKRST's interrupt state on the turbo R, one variation.
; xbsys2.asm's 17 cases verbatim but IX = IY = 0 at entry: do the entry IX / IY matter?
;
; Frame, step and record format: probes/bios/spec/xtrdsk_body.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdsk2c.asm --row turbor
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.
;
; @disk empty
; @cap A000
; @caplen 121
; @cpusnap C100 A80B
; @timeout 60

                include "probes/bios/spec/xtrdsk_body.inc"

steps:
                db      $2B, 0
                dw      $0B17, $07EA
                db      $2A, 0
                dw      $0000, $0000
                db      $2B, 0
                dw      $0D01, $07EA
                db      $2A, 0
                dw      $0000, $0000
                db      $2B, 0
                dw      $0001, $07EA
                db      $2B, 0
                dw      $0100, $07EA
                db      $2B, 0
                dw      $0120, $07EA
                db      $2D, 0
                dw      $0000, $1800
                db      $2D, 0
                dw      $0000, $003C
                db      $2D, 0
                dw      $3C00, $0000
                db      $1B, 0
                dw      $0000, $0000
                db      $1B, 0
                dw      $0001, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $19, 0
                dw      $0000, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $19, 0
                dw      $0000, $0000
                db      $18, 0
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
