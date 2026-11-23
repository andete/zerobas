; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRBOOT -- D-TRSPEC, docs/turbor/main/CHGCPU.md / GETCPU.md: which CPU a turbo R runs in at cartridge INIT and
; after its boot has finished, with no CHGCPU call of ours. INIT records the S1990's register 6, $FCB1 and GETCPU's
; A, then RETURNS, so the boot goes on (no disk in the drive). It NEVER sets DONE: the run ends at @timeout, and the
; harness reports "NO READING" by design -- the reading is the SYS line (--row turbor adds the active CPU, $FCB1 and
; every change of the S1990's register 6, polled each 0.1 s). CAP past +3 is not written (power-on RAM).
; Capture (CAP = C001): +0 S1990 R#6 at INIT, +1 $FCB1 at INIT, +2 GETCPU's A at INIT, +3 $5A.
; (A first version hooked H.KEYI / H.TIMI from RAM at $C7F0-$C9FF to sample the CPU itself; the boot never reached
; BASIC with it -- JIFFY stopped at $0036 -- while the same cartridge with a bare RET boots: the sampling moved to
; the harness.)
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrboot.asm --row turbor
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, work-area RAM, I/O ports, VRAM. No ROM byte read.
;
; @cap C000
; @timeout 25

GETCPU  equ     $0183
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (CAP+0), a
                ld      a, ($FCB1)
                ld      (CAP+1), a
                call    GETCPU
                ld      (CAP+2), a
                ld      a, $5A
                ld      (CAP+3), a
                ret

                ds      $8000-$, $FF
