; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVSQ -- D-TRSPEC (2026-11-23, tr6): PCMREC with a 1 kHz square wave (+-16384 of 32768, xpcmwav_mk.py's sq1k) in
; the PCM input, R800 DRAM mode. Frame: probes/bios/spec/xpcmwav.inc. Cases: 0-3 rate codes 3, 2, 1, 0 (256 bytes
; each); 4 threshold 1 (A $0B); 5 compression (A $07); 6 threshold 15 (A $7B) -- last, it may never return.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavsq.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_sq1k.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $03
                dw      $8100, $0100
                db      $02
                dw      $8200, $0100
                db      $01
                dw      $8300, $0100
                db      $00
                dw      $8400, $0100
                db      $0B
                dw      $8500, $0100
                db      $07
                dw      $8600, $0100
                db      $7B
                dw      $8700, $0100
                db      $FF

                ds      $8000 - $, $FF
