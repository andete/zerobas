; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPADG -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md (goldfish pass 1, 2026-11-23): the main ROM's GTPAD ($00DB) with A = 20-23
; and out of range (24, 31, $80, $FF), nothing plugged, after a GTPAD 12 (a fetch of port 1).
; The program and the capture layout: probes/bios/spec/xsubpad_body.inc.
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpadg.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60

SEQ     equ     4
                include "probes/bios/spec/xsubpad_body.inc"
