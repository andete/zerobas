; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XLPT3 -- docs/bios/LPTOUT.md round 3 (2026-11-18): LPTOUT ($00A5) ABORTED. Nothing is plugged into the printer port
; (no @printer), so LPTOUT waits; the probe sets KEYREADY (CAP+$FF) to 1 right before the call and the harness then
; holds CTRL + STOP (key matrix row 6 bit 1, row 7 bit 4) for 0.3 s. Entry A $41, F $00; interrupts off; BC $1357,
; DE $9BDF, HL $2468, IX $4321, IY $8765 compared after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xlpt3.asm --row nodisk (and disk)
; The capture: CAP+0 = $A5 when finished (only if LPTOUT returned); CAP+1 A, +2 F, +3 moved (a bit per register that
; changed: 0 BC, 1 DE, 2 HL, 3 IX, 4 IY); +4 $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry and the published key matrix.
;
; @cap C000
; @timeout 30
; @matrix 6 02 7 10

DONE    equ     $C000
CAP     equ     $C001
KEYREADY equ    $C100
ptr     equ     $EF00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $00FE
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      a, 1
                ld      (KEYREADY), a
                ld      bc, $4100
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                call    $00A5                   ; LPTOUT
                call    after
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

after:
                push    af
                push    hl
                ld      l, 0
                ld      a, b
                cp      $13
                jr      nz, m_bc
                ld      a, c
                cp      $57
                jr      z, m_bc_ok
m_bc:
                set     0, l
m_bc_ok:
                ld      a, d
                cp      $9B
                jr      nz, m_de
                ld      a, e
                cp      $DF
                jr      z, m_de_ok
m_de:
                set     1, l
m_de_ok:
                ld      a, l
                pop     hl
                ld      e, a
                ld      a, h
                cp      $24
                jr      nz, m_hl
                ld      a, l
                cp      $68
                jr      z, m_hl_ok
m_hl:
                set     2, e
m_hl_ok:
                push    ix
                pop     hl
                ld      a, h
                cp      $43
                jr      nz, m_ix
                ld      a, l
                cp      $21
                jr      z, m_ix_ok
m_ix:
                set     3, e
m_ix_ok:
                push    iy
                pop     hl
                ld      a, h
                cp      $87
                jr      nz, m_iy
                ld      a, l
                cp      $65
                jr      z, m_iy_ok
m_iy:
                set     4, e
m_iy_ok:
                pop     hl
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                ld      a, e
                jp      emit

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
