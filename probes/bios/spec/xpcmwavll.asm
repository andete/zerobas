; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVLL -- D-TRSPEC (2026-11-23, tr6): PCMREC with a known input, R800 DRAM mode -- small levels between marks
; ($F0 1 ms, then $82 $86 $87 $88 $8F $90 $7A $79 $78 $71 $70, 2 ms each): does the threshold widen what compression
; counts as silence? Case 0 plain + threshold 1 (A $0B), 512 bytes; case 1 compression + threshold 1 (A $0F); 2
; compression + threshold 2 (A $17); 3 compression alone (A $07); 256 bytes each.
; Frame and record: probes/bios/spec/xpcmwav.inc; the WAV: scratchpad/xpcmwav_mk.py's lowlev.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavll.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_lowlev.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $0B
                dw      $8100, $0200
                db      $0F
                dw      $8300, $0100
                db      $17
                dw      $8400, $0100
                db      $07
                dw      $8500, $0100
                db      $FF

                ds      $8000 - $, $FF
