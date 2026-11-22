; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XOUTDLP -- docs/bios/OUTDLP.md round 2 (2026-11-18): OUTDLP ($014D), the printer output with the BASIC conversions,
; with openMSX's printer logger plugged in (@printer). One sequence of bytes, sent twice: pass 0 with NTMSXP ($F417)
; := 0 (an MSX printer), pass 1 with NTMSXP := $FF (not one); LPTPOS ($F415) := 0 before each pass. The sequence:
;   41 42 09 43 0D 0A 09 44 45 46 47 48 49 4A 09 78 01 41 85 FF 20 0D 0A
; (letters, TAB at columns 2, 0, 7 and 8, CR / LF, the graphic header $01 + $41, $85, $FF). Interrupts off. Entry F $00
; in pass 0, $FF in pass 1; BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 compared after each call.
; Round 2 adds two passes of a second sequence, 41 01 5F 09 42 01 7E 0D 0A (two other graphic codes, a TAB right after
; a graphic character): pass 2 with NTMSXP := $01, entry F $5A; pass 3 with NTMSXP := 0, entry F $00.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xoutdlp.asm --row nodisk (and disk)
; The capture: CAP+0 = $A5 when finished; then per call 4 bytes: LPTPOS after, A after, F after, moved (a bit per
; register that changed: 0 BC, 1 DE, 2 HL, 3 IX, 4 IY); pass 0's 23 calls, pass 1's, pass 2's 9, pass 3's 9; then $C3.
; The printer log (`PRN`) holds what the printer received, the passes in order.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, published work-area cells, the printer port through the
; emulator's logger.
;
; @cap C000
; @caplen 0120
; @timeout 60
; @printer

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
sp_     equ     $EF02
pass    equ     $EF04
pnt     equ     $EF05                   ; the pass: NTMSXP, entry F, sequence (2), its end (2)
pef     equ     $EF06
pseq    equ     $EF07
pend    equ     $EF09
LPTPOS  equ     $F415
NTMSXP  equ     $F417
SEQN    equ     23

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $011F
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                xor     a
                ld      (pass), a
p_lp:
                ld      a, (pass)
                add     a, a
                ld      c, a
                add     a, a
                add     a, c                    ; 6 * pass
                ld      e, a
                ld      d, 0
                ld      hl, passes
                add     hl, de
                ld      de, pnt
                ld      bc, 6
                ldir
                ld      a, (pnt)
                ld      (NTMSXP), a
                xor     a
                ld      (LPTPOS), a
                ld      hl, (pseq)
                ld      (sp_), hl
s_lp:
                ld      hl, (sp_)
                ld      a, (hl)
                inc     hl
                ld      (sp_), hl
                ld      b, a
                ld      a, (pef)
                ld      c, a
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                call    $014D                   ; OUTDLP
                call    after
                ld      hl, (sp_)
                ld      de, (pend)
                or      a
                sbc     hl, de
                jr      c, s_lp
                ld      hl, pass
                inc     (hl)
                ld      a, (hl)
                cp      4
                jr      c, p_lp
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

passes:
                db      $00, $00
                dw      seq, seq + SEQN
                db      $FF, $FF
                dw      seq, seq + SEQN
                db      $01, $5A
                dw      seq2, seq2 + 9
                db      $00, $00
                dw      seq2, seq2 + 9
seq:
                db      $41, $42, $09, $43, $0D, $0A, $09, $44, $45, $46, $47, $48, $49, $4A, $09, $78
                db      $01, $41, $85, $FF, $20, $0D, $0A
seq2:
                db      $41, $01, $5F, $09, $42, $01, $7E, $0D, $0A

; after -- record LPTPOS, A, F, moved
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
                ld      a, (LPTPOS)
                call    emit
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
