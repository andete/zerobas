; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCHRGTR2 -- docs/bios/CHRGTR.md round 5 (2026-11-18), after the first review: what a caller sees when it goes on
; calling CHRGTR after a numeric-constant token, as a caller walking a text does (the call after a token returns
; HL = $46E6, not a text pointer). Per case: the text at BUF is "X t 31 32 33 34 35 36 37 38 39 3A 00" (t = the token),
; HL = BUF, then CHRGTR three times, each from the HL the one before returned. Cells $F666-$F671 seeded as XCHRGTR's
; pass 0 (CONTXT = BUF+$20 -> "20 41 00", $F668.. = $61..$6A) before the first call only. Every numeric token
; ($0B-$0F, $11-$1D, $1F) in order, then the same 19 with entry F $FF on every call (pass 1).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchrgtr2.asm --row nodisk
; Runs from RAM ($EA00) with page 1 the main ROM (ENASLT), as XCHRGTR.
; The capture: CAP+0 = $A5 when finished; per case a 24-byte record from CAP+1:
;   +0..3 call 1: A, F, HL (low, high)  +4..7 call 2  +8..11 call 3  +12..23 $F666-$F671 after call 3
; then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry called as a caller calls it, work-area RAM.
;
; @cap C000
; @caplen 0400
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tp      equ     $EF02
ef      equ     $EF04
pidx    equ     $EF05
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
                ld      bc, $03FF
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
                ld      hl, BUF+$20
                ld      (hl), $20
                inc     hl
                ld      (hl), $41
                inc     hl
                ld      (hl), 0
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (pidx), a
                ld      (ef), a
pass:
                ld      hl, RAMB + toks - blk
                ld      (tp), hl
t_next:
                ld      hl, (tp)
                ld      a, (hl)
                or      a
                jr      z, t_done
                inc     hl
                ld      (tp), hl
                call    RAMB + one - blk
                jr      t_next
t_done:
                ld      a, (pidx)
                or      a
                jp      nz, RAMB + finish - blk
                inc     a
                ld      (pidx), a
                ld      a, $FF
                ld      (ef), a
                jr      pass
toks:
                db      $0B, $0C, $0D, $0E, $0F, $11, $12, $13, $14, $15, $16, $17, $18, $19, $1A, $1B, $1C, $1D, $1F, 0

; one -- A = the token: text, seeds, three calls, record
one:
                ld      hl, BUF
                ld      (hl), $58
                inc     hl
                ld      (hl), a
                inc     hl
                ld      a, $31
                ld      b, 10
t_lp:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    t_lp
                ld      (hl), 0
                ld      hl, BUF+$20
                ld      ($F666), hl
                ld      hl, $F668
                ld      a, $61
                ld      b, 10
k_lp:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    k_lp
                ld      hl, BUF
                ld      b, 3
call_lp:
                push    bc
                ld      a, (ef)
                ld      c, a
                ld      b, $A7
                push    bc
                pop     af
                rst     $10
                push    af
                pop     bc                      ; B = A after, C = F after
                ld      a, b
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      a, l
                call    RAMB + emit - blk
                ld      a, h
                call    RAMB + emit - blk
                pop     bc
                djnz    call_lp
                ld      hl, $F666
                ld      b, 12
r_lp:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r_lp
                ret

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
