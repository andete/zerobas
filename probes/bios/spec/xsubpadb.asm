; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPADB -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md: port 1 EMPTY, openMSX's MSX mouse in port 2 (still) -- the two
; ports' fetches give different readings ($01 vs 0), so the call list (probes/bios/spec/xsubpad_body.inc, SEQ 2) shows
; which fetch a read returns, and what 9 / 10 / 20-22 / 0 read.
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpadb.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60
; @plug joyportb mouse

SEQ     equ     2
                include "probes/bios/spec/xsubpad_body.inc"
