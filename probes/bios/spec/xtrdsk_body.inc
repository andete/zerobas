; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK_BODY -- D-TRSPEC (2026-11-23, tr6): the frame of the xtrdsk* probes (the DSKRST interrupt state on the turbo
; R; xtrdskrst.asm's frame, widened). The program runs from H.STKE (the disk ROM's work area live), BDOS at $F37D.
; The including file defines `steps`, a list of 6-byte STEPS: OP, FLAGS, DE (word), HL (word).
;   OP < $80: a BDOS function (C = OP, DE, HL as given), entered DI unless FLAGS bit 0 (then EI); FLAGS bit 1:
;   IX = $1111, IY = $2222 at entry (as xbsys2.asm), else IX = IY = 0.
;   OP $F0: CHGCPU ($0180) with A = E.  OP $F1: EI, E x HALT, DI (a wait of E frames).
;   OP $F2: 4096 x LD A,I in a loop (~50 T-states each, ~57 ms on the Z80) under whatever interrupt state the previous
;   step left; the record's BC = how many read P/V = 0 (interrupts off -- or the read an interrupt was accepted right
;   after, the Z80's LD A,I quirk), HL = the first such read's index ($FFFF none), DE = the last's.
;   OP $F3: DI, then a delay of DE x 26 T-states.
;   OP $FE: a group marker (E = the group number).  OP $FF: the end.
; RECORD per step, 17 bytes: OP, A, F, B, C, D, E, H, L, IXh, IXl, IFF (1 = enabled on return, LD A,I's P/V), then
; @cpusnap's 5 bytes: the active CPU (0 Z80 / 1 R800) and the emulated time in microseconds (32-bit LE) just after.
; A marker records FE, E, 15 x 0. The capture: CAP = $A001, up to $7EF bytes (@caplen as needed); work cells at $A800.
; CLEAN-ROOM: 100% own code; only published BIOS / BDOS entries, registers and the interrupt flag.

BDOS    equ     $F37D
CHGCPU  equ     $0180
DRVSLT  equ     $FB22
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000
CAP     equ     $A001
ptr     equ     $A800
tptr    equ     $A802
cop     equ     $A804
ce      equ     $A805
cfl     equ     $A806
cde     equ     $A807
chl     equ     $A809
cptr    equ     $A80B
snappt  equ     $C100                       ; the @cpusnap point: a RET the program puts in page 3 RAM (a breakpoint
                                            ; in page 1 also fires on the disk ROM's code at that address)
sv_af   equ     $A810
sv_bc   equ     $A812
sv_de   equ     $A814
sv_hl   equ     $A816
sv_ix   equ     $A818

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $7EE
                ld      (hl), 0
                ldir
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h call in H.STKE
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      (snappt), a
                ld      hl, CAP
                ld      (ptr), hl
                ld      hl, steps
                ld      (tptr), hl
                ld      a, (DRVSLT)
                or      a
                jp      z, fin              ; no disk ROM: nothing to measure (the capture stays empty)
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      (cop), a
                inc     hl
                ld      a, (hl)
                ld      (cfl), a
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (cde), de
                ld      a, e
                ld      (ce), a
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
                ld      (tptr), hl
                ld      a, (cop)
                cp      $FE
                jp      z, marker
                cp      $F1
                jr      z, wait
                cp      $F0
                jr      z, cpu
                cp      $F2
                jp      z, trace
                cp      $F3
                jp      z, delay
                ld      ix, 0
                ld      iy, 0
                ld      a, (cfl)
                and     2
                jr      z, noixy
                ld      ix, $1111
                ld      iy, $2222
noixy:
                ld      a, (cop)
                ld      c, a                ; a BDOS function
                ld      de, (cde)
                ld      hl, (chl)
                ld      a, (cfl)
                rrca
                di
                jr      nc, go
                ei
go:
                call    BDOS
                jr      rec
cpu:
                ld      a, (ce)
                di
                call    CHGCPU
                jr      rec
wait:
                ld      a, (ce)
                ld      b, a
                ei
wt1:
                halt
                djnz    wt1
                di
                jr      rec
delay:                                      ; DI, DE x 26 T-states (Z80), then record
                ld      de, (cde)
                di
dl1:
                dec     de
                ld      a, d
                or      e
                jr      nz, dl1
                jp      rec
trace:                                      ; 4096 x LD A,I under the state the previous step left (no DI / EI)
                ld      ix, 0               ; IX: how many read P/V = 0
                ld      iy, $FFFF           ; IY: the first such read's index ($FFFF: none)
                ld      de, 0               ; DE: the last such read's index
                ld      bc, 0
tl:
                ld      a, i
                jp      pe, tok
                inc     ix
                ld      d, b
                ld      e, c
                push    iy
                pop     hl
                inc     hl
                ld      a, h
                or      l
                jr      nz, tok
                push    bc
                pop     iy
tok:
                inc     bc
                ld      a, b
                cp      $10
                jr      nz, tl
                push    ix
                pop     bc                  ; BC := the count
                push    iy
                pop     hl                  ; HL := the first index
                jp      rec                 ; (IX = the count again in the record; IFF = a final read)
marker:
                ld      hl, (ptr)
                ld      (hl), $FE
                inc     hl
                ld      a, (ce)
                ld      (hl), a
                inc     hl
                ld      b, 15
mk1:
                ld      (hl), 0
                inc     hl
                djnz    mk1
                ld      (ptr), hl
                jp      nxt
rec:
                ld      (sv_hl), hl
                ld      (sv_de), de
                ld      (sv_bc), bc
                ld      (sv_ix), ix
                push    af
                pop     hl
                ld      (sv_af), hl         ; L = F, H = A
                ld      a, i                ; P/V := IFF2
                ld      a, 0
                jp      po, ioff
                ld      a, 1
ioff:
                di
                ld      (cfl), a            ; the IFF
                ld      hl, (ptr)
                ld      a, (cop)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af+1)
                ld      (hl), a
                inc     hl
                ld      a, (sv_af)
                ld      (hl), a
                inc     hl
                ld      de, sv_bc+1         ; B C D E H L IXh IXl: the big-endian pairs
                ld      b, 4
rc1:
                ld      a, (de)
                ld      (hl), a
                inc     hl
                dec     de
                ld      a, (de)
                ld      (hl), a
                inc     hl
                inc     de
                inc     de
                inc     de
                djnz    rc1
                ld      a, (cfl)
                ld      (hl), a
                inc     hl
                ld      (cptr), hl          ; +12: the CPU and the emulated time (@cpusnap at snappt)
                call    snappt
                ld      hl, (cptr)
                ld      (ptr), hl
                ld      a, (cfl)            ; the interrupt state the step left is restored (for a following
                or      a                   ; OP $F2 trace)
                jp      z, nxt
                ei
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

