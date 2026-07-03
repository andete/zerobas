; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX0.COM -- Tier-2 BDOS exerciser, M23: BDOS $00 TERM0 micro-test. See
; disk/docs/tier2-bdos-remaining-spec.md SS5.2 for the full design. TERM0
; never returns to its caller (it warm-boots back into COMMAND.COM), so
; unlike bdosx.asm/bdosx2.asm there is no `done` self-loop anchor and no
; register-buffer capture -- the evidence is (i) `callseq --log 0x0005`
; showing the final C=00 call aligned ours==stock, and (ii) a `screen`
; arbiter showing both machines back at a live A> prompt afterward (which
; doubles as a free regression test of the M21b generic COMMAND.COM
; re-entry path, since TERM0's warm boot reloads COMMAND.COM the same way).
;
; `trap` must NEVER be reached: if BDOS $00 ever returned on either machine
; instead of warm-booting, execution would fall through the trap `jr $` and
; spin forever at $0103 -- a loud, unambiguous failure the callseq/screen
; arbiters would both catch (alignment guard timeout / stale screen).
;
; CLEAN-ROOM: 100% own code. BDOS $00 TERM0 contract is the published
; map.grauw.nl MSX-DOS function spec / MSX2 Technical Handbook Chapter 3 /
; CP/M 2.2 equivalent ("terminates the program, warm boot"). No stock/kernel
; bytes decoded.
;
; Build: pasmo --bin bdosx0.asm bdosx0.com

                org     $0100

BDOS            equ     $0005

start:
                ld      c, $00          ; BDOS func $00 TERM0
                call    BDOS
trap:
                jr      trap            ; must never be reached
