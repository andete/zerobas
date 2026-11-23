; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPADS -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md (goldfish pass 1, 2026-11-23): the sub-ROM's NEWPAD ($01AD) with EVERY
; number 0-255, nothing plugged, after a fetch of port 1 (X = Y = $01), so the reads are told apart by value.
; The program and the capture layout: probes/bios/spec/xsubpad_body.inc.
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpads.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 1100
; @timeout 60

SEQ     equ     3
                include "probes/bios/spec/xsubpad_body.inc"
