; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPADX -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md: the sub-ROM's NEWPAD ($01AD) with function numbers out of the
; published range (0-7, 24, 31, $80, $FF), nothing plugged; a separate run so a hang loses only these.
; The program and the capture layout: probes/bios/spec/xsubpad_body.inc.
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpadx.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60

SEQ     equ     1
                include "probes/bios/spec/xsubpad_body.inc"
