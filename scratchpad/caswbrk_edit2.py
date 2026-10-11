#!/usr/bin/env python3
"""D-CASWBRK edit, tape half, second cut: TAPOUT calls BREAKX per byte (the
first cut's own row test did not fit -- the tape region has no slack, island 4
starts at tape_end) and cas_baud shrinks to its one real test to pay for it."""
import sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

T = "tape/tape.asm"
sub(T, """; LOW word against CS120 first, then CS240: a CS240 match means 2400, anything
; else -- a CS120 match or any unrecognised value -- defaults to the MSX-standard
; 1200. TAPOON's cas_seed guarantees CS120/CS240 hold their real reference words
; before we get here, so an unselected baud (active still 0) simply matches
; neither table and falls to the 1200 default via the catch-all no-match path.
; Pure comparison against the live tables: no copied timing constants.
; Out:     Z set => 1200 baud, Z clear (NZ) => 2400 baud.   Changes: AF, HL
cas_baud:
                push    hl
                ; 1200 (and the safe default): active LOW == CS120 LOW word.
                ld      hl,CS120_LOW
                ld      a,(ACT_LOW)
                cp      (hl)
                jr      nz,cas_baud_chk24
                inc     hl
                ld      a,(ACT_LOW+1)
                cp      (hl)
                jr      z,cas_baud_1200
cas_baud_chk24:
                ; 2400: active LOW == CS240 LOW word.
                ld      hl,CS240_LOW
                ld      a,(ACT_LOW)
                cp      (hl)
                jr      nz,cas_baud_1200
                inc     hl
                ld      a,(ACT_LOW+1)
                cp      (hl)
                jr      nz,cas_baud_1200
                pop     hl              ; matched CS240 -> 2400 baud
                or      $FF             ; A nonzero -> Z clear (NZ)
                ret
cas_baud_1200:
                pop     hl
                xor     a               ; A = 0 -> Z set
                ret
""", """; LOW word against CS240: a match means 2400, anything else -- a CS120 match or
; any unrecognised value -- defaults to the MSX-standard 1200. TAPOON's cas_seed
; guarantees CS120/CS240 hold their real reference words before we get here, so
; an unselected baud (active still 0) simply matches neither table and falls to
; the 1200 default. (D-CASWBRK: it used to test CS120 first, but a CS120 match
; and no match both gave 1200, so that test decided nothing -- 26 B, spent on
; TAPOUT's Ctrl-STOP test.) Runs before the motor is on: its time is free.
; Pure comparison against the live tables: no copied timing constants.
; Out:     A = 0 (1200) or $FF (2400).   Changes: AF, DE, HL
cas_baud:
                ld      hl,(ACT_LOW)
                ld      de,(CS240_LOW)
                or      a
                sbc     hl,de
                ld      a,0             ; 1200 (flags kept)
                ret     nz
                dec     a               ; $FF: 2400
                ret
""")
sub(T, """PSG_STAT:       equ     $A2             ; PSG value read port (CAS-in on R14 bit 7)
""", """PSG_STAT:       equ     $A2             ; PSG value read port (CAS-in on R14 bit 7)
BREAKX:         equ     $00B7           ; published BIOS entry: CF = Ctrl-STOP held,
                                        ; read from the matrix (interrupts may be off)
""")
sub(T, """CAS_BITCOMP0:   equ     14              ; '0' bit: its own tail, its own figure
""", """CAS_BITCOMP0:   equ     14              ; '0' bit: its own tail, its own figure
; D-CASWBRK: the byte boundary also carries TAPOUT's `call BREAKX` / `jr c` with
; STOP up: call 18 + jp 11 + in/and/or/out/in/and 64 + ret nz 12 + jr 8 = 113 T
; with the M1 waits = eight 14 T iterations. Its own figure, so the '1' bit's last
; cycle keeps CAS_BITCOMP; 21 < CAS_HHALF24 = 24.
CAS_BYTECOMP:   equ     CAS_BITCOMP + 8
""")
sub(T, """; Input:   A  = data to write
; Output:  CF = set if failed
; Changes: all
; Frames A as: start bit (0), 8 data bits LSB-first, 2 stop bits (1).
tapout:
                di
                push    af              ; save the data byte across cycle calls
                call    cas_long        ; start bit = '0' = one low-freq cycle
""", """; Input:   A  = data to write
; Output:  CF = set if failed: Ctrl-STOP held (that byte not written)
; Changes: all
; Frames A as: start bit (0), 8 data bits LSB-first, 2 stop bits (1).
; 🔴 D-CASWBRK (2026-10-11): THE VG-8020 BREAKS A TAPE WRITE ON Ctrl-STOP -- a 2 KB
; BSAVE / a 1.6 KB CSAVE broken in the data raise `19 in 15` there, trapped, and
; ran to the end here (scratchpad/caswbrk_diag4.out); STOP ALONE does not break it
; (an 8 KB BSAVE under a STOP press every 4 s completes, caswbrk_diag5.out), which
; is BREAKX's own test. Once per byte, at the byte boundary (CAS_BYTECOMP).
tapout:
                di
                push    af              ; save the data byte across cycle calls
                call    BREAKX          ; CF = Ctrl-STOP held
                jr      c,tapout_brk
                call    cas_long        ; start bit = '0' = one low-freq cycle
""")
sub(T, """                ld      e,CAS_BITCOMP
                call    cas_cycle_last
                or      a               ; CF = 0: success
                ret

;--------------------------------
; $00F0 TAPOOF""", """                ld      e,CAS_BYTECOMP  ; D-CASWBRK: + the BREAKX test
                call    cas_cycle_last
                or      a               ; CF = 0: success
                ret
tapout_brk:
                pop     de              ; drop the byte; CF (BREAKX's) stays set
                ret

;--------------------------------
; $00F0 TAPOOF""")
