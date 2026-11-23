; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XWV -- D-MSX2SPEC, docs/msx2/sub/WRTVDP.md and VDPSTA.md: the sub-ROM's WRTVDP ($012D: C = the register, B = the
; value) and VDPSTA ($0131: A = the status register, A out) through EXTROM, on the MSX2 / MSX2+ references.
; WRTVDP: per case (the table `wcases`: C -- registers 0-27 and 32-46; B := the register's own value XOR $0F, R#15
; its own value, R#46 $00 the STOP command -- see the code), with
; interrupts OFF throughout (so no register value can upset the machine): the call, then the VDP's register C
; (the debugger), both RAM copy areas ($F3DF-$F3E6, $FFE7-$FFFF), the port $99 writes it made (a direct write is
; value, $80 | C; an indirect one goes through R#17 and port $9B) and A / F / B / C after; then the register and
; the copies are PUT BACK from the state before (the register through port $99 by hand, the copies by copy).
; VDPSTA: A 0-9, A and F after, next to S#0-S#9 as the debugger held them just before the call.
; The capture (CAP = C001): +0 $A5 when finished, +1 the WRTVDP case count; per WRTVDP case a 48-byte record from
;   +2: +0 C, +1 B, +2 the register after, +3 A, +4 F, +5 B, +6 C after, +7 the number of port $99 writes,
;   +8..+13 the first six, +14 the port $9B write count, +15 0, +16..+23 $F3DF-$F3E6, +24..+48 $FFE7-$FFFF (25);
; then from +2 + 48 x 43 the ten VDPSTA records of 4 bytes: A after, F after, S#n before (debugger), n.
; Added 2026-11-23 (goldfish pass 1), after the above, which is unchanged:
; PHASE 3 (from CAP + $0840, table `w3cases`: C, flags, B, P; 38-byte records): WRTVDP once per C 0-46 (C 28-31
;   included) plus C 0 variants, each with a WHOLE-WORK-AREA diff: $F380-$FFFE is copied to RAM before the call and
;   compared after it. flags bit 0: B as given (else the old rule: own value XOR $0F, R#15 own, R#46 $00); bit 1:
;   $FFE8 (R#9's copy) := P first. Record: +0 C, +1 B, +2 the register after, +3 port $99 writes, +4..+11 the first
;   eight, +12 port $9B writes, +13 the number of changed work-area bytes, +14..+37 the first eight (address lo,
;   hi, new value). Then the work area is copied back and R#0-R#15 / R#18-R#23 rewritten from the state before.
; PHASE 4 (from CAP + $1020): +0/+1 SP; +2 the phase-3 case count; then three 12-byte VDPSTA records: A after,
;   F after, S#n before (debugger), STATFL after, port $99 writes, the first six, IFF (bit 2 of F after LD A,I).
;   r0: STATFL := $5A, ~0.1 s of DI wait (S#0's F flag set by the frame), VDPSTA 0; r1: STATFL := $A5 at once,
;   VDPSTA 0 again; r2: STATFL := $5A, VDPSTA 1.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xwv.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 1060
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @portlog 9B E906 E8F4
; @timeout 120

EXTROM  equ     $015F
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
ARMFN   equ     $E8F4
SNAPP   equ     $E900
LOGP    equ     $E902
LOG9B   equ     $E906
ptr     equ     $E908
tp      equ     $E90A
cidx    equ     $E90C
rsave   equ     $E910
cur     equ     $E918
SNAPB   equ     $E000                   ; 114 bytes: R#0-63, S#0-15, pointer, palette
SNAP0   equ     $E080                   ; the state before (114)
LOGB    equ     $E100
LOGC    equ     $E180                   ; port $9B log (count only)
COPY1   equ     $E200                   ; $F3DF-$F3E6 before
COPY2   equ     $E210                   ; $FFE7-$FFFF before
P3      equ     CAP+$0840
P4      equ     CAP+$1020
P3BUF   equ     $D100                   ; $F380-$FFFE before (3199 bytes, to $DD7E)
P3N     equ     $FFFF-$F380
dptr    equ     $E930
dcnt    equ     $E932
p3cnt   equ     $E933
STATFL  equ     $F3E7

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $105F
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                ld      (LOG9B), hl
                call    ARMFN
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, wcases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
                ; the state before, once: the VDP and the copies
                ld      hl, SNAP0
                ld      (SNAPP), hl
                call    SNAPFN
                ld      hl, $F3DF
                ld      de, COPY1
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      de, COPY2
                ld      bc, 25
                ldir
w_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, w_done
                ld      de, cur
                ld      bc, 2
                ldir
                ld      (tp), hl
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      hl, LOGC
                ld      (LOG9B), hl
                ; B := the register's value before (SNAP0, the debugger) XOR $0F -- bits 0-3 only, so no interrupt
                ; enable (R#0 bits 4-6, R#1 bit 5) is ever set; R#15 (the status pointer the interrupt handler
                ; relies on) gets its own value back; R#46 the table's $00 (STOP). The first run, with fixed values,
                ; set R#0 := $5A (IE1) and never came back.
                ld      hl, SNAP0
                ld      a, (cur)
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      a, (hl)
                ld      b, a
                ld      a, e
                cp      15
                jr      z, b_set
                cp      46
                jr      z, b_46
                ld      a, b
                xor     $0F
                ld      b, a
                jr      b_set
b_46:
                ld      b, 0
b_set:
                ld      a, b
                ld      (cur+1), a              ; the record's B is the value actually written
                ld      c, e
                ld      a, $A7
                ld      ix, $012D
                call    EXTROM
                di
                push    af
                pop     hl
                ld      (rsave), hl
                ld      (rsave+2), bc
                ld      hl, (LOGP)
                ld      de, LOGB
                or      a
                sbc     hl, de
                ld      a, l
                ld      (rsave+4), a
                ld      hl, (LOG9B)
                ld      de, LOGC
                or      a
                sbc     hl, de
                ld      a, l
                ld      (rsave+5), a
                ld      hl, 0
                ld      (LOGP), hl
                ld      (LOG9B), hl
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ; the record
                ld      de, (ptr)
                ld      a, (cur)
                ld      (de), a
                inc     de
                ld      a, (cur+1)
                ld      (de), a
                inc     de
                ld      hl, SNAPB
                ld      a, (cur)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (hl)
                ld      (de), a                 ; the register after
                inc     de
                ld      a, (rsave+1)
                ld      (de), a                 ; A
                inc     de
                ld      a, (rsave)
                ld      (de), a                 ; F
                inc     de
                ld      a, (rsave+3)
                ld      (de), a                 ; B
                inc     de
                ld      a, (rsave+2)
                ld      (de), a                 ; C
                inc     de
                ld      a, (rsave+4)
                ld      (de), a
                inc     de
                ld      hl, LOGB
                ld      bc, 6
                ldir
                ld      a, (rsave+5)
                ld      (de), a
                inc     de
                inc     de
                ld      hl, $F3DF
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      bc, 25
                ldir
                ld      hl, (ptr)
                ld      bc, 48
                add     hl, bc
                ld      (ptr), hl
                ; put back: the register from SNAP0, the copies from COPY1 / COPY2
                ld      hl, SNAP0
                ld      a, (cur)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (cur)
                cp      46
                jr      z, w_nores              ; R#46: a command register, not written back
                ld      a, (hl)
                out     ($99), a
                ld      a, (cur)
                or      $80
                out     ($99), a
w_nores:
                ld      hl, COPY1
                ld      de, $F3DF
                ld      bc, 8
                ldir
                ld      hl, COPY2
                ld      de, $FFE7
                ld      bc, 24                  ; NOT $FFFF: it is the secondary slot register, not RAM (writing it
                ldir                            ; switched page 3 and the probe died after its first case)
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                jp      w_next
w_done:
                ld      a, (cidx)
                ld      (CAP+1), a
                ; VDPSTA: S#0 .. S#9
                ld      hl, CAP+2+48*43
                ld      (ptr), hl
                xor     a
                ld      (cur), a
v_next:
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ld      a, (cur)
                ld      ix, $0131
                call    EXTROM
                di
                push    af
                pop     bc
                ld      de, (ptr)
                ld      a, b
                ld      (de), a                 ; A
                inc     de
                ld      a, c
                ld      (de), a                 ; F
                inc     de
                ld      hl, SNAPB+64
                ld      a, (cur)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (hl)
                ld      (de), a                 ; S#n before
                inc     de
                ld      a, (cur)
                ld      (de), a
                inc     de
                ld      (ptr), de
                ld      a, (cur)
                inc     a
                ld      (cur), a
                cp      10
                jr      nz, v_next
                call    phase3
                call    phase4
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

; C, B
wcases:
                db      $00, $5A
                db      $01, $77
                db      $02, $94
                db      $03, $B1
                db      $04, $CE
                db      $05, $EB
                db      $06, $08
                db      $07, $25
                db      $08, $42
                db      $09, $5F
                db      $0A, $7C
                db      $0B, $99
                db      $0C, $B6
                db      $0D, $D3
                db      $0E, $F0
                db      $0F, $0D
                db      $10, $2A
                db      $11, $47
                db      $12, $64
                db      $13, $81
                db      $14, $9E
                db      $15, $BB
                db      $16, $D8
                db      $17, $F5
                db      $18, $12
                db      $19, $2F
                db      $1A, $4C
                db      $1B, $69
                db      $20, $FA
                db      $21, $17
                db      $22, $34
                db      $23, $51
                db      $24, $6E
                db      $25, $8B
                db      $26, $A8
                db      $27, $C5
                db      $28, $E2
                db      $29, $FF
                db      $2A, $1C
                db      $2B, $39
                db      $2C, $56
                db      $2D, $73
                db      $2E, $00
                db      $FF

; PHASE 3 -- WRTVDP with a whole-work-area diff (see the header)
phase3:
                ld      hl, P3
                ld      (ptr), hl
                ld      hl, w3cases
                ld      (tp), hl
                xor     a
                ld      (p3cnt), a
w3_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                ret     z
                ld      de, cur
                ld      bc, 4
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                bit     0, a
                jr      nz, w3_bx
                ld      hl, SNAP0               ; the old rule
                ld      a, (cur)
                ld      e, a
                ld      d, 0
                add     hl, de
                ld      b, (hl)
                ld      a, e
                cp      15
                jr      z, w3_bs
                cp      46
                jr      z, w3_b46
                ld      a, b
                xor     $0F
                ld      b, a
                jr      w3_bs
w3_b46:
                ld      b, 0
w3_bs:
                ld      a, b
                ld      (cur+2), a
w3_bx:
                ld      a, (cur+1)
                bit     1, a
                jr      z, w3_np
                ld      a, (cur+3)
                ld      ($FFE8), a
w3_np:
                ld      hl, $F380
                ld      de, P3BUF
                ld      bc, P3N
                ldir
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      hl, LOGC
                ld      (LOG9B), hl
                ld      a, (cur+2)
                ld      b, a
                ld      a, (cur)
                ld      c, a
                ld      a, $A7
                ld      ix, $012D
                call    EXTROM
                di
                ld      hl, (LOGP)
                ld      de, LOGB
                or      a
                sbc     hl, de
                ld      a, l
                ld      (rsave+4), a
                ld      hl, (LOG9B)
                ld      de, LOGC
                or      a
                sbc     hl, de
                ld      a, l
                ld      (rsave+5), a
                ld      hl, 0
                ld      (LOGP), hl
                ld      (LOG9B), hl
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ld      de, (ptr)
                ld      a, (cur)
                ld      (de), a
                inc     de
                ld      a, (cur+2)
                ld      (de), a
                inc     de
                ld      hl, SNAPB
                ld      a, (cur)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (hl)
                ld      (de), a
                inc     de
                ld      a, (rsave+4)
                ld      (de), a
                inc     de
                ld      hl, LOGB
                ld      bc, 8
                ldir
                ld      a, (rsave+5)
                ld      (de), a
                inc     de
                inc     de                      ; +13 the diff count, below
                ld      (dptr), de
                xor     a
                ld      (dcnt), a
                ld      hl, $F380
                ld      de, P3BUF
                ld      bc, P3N
d_loop:
                ld      a, (de)
                cp      (hl)
                call    nz, d_rec
                inc     hl
                inc     de
                dec     bc
                ld      a, b
                or      c
                jr      nz, d_loop
                ld      hl, (ptr)
                ld      bc, 13
                add     hl, bc
                ld      a, (dcnt)
                ld      (hl), a
                ld      hl, (ptr)
                ld      bc, 38
                add     hl, bc
                ld      (ptr), hl
                ; put back: the work area, the copies, R#0-R#15 and R#18-R#23
                ld      hl, P3BUF
                ld      de, $F380
                ld      bc, P3N
                ldir
                ld      hl, COPY2
                ld      de, $FFE7
                ld      bc, 24
                ldir
                ld      hl, SNAP0
                ld      c, 0
w3_rr:
                ld      a, c
                cp      16
                jr      z, w3_rs
                cp      17
                jr      z, w3_rs
                ld      a, (hl)
                out     ($99), a
                ld      a, c
                or      $80
                out     ($99), a
w3_rs:
                inc     hl
                inc     c
                ld      a, c
                cp      24
                jr      nz, w3_rr
                ld      a, (p3cnt)
                inc     a
                ld      (p3cnt), a
                jp      w3_next

; one changed work-area byte at HL (keeps BC, DE, HL); the first eight are recorded
d_rec:
                push    de
                ld      a, (dcnt)
                inc     a
                jr      z, d_skip               ; saturate at $FF
                ld      (dcnt), a
                cp      9
                jr      nc, d_skip
                ld      de, (dptr)
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                ld      a, (hl)
                ld      (de), a
                inc     de
                ld      (dptr), de
d_skip:
                pop     de
                ret

; PHASE 4 -- VDPSTA A 0: STATFL vs the port, with S#0's F flag pending
phase4:
                ld      hl, 0
                add     hl, sp
                ld      (P4), hl
                ld      a, (p3cnt)
                ld      (P4+2), a
                ld      hl, P4+3
                ld      (ptr), hl
                ld      a, $5A
                ld      (STATFL), a
                ld      bc, $4000
p4_w:
                dec     bc
                ld      a, b
                or      c
                jr      nz, p4_w
                xor     a
                call    p4_one
                ld      a, $A5
                ld      (STATFL), a
                xor     a
                call    p4_one
                ld      a, $5A
                ld      (STATFL), a
                ld      a, 1
p4_one:
                ld      (cur), a
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      a, (cur)
                ld      ix, $0131
                call    EXTROM
                push    af
                ld      a, i
                push    af
                di
                ld      hl, (LOGP)
                ld      de, LOGB
                or      a
                sbc     hl, de
                ld      a, l
                ld      (rsave+4), a
                ld      hl, 0
                ld      (LOGP), hl
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+5), a            ; IFF
                pop     bc
                ld      de, (ptr)
                ld      a, b
                ld      (de), a                 ; A
                inc     de
                ld      a, c
                ld      (de), a                 ; F
                inc     de
                ld      hl, SNAPB+64
                ld      a, (cur)
                ld      c, a
                ld      b, 0
                add     hl, bc
                ld      a, (hl)
                ld      (de), a                 ; S#n before
                inc     de
                ld      a, (STATFL)
                ld      (de), a
                inc     de
                ld      a, (rsave+4)
                ld      (de), a
                inc     de
                ld      hl, LOGB
                ld      bc, 6
                ldir
                ld      a, (rsave+5)
                ld      (de), a
                inc     de
                ld      (ptr), de
                ret

; C, flags (bit 0 B given, bit 1 $FFE8 := P), B, P
w3cases:
                db      0, 0, 0, 0
                db      1, 0, 0, 0
                db      2, 0, 0, 0
                db      3, 0, 0, 0
                db      4, 0, 0, 0
                db      5, 0, 0, 0
                db      6, 0, 0, 0
                db      7, 0, 0, 0
                db      8, 0, 0, 0
                db      9, 0, 0, 0
                db      10, 0, 0, 0
                db      11, 0, 0, 0
                db      12, 0, 0, 0
                db      13, 0, 0, 0
                db      14, 0, 0, 0
                db      15, 0, 0, 0
                db      16, 0, 0, 0
                db      17, 0, 0, 0
                db      18, 0, 0, 0
                db      19, 0, 0, 0
                db      20, 0, 0, 0
                db      21, 0, 0, 0
                db      22, 0, 0, 0
                db      23, 0, 0, 0
                db      24, 0, 0, 0
                db      25, 0, 0, 0
                db      26, 0, 0, 0
                db      27, 0, 0, 0
                db      28, 0, 0, 0
                db      29, 0, 0, 0
                db      30, 0, 0, 0
                db      31, 0, 0, 0
                db      32, 0, 0, 0
                db      33, 0, 0, 0
                db      34, 0, 0, 0
                db      35, 0, 0, 0
                db      36, 0, 0, 0
                db      37, 0, 0, 0
                db      38, 0, 0, 0
                db      39, 0, 0, 0
                db      40, 0, 0, 0
                db      41, 0, 0, 0
                db      42, 0, 0, 0
                db      43, 0, 0, 0
                db      44, 0, 0, 0
                db      45, 0, 0, 0
                db      46, 0, 0, 0
                db      0, 1, $00, 0            ; C 0, B $00
                db      0, 1, $0E, 0            ; C 0, B $0E
                db      0, 2, 0, $80            ; C 0, old-rule B, R#9 copy $80
                db      0, 3, $0E, $80          ; C 0, B $0E, R#9 copy $80
                db      0, 1, $01, 0            ; C 0, B $01 (bit 0 alone)
                db      0, 1, $0D, 0            ; C 0, B $0D (bit 0, no bit 1)
                db      $FF

                ds      $8000 - $, $FF
