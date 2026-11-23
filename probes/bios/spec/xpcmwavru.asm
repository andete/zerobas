; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAVRU -- D-TRSPEC (2026-11-23, tr6): PCMREC with a known input, R800 DRAM mode -- silence, then once a second a
; ramp up from $80 by one unit per 2 ms: thresholds 1, 2, 3, 4, 8, 15 (A $0B $13 $1B $23 $43 $7B), rate 3, 64 bytes
; each; the first stored byte = the level that started the recording.
; Frame and record: probes/bios/spec/xpcmwav.inc; the WAV: scratchpad/xpcmwav_mk.py's rampup.
; Run: python3 tools/agent_wt.py tr6 -- python3 scratchpad/xpcmwav_mk.py, then
;      python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmwavru.asm --row turbor
;
; @wavin $ZEROBAS_TMP/xpcmwav_rampup.wav
; @cap 8000
; @caplen 0FFF
; @cpusnap E000 E010
; @timeout 40

                include "probes/bios/spec/xpcmwav.inc"

cases:
                db      $0B
                dw      $8100, $0040
                db      $13
                dw      $8140, $0040
                db      $1B
                dw      $8180, $0040
                db      $23
                dw      $81C0, $0040
                db      $43
                dw      $8200, $0040
                db      $7B
                dw      $8240, $0040
                db      $FF

                ds      $8000 - $, $FF
