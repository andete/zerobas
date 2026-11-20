; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XINITIO -- docs/bios/INITIO.md round 1 (2026-11-18): INITIO ($003B) from desynced states. Per case: the PSG's 16
; registers set to a pattern (R7's top two bits included), port $AA's high nibble set, entry F and the interrupt state
; chosen independently, every register garbage; then INITIO. Read back: the registers (AF BC DE HL IX IY), IFF2,
; all 16 PSG registers through the PSG's own ports ($A0 latch, $A2 read), port $AA, and the whole work area
; $F380-$FFFF compared with a copy taken just before the call (the interrupt's own cells skipped).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xinitio.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a 105-byte record from CAP+1:
;   +0..11  AF BC DE HL IX IY (each high, low)   +12 LD A,I's flags (bit 2 = IFF2)
;   +13..28 PSG R0..R15   +29 port $AA   +30,31 the count of changed work-area cells (low, high)
;   +32..103 the first 24 changed cells: address (low, high), value   +104 sentinel $C3
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the PSG's and the PPI's published ports, work-area RAM.
;
; @cap C000
; @caplen 0220
; @timeout 60

WAREA   equ     $F380
SNAP    equ     $D000

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
cei     equ     $EF04                   ; the case's 5 bytes: ei, PSG pattern base, step, $AA high nibble, F
cpat    equ     $EF05
cstep   equ     $EF06
caa     equ     $EF07
cf      equ     $EF08
cnt     equ     $EF0A
naddr   equ     $EF0C
regno   equ     $EF0E

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $021F
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cei
                ld      bc, 5
                ldir
                ld      (tptr), hl
                ; the PSG: register k := base + k * step (R7 with its top bits as the pattern gives them)
                xor     a
                ld      (regno), a
                ld      a, (cpat)
                ld      c, a
psg_lp:
                ld      a, (regno)
                out     ($A0), a
                ld      a, c
                out     ($A1), a
                ld      a, (cstep)
                add     a, c
                ld      c, a
                ld      a, (regno)
                inc     a
                ld      (regno), a
                cp      16
                jr      c, psg_lp
                ; port $AA: keep the low nibble (the keyboard row), the case's high nibble
                in      a, ($AA)
                and     $0F
                ld      b, a
                ld      a, (caa)
                and     $F0
                or      b
                out     ($AA), a
                ; with interrupts staying off, PLAY's state gets garbage first (QUETAB + QUEBAK $F959-$F974,
                ; MUSICF / PLYCNT $FB3F-$FB40): does INITIO reset it?
                ld      a, (cei)
                or      a
                jr      nz, g_done
                ld      hl, $F959
                ld      b, 28
                ld      a, $5A
g_q:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    g_q
                ld      a, $A5
                ld      ($FB3F), a
                ld      ($FB40), a
g_done:
                ; the work area, copied
                ld      hl, WAREA
                ld      de, SNAP
                ld      bc, 3200
                ldir
                ; the call: every register garbage, F the case's, interrupts per cei
                ld      a, (cf)
                ld      e, a
                ld      d, $A7
                push    de
                ld      a, 30                   ; SCNCNT: no key scan inside the window, on any machine -- the
                ld      ($F3F6), a              ; scan writes TRGFLG and PSG R15, and where it lands is timing
                ld      a, (cei)                ; (D-TRGFLGISR: zerobas's landed INSIDE INITIO, the references'
                or      a                       ; after it). SCNCNT is an interrupt cell the compare skips.
                jr      z, c_di
                ei
c_di:
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                call    $003B
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                push    af
                di
                pop     bc                      ; C = LD A,I's flags
                ld      b, 6
r_regs:
                pop     hl
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                djnz    r_regs
                ld      a, c
                call    emit
                ; the PSG's 16 registers, read through its own ports
                ld      b, 0
r_psg:
                ld      a, b
                out     ($A0), a
                in      a, ($A2)
                call    emit
                inc     b
                ld      a, b
                cp      16
                jr      c, r_psg
                in      a, ($AA)
                call    emit
                ; the work area compared, skipping the interrupt's cells
                ld      hl, 0
                ld      (cnt), hl
                ld      hl, (ptr)
                ld      (naddr), hl
                ld      de, 74                  ; the count (2) + 24 cells x 3
                add     hl, de
                ld      (ptr), hl
                ld      hl, WAREA
                ld      de, SNAP
w_lp:
                call    skip
                jr      z, w_next
                ld      a, (de)
                cp      (hl)
                jr      z, w_next
                push    hl
                push    de
                ld      de, (cnt)
                inc     de
                ld      (cnt), de
                ld      a, d
                or      a
                jr      nz, w_skp
                ld      a, e
                cp      25
                jr      nc, w_skp
                dec     a                       ; slot (count - 1) * 3 + 2
                ld      c, a
                add     a, a
                add     a, c
                add     a, 2
                ld      e, a
                ld      d, 0
                ld      ix, (naddr)
                add     ix, de
                pop     de
                pop     hl
                ld      (ix+0), l
                ld      (ix+1), h
                ld      a, (hl)
                ld      (ix+2), a
                jr      w_next
w_skp:
                pop     de
                pop     hl
w_next:
                inc     de
                inc     hl
                ld      a, h
                or      l
                jr      nz, w_lp
                ld      ix, (naddr)
                ld      hl, (cnt)
                ld      (ix+0), l
                ld      (ix+1), h
                ld      a, $C3
                call    emit
                jp      next

; skip -- Z for the cells the interrupt itself moves: SCNCNT etc. ($F3F6-$F3F7), the key matrices OLDKEY / NEWKEY
; ($FBDA-$FBEF), JIFFY and the timers ($FC9E-$FCA2)
skip:
                ld      a, h
                cp      $F3
                jr      nz, sk_fb
                ld      a, l
                cp      $F6
                jr      c, sk_no
                cp      $F8
                jr      c, sk_yes
                jr      sk_no
sk_fb:
                cp      $FB
                jr      nz, sk_fc
                ld      a, l
                cp      $DA
                jr      c, sk_no
                cp      $F0
                jr      c, sk_yes
                jr      sk_no
sk_fc:
                cp      $FC
                jr      nz, sk_no
                ld      a, l
                cp      $9E
                jr      c, sk_no
                cp      $A3
                jr      c, sk_yes
sk_no:
                or      1                       ; NZ
                ret
sk_yes:
                xor     a                       ; Z
                ret

finish:
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

; ---- cases: ei, PSG base, step, $AA high nibble, F; $FF ends (the first field is 0 / 1) ----
cases:
                db      0, $40, $01, $00, $00   ; 1  R_k = $40 + k, $AA high 0, F 00, DI, PLAY garbage
                db      0, $A0, $07, $F0, $FF   ; 2  R_k = $A0 + 7k, $AA high F (CAPS / click / motor / out), F FF
                db      1, $FF, $00, $50, $00   ; 3  all $FF, $AA high 5, EI
                db      1, $00, $00, $A0, $FF   ; 4  all $00, $AA high A, F FF, EI
                db      0, $5A, $13, $C0, $00   ; 5  R_k = $5A + 13k, $AA high C, PLAY garbage
                db      $FF
