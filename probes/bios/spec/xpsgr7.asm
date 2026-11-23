; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPSGR7 -- D-MSX1ON2 (d), docs/bios/WRTPSG.md: on the MSX2s, WRTPSG ($0093) R7 := $3E reads back $BE (RDPSG). Is
; bit 7 the BIOS's (WRTPSG sets it) or the PSG's (the chip / the machine's PSG port B direction reads it as 1)?
; Per value V in $3F, $7F, $BF, $FF: (1) R7 := V straight through the PSG's ports ($A0 the register, $A1 the data)
; and read back through port $A2; (2) R7 := V through WRTPSG and read back through RDPSG ($0096); (3) through
; WRTPSG, read back through port $A2. Interrupts off throughout (the frame interrupt's sound code stays out).
; The capture (CAP = C001): +0 = $A5 when finished; then per V three bytes (1) (2) (3); then the sentinel $C3.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpsgr7.asm --row msx2all (and --row nodisk)
;
; CLEAN-ROOM: 100% own code; published BIOS entries and the PSG's published ports.
;
; @cap C000
; @caplen 10

WRTPSG  equ     $0093
RDPSG   equ     $0096
DONE    equ     $C000
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP+1
                ld      de, vals
v_lp:
                ld      a, (de)
                or      a
                jr      z, v_done
                ld      c, a
                ; (1) ports in, port out
                ld      a, 7
                out     ($A0), a
                ld      a, c
                out     ($A1), a
                ld      a, 7
                out     ($A0), a
                in      a, ($A2)
                ld      (hl), a
                inc     hl
                ; (2) WRTPSG in, RDPSG out
                push    de
                push    hl
                ld      e, c
                ld      a, 7
                call    WRTPSG
                di
                ld      a, 7
                call    RDPSG
                di
                pop     hl
                pop     de
                ld      (hl), a
                inc     hl
                ; (3) WRTPSG in, port out
                push    de
                push    hl
                ld      e, c
                ld      a, 7
                call    WRTPSG
                di
                pop     hl
                pop     de
                ld      a, 7
                out     ($A0), a
                in      a, ($A2)
                ld      (hl), a
                inc     hl
                inc     de
                jr      v_lp
v_done:
                ld      (hl), $C3
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ; R7 back to the BIOS's usual $B8 (tone and noise off, port A in, port B out)
                ld      e, $B8
                ld      a, 7
                call    WRTPSG
                ei
fin:
                jr      fin

vals:           db      $3F, $7F, $BF, $FF, 0

                ds      $8000 - $, $FF
