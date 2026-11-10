; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B5SOUND -- D-BIOSLADDER rung B5 (TODO.md): the PSG as a ROM program drives it.
; A 16 KB "AB" cartridge; INIT runs it.
;   1. RDPSG 0..15 as the cartridge finds them (CAP+0);
;   2. GICINI; RDPSG 0..13 (CAP+$10) -- registers 14 / 15 are the joystick port,
;      not sound state;
;   3. WRTPSG: a tone on channel A (R0 = $FE, R1 = $01, R7 = $3E, R8 = 15),
;      RDPSG 0..13 (CAP+$20); R8 := 16 (envelope), R11 / R12 / R13 = $00 / $10 / $0E,
;      RDPSG 8, 11, 12, 13 (CAP+$30);
;   4. GICINI again: RDPSG 0..13 (CAP+$40);
;   5. BEEP: RDPSG 0..13 right after it (CAP+$50). The play queues (STRTMS / PUTQ)
;      are a separate, already filed divergence and are not exercised here.
; CLEAN-ROOM: 100% own code; only published BIOS entries.
;
; @timeout 40

GICINI  equ     $0090
WRTPSG  equ     $0093
RDPSG   equ     $0096
BEEP    equ     $00C0

DONE    equ     $E000
CAP     equ     $E001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ei
                ; --- 1 -----------------------------------------------------------------
                ld      hl, CAP+0
                ld      b, 16
                call    rdall
                ; --- 2 -----------------------------------------------------------------
                call    GICINI
                ld      hl, CAP+$10
                ld      b, 14
                call    rdall
                ; --- 3 -----------------------------------------------------------------
                ld      hl, tone
wr_lp:
                ld      a, (hl)
                cp      $FF
                jr      z, wr_done
                inc     hl
                ld      e, (hl)
                inc     hl
                push    hl
                call    WRTPSG
                pop     hl
                jr      wr_lp
wr_done:
                ld      hl, CAP+$20
                ld      b, 14
                call    rdall
                ld      hl, env
wr2_lp:
                ld      a, (hl)
                cp      $FF
                jr      z, wr2_done
                inc     hl
                ld      e, (hl)
                inc     hl
                push    hl
                call    WRTPSG
                pop     hl
                jr      wr2_lp
wr2_done:
                ld      a, 8
                call    RDPSG
                ld      (CAP+$30), a
                ld      a, 11
                call    RDPSG
                ld      (CAP+$31), a
                ld      a, 12
                call    RDPSG
                ld      (CAP+$32), a
                ld      a, 13
                call    RDPSG
                ld      (CAP+$33), a
                ; --- 4 -----------------------------------------------------------------
                call    GICINI
                ld      hl, CAP+$40
                ld      b, 14
                call    rdall
                ; --- 5 -----------------------------------------------------------------
                call    BEEP
                ld      hl, CAP+$50
                ld      b, 14
                call    rdall
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; rdall -- (HL..HL+B-1) := RDPSG 0..B-1
rdall:
                ld      c, 0
rd_lp:
                push    bc
                push    hl
                ld      a, c
                call    RDPSG
                pop     hl
                pop     bc
                ld      (hl), a
                inc     hl
                inc     c
                djnz    rd_lp
                ret

tone:           db      0, $FE, 1, $01, 7, $3E, 8, 15, $FF
env:            db      8, 16, 11, $00, 12, $10, 13, $0E, $FF
