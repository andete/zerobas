; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XRSLREG -- docs/bios/RSLREG.md / WSLREG.md round 2 (2026-11-18): WSLREG ($013B) writes the primary slot register,
; RSLREG ($0138) reads it. The probe runs from RAM ($EA00, page 3). Per case it calls WSLREG with A = v, where v keeps
; page 0 at slot 0 (the BIOS) and page 3 at the boot RAM slot and takes every page-1 / page-2 slot (16 values), then
; reads the register by hand (IN A,($A8)), then WRITES v XOR $3C by hand (pages 1 and 2 flipped: round 2, so RSLREG's
; value cannot be WSLREG's remembered one), then calls RSLREG, then puts the boot value back by hand. Two passes:
;   pass 0: entry F $00, interrupts off, markers as listed (BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765)
;   pass 1: entry F $FF, interrupts ON, every marker complemented; RSLREG's entry A is $5A (pass 0: $A5)
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xrslreg.asm --row nodisk (and disk, cf3300)
; The capture: CAP+0 = $A5 when finished; CAP+1 = $A8 at boot; then per case 10 bytes: WSLREG's A after, F after,
; moved (a bit per register pair that changed: 0 BC, 1 DE, 2 HL, 3 IX, 4 IY), IFF after (1 = on; read twice, ORed),
; the register read by hand after; RSLREG's A after, F after, moved, IFF after; 0. Then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries and the published slot register.
;
; @cap C000
; @caplen 0180
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
a8b     equ     $E902
vi      equ     $E903                   ; the case's index 0..15
pidx    equ     $E904
pf      equ     $E905                   ; the pass: entry F, ei, marker XOR, RSLREG's entry A
pei     equ     $E906
pm      equ     $E907
pra     equ     $E908
vv      equ     $E909                   ; the value written
rhl     equ     $E90A
RAMB    equ     $EA00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $017F
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

blk:
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                in      a, ($A8)
                ld      (a8b), a
                call    RAMB + emit - blk
                xor     a
                ld      (pidx), a
pass:
                ld      a, (pidx)
                ld      hl, RAMB + passes - blk
                or      a
                jr      z, p_got
                ld      de, 4
                add     hl, de
p_got:
                ld      de, pf
                ld      bc, 4
                ldir
                xor     a
                ld      (vi), a
v_lp:
                call    RAMB + one - blk
                ld      hl, vi
                inc     (hl)
                ld      a, (hl)
                cp      16
                jr      c, v_lp
                ld      hl, pidx
                inc     (hl)
                ld      a, (hl)
                cp      2
                jr      c, pass
                jp      RAMB + finish - blk
passes:
                db      $00, 0, $00, $A5
                db      $FF, 1, $FF, $5A

; one -- v = (boot & $C0) | (vi << 2): page 0 slot 0, page 3 as at boot, pages 1 / 2 from vi
one:
                ld      a, (vi)
                add     a, a
                add     a, a
                ld      b, a
                ld      a, (a8b)
                and     $C0
                or      b
                ld      (vv), a
                ; WSLREG
                ld      b, a
                ld      a, (pf)
                ld      c, a
                push    bc
                call    RAMB + markers - blk
                ld      a, (pei)
                or      a
                jr      z, w_di
                ei
w_di:
                pop     af
                call    $013B                   ; WSLREG
                call    RAMB + after - blk      ; A, F, moved, IFF
                in      a, ($A8)
                call    RAMB + emit - blk
                ; by hand: v XOR $3C (pages 1 and 2 to other slots), then RSLREG
                ld      a, (vv)
                xor     $3C
                out     ($A8), a
                ld      a, (pra)
                ld      b, a
                ld      a, (pf)
                ld      c, a
                push    bc
                call    RAMB + markers - blk
                ld      a, (pei)
                or      a
                jr      z, r_di
                ei
r_di:
                pop     af
                call    $0138                   ; RSLREG
                call    RAMB + after - blk
                xor     a
                call    RAMB + emit - blk
                ld      a, (a8b)                ; the boot value back
                out     ($A8), a
                ret

; markers -- BC, DE, HL, IX, IY := the listed markers XOR (pm); keeps the stack balanced (no push left)
markers:
                ld      a, (pm)
                ld      e, a
                xor     $43
                ld      h, a
                ld      a, e
                xor     $21
                ld      l, a
                push    hl
                pop     ix
                ld      a, e
                xor     $87
                ld      h, a
                ld      a, e
                xor     $65
                ld      l, a
                push    hl
                pop     iy
                ld      a, e
                xor     $24
                ld      h, a
                ld      a, e
                xor     $68
                ld      l, a
                ld      a, e
                xor     $13
                ld      b, a
                ld      a, e
                xor     $57
                ld      c, a
                ld      a, e
                xor     $9B
                ld      d, a
                ld      a, e
                xor     $DF
                ld      e, a
                ret

; after -- right after a call: record A, F, moved, IFF (interrupts off from here)
after:
                push    af
                ld      (rhl), hl
                ld      a, i
                push    af
                ld      a, i
                di
                push    af
                pop     hl                      ; L bit 2: IFF, second read
                ld      a, l
                pop     hl                      ; first read
                or      l
                rrca
                rrca
                and     1
                push    af                      ; IFF
                ; moved: compare BC, DE, (rhl), IX, IY with the markers XOR (pm)
                push    de
                ld      hl, pm
                ld      e, 0
                ld      a, b
                xor     (hl)
                xor     $13
                jr      nz, m_bc
                ld      a, c
                xor     (hl)
                xor     $57
                jr      z, m_bc_ok
m_bc:
                set     0, e
m_bc_ok:
                pop     bc                      ; BC := DE after the call
                ld      a, b
                xor     (hl)
                xor     $9B
                jr      nz, m_de
                ld      a, c
                xor     (hl)
                xor     $DF
                jr      z, m_de_ok
m_de:
                set     1, e
m_de_ok:
                ld      bc, (rhl)
                ld      a, b
                xor     (hl)
                xor     $24
                jr      nz, m_hl
                ld      a, c
                xor     (hl)
                xor     $68
                jr      z, m_hl_ok
m_hl:
                set     2, e
m_hl_ok:
                push    ix
                pop     bc
                ld      a, b
                xor     (hl)
                xor     $43
                jr      nz, m_ix
                ld      a, c
                xor     (hl)
                xor     $21
                jr      z, m_ix_ok
m_ix:
                set     3, e
m_ix_ok:
                push    iy
                pop     bc
                ld      a, b
                xor     (hl)
                xor     $87
                jr      nz, m_iy
                ld      a, c
                xor     (hl)
                xor     $65
                jr      z, m_iy_ok
m_iy:
                set     4, e
m_iy_ok:
                pop     af                      ; IFF
                ld      d, a
                pop     hl                      ; H = A after, L = F after
                ld      a, h
                call    RAMB + emit - blk
                ld      a, l
                call    RAMB + emit - blk
                ld      a, e
                call    RAMB + emit - blk
                ld      a, d
                jp      RAMB + emit - blk

finish:
                ld      a, $C3
                call    RAMB + emit - blk
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
blk_end:
