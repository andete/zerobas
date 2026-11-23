; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK2B -- D-TRSPEC (2026-11-23, tr6): DSKRST's interrupt state on the turbo R, one variation.
; xbsys2.asm's cases 10-16 only (ALLOC E 0 / E 1, SELDSK 1, CURDRV, DSKRST, CURDRV, LOGIN), IX / IY as
; xbsys2: is the SDATE / GDATE / STIME prefix needed?
;
; Frame, step and record format: probes/bios/spec/xtrdsk_body.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdsk2b.asm --row turbor
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.
;
; @disk empty
; @cap A000
; @caplen 77
; @cpusnap C100 A80B
; @timeout 60

                include "probes/bios/spec/xtrdsk_body.inc"

steps:
                db      $1B, 2
                dw      $0000, $0000
                db      $1B, 2
                dw      $0001, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $19, 2
                dw      $0000, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $19, 2
                dw      $0000, $0000
                db      $18, 2
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
