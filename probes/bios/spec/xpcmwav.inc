; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMWAV -- D-TRSPEC (2026-11-23, tr6): the frame of the xpcmwav* probes (included; the including file carries the
; harness directives -- @wavin names the WAV fed into the PCM input, built by scratchpad/xpcmwav_mk.py -- and the
; table `cases`: A, HL (word), BC (word) per case, $FF ends). PCMREC ($0189) with a KNOWN input.
; At INIT (DI, SP $E800): $8100-$8FFF := $5A; a RET at $E000 (the @cpusnap point, in page 3 RAM); CHGCPU $82 (R800
; DRAM mode: every rate code records there). Per case: DI, A / HL / BC from the table, DE = 0, F = $00, CALL $0189.
; Record (32 bytes from CAP = $8001 + 32 x case): +0 case, +1 A in, +2 A out, +3 F out, +4 HL out, +6 BC out, +8 DE
; out (words LE), +10 IFF after (LD A,I, read twice), +11 $5A, +12 / +17 @cpusnap before / after the call (CPU,
; emulated time in us, 32-bit LE). The recorded bytes stay where each case's HL put them (in the capture).
; CLEAN-ROOM: 100% own code; published BIOS entries (CHGCPU, PCMREC), RAM the call writes. No ROM byte read; the
; recording's destination is page 2 RAM.

CHGCPU  equ     $0180
PCMREC  equ     $0189
DONE    equ     $8000
CAP     equ     $8001
SNAP    equ     $E000
SNAPP   equ     $E010
tptr    equ     $E012
rptr    equ     $E014
cidx    equ     $E016
sva     equ     $E018
svf     equ     $E019
svde    equ     $E01A

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, $8100
                ld      de, $8101
                ld      bc, $0EFF
                ld      (hl), $5A
                ldir
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAP), a
                ld      a, $82
                call    CHGCPU
                ld      hl, cases
                ld      (tptr), hl
                ld      hl, CAP
                ld      (rptr), hl
                xor     a
                ld      (cidx), a
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      ix, (rptr)
                ld      b, a                ; A in
                ld      a, (cidx)
                ld      (ix+0), a
                ld      (ix+1), b
                ld      (ix+11), $5A
                push    ix
                pop     de
                ld      hl, 12
                add     hl, de
                ld      (SNAPP), hl
                call    SNAP                ; before
                ld      hl, (tptr)
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl
                ld      (tptr), hl
                ex      de, hl              ; HL = the destination, BC = the length
                ld      a, (ix+1)
                push    af
                pop     de
                ld      e, 0                ; F = $00
                push    de
                pop     af
                ld      de, 0
                di
                call    PCMREC
                ld      (sva), a
                ld      (svde), de
                push    af
                pop     de
                ld      a, e
                ld      (svf), a
                call    SNAP                ; after (SNAPP has moved on by 5)
                ld      ix, (rptr)
                ld      a, (sva)
                ld      (ix+2), a
                ld      a, (svf)
                ld      (ix+3), a
                ld      (ix+4), l
                ld      (ix+5), h
                ld      (ix+6), c
                ld      (ix+7), b
                ld      de, (svde)
                ld      (ix+8), e
                ld      (ix+9), d
                ld      a, i
                jp      pe, ion
                ld      a, i
ion:
                ld      a, 0
                jp      po, ioff
                inc     a
ioff:
                di
                ld      (ix+10), a
                ld      de, 32
                add     ix, de
                ld      (rptr), ix
                ld      hl, cidx
                inc     (hl)
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp
