; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRRESET1 -- D-TRSPEC (2026-11-23, tr6): a soft reset (JP $0000) with port $F4 bit 7 = 1 (as the boot leaves it: INIT reads $A0) written just
; before it; evidence kept in VRAM. Frame: probes/bios/spec/xtrreset.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrreset1.asm --row turbor
; CLEAN-ROOM: 100% own code; VRAM through the VDP's ports, port $F4, JIFFY, GETCPU. No ROM byte read.
;
; @cap C000
; @caplen 0020
; @vram 1F000:40
; @vram F000:10
; @vram 0000:800
; @vram 1800:300
; @dumpstate
; @timeout 60

F4OUT   equ     $80
                include "probes/bios/spec/xtrreset.inc"
