; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVGP -- D-TRSPEC (2026-11-23, tr6): PCMREC with a known input, R800 DRAM mode -- 14 marks (levels $90 .. $F8, 1
; ms each) with silences of 0.1 .. 130 ms between them, once a second: case 0 threshold 1, plain (A $0B), 2048 bytes
; -- the uncompressed stream, the true length of each silence in samples; case 1 threshold 1 + compression (A $0F),
; 512 bytes; case 2 the same at rate code 1 (A $0D); case 3 compression alone (A $07), 512 bytes.
; Frame and record: probes/bios/spec/xpcmwav.inc; the WAV: scratchpad/xpcmwav_mk.py's gaps.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavgp.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_gaps.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $0B
                dw      $8100, $0800
                db      $0F
                dw      $8900, $0200
                db      $0D
                dw      $8B00, $0200
                db      $07
                dw      $8D00, $0200
                db      $FF

                ds      $8000 - $, $FF
