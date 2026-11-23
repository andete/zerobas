; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK4 -- D-TRSPEC (2026-11-23, tr6): the frame of xtrdsk4a / 4b / 4c (included; the including file sets SELB,
; R800 and NK). A phase sweep of DSKRST's return interrupt state: after one ALLOC (E 0, the disk read once, as in
; xbsys2), NK trials k = 0 .. NK-1, each locked to the frame: EI, HALT (resumes right after the timer interrupt), DI,
; a delay of k x 26 T-states (DEC DE / LD A,D / OR E / JR NZ; ~59736 T-states = 2297 steps per frame on the Z80),
; then [SELDSK 1 if SELB] and DSKRST, both entered DI with IX $1111 / IY $2222 (xbsys2's entry), then THREE LD A,I
; reads: DI is scored only if all three read P/V = 0 (one read can be a false 0: an interrupt accepted right after
; LD A,I resets P/V -- and DI cannot be undone between the reads, an interrupt cannot occur while DI).
; If R800 != 0, CHGCPU R800 (A = R800) first; the trials then run on the R800. If ALLOCEACH, each trial starts with
; ALLOC E 1 (entered DI), before the HALT: DSKRST then comes within ~1-2 frames of a disk access (xbsys2: 4 ms).
; Capture (CAP = $A001): +0 / +1 the number of trials scored DI, +2 / +3 trials run; +4 .. the DI trials, 4 bytes
; each: k (word), JIFFY at the trial (word); at most 60 listed.
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.

BDOS    equ     $F37D
CHGCPU  equ     $0180
DRVSLT  equ     $FB22
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA
JIFFY   equ     $FC9E

DONE    equ     $A000
CAP     equ     $A001
kk      equ     $A800
lptr    equ     $A802

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1FF
                ld      (hl), 0
                ldir
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h call in H.STKE
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      a, (DRVSLT)
                or      a
                jp      z, fin
                ld      hl, CAP+4
                ld      (lptr), hl
                ld      hl, 0
                ld      (kk), hl
                if      R800
                ld      a, R800
                call    CHGCPU
                endif
                ld      c, $1B              ; ALLOC E 0: the disk read once
                ld      de, 0
                ld      hl, 0
                di
                call    BDOS
trial:
                if      ALLOCEACH
                ld      ix, $1111
                ld      iy, $2222
                ld      c, $1B              ; ALLOC E 1 before each trial (the disk accessed just before, as in xbsys2)
                ld      de, 1
                ld      hl, 0
                di
                call    BDOS
                endif
                ei
                halt
                di
                ld      de, (kk)
                inc     de
dl1:
                dec     de
                ld      a, d
                or      e
                jr      nz, dl1
                if      SELB
                ld      ix, $1111
                ld      iy, $2222
                ld      c, $0E
                ld      de, 1
                ld      hl, 0
                di
                call    BDOS
                endif
                ld      ix, $1111
                ld      iy, $2222
                ld      c, $0D
                ld      de, 0
                ld      hl, 0
                di
                call    BDOS
                ld      a, i
                jp      pe, ison
                ld      a, i
                jp      pe, ison
                ld      a, i
                jp      pe, ison
                di
                ld      hl, (CAP)           ; scored DI
                inc     hl
                ld      (CAP), hl
                ld      de, 61
                or      a
                sbc     hl, de
                jr      nc, ison
                ld      hl, (lptr)
                ld      de, (kk)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      de, (JIFFY)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (lptr), hl
ison:
                di
                ld      hl, (kk)
                inc     hl
                ld      (kk), hl
                ld      (CAP+2), hl
                ld      de, NK
                or      a
                sbc     hl, de
                jp      nz, trial
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

                ds      $8000 - $, $FF
