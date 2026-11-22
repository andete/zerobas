; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSYNCHR -- docs/bios/SYNCHR.md round 1 (2026-11-18): SYNCHR ($0008, RST 08h) on its MATCH path, for every byte value
; c. Per case the text at BUF is "c" then the pass's tail, HL = BUF, and the code is `rst $08 / db c` (the expected
; byte written into the RAM block before each call), so the byte at HL always equals the expected one. The mismatch
; path (a Syntax error into BASIC's error handler) is not run. Two passes:
;   pass 0: tail "31 32 00"; entry A $A7, F $00; markers as listed
;   pass 1: tail "20 41 00" (a space, 'A'); entry A $00, F $FF; every marker complemented
; Markers: BC = $1357, DE = $9BDF, IX = $4321, IY = $8765 (XOR the pass's mask), compared after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsynchr.asm --row nodisk
; Runs from RAM ($EA00) with page 1 the main ROM (ENASLT, EXPTBL), as XCHRGTR.
; The capture: CAP+0 = $A5 when finished; per case 6 bytes from CAP+1: A, F, HL - BUF (low, high), kept (0 = BC / DE /
; IX / IY kept), $5C (written by the instruction after the `db`: the call returned past the expected byte);
; pass 0's c = 0..255, then pass 1's; then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry.
;
; @cap C000
; @caplen 0C10
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
cc      equ     $EF02
pidx    equ     $EF03
pf      equ     $EF04                   ; the pass: entry F, entry A, marker XOR, tail (3)
pa      equ     $EF05
pm      equ     $EF06
ptl     equ     $EF07
RAMB    equ     $EA00
BUF     equ     $E900

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0C0F
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

blk:
                ld      a, ($FCC1)
                ld      h, $40
                call    $0024                   ; ENASLT: page 1 := the main ROM
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (pidx), a
pass:
                ld      a, (pidx)
                ld      hl, RAMB + passes - blk
                or      a
                jr      z, p_got
                ld      de, 6
                add     hl, de
p_got:
                ld      de, pf
                ld      bc, 6
                ldir
                xor     a
                ld      (cc), a
c_lp:
                call    RAMB + one - blk
                ld      hl, cc
                inc     (hl)
                jr      nz, c_lp
                ld      hl, pidx
                inc     (hl)
                ld      a, (hl)
                cp      2
                jr      c, pass
                jp      RAMB + finish - blk
passes:
                db      $00, $A7, $00, $31, $32, $00
                db      $FF, $00, $FF, $20, $41, $00

one:
                ld      a, (cc)
                ld      (BUF), a
                ld      (RAMB + sy_byte - blk), a
                ld      hl, ptl
                ld      de, BUF+1
                ld      bc, 3
                ldir
                ld      a, (pf)
                ld      c, a
                ld      a, (pa)
                ld      b, a
                push    bc
                ld      a, (pm)
                ld      e, a
                xor     $43
                ld      h, a
                ld      a, e
                xor     $21
                ld      l, a
                push    hl
                pop     ix
                ld      a, e
                xor     $87
                ld      h, a
                ld      a, e
                xor     $65
                ld      l, a
                push    hl
                pop     iy
                ld      a, e
                xor     $13
                ld      b, a
                ld      a, e
                xor     $57
                ld      c, a
                ld      a, e
                xor     $9B
                ld      d, a
                ld      a, e
                xor     $DF
                ld      e, a
                ld      hl, BUF
                pop     af
                rst     $08
sy_byte:
                db      0
                push    af
                push    hl
                ld      hl, pm
                ld      a, b
                xor     (hl)
                xor     $13
                jr      nz, o_moved
                ld      a, c
                xor     (hl)
                xor     $57
                jr      nz, o_moved
                ld      a, d
                xor     (hl)
                xor     $9B
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $DF
                jr      nz, o_moved
                push    ix
                pop     de
                ld      a, d
                xor     (hl)
                xor     $43
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $21
                jr      nz, o_moved
                push    iy
                pop     de
                ld      a, d
                xor     (hl)
                xor     $87
                jr      nz, o_moved
                ld      a, e
                xor     (hl)
                xor     $65
                jr      nz, o_moved
                ld      c, 0
                jr      o_rec
o_moved:
                ld      c, 1
o_rec:
                pop     de                      ; DE = HL after
                pop     hl                      ; H = A after, L = F after
                ld      a, h
                call    RAMB + emit - blk
                ld      a, l
                call    RAMB + emit - blk
                ld      hl, -BUF
                add     hl, de
                ld      a, l
                call    RAMB + emit - blk
                ld      a, h
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      a, $5C
                jp      RAMB + emit - blk

finish:
                ld      a, $C3
                call    RAMB + emit - blk
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
blk_end:
