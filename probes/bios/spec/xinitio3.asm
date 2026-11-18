; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XINITIO3 -- docs/bios/INITIO.md round 3 (2026-11-18), after the confirming review: XINITIO2's record, with each
; seed set independently -- the queue descriptors / QUEBAK, the voice control blocks, and MUSICF / PLYCNT written with
; chosen values (MUSICF 0 with garbage elsewhere, so the blocks' rewrite is seen with interrupts ON too) -- and port
; $AA's whole byte written (its keyboard-row nibble too, with interrupts off). Case 1 is the first call after boot,
; nothing seeded. XINITIO2's notes follow:
;   - a second set of entry registers (A $00, other BC / DE / HL / IX / IY) and the SHADOW registers, set before and
;     read after;
;   - PLAY's seed in three modes: 0 none; 1 all of it -- QUETAB / QUEBAK, MUSICF / PLYCNT and the three voice control
;     blocks VCBA..VCBC ($FB41-$FBAF) -- with interrupts staying off; 2 only the queue descriptors / QUEBAK
;     ($F959-$F974), MUSICF / PLYCNT left 0, so that interrupts can stay ON (the interrupt plays nothing).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xinitio3.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; per case a 224-byte record from CAP+1:
;   +0..7 AF' BC' DE' HL' (each high, low)   +8..19 AF BC DE HL IX IY   +20 LD A,I's flags (bit 2 = IFF2)
;   +21..36 PSG R0..R15   +37 port $AA   +38,39 the count of changed work-area cells (low, high)
;   +40..111 the first 24 changed cells: address (low, high), value   +112..222 the voice control blocks
;   VCBA..VCBC ($FB41-$FBAF) after the call, whole (run 2)   +223 sentinel $C3
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the PSG's and the PPI's published ports, work-area RAM.
;
; @cap C000
; @caplen 0560
; @timeout 60

WAREA   equ     $F380
SNAP    equ     $D000

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
cei     equ     $EF04                   ; the case's 10 bytes: ei, PSG pattern base, step, port $AA (whole byte), F,
cpat    equ     $EF05                   ; the register set, desc seed, VCB seed, MUSICF / PLYCNT write, MUSICF,
cstep   equ     $EF06                   ; PLYCNT
caa     equ     $EF07
cf      equ     $EF08
cset    equ     $EF09
cdesc   equ     $EF10
cvcb    equ     $EF11
cmp     equ     $EF12
cmus    equ     $EF13
cply    equ     $EF14
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
                ld      bc, $055F
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
                ld      de, cset
                ld      bc, 1
                ldir
                ld      de, cdesc
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
                ; port $AA: the case's whole byte (with interrupts on, the interrupt's scan then sets the row)
                ld      a, (caa)
                out     ($AA), a
                ; PLAY's seeds, each independent
                ld      a, (cdesc)
                or      a
                jr      z, g_nodesc
                ld      hl, $F959
                ld      b, 28
                ld      a, $5A
g_q:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    g_q
g_nodesc:
                ld      a, (cvcb)
                or      a
                jr      z, g_novcb
                ld      hl, $FB41               ; VCBA..VCBC
                ld      b, 111
                ld      a, $33
g_v:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    g_v
g_novcb:
                ld      a, (cmp)
                or      a
                jr      z, g_done
                ld      a, (cmus)
                ld      ($FB3F), a
                ld      a, (cply)
                ld      ($FB40), a
g_done:
                ; the work area, copied
                ld      hl, WAREA
                ld      de, SNAP
                ld      bc, 3200
                ldir
                ; the call: every register garbage (set 0 or set 1, the shadows too), F the case's, interrupts per cei
                ld      a, (cset)
                or      a
                jr      nz, set1
                ld      bc, $1111
                ld      de, $2222
                ld      hl, $3333
                exx
                ld      hl, $C35A
                push    hl
                pop     af
                ex      af, af'
                ld      a, (cf)
                ld      e, a
                ld      d, $A7
                push    de
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      ix, $4321
                ld      iy, $8765
                jr      set_go
set1:
                ld      bc, $8642
                ld      de, $0FE1
                ld      hl, $7531
                exx
                ld      hl, $3CA5
                push    hl
                pop     af
                ex      af, af'
                ld      a, (cf)
                ld      e, a
                ld      d, $00
                push    de
                ld      bc, $ECA8
                ld      de, $6420
                ld      hl, $DB97
                ld      ix, $BCDE
                ld      iy, $789A
set_go:
                ld      a, (cei)
                or      a
                jr      z, c_di
                ei
c_di:
                pop     af
                call    $003B
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                exx
                push    hl
                push    de
                push    bc
                exx
                ex      af, af'
                push    af
                ex      af, af'
                ld      a, i
                push    af
                di
                pop     bc                      ; C = LD A,I's flags
                ld      b, 4                    ; AF' BC' DE' HL' first (they were pushed last)
r_shad:
                pop     hl
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                djnz    r_shad
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
                ld      hl, $FB41               ; the voice control blocks, whole
                ld      b, 111
r_vcb:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    r_vcb
                ld      a, $C3
                call    emit
                jp      next

; skip -- Z for the cells the interrupt itself moves: STATFL / TRGFLG ($F3E7-$F3E8), SCNCNT etc. ($F3F6-$F3F7), the key matrices OLDKEY / NEWKEY
; ($FBDA-$FBEF), JIFFY and the timers ($FC9E-$FCA2)
skip:
                ld      a, h
                cp      $F3
                jr      nz, sk_fb
                ld      a, l
                cp      $E7                     ; STATFL / TRGFLG ($F3E7-$F3E8): the interrupt's (run 2)
                jr      c, sk_no
                cp      $E9
                jr      c, sk_yes
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

; ---- cases: ei, PSG base, step, port $AA, F, register set, desc, VCB, MUSICF/PLYCNT write, MUSICF, PLYCNT; $FF ends ----
cases:
                db      0, $40, $01, $35, $00, 0, 0, 0, 0, $00, $00     ; 1  first call after boot, nothing seeded
                db      0, $A0, $07, $35, $FF, 0, 1, 1, 1, $00, $5A     ; 2  DI, all garbage, MUSICF 0, PLYCNT $5A
                db      1, $5A, $13, $C0, $00, 1, 1, 1, 1, $00, $00     ; 3  EI, desc + VCB garbage, MUSICF / PLYCNT 0
                db      0, $FF, $00, $A5, $FF, 1, 0, 0, 1, $FF, $00     ; 4  DI, MUSICF $FF alone
                db      0, $00, $00, $F0, $00, 0, 1, 1, 1, $5A, $FF     ; 5  DI, all garbage, MUSICF $5A, PLYCNT $FF
                db      1, $33, $05, $50, $FF, 0, 0, 1, 1, $00, $33     ; 6  EI, VCB garbage alone, PLYCNT $33
                db      $FF
