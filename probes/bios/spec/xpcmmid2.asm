; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMMID2 -- D-TRSPEC goldfish pass 1, docs/turbor/main/PCMPLY.md: xpcmmid.asm (same code, same capture) with STOP
; ALONE pressed while PCMPLY ($0186) plays, and data that is one long `$00` run, on the two turbo R references
; (--row turbor: FS-A1GT vs FS-A1ST). It separates (a) "STOP alone ends it during the sound" from "only CTRL+STOP
; does" (xpcmmid pressed CTRL+STOP; xpcmstop held STOP from before the call), and (b) "after an abort D:BC = the
; samples left" from "the bytes left" (xpcmmid's data had no `$00`, so the two counts were equal).
; RAM $8000-$803F := $00 (page 2): 32 pairs `$00 $00`, each 256 samples of $80 -- 8192 samples. R800 DRAM mode
; (CHGCPU $82), DI, the VDP interrupt off (R#1 bit 5); A = $03 (RAM, rate code 3: about 2.09 s), HL = $8000,
; BC = 64, D = E = 0; cpusnap; KEYREADY := 1 -- the harness then presses STOP (@matrix 7 10, held 0.3 s) at its next
; poll --; CALL $0186; cpusnap; AF, BC, DE, HL.
; Capture (CAP = $C001): +0..+9 two cpusnaps (cpu, time us x4), +10 AF, +12 BC, +14 DE, +16 HL (LE), +18 S1990 R#6.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmmid2.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM and I/O ports. No ROM byte read; the data played is
; this probe's own page-2 RAM.
;
; @cap C000
; @timeout 60
; @matrix 7 10
; @cpusnap 4100 E908

CHGCPU  equ     $0180
PCMPLY  equ     $0186
DONE    equ     $C000
CAP     equ     $C001
KEYREADY equ    $C100
CSPTR   equ     $E908

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                jp      main

                ds      $4100-$, 0
snap:           ret

main:
                xor     a
                ld      (KEYREADY), a
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ld      hl, $8000
                ld      de, $8001
                ld      bc, 63
                ld      (hl), 0
                ldir
                ld      a, $82
                call    CHGCPU
                di
                ld      a, ($F3E0)
                and     $DF
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ld      hl, CAP
                ld      (CSPTR), hl
                call    snap
                ld      a, 1
                ld      (KEYREADY), a
                ld      a, $03
                ld      hl, $8000
                ld      bc, 64
                ld      de, $0000
                call    PCMPLY
                call    snap
                di
                ld      (CAP+12), bc
                ld      (CAP+14), de
                ld      (CAP+16), hl
                push    af
                pop     hl
                ld      (CAP+10), hl
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (CAP+18), a
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

                ds      $8000-$, $FF
