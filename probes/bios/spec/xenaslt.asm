; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XENASLT -- docs/bios/ENASLT.md round 4 (2026-11-18): ENASLT ($0024) -- A = a slot ID, H = an address in the page --
; switches pages 1 and 2 to the machine's RAM slot and to the probe's own cartridge. The probe runs from RAM ($EA00,
; page 3). It first writes marker bytes into the RAM slot by hand: $4000 / $4001 := $5A / $A5, $8002 / $8003 :=
; $C6 / $6C. Per case it restores the boot state by hand (the slot register, slot 3's secondary register when expanded,
; SLTTBL), then (round 4) puts junk into the SLTTBL entry of every slot that is NOT expanded ($1B + $11 * k for
; slot k: "left alone" against "written"), applies the case's preset (1: page 2 := the cartridge by hand, so page 2 is
; switched to RAM FROM another slot), calls ENASLT, and then -- without switching anything -- records what the page now shows: $4000 / $4001
; (page 1) or $8002 / $8003 (page 2). RAM shows the markers; the cartridge shows "AB" in page 1 and its own image
; mirrored in page 2 ($10 / $40 at $8002 / $8003, init's address $4010).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xenaslt.asm --row nodisk (and disk, cf3300)
; The capture: CAP+0 = $A5 when finished; CAP+1 the slot register at boot, +2..5 EXPTBL, +6..9 SLTTBL at boot, +10
; slot 3's secondary selection at boot (0 if not expanded), +11 the RAM slot ID, +12 the cartridge's; then per case 16
; bytes: A, F, IFF (read twice, ORed), the slot register, slot 3's secondary selection (0 if not expanded), SLTTBL
; (4), moved (a bit per register that changed: 0 B, 1 C, 2 D, 3 E, 4 HL, 5 IX, 6 IY), the two witness bytes, B, C, D,
; E; then $C3. Markers: BC $1357, DE $9BDF, IX $4321, IY $8765; HL is the case's address.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the published slot registers and work-area cells; the probe's own
; cartridge bytes. No other ROM byte.
;
; @cap C000
; @caplen 0100
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
a8b     equ     $E902
secb    equ     $E903
ramid   equ     $E904
cartid  equ     $E905
tp      equ     $E906
cwh     equ     $E908                   ; the case: which (0 RAM, 1 cart), H, entry F, ei
ch      equ     $E909
cef     equ     $E90A
cei     equ     $E90B
cpr     equ     $E90C                   ; the case's preset
rhl     equ     $E91C
rbc     equ     $E90E
rde     equ     $E910
riff    equ     $E912
raf     equ     $E914
slts    equ     $E918                   ; SLTTBL at boot (4)
RAMB    equ     $EA00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $00FF
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
                ld      hl, $FCC1
                ld      b, 4
h1:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    h1
                ld      hl, $FCC5
                ld      de, slts
                ld      b, 4
h2:
                ld      a, (hl)
                ld      (de), a
                call    RAMB + emit - blk
                inc     hl
                inc     de
                djnz    h2
                xor     a
                ld      (secb), a
                ld      a, ($FCC4)
                or      a
                jp      p, RAMB + h_nosec - blk
                ld      a, ($FFFF)
                cpl
                ld      (secb), a
h_nosec:
                ld      a, (secb)
                call    RAMB + emit - blk
                ; the RAM slot ID: page 3's primary, its secondary from SLTTBL when expanded
                ld      a, (a8b)
                rlca
                rlca
                and     3
                ld      e, a
                ld      a, ($FCC4)
                or      a
                ld      a, e
                jp      p, RAMB + h_rid - blk
                ld      a, (slts+3)
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
                ld      a, (a8b)                ; the cartridge: page 1's primary at boot (not expanded on any machine)
                rrca
                rrca
                and     3
                ld      (cartid), a
                call    RAMB + emit - blk
                ; the RAM markers, by hand: pages 1 and 2 := page 3's slot (and secondary)
                call    RAMB + toram - blk
                ld      a, $5A
                ld      ($4000), a
                ld      a, $A5
                ld      ($4001), a
                ld      a, $C6
                ld      ($8002), a
                ld      a, $6C
                ld      ($8003), a
                call    RAMB + boot - blk
                ld      hl, RAMB + cases - blk
                ld      (tp), hl
next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, RAMB + finish - blk
                ld      de, cwh
                ld      bc, 5
                ldir
                ld      (tp), hl
                call    RAMB + boot - blk
                ld      hl, $FCC1               ; junk into the SLTTBL entries of the slots that are not expanded
                ld      de, $FCC5
                ld      c, $1B
j_lp:
                bit     7, (hl)
                jr      nz, j_skip
                ld      a, c
                ld      (de), a
j_skip:
                inc     hl
                inc     de
                ld      a, c
                add     a, $11
                ld      c, a
                cp      $5F
                jr      c, j_lp
                ld      a, (cpr)                ; preset 1: page 2 := the cartridge, by hand
                or      a
                jr      z, c_nopre
                ld      a, (cartid)
                and     3
                rlca
                rlca
                rlca
                rlca
                ld      b, a
                ld      a, (a8b)
                and     $CF
                or      b
                out     ($A8), a
c_nopre:
                ld      a, (cwh)
                or      a
                ld      a, (ramid)
                jr      z, c_id
                ld      a, (cartid)
c_id:
                ld      b, a
                ld      a, (cef)
                ld      c, a
                push    bc
                ld      a, (ch)
                ld      h, a
                ld      l, $33
                ld      bc, $1357
                ld      de, $9BDF
                ld      ix, $4321
                ld      iy, $8765
                ld      a, (cei)
                or      a
                jr      z, c_noei
                ei
c_noei:
                pop     af
                call    $0024                   ; ENASLT
                push    af
                ld      (rhl), hl
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
                ld      (riff), a
                pop     hl
                ld      (raf), hl
                ld      (rbc), bc
                ld      (rde), de
                ; the witness: what the case's page shows now, read directly
                ld      a, (ch)
                and     $C0
                cp      $40
                ld      hl, $4000
                jr      z, w_got
                ld      hl, $8002
w_got:
                ld      d, (hl)
                inc     hl
                ld      e, (hl)
                push    de
                ; the record
                ld      a, (raf+1)
                call    RAMB + emit - blk
                ld      a, (raf)
                call    RAMB + emit - blk
                ld      a, (riff)
                call    RAMB + emit - blk
                in      a, ($A8)
                call    RAMB + emit - blk
                xor     a
                ld      c, a
                ld      a, ($FCC4)
                or      a
                jp      p, RAMB + r_nosec - blk
                ld      a, ($FFFF)
                cpl
                ld      c, a
r_nosec:
                ld      a, c
                call    RAMB + emit - blk
                ld      hl, $FCC5
                ld      b, 4
r_slt:
                ld      a, (hl)
                call    RAMB + emit - blk
                inc     hl
                djnz    r_slt
                ; moved
                ld      c, 0
                ld      a, (rbc+1)
                cp      $13
                jr      z, m1
                set     0, c
m1:
                ld      a, (rbc)
                cp      $57
                jr      z, m2
                set     1, c
m2:
                ld      a, (rde+1)
                cp      $9B
                jr      z, m3
                set     2, c
m3:
                ld      a, (rde)
                cp      $DF
                jr      z, m4
                set     3, c
m4:
                ld      hl, (rhl)
                ld      a, l
                cp      $33
                jr      nz, m4b
                ld      a, (ch)
                cp      h
                jr      z, m5
m4b:
                set     4, c
m5:
                push    ix
                pop     hl
                ld      de, $4321
                or      a
                sbc     hl, de
                jr      z, m6
                set     5, c
m6:
                push    iy
                pop     hl
                ld      de, $8765
                or      a
                sbc     hl, de
                jr      z, m7
                set     6, c
m7:
                ld      a, c
                call    RAMB + emit - blk
                pop     de
                ld      a, d
                call    RAMB + emit - blk
                ld      a, e
                call    RAMB + emit - blk
                ld      a, (rbc+1)
                call    RAMB + emit - blk
                ld      a, (rbc)
                call    RAMB + emit - blk
                ld      a, (rde+1)
                call    RAMB + emit - blk
                ld      a, (rde)
                call    RAMB + emit - blk
                jp      RAMB + next - blk

; toram -- by hand: pages 1 and 2 := page 3's primary (and, expanded, its secondary selection for pages 1 / 2)
toram:
                ld      a, ($FCC4)
                or      a
                jp      p, RAMB + tr_p - blk
                ld      a, (secb)
                and     $C3
                ld      b, a
                ld      a, (secb)
                rrca
                rrca
                rrca
                rrca
                and     $0C                     ; page 3's selection, into page 1's field
                or      b
                ld      b, a
                ld      a, (secb)
                rrca
                rrca
                and     $30                     ; and into page 2's
                or      b
                ld      ($FFFF), a
tr_p:
                ld      a, (a8b)
                and     $C3
                ld      b, a
                ld      a, (a8b)
                rrca
                rrca
                rrca
                rrca
                and     $0C
                or      b
                ld      b, a
                ld      a, (a8b)
                rrca
                rrca
                and     $30
                or      b
                out     ($A8), a
                ret

; boot -- by hand: the slot register, slot 3's secondary selection and SLTTBL as at boot
boot:
                ld      a, ($FCC4)
                or      a
                jp      p, RAMB + b_p - blk
                ld      a, (secb)
                ld      ($FFFF), a
b_p:
                ld      a, (a8b)
                out     ($A8), a
                ld      hl, slts
                ld      de, $FCC5
                ld      bc, 4
                ldir
                ret

finish:
                call    RAMB + boot - blk
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

; ---- cases: which (0 RAM, 1 cart), H, entry F, ei, preset (1: page 2 := the cartridge first); $FF ends ----
cases:
                db      0, $40, $00, 0, 0       ; 0 page 1 := RAM
                db      1, $5A, $FF, 0, 0       ; 1 page 1 := the cartridge (H $5A: only bits 6-7 count?)
                db      0, $7F, $FF, 1, 0       ; 2 page 1 := RAM, ei
                db      1, $A5, $00, 0, 0       ; 3 page 2 := the cartridge
                db      0, $80, $00, 1, 0       ; 4 page 2 := RAM (already mapped), ei
                db      1, $40, $00, 1, 0       ; 5 page 1 := the cartridge (already mapped), ei
                db      0, $BF, $FF, 0, 0       ; 6 page 2 := RAM after nothing, H $BF
                db      0, $80, $FF, 0, 1       ; 7 page 2 := RAM FROM the cartridge (preset by hand)
                db      0, $9C, $00, 1, 1       ; 8 the same, H $9C, ei
                db      $FF
blk_end:
