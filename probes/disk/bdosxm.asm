; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXM.COM -- spec-bdos-conout.md round 3 (2026-11-17): the console-output MATRIX. Every byte
; 0..255, from a state where the logical column ($F237) and the screen cursor DISAGREE, through
; five paths. It answers the second goldfish review's separating findings in one run, instead
; of case by case.
;
; Setup before every case: CONOUT "xx" (completes any escape / prefix the case before left
; pending: MSX escapes take at most two parameter bytes), CR, then ESC Y to row 10, column 20.
; After it the count is 3 (Y, r and c counted) and the cursor is at CSRY 11, CSRX 21: a rule that
; follows the cursor gives a different answer than one that keeps the count.
;
; Modes, 256 cases each, v = 0..255:
;   0  CONOUT v
;   1  DIRIO-out v       (v = $FF is DIRIO's INPUT: skipped, recorded as the bare setup)
;   2  STROUT v,'$'      (v = '$' skipped likewise)
;   3  CONOUT ESC, then CONOUT v
;   4  CONOUT 1 (the graphic prefix), then CONOUT v
; Then the EXTRAS (one case each, after the same setup):
;   0  ($F237) := 5, CONOUT TAB          -- is the cell LIVE (3 spaces -> 8), or a copy?
;   1  ($F237) := 250, CONOUT TAB
;   2  ($F237) := 5, STROUT TAB,'$'
;   3  ($F237) := 5, DIRIO TAB
;   4  ($F237) := 5, CONOUT 'Q'
;   5  CONST ($0B), nothing typed
;   6  DIRIO input (E = $FF), nothing typed
; Each case records 4 bytes: ($F237), CSRX, CSRY, and the A the last BDOS call returned.
;
; CLEAN-ROOM: 100% own code; the published BDOS interface and work-area cells. Nothing of the
; reference read.
;
; Build: pasmo --bin bdosxm.asm bdosxm.com bdosxm.sym

                org     $0100

BDOS            equ     $0005
LINLEN          equ     $F3B0
CSRY            equ     $F3DC
CSRX            equ     $F3DD
COLUMN          equ     $F237

start:
                jr      begin                   ; $0102 = $4D: a distinctive arm signature
                db      $4D
begin:
                ld      a, (LINLEN)
                ld      (head+0), a
                ld      a, (COLUMN)
                ld      (head+1), a
                ld      hl, results
                ld      (ptr), hl
                xor     a
                ld      (mode), a
mloop:
                xor     a
                ld      (val), a
vloop:
                call    setup
                call    dotest
                call    rec
                ld      a, (val)
                inc     a
                ld      (val), a
                jr      nz, vloop
                ld      a, (mode)
                inc     a
                ld      (mode), a
                cp      5
                jr      c, mloop

                ; --- the extras ---
                call    setup
                ld      a, 5
                ld      (COLUMN), a
                ld      e, 9
                call    co
                call    rec                     ; X0
                call    setup
                ld      a, 250
                ld      (COLUMN), a
                ld      e, 9
                call    co
                call    rec                     ; X1
                call    setup
                ld      a, 5
                ld      (COLUMN), a
                ld      a, 9
                call    so
                call    rec                     ; X2
                call    setup
                ld      a, 5
                ld      (COLUMN), a
                ld      e, 9
                ld      c, $06
                call    BDOS
                call    rec                     ; X3
                call    setup
                ld      a, 5
                ld      (COLUMN), a
                ld      e, 'Q'
                call    co
                call    rec                     ; X4
                call    setup
                ld      c, $0B
                call    BDOS
                call    rec                     ; X5
                call    setup
                ld      e, $FF
                ld      c, $06
                call    BDOS
                call    rec                     ; X6

                call    setup                   ; leave the screen tidy
                ld      e, 13
                call    co
                ld      e, 10
                call    co
                ld      a, $A5
                ld      (mark), a
                jp      done

; setup -- "xx", CR, ESC Y row 10 column 20: count 3, CSRY 11, CSRX 21
setup:
                ld      hl, setseq
su_lp:
                ld      a, (hl)
                or      a
                ret     z
                push    hl
                ld      e, a
                call    co
                pop     hl
                inc     hl
                jr      su_lp
setseq:         db      "xx", 13, 27, "Y", 32+10, 32+20, 0

; dotest -- the current mode's output of (val); A = the last call's A
dotest:
                ld      a, (mode)
                or      a
                jr      z, dt_co
                dec     a
                jr      z, dt_dirio
                dec     a
                jr      z, dt_str
                dec     a
                jr      z, dt_esc
                ld      e, 1                    ; mode 4: the graphic prefix first
                call    co
                jr      dt_co
dt_esc:
                ld      e, 27
                call    co
dt_co:
                ld      a, (val)
                ld      e, a
                jp      co
dt_dirio:
                ld      a, (val)
                cp      $FF
                ret     z                       ; DIRIO's input: not an output case
                ld      e, a
                ld      c, $06
                jp      BDOS
dt_str:
                ld      a, (val)
                cp      '$'
                ret     z                       ; the terminator itself
so:
                ld      (sbuf), a
                ld      a, '$'
                ld      (sbuf+1), a
                ld      de, sbuf
                ld      c, $09
                jp      BDOS

co:
                ld      c, $02
                jp      BDOS

; rec -- (ptr) := ($F237), CSRX, CSRY, A; ptr += 4
rec:
                ld      b, a
                ld      hl, (ptr)
                ld      a, (COLUMN)
                ld      (hl), a
                inc     hl
                ld      a, (CSRX)
                ld      (hl), a
                inc     hl
                ld      a, (CSRY)
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (ptr), hl
                ret

mode:           db      0
val:            db      0
ptr:            dw      0
sbuf:           ds      2

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
mark:           db      $EE                     ; $A5: the run finished
head:           ds      2, $EE                  ; LINLEN, the column at entry
results:        ds      4 * (5 * 256 + 7), $EE
