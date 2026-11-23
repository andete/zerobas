; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPAD -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md: the sub-ROM's NEWPAD ($01AD) through EXTROM, and GTPAD ($00DB), for
; the functions 8-23, with NOTHING plugged in either joystick port, on the MSX2 / MSX2+ references. The program and
; the capture layout: probes/bios/spec/xsubpad_body.inc. XSUBPADM: the same with a mouse / track ball plugged;
; XSUBPADX: the functions out of range.
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpad.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60

SEQ     equ     0
                include "probes/bios/spec/xsubpad_body.inc"
