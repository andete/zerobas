; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCALSLT -- docs/bios/CALSLT.md / CALLF.md / CALBAS.md round 4 (2026-11-18): the inter-slot calls CALSLT ($001C: IY's
; high byte = the slot ID, IX = the address), CALLF ($0030, RST 30h followed by the slot ID and the address) and
; CALBAS ($0159: IX = an address in the main ROM). The probe runs from RAM ($EA00, page 3). Its target is its OWN
; routine `tgt`, run in the cartridge's slot (page 1, and page 2 where the 16 KB image is mirrored) or, copied there by
; hand, in the RAM slot's page 1. Before each call the probe maps page 1 to ANOTHER slot by hand (RAM for a cartridge
; target, the cartridge for a RAM one), so the call must switch. In the target it records the slot register, the
; interrupt state, slot 3's secondary selection, the stack depth from the caller's SP and every register it was handed;
; then it returns AF = $C3D7, BC = $1122, DE = $3344, HL = $5566. CALBAS's target is the published RSLREG ($0138), so
; A after is the slot register during that call. Round 2, after the first reviews: the target sets IX := $A55A and
; IY := $5AA5 before returning ("comes back as the target left it" against "restored"); a CONTROL record (op 3) calls
; the target directly with interrupts on (the IFF readout reads 1); where slot 3 is expanded, cases with a secondary
; preset set page 1's secondary selection to 3-1 by hand first (a call naming 3-0 must switch it, and put it back); a
; RAM target in page 2 ($8010, page 2 set to the cartridge by hand first); entry F $5A; CALSLT's IY low byte per case.
; Round 4, after the second reviews: the secondary preset for page 2 too (2: page 2's field := 3-1), cartridge targets
; under a preset (does a call into a slot that is not expanded leave the selection alone?), a cartridge CALSLT with IY
; low $C3, an expanded CALSLT with interrupts on; the target reads the interrupt state twice, as `after` does.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xcalslt.asm --row nodisk (and disk, cf3300)
; Inputs: A $A5, F per case, BC $1357, DE $9BDF, HL $2468 (CALSLT: IX the address, IY the slot ID over the case's
; low byte; CALLF: IX $4321, IY $8765; CALBAS: IX $0138, IY $8765).
; The capture: CAP+0 = $A5 when finished; CAP+1 the slot register at boot, +2 EXPTBL+3, +3 the RAM slot ID, +4 the
; cartridge's; then per case 40 bytes:
;   +0 the slot register in the target  +1 IFF there  +2 slot 3's secondary selection there (0 if not expanded)
;   +3,4 SP: the caller's minus the target's (low, high)  +5..16 AF, BC, DE, HL, IX, IY in the target (low byte first)
;   +17..28 AF, BC, DE, HL, IX, IY after the call  +29 the slot register after  +30 IFF after  +31 the secondary after
;   +32 1 when the target ran  +33..39 0
; (For CALBAS +0..16 and +32 stay 0: the target is RSLREG.) Then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries (the calls, and RSLREG as CALBAS's target), the published slot
; registers and work-area cells.
;
; @cap C000
; @caplen 0340
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
a8b     equ     $E902
ramid   equ     $E903
cartid  equ     $E904
tp      equ     $E906
cop     equ     $E908                   ; the case: op (0 CALSLT, 1 CALLF, 2 CALBAS), where (0 cart p1, 1 cart p2, 2 RAM p1),
cwh     equ     $E909                   ; 3 RAM p2), entry F, ei
cef     equ     $E90A
cei     equ     $E90B
csp     equ     $E90C
cps     equ     $E90E                   ; the case's secondary preset (1 / 2: page 1 / 2 := 3-1, where slot 3 is expanded)
ciy     equ     $E90F                   ; CALSLT's IY low byte
ra      equ     $E910                   ; after: AF, BC, DE, HL, IX, IY
TREC    equ     $E920                   ; the target's 17 bytes + the ran flag
secb    equ     $E91C                   ; slot 3's secondary selection at boot (where expanded)
TBUF    equ     $E980                   ; tgt's bytes on their way into the RAM slot                   ; the target's 17 bytes + the ran flag (written by tgt)
RAMB    equ     $EA00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

; tgt -- the target: position-independent (relative jumps only), stores into page-3 RAM only
tgt:
                ld      (TREC+3), sp
                ld      (TREC+11), hl
                push    af
                pop     hl
                ld      (TREC+5), hl
                ld      (TREC+7), bc
                ld      (TREC+9), de
                ld      (TREC+13), ix
                ld      (TREC+15), iy
                in      a, ($A8)
                ld      (TREC+0), a
                ld      a, i                    ; twice, ORed: a read during an interrupt's acceptance reads 0
                push    af
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                pop     hl
                or      l
                rrca
                rrca
                and     1
                ld      (TREC+1), a
                xor     a
                ld      (TREC+2), a
                ld      a, ($FCC4)
                rla
                jr      nc, tgt_ns
                ld      a, ($FFFF)
                cpl
                ld      (TREC+2), a
tgt_ns:
                ld      a, 1
                ld      (TREC+17), a
                ld      hl, $C3D7
                push    hl
                pop     af
                ld      bc, $1122
                ld      de, $3344
                ld      hl, $5566
                ld      ix, $A55A
                ld      iy, $5AA5
                ret
tgt_end:

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $033F
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
                ld      a, ($FCC4)
                call    RAMB + emit - blk
                ld      a, ($FFFF)              ; slot 3's secondary selection at boot (used only where expanded)
                cpl
                ld      (secb), a
                ; the RAM slot ID (page 3's; SLTTBL's selection when expanded) and the cartridge's (page 1 at boot)
                ld      a, (a8b)
                rlca
                rlca
                and     3
                ld      e, a
                ld      a, ($FCC4)
                or      a
                ld      a, e
                jp      p, RAMB + h_rid - blk
                ld      a, ($FCC8)
                rrca
                rrca
                rrca
                rrca
                and     $0C
                or      e
                or      $80
h_rid:
                ld      (ramid), a
                call    RAMB + emit - blk
                ld      a, (a8b)
                rrca
                rrca
                and     3
                ld      (cartid), a
                call    RAMB + emit - blk
                ; a copy of tgt into the RAM slot's page 1, by hand: first into a page-3 buffer (page 1 is the
                ; cartridge now), then page 1 := page 3's slot (3-0 selected where expanded) and into place
                ld      hl, tgt
                ld      de, TBUF
                ld      bc, tgt_end - tgt
                ldir
                ld      a, (a8b)
                or      $0C
                out     ($A8), a
                ld      hl, TBUF
                ld      de, tgt
                ld      bc, tgt_end - tgt
                ldir
                ld      a, (a8b)
                out     ($A8), a
                ld      hl, TBUF                ; and at $8010 in page 2 (the RAM slot there at boot)
                ld      de, tgt + $4000
                ld      bc, tgt_end - tgt
                ldir
                ld      hl, RAMB + cases - blk
                ld      (tp), hl
