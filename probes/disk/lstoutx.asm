; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; LSTOUTX.COM -- Tier-2 LSTOUT characterisation trigger (M27 follow-up, the
; deferred printer-pluggable angle). Issues a handful of REAL BDOS $05 LSTOUT
; calls (char in E, the published MSX-DOS/CP-M contract) so a differential
; I/O-port trace can observe what the STOCK kernel+BIOS list-output path does
; on the wire -- which status port it polls, whether the poll is hang-safe with
; NO printer attached, and the return-register contract -- WITHOUT decoding any
; stock code (black-box side-effects only; see disk/docs/no-reference-rom-disasm
; rule). Ours' func-5 is un-wired ($5465 squat, M27 SS4), so this .COM is a
; STOCK-only characterisation harness; it is NOT a differential correctness
; test of ours.
;
; Sends the recognisable 5-byte stream  'L' 'P' '!' CR LF  to the list device,
; each via its own $05 call, then spins at `done:` -- a deterministic anchor for
; `capture` (return-contract regs) and the end-marker of the I/O-port trace.
; If STOCK's LSTOUT poll hangs waiting for a not-ready printer, `done` is simply
; never reached (the harness safety-timeout catches it) -- itself the answer to
; "is the poll hang-safe unplugged?".
;
; CLEAN-ROOM: 100% own code. BDOS $05 LSTOUT contract is the published
; map.grauw.nl MSX-DOS function spec / CP/M 2.2 equivalent (C=$05, E=char,
; "send one byte to the list device"). No stock/kernel bytes decoded.
;
; Build: pasmo --bin lstoutx.asm lstoutx.com

                org     $0100

BDOS            equ     $0005
LSTOUT          equ     $05

start:
                ld      c, LSTOUT
                ld      e, 'L'
                call    BDOS
                ld      c, LSTOUT
                ld      e, 'P'
                call    BDOS
                ld      c, LSTOUT
                ld      e, '!'
                call    BDOS
                ld      c, LSTOUT
                ld      e, $0D          ; CR
                call    BDOS
                ld      c, LSTOUT
                ld      e, $0A          ; LF
                call    BDOS
done:
                jr      done            ; deterministic anchor (capture/trace end)
