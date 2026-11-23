; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRRESET0 -- D-TRSPEC (2026-11-23, tr6): a soft reset (JP $0000) with port $F4 bit 7 = 0 (WRRES A = $00 on the turbo R) written just
; before it; evidence kept in VRAM. Frame: probes/bios/spec/xtrreset.inc.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrreset0.asm --row turbor
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

F4OUT   equ     $00
                include "probes/bios/spec/xtrreset.inc"
