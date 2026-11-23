; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVST -- D-TRSPEC (2026-11-23, tr6): PCMREC with a known input, R800 DRAM mode -- the staircase (32 levels, 8
; units apart, 10 ms each): one plain rate-code-3 recording of 3584 bytes (the transfer function).
; Frame and record: probes/bios/spec/xpcmwav.inc; the WAV: scratchpad/xpcmwav_mk.py's stairs.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavst.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_stairs.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $03
                dw      $8100, $0E00
                db      $FF

                ds      $8000 - $, $FF
