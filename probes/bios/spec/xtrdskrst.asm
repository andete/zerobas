; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSKRST -- D-TRSPEC (2026-11-23, tr6): DSKRST's interrupt state on the turbo R, one variation.
; The black-box variations of xbsys2's case 14 (ALLOC E 0, ALLOC E 1, SELDSK 1, CURDRV, DSKRST entered DI: DI on the
; FS-A1GT, EI on the FS-A1ST). IX = IY = 0 at every entry. Groups:
;   1: DSKRST, the first BDOS call of the run, drive A current      2: SELDSK 1, DSKRST (no disk access yet)
;   3: SELDSK 1, DSKRST (repeat)        4: SELDSK 0, DSKRST
;   5: ALLOC E 0, ALLOC E 1, SELDSK 1, CURDRV, DSKRST, CURDRV (xbsys2 cases 10-15)
;   6: SELDSK 1, DSKRST (after the disk was accessed)    7: SELDSK 1, DSKRST entered EI
;   8: SELDSK 1, wait 120 frames, DSKRST                 9: SELDSK 1, SELDSK 0, DSKRST
;  10: CHGCPU $81 (R800 ROM), SELDSK 1, DSKRST, CHGCPU $80
;  11: CHGCPU $82 (R800 DRAM), SELDSK 1, DSKRST, CHGCPU $80
;  12: SELDSK 2 (drive C, absent), DSKRST                13: ALLOC E 0, DSKRST (drive A current, just accessed)
;  14: SELDSK 1, CURDRV, DSKRST                          15: ALLOC E 1, SELDSK 1, DSKRST
;  16: ALLOC E 1, wait 120 frames, SELDSK 1, DSKRST
;
; Frame, step and record format: probes/bios/spec/xtrdsk_body.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdskrst.asm --row turbor
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.
;
; @disk empty
; @cap A000
; @caplen 40D
; @cpusnap C100 A80B
; @timeout 60

                include "probes/bios/spec/xtrdsk_body.inc"

steps:
                db      $FE, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0002, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0003, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0004, $0000
                db      $0E, 0
                dw      $0000, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0005, $0000
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
                db      $FE, 0
                dw      $0006, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0007, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 1
                dw      $0000, $0000
                db      $FE, 0
                dw      $0008, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $F1, 0
                dw      $0078, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0009, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0E, 0
                dw      $0000, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000A, $0000
                db      $F0, 0
                dw      $0081, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $F0, 0
                dw      $0080, $0000
                db      $FE, 0
                dw      $000B, $0000
                db      $F0, 0
                dw      $0082, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $F0, 0
                dw      $0080, $0000
                db      $FE, 0
                dw      $000C, $0000
                db      $0E, 0
                dw      $0002, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000D, $0000
                db      $1B, 0
                dw      $0000, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000E, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $19, 0
                dw      $0000, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $000F, $0000
                db      $1B, 0
                dw      $0001, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FE, 0
                dw      $0010, $0000
                db      $1B, 0
                dw      $0001, $0000
                db      $F1, 0
                dw      $0078, $0000
                db      $0E, 0
                dw      $0001, $0000
                db      $0D, 0
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
