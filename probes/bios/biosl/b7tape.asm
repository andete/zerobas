; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B7TAPE -- D-BIOSLADDER rung B7 (TODO.md): a ROM saving a block to tape and loading
; it back through the published cassette entries. A 16 KB "AB" cartridge; INIT runs it.
;   1. TAPOON (long header), TAPOUT x 16 bytes, TAPOOF: CF of TAPOON (CAP+0) and
;      the OR of TAPOUT's CF (CAP+1);
;   2. TAPEREADY := 1; the harness rewinds the recording and plays it, then
;      acknowledges (@tape);
;   3. TAPION (CF: CAP+2), TAPIN x 16 (the OR of CF: CAP+3; the bytes: CAP+$10..$1F),
;      TAPIOF; the bytes as written (CAP+4: 1).
; The tape is the emulator's own fresh recording on each machine, so what is compared
; is each machine's round trip, not one recording read by both.
; CLEAN-ROOM: 100% own code; only published BIOS entries.
;
; @tape
; @timeout 60

TAPION  equ     $00E1
TAPIN   equ     $00E4
TAPIOF  equ     $00E7
TAPOON  equ     $00EA
TAPOUT  equ     $00ED
TAPOOF  equ     $00F0

DONE    equ     $E000
CAP     equ     $E001
TREADY  equ     $E101
TACK    equ     $E102

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
                ei
                ; --- 1: save ----------------------------------------------------------
                ld      a, $FF              ; a long header
                call    TAPOON
                sbc     a, a
                ld      (CAP+0), a
                ld      hl, data
                ld      b, 16
                ld      c, 0
out_lp:
                ld      a, (hl)
                push    hl
                push    bc
                call    TAPOUT
                pop     bc
                pop     hl
                sbc     a, a
                or      c
                ld      c, a
                inc     hl
                djnz    out_lp
                ld      a, c
                ld      (CAP+1), a
                call    TAPOOF
                ; --- 2: the harness turns the tape round ------------------------------
                ei
                ld      a, 1
                ld      (TREADY), a
wait_ack:
                halt
                ld      a, (TACK)
                or      a
                jr      z, wait_ack
                ; --- 3: load -----------------------------------------------------------
                call    TAPION
                sbc     a, a
                ld      (CAP+2), a
                ld      hl, CAP+$10
                ld      b, 16
                ld      c, 0
in_lp:
                push    hl
                push    bc
                call    TAPIN
                pop     bc
                pop     hl
                ld      (hl), a
                sbc     a, a
                or      c
                ld      c, a
                inc     hl
                djnz    in_lp
                ld      a, c
                ld      (CAP+3), a
                call    TAPIOF
                ei
                ld      hl, data
                ld      de, CAP+$10
                ld      b, 16
cmp_lp:
                ld      a, (de)
                cp      (hl)
                jr      nz, cmp_bad
                inc     hl
                inc     de
                djnz    cmp_lp
                ld      a, 1
                ld      (CAP+4), a
cmp_bad:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

data:           db      $00, $FF, $55, $AA, $01, $80, $7E, $81
                db      "ZEROBAS!"