next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, RAMB + finish - blk
                ld      de, cop
                ld      bc, 4
                ldir
                ld      de, cps
                ld      bc, 2
                ldir
                ld      (tp), hl
                ld      hl, TREC                ; clear the target's record
                ld      b, 18
cl:
                ld      (hl), 0
                inc     hl
                djnz    cl
                ; the page := another slot by hand: RAM for a cartridge target, the cartridge for a RAM one
                ld      a, (cop)
                cp      3
                jr      z, pre_done             ; the control: nothing switched
                ld      a, (cwh)
                cp      2
                ld      a, (a8b)
                jr      z, pre_set              ; RAM page 1: page 1 is the cartridge at boot
                jr      nc, pre_p2
                or      $0C                     ; page 1 := slot 3 (RAM; 3-0 selected where expanded)
                jr      pre_set
pre_p2:
                and     $CF                     ; RAM page 2: page 2 := the cartridge's slot
                ld      b, a
                ld      a, (cartid)
                rlca
                rlca
                rlca
                rlca
                or      b
pre_set:
                out     ($A8), a
                ld      a, (cps)                ; the secondary preset: page 1 / 2 := 3-1 (slot 3 expanded only)
                or      a
                jr      z, pre_done
                ld      a, ($FCC4)
                rla
                jr      nc, pre_done
                ld      bc, $F304               ; page 1: keep the other fields, set 01
                ld      a, (cps)
                cp      1
                jr      z, pre_sec
                ld      bc, $CF10               ; page 2
pre_sec:
                ld      a, ($FFFF)
                cpl
                and     b
                or      c
                ld      ($FFFF), a
pre_done:
                ; the call's address and slot
                ld      a, (cwh)
                ld      hl, tgt
                ld      b, 0
                or      a
                jr      z, w_c
                dec     a
                jr      z, w_c2
                dec     a
                jr      z, w_r1
                ld      hl, tgt + $4000         ; RAM, page 2
w_r1:
                ld      a, (ramid)              ; RAM, page 1
                ld      b, a
                jr      w_go
w_c2:
                ld      hl, tgt + $4000         ; the cartridge, page 2 (mirrored)
w_c:
                ld      a, (cartid)
                ld      b, a
w_go:
                ld      (RAMB + cf_adr - blk), hl
                ld      a, b
                ld      (RAMB + cf_slt - blk), a
                ld      (RAMB + cs_iy - blk), a
                ld      (RAMB + cs_ix - blk), hl
                ld      a, (ciy)
                ld      (RAMB + cs_iylo - blk), a
                ; inputs
                ld      a, (cef)
                ld      c, a
                ld      b, $A5
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      a, (cop)
                or      a
                jr      z, do_cs
                dec     a
                jr      z, do_cf
                dec     a
                jr      nz, do_ctl
                ; CALBAS: IX = RSLREG, IY = $8765
                ld      ix, $0138
                ld      iy, $8765
                call    RAMB + eion - blk
                pop     af
                ld      (csp), sp
                call    $0159
                jr      after
do_cs:
                db      $DD, $21                ; ld ix, (address)
