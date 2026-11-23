; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVBU -- D-TRSPEC (2026-11-23, tr6): PCMREC with a known input, R800 DRAM mode -- 5 ms bursts of a 1 kHz square
; (+-16384) every 500 ms in silence: case 0 plain rate 3, 2048 bytes (the raw stream); 1 compression (A $07), 256
; bytes; 2 compression + threshold 1 (A $0F); 3 threshold 1 (A $0B).
; Frame and record: probes/bios/spec/xpcmwav.inc; the WAV: scratchpad/xpcmwav_mk.py's burst.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavbu.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_burst.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $03
                dw      $8100, $0800
                db      $07
                dw      $8900, $0100
                db      $0F
                dw      $8A00, $0100
                db      $0B
                dw      $8B00, $0100
                db      $FF

                ds      $8000 - $, $FF
