; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; VERIFYX.COM -- BDOS $2E VERIFY effect characterisation (tier2-bdos-remaining
; §5.4 open question). Does turning VERIFY ON actually make the write path do a
; verify-after-write read-back on stock? Black-box test: do the SAME WRABS
; (sector 0, unchanged data) twice -- once with VERIFY OFF, once with VERIFY ON
; -- so a differential count of $4010 DSKIO calls between the two write BDOS
; calls reveals the effect (VERIFY-on adds a post-write READ iff stock verifies).
;
; CLEAN-ROOM: 100% own code. VERIFY ($2E, E=on/off) / RDABS ($2F) / WRABS ($30) /
; SETDTA ($1A) are the published MSX-DOS BDOS contracts (map.grauw.nl). No
; stock/kernel bytes decoded. Reads sector 0 first and writes it back UNCHANGED,
; so disk state is preserved (still run on a /tmp copy).
;
; Build: pasmo --bin verifyx.asm verifyx.com

                org     $0100

BDOS            equ     $0005

start:
                ld      de, buf         ; SETDTA -> buf
                ld      c, $1A
                call    BDOS

                ld      de, 0           ; RDABS sector 0 (drive A, 1 sector) -> buf
                ld      l, 0
                ld      h, 1
                ld      c, $2F
                call    BDOS

                ; --- WRABS #1 with VERIFY OFF ---
                ld      e, $00          ; VERIFY off
                ld      c, $2E
                call    BDOS
wr_off:
                ld      de, 0           ; WRABS buf -> sector 0 (unchanged)
                ld      l, 0
                ld      h, 1
                ld      c, $30
                call    BDOS

                ; --- WRABS #2 with VERIFY ON ---
                ld      e, $01          ; VERIFY on
                ld      c, $2E
                call    BDOS
wr_on:
                ld      de, 0           ; WRABS buf -> sector 0 (unchanged)
                ld      l, 0
                ld      h, 1
                ld      c, $30
                call    BDOS

                ld      e, $00          ; restore VERIFY off
                ld      c, $2E
                call    BDOS
done:
                jr      done            ; anchor

buf:            ds      512
