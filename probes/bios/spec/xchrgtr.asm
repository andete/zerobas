; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHRGTR -- docs/bios/CHRGTR.md (2026-11-18): CHRGTR ($0010, RST 10h) for every byte value c after the text pointer.
; Per case the probe builds, at BUF, the text "X c 31 32 33 34 35 36 37 38 39 00" ('X' = $58), points HL at the 'X' and
; calls CHRGTR. Before each call the constant-token cells are seeded per pass: CONTXT ($F666) := a RAM text, and
; $F668-$F671 := v, v+1, ... v+9. Run 1 is discarded (it left CONTXT at $5A5A, in the ROM); run 2 had all cells $5A;
; run 3 was pass 0 alone. Run 4 has two passes:
;   pass 0: entry A $A7, F $00, markers as listed; CONTXT = BUF+$20 -> "20 41 00" (space, 'A'); cells $61..$6A
;   pass 1: entry A $00, F $FF, every marker complemented; CONTXT = BUF+$30 -> "42 41 00" ('B', 'A'); cells $71..$7A
; Markers: BC = $1357, DE = $9BDF, IX = $4321, IY = $8765 (XOR the pass's mask), compared after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchrgtr.asm --row nodisk
; It runs from RAM ($EA00) with page 1 switched to the main ROM's slot (ENASLT, EXPTBL), as XGETYPR: on the VG-8020 the
; interpreter entries continue into the BASIC ROM there.
; The capture: CAP+0 = $A5 when finished; per case a 20-byte record from CAP+1:
;   +0 A after  +1 F after  +2,3 HL after as an offset from BUF (low, high)  +4 kept (0 = BC / DE / IX / IY kept)
;   +5..16 $F666-$F671 after   +17..19 0
; pass 0's c = 0..255, then pass 1's; then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, work-area RAM.
;
; @cap C000
; @caplen 2810
; @timeout 90

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
cc      equ     $EF02
pidx    equ     $EF03
pf      equ     $EF04                   ; the pass: entry F, entry A, marker XOR, CONTXT text (2), first cell value
pa      equ     $EF05
pm      equ     $EF06
pt      equ     $EF07
pv      equ     $EF09
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
                ld      bc, $280F
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

; ---- the RAM block (call / jp targets inside it: RAMB + label - blk) ----
blk:
                ld      a, ($FCC1)
                ld      h, $40
                call    $0024                   ; ENASLT: page 1 := the main ROM
                di
                ld      hl, BUF+$20             ; the two CONTXT texts
                ld      (hl), $20
                inc     hl
                ld      (hl), $41
                inc     hl
                ld      (hl), 0
                ld      hl, BUF+$30
                ld      (hl), $42
                inc     hl
                ld      (hl), $41
                inc     hl
                ld      (hl), 0
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
                db      $00, $A7, $00
                dw      BUF+$20
                db      $61
                db      $FF, $00, $FF
                dw      BUF+$30
                db      $71

; one -- the text at BUF, the cells seeded, HL = BUF, RST 10h, record
one:
                ld      hl, BUF
                ld      (hl), $58
                inc     hl
                ld      a, (cc)
                ld      (hl), a
                inc     hl
                ld      a, $31
                ld      b, 9
t_lp:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    t_lp
                ld      (hl), 0
                ld      hl, (pt)
                ld      ($F666), hl
                ld      hl, $F668
                ld      a, (pv)
                ld      b, 10
k_lp:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    k_lp
                ld      a, (pf)
                ld      c, a
                ld      a, (pa)
                ld      b, a
                push    bc                      ; A, F for the call
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
                rst     $10
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
                add     hl, de                  ; HL after - BUF
                ld      a, l
                call    RAMB + emit - blk
                ld      a, h
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      hl, $F666
                ld      b, 12
r_lp:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r_lp
                xor     a
                call    RAMB + emit - blk
                call    RAMB + emit - blk
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
