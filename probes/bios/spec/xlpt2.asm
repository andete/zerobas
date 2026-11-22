; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XLPT2 -- docs/bios/LPTSTT.md round 2 (2026-11-18): LPTSTT ($00A8) with NOTHING plugged into the printer port (no
; @printer): the not-ready answer. LPTSTT twice: entry A / F $5A / $FF, then $A5 / $00; interrupts off; BC $1357,
; DE $9BDF, HL $2468, IX $4321, IY $8765 compared after. (No LPTOUT: it would wait for a printer that never comes.)
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xlpt2.asm --row nodisk (and disk)
; The capture: CAP+0 = $A5 when finished; per call A, F, moved (a bit per register that changed: 0 BC, 1 DE, 2 HL,
; 3 IX, 4 IY); then $C3.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry.
;
; @cap C000
; @caplen 0020
; @timeout 30

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
cc      equ     $EF02

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $001F
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      bc, $5AFF
                call    stt
                ld      bc, $A500
                call    stt
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; stt -- LPTSTT with A = B, F = C; record
stt:
                push    bc
                call    markers
                pop     af
                call    $00A8                   ; LPTSTT
                jp      after

markers:
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                ret

; after -- record A, F, moved
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
                ld      e, a                    ; E = the mask so far (DE is checked)
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
                pop     hl                      ; H = A, L = F
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