cs_ix:
                dw      0
                db      $FD, $21               ; ld iy, (slot) << 8 | (the case's low byte)
cs_iylo:
                db      0
cs_iy:
                db      0
                call    RAMB + eion - blk
                pop     af
                ld      (csp), sp
                call    $001C
                jr      after
do_cf:
                ld      ix, $4321
                ld      iy, $8765
                call    RAMB + eion - blk
                pop     af
                ld      (csp), sp
                rst     $30
cf_slt:
                db      0
cf_adr:
                dw      0
                jr      after
do_ctl:                                         ; the control: the target called directly, interrupts on
                ld      ix, $4321
                ld      iy, $8765
                call    RAMB + eion - blk
                pop     af
                ld      (csp), sp
                call    tgt
after:
                ld      (ra+6), hl
                push    af
                pop     hl
                ld      (ra), hl
                ld      (ra+2), bc
                ld      (ra+4), de
                ld      (ra+8), ix
                ld      (ra+10), iy
                ld      a, i
                push    af
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                pop     hl
                or      l
                rrca
                rrca
                and     1
                ld      c, a                    ; C = IFF after
                ; record: the target's part
                ld      hl, TREC
                ld      b, 3
r1:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r1
                ld      a, (TREC+17)            ; the depth: only when the target ran
                or      a
                jr      z, r_nosp
                push    bc
                ld      hl, (csp)
                ld      de, (TREC+3)
                or      a
                sbc     hl, de
                pop     bc
                jr      r_sp
r_nosp:
                ld      hl, 0
r_sp:
                ld      a, l
                call    RAMB + emit - blk
                ld      a, h
                call    RAMB + emit - blk
                ld      hl, TREC+5
                ld      b, 12
r2:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r2
                ld      hl, ra
                ld      b, 12
r3:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r3
                in      a, ($A8)
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                xor     a
                ld      b, a
                ld      a, ($FCC4)
                or      a
                jp      p, RAMB + r_ns - blk
                ld      a, ($FFFF)
                cpl
                ld      b, a
r_ns:
                ld      a, b
                call    RAMB + emit - blk
                ld      a, (TREC+17)
                call    RAMB + emit - blk
                xor     a
                ld      b, 7
r4:
                call    RAMB + emit - blk
                djnz    r4
                ld      a, (a8b)                ; boot state back: the slot register, and slot 3's secondary
                out     ($A8), a
                ld      a, ($FCC4)
                rla
                jp      nc, RAMB + next - blk
                ld      a, (secb)
                ld      ($FFFF), a
                jp      RAMB + next - blk

; eion -- interrupts on when the case says so (called before the inputs' POP AF)
eion:
                ld      a, (cei)
                or      a
                ret     z
                ei
                ret

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

; ---- cases: op (0 CALSLT, 1 CALLF, 2 CALBAS, 3 control), where (0 cart page 1, 1 cart page 2, 2 RAM page 1, 3 RAM
; page 2), entry F, ei, secondary preset, CALSLT's IY low byte ----
cases:
                db      0, 0, $00, 0, 0, $65    ;  0 CALSLT, the cartridge, page 1
                db      0, 0, $FF, 1, 0, $65    ;  1 the same, ei
                db      1, 0, $00, 0, 0, $65    ;  2 CALLF, the cartridge, page 1
                db      1, 0, $5A, 1, 0, $65    ;  3 the same, F $5A, ei
                db      0, 1, $00, 0, 0, $65    ;  4 CALSLT, the cartridge, page 2
                db      1, 1, $FF, 0, 0, $65    ;  5 CALLF, the cartridge, page 2
                db      0, 2, $00, 0, 0, $65    ;  6 CALSLT, RAM page 1 (page 1 the cartridge before)
                db      1, 2, $FF, 1, 0, $65    ;  7 CALLF, RAM page 1, ei
                db      2, 0, $00, 0, 0, $65    ;  8 CALBAS -> RSLREG
                db      2, 0, $FF, 1, 0, $65    ;  9 the same, ei
                db      0, 2, $5A, 0, 1, $C3    ; 10 CALSLT, RAM page 1, page 1's secondary preset 3-1, IY low $C3
                db      1, 2, $00, 1, 1, $65    ; 11 CALLF, the same preset, ei
                db      0, 3, $00, 0, 0, $65    ; 12 CALSLT, RAM page 2 (page 2 the cartridge before)
                db      1, 3, $FF, 0, 0, $65    ; 13 CALLF, RAM page 2
                db      3, 0, $00, 1, 0, $65    ; 14 CONTROL: the target called directly, interrupts on
                db      0, 0, $00, 0, 1, $C3    ; 15 CALSLT, the cartridge, page 1, IY low $C3, page 1's preset 3-1
                db      1, 1, $FF, 1, 2, $65    ; 16 CALLF, the cartridge, page 2, page 2's preset 3-1, ei
                db      0, 3, $00, 0, 2, $65    ; 17 CALSLT, RAM page 2, page 2's preset 3-1
                db      1, 3, $5A, 1, 2, $65    ; 18 CALLF, RAM page 2, page 2's preset 3-1, ei
                db      0, 2, $FF, 1, 0, $3C    ; 19 CALSLT, RAM page 1, ei, IY low $3C
                db      $FF

blk_end:
