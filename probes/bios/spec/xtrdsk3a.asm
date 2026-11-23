; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK3A -- D-TRSPEC (2026-11-23, tr6): DSKRST's interrupt state on the turbo R, one variation.
; A coarse sweep of DSKRST's timing: ALLOC E 0 / E 1 (as xbsys2), then 16 groups k = 0..15 of SELDSK 1, a DI
; delay of 1 + 150k x 26 T-states (~1/16 frame apart), DSKRST (entered DI, IX / IY as xbsys2), and a 4096-read
; LD A,I trace under the state DSKRST left (OP $F2).
;
; Frame, step and record format: probes/bios/spec/xtrdsk_body.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdsk3a.asm --row turbor
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.
;
; @disk empty
; @cap A000
; @caplen 572
; @cpusnap C100 A80B
; @timeout 60

                include "probes/bios/spec/xtrdsk_body.inc"

steps:
                db      $1B, 2
                dw      $0000, $0000
                db      $1B, 2
                dw      $0001, $0000
                db      $FE, 0
                dw      $0000, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0001, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0001, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0097, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0002, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $012D, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0003, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $01C3, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0004, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0259, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0005, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $02EF, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0006, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0385, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0007, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $041B, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0008, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $04B1, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0009, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0547, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000A, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $05DD, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000B, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0673, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000C, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0709, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000D, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $079F, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000E, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $0835, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000F, $0000
                db      $0E, 2
                dw      $0001, $0000
                db      $F3, 0
                dw      $08CB, $0000
                db      $0D, 2
                dw      $0000, $0000
                db      $F2, 0
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
