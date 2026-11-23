; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPADM -- D-MSX2SPEC, docs/msx2/sub/NEWPAD.md: XSUBPAD's calls (probes/bios/spec/xsubpad_body.inc) with openMSX's
; MSX mouse in joystick port 1 and its MSX track ball in port 2, plugged before boot (@plug). Nothing moves them: no
; host input reaches an emulator run with no renderer, so every movement is 0 -- the run measures "connected, still".
; Run (from the repository root): python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpadm.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's published ports.
;
; @cap C000
; @caplen 0400
; @timeout 60
; @plug joyporta mouse
; @plug joyportb trackball

SEQ     equ     0
                include "probes/bios/spec/xsubpad_body.inc"
