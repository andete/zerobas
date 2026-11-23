; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK4A -- D-TRSPEC (2026-11-23, tr6): the phase sweep (probes/bios/spec/xtrdsk4.inc) of SELDSK 1 + DSKRST on the
; Z80, 2400 trials (a little more than one frame of 26-T-state steps).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdsk4a.asm --row turbor
;
; @disk empty
; @cap A000
; @caplen 100
; @timeout 200

SELB    equ     1
R800    equ     0
ALLOCEACH equ   0
NK      equ     2400
                include "probes/bios/spec/xtrdsk4.inc"
