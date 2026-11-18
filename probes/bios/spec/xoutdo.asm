; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XOUTDO -- docs/bios/OUTDO.md / ISFLIO.md round 2 (2026-11-18), with openMSX's printer logger plugged (@printer).
;   Section A: ISFLIO ($014A) with PTRFIL ($F864) := $0000, $0001, $0100, $8000, $FFFF (put back to 0 after); entry
;              A $5A, F $00 for the even-numbered calls and $FF for the odd ones.
;   Section B: OUTDO ($0018, RST 18h) with PRTFLG ($F416) := 0, PTRFIL 0, the cursor set by hand to CSRY ($F3DC)
;              5, CSRX ($F3DD) 3, entry F $00: '~' ($7E) to the screen. CSRY, CSRX before and after.
;   Section C: PRTFLG := 1, LPTPOS ($F415) := 0, NTMSXP ($F417) := 0: OUTDO 50 09 5A 01 41 0D 0A ('P', TAB, 'Z', the
;              graphic character $01 $41, CR, LF) to the printer, entry F $00 / $FF alternately; then PRTFLG := $FF
;              and 'K' (entry F $FF).
;   Section D: PRTFLG := 0 again, the cursor set to CSRY 12, CSRX 10, entry F $FF: '|' ($7C) to the screen; CSRY, CSRX
;              before and after.
;   Section E: RG2SAV ($F3E1, the BIOS's copy of VDP R#2: the name table at RG2SAV * $400); the probe reads 768 bytes
;              of that table through the VDP ports and records where '~' and '|' are: the first index of each and how
;              many ($FFFF / 0 when none). Neither machine's boot text holds either.
; Round 2 (after the first review): the cursor set by hand (round 1 left it as boot did), entry F $FF too, PRTFLG $FF,
; the table from RG2SAV (round 1 assumed $1800).
; Interrupts off. BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 compared after each call.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xoutdo.asm --row nodisk (and disk)
; The capture: CAP+0 = $A5 when finished; A: 5 x (A, F, moved); B: CSRY, CSRX before, CSRY, CSRX after, A, F, moved;
; C: 8 x (LPTPOS, A, F, moved); D: as B; E: RG2SAV, '~' index (2), '~' count, '|' index (2), '|' count; then $C3.
; moved: a bit per register that changed (0 BC, 1 DE, 2 HL, 3 IX, 4 IY). The printer log (`PRN`) holds what the
; printer received.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, published work-area cells, the printer port through the
; emulator's logger.
;
; @cap C000
; @caplen 0080
; @timeout 60
; @printer

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tp      equ     $EF02
PTRFIL  equ     $F864
PRTFLG  equ     $F416
LPTPOS  equ     $F415
NTMSXP  equ     $F417
CSRX    equ     $F3DD
CSRY    equ     $F3DC
RG2SAV  equ     $F3E1

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $007F
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ; A: ISFLIO
                ld      hl, ptrs
                ld      (tp), hl
                ld      b, 0                    ; the call's index
a_lp:
                push    bc
                ld      hl, (tp)
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (tp), hl
                ld      (PTRFIL), de
                ld      a, b
                and     1
                neg
                ld      c, a
                ld      b, $5A
                push    bc
                call    markers
                pop     af
                call    $014A                   ; ISFLIO
                call    after
                ld      hl, 0
                ld      (PTRFIL), hl
                pop     bc
                inc     b
                ld      a, b
                cp      5
                jr      c, a_lp
                ; B: OUTDO to the screen, the cursor at 5 / 3, entry F $00
                xor     a
                ld      (PRTFLG), a
                ld      hl, $0305               ; CSRX 3, CSRY 5
                ld      bc, $7E00
                call    scr
                ; C: OUTDO to the printer
                ld      a, 1
                ld      (PRTFLG), a
                xor     a
                ld      (LPTPOS), a
                ld      (NTMSXP), a
                ld      hl, seq
                ld      (tp), hl
c_lp:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jr      z, c_done
                inc     hl
                ld      (tp), hl
                ld      b, a
                ld      a, l
                and     1
                neg
                ld      c, a                    ; entry F alternates $00 / $FF
                call    prt
                jr      c_lp
c_done:
                ld      a, $FF                  ; PRTFLG $FF: 'K'
                ld      (PRTFLG), a
                ld      bc, $4BFF
                call    prt
                ; D: the screen again, the cursor at 12 / 10, entry F $FF
                xor     a
                ld      (PRTFLG), a
                ld      hl, $0A0C               ; CSRX 10, CSRY 12
                ld      bc, $7CFF
                call    scr
                ; E: RG2SAV, then where the two characters are
                ld      a, (RG2SAV)
                call    emit
                ld      e, $7E
                call    find
                ld      e, $7C
                call    find
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; prt -- OUTDO B (entry F = C) to the printer: record LPTPOS, A, F, moved
prt:
                push    bc
                call    markers
                pop     af
                rst     $18                     ; OUTDO
                push    af
                ld      a, (LPTPOS)
                call    emit
                pop     af
                jp      after

; find -- scan 768 bytes of the name table (RG2SAV * $400) for E: emit its first index (low, high; $FFFF if none)
; and its count
find:
                ld      a, (RG2SAV)
                and     $0F
                add     a, a
                add     a, a                    ; the base's high byte: RG2SAV * 4
                ld      h, a
                xor     a
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ld      ix, $FFFF               ; the first index
                ld      hl, 0                   ; the index
                ld      d, 0                    ; the count
f_lp:
                in      a, ($98)
                cp      e
                jr      nz, f_next
                inc     d
                ld      a, ixh
                inc     a
                jr      nz, f_next
                push    hl
                pop     ix
f_next:
                inc     hl
                ld      a, h
                cp      3
                jr      c, f_lp
                push    ix
                pop     hl
                ld      a, l
                call    emit
                ld      a, h
                call    emit
                ld      a, d
                jp      emit

ptrs:
                dw      $0000, $0001, $0100, $8000, $FFFF
seq:
                db      $50, $09, $5A, $01, $41, $0D, $0A, $FF

; scr -- the cursor := L (CSRY), H (CSRX); OUTDO B with entry F C to the screen; record CSRY, CSRX before / after,
; A, F, moved
scr:
                ld      a, l
                ld      (CSRY), a
                ld      a, h
                ld      (CSRX), a
                ld      a, (CSRY)
                call    emit
                ld      a, (CSRX)
                call    emit
                push    bc
                call    markers
                pop     af
                rst     $18                     ; OUTDO
                push    af
                ld      a, (CSRY)
                call    emit
                ld      a, (CSRX)
                call    emit
                pop     af
                jp      after

markers:
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                ret

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
