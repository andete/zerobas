; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XVDPREG -- docs/bios/WRTVDP.md, DISSCR.md, ENASCR.md, RDVDP.md round 2 (2026-11-18; round 1 had no boot copy and no sprite case): the VDP register calls.
; Per case (the table `cases` at the end: op, C, B, entry F, interrupts, RG1SAV) the probe first sets, BY HAND:
;   - VDP registers R#0-R#7 := $00 $C0 $06 $80 $00 $36 $07 $F4 (ports $99), R#1 with the interrupt bit clear;
;   - RG0SAV-RG7SAV ($F3DF-$F3E6) := $30 + k, a pattern none of the calls' values share -- then RG1SAV := the
;     case's value;
;   - $F3E7-$F3EE := the copy taken at boot (they are recorded, to show a call writing past RG7SAV);
;   - sprite 0's Y := $D0 in VRAM at $1B00 (R#5 = $36), so no sprite counts for the status;
;   - the VDP status read once (cleared); for an RDVDP case with B = 1 a wait of more than one frame follows;
;     with B = 2, first sprites 0-4 on one line at the same place ($40, $40; pattern 0 = 8 x $FF at $3800,
;     colour 15; sprite 5's Y $D0; written slowly), then the wait: five on a line, and overlapping.
; Then A = $A7, DE $9BDF, HL $2468, IX $4321, IY $8765 (all XOR $FF in odd cases), B and C as listed, F as listed,
; interrupts on or off, and the call: op 0 WRTVDP ($0047), 1 DISSCR ($0041), 2 ENASCR ($0044), 3 RDVDP ($013E).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xvdpreg.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; CAP+1..8 = $F3E7-$F3EE at boot (the copy every case starts from);
; per case a 30-byte record from CAP+9:
;   +0 A after  +1 F after  +2 B after  +3 C after  +4 moved: bit 0 DE, 1 HL, 2 IX, 3 IY (0 = all kept)
;   +5 interrupts after (1 on)  +6..13 RG0SAV-RG7SAV after  +14..21 $F3E7-$F3EE after
;   +22..29 VDP R#0-R#7 after (written by the debugger at SNAP: @vdpsnap)
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, the VDP's ports, and the VDP's registers
; read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0800
; @timeout 60
; @vdpsnap E8F0 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $E8F0                   ; a `ret`: the debugger's snapshot point
STUB    equ     $E8F2                   ; ei / nop, call target, ret
SAVE    equ     $E900                   ; $F3E7-$F3EE at boot
cop     equ     $E910                   ; the case: op, C, B, F, ei, RG1SAV
mask    equ     $E916
cidx    equ     $E917
raf     equ     $E918                   ; F, A after
rbc     equ     $E91A                   ; C, B after
riff    equ     $E91C
rkept   equ     $E91D

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $07FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAP), a
                ld      hl, $F3E7
                ld      de, SAVE
                ld      bc, 8
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, SAVE
                ld      b, 8
h_lp:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    h_lp
                ld      hl, cases
                ld      (tptr), hl
                xor     a
                ld      (cidx), a
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cop
                ld      bc, 6
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                sbc     a, a                    ; $FF in odd cases
                ld      (mask), a
                call    preset
                in      a, ($99)                ; the status cleared
                ld      a, (cop)
                cp      3
                jr      nz, nowait
                ld      a, (cop+2)
                or      a
                jr      z, nowait
                cp      2
                call    z, sprites
                ld      bc, $1000               ; > 100 000 T-states: more than one frame
w_lp:
                dec     bc
                ld      a, b
                or      c
                jr      nz, w_lp
nowait:
                ld      a, (cop+3)
                ld      c, a
                ld      a, (mask)
                xor     $A7
                ld      b, a
                push    bc                      ; A, F for the call
                ld      a, (mask)
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
                xor     $9B
                ld      d, a
                ld      a, e
                xor     $DF
                ld      e, a
                ld      a, (cop+1)
                ld      c, a
                ld      a, (cop+2)
                ld      b, a
                pop     af
                call    STUB
                push    af
                ld      a, i                    ; P/V := IFF2
                di
                ld      (rbc), bc
                push    af
                pop     bc
                ld      a, c
                and     4
                ld      (riff), a
                pop     bc
                ld      (raf), bc
                ld      b, 0
                ld      a, (mask)
                xor     $9B
                cp      d
                jr      nz, k1x
                ld      a, (mask)
                xor     $DF
                cp      e
                jr      z, k1
k1x:
                set     0, b
k1:
                ld      a, (mask)
                xor     $24
                cp      h
                jr      nz, k2x
                ld      a, (mask)
                xor     $68
                cp      l
                jr      z, k2
k2x:
                set     1, b
k2:
                push    ix
                pop     hl
                ld      a, (mask)
                xor     $43
                cp      h
                jr      nz, k3x
                ld      a, (mask)
                xor     $21
                cp      l
                jr      z, k3
k3x:
                set     2, b
k3:
                push    iy
                pop     hl
                ld      a, (mask)
                xor     $87
                cp      h
                jr      nz, k4x
                ld      a, (mask)
                xor     $65
                cp      l
                jr      z, k4
k4x:
                set     3, b
k4:
                ld      a, b
                ld      (rkept), a
                ld      a, (raf+1)
                call    emit
                ld      a, (raf)
                call    emit
                ld      a, (rbc+1)
                call    emit
                ld      a, (rbc)
                call    emit
                ld      a, (rkept)
                call    emit
                ld      a, (riff)
                or      a
                jr      z, i0
                ld      a, 1
i0:
                call    emit
                ld      hl, $F3DF
                ld      b, 16
r_lp:
                ld      a, (hl)
                call    emit
                inc     hl
                djnz    r_lp
                call    SNAP                    ; the debugger appends R#0-R#7
                ld      hl, SAVE
                ld      de, $F3E7
                ld      bc, 8
                ldir
                ld      hl, cidx
                inc     (hl)
                jp      next

; preset -- the VDP registers, RG0SAV.., $F3E7.., sprite 0's Y, and the call stub, by hand
preset:
                ld      hl, vpre
                ld      c, $80
                ld      b, 8
p_lp:
                ld      a, (hl)
                out     ($99), a
                ld      a, c
                out     ($99), a
                inc     hl
                inc     c
                djnz    p_lp
                ld      hl, $F3DF
                ld      a, $30
                ld      b, 8
p2:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    p2
                ld      a, (cop+5)
                ld      ($F3E0), a
                ld      hl, SAVE
                ld      de, $F3E7
                ld      bc, 8
                ldir
                xor     a
                out     ($99), a
                ld      a, $1B | $40
                out     ($99), a
                ld      a, $D0
                out     ($98), a
                ld      a, (cop+4)
                or      a
                ld      a, $00                  ; nop
                jr      z, p3
                ld      a, $FB                  ; ei
p3:
                ld      (STUB), a
                ld      a, $CD
                ld      (STUB+1), a
                ld      a, $C9
                ld      (STUB+4), a
                ld      a, (cop)
                add     a, a
                ld      hl, targets
                add     a, l
                ld      l, a
                jr      nc, p4
                inc     h
p4:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (STUB+2), de
                ret

; sprites -- sprites 0-4 at Y $40, X $40, pattern 0, colour 15; sprite 5 ends the list; pattern 0 = 8 x $FF
sprites:
                xor     a
                out     ($99), a
                ld      a, $1B | $40
                out     ($99), a
                ld      b, 5
s_lp:
                ld      a, $40
                call    vput
                call    vput
                xor     a
                call    vput
                ld      a, $0F
                call    vput
                djnz    s_lp
                ld      a, $D0
                call    vput
                xor     a
                out     ($99), a
                ld      a, $38 | $40
                out     ($99), a
                ld      b, 8
                ld      a, $FF
s_p:
                call    vput
                djnz    s_p
                in      a, ($99)                ; cleared again
                ret

; vput -- one VRAM write, at least 38 T-states from the next (a TMS9918 drops faster writes in active display)
vput:
                out     ($98), a
                ret

targets:
                dw      $0047, $0041, $0044, $013E
vpre:
                db      $00, $C0, $06, $80, $00, $36, $07, $F4

finish:
                ld      a, $C3
                call    emit
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

; ---- cases: op, C, B, entry F, interrupts (1 on), RG1SAV; $FF ends ----
; op 0 WRTVDP: C 0-7 x B {00, FF, 5A, A5}, then C 8-15; op 1 DISSCR / 2 ENASCR: RG1SAV over 8 values;
; op 3 RDVDP: B = 1 waits more than a frame first, B = 0 does not, B = 2 sets the sprites up and waits
cases:
                db      $00, $00, $00, $00, $00, $31   ; 0
                db      $00, $00, $FF, $FF, $00, $31   ; 1
                db      $00, $00, $5A, $00, $01, $31   ; 2
                db      $00, $00, $A5, $FF, $01, $31   ; 3
                db      $00, $01, $00, $00, $00, $31   ; 4
                db      $00, $01, $FF, $FF, $00, $31   ; 5
                db      $00, $01, $5A, $00, $01, $31   ; 6
                db      $00, $01, $A5, $FF, $01, $31   ; 7
                db      $00, $02, $00, $00, $00, $31   ; 8
                db      $00, $02, $FF, $FF, $00, $31   ; 9
                db      $00, $02, $5A, $00, $01, $31   ; 10
                db      $00, $02, $A5, $FF, $01, $31   ; 11
                db      $00, $03, $00, $00, $00, $31   ; 12
                db      $00, $03, $FF, $FF, $00, $31   ; 13
                db      $00, $03, $5A, $00, $01, $31   ; 14
                db      $00, $03, $A5, $FF, $01, $31   ; 15
                db      $00, $04, $00, $00, $00, $31   ; 16
                db      $00, $04, $FF, $FF, $00, $31   ; 17
                db      $00, $04, $5A, $00, $01, $31   ; 18
                db      $00, $04, $A5, $FF, $01, $31   ; 19
                db      $00, $05, $00, $00, $00, $31   ; 20
                db      $00, $05, $FF, $FF, $00, $31   ; 21
                db      $00, $05, $5A, $00, $01, $31   ; 22
                db      $00, $05, $A5, $FF, $01, $31   ; 23
                db      $00, $06, $00, $00, $00, $31   ; 24
                db      $00, $06, $FF, $FF, $00, $31   ; 25
                db      $00, $06, $5A, $00, $01, $31   ; 26
                db      $00, $06, $A5, $FF, $01, $31   ; 27
                db      $00, $07, $00, $00, $00, $31   ; 28
                db      $00, $07, $FF, $FF, $00, $31   ; 29
                db      $00, $07, $5A, $00, $01, $31   ; 30
                db      $00, $07, $A5, $FF, $01, $31   ; 31
                db      $00, $08, $5A, $FF, $00, $31   ; 32
                db      $00, $09, $5A, $00, $01, $31   ; 33
                db      $00, $0A, $5A, $FF, $00, $31   ; 34
                db      $00, $0B, $5A, $00, $01, $31   ; 35
                db      $00, $0C, $A5, $FF, $00, $31   ; 36
                db      $00, $0D, $A5, $00, $01, $31   ; 37
                db      $00, $0E, $A5, $FF, $00, $31   ; 38
                db      $00, $0F, $A5, $00, $01, $31   ; 39
                db      $01, $77, $77, $00, $00, $00   ; 40
                db      $01, $77, $77, $FF, $00, $FF   ; 41
                db      $01, $77, $77, $00, $01, $A0   ; 42
                db      $01, $77, $77, $FF, $01, $E2   ; 43
                db      $01, $77, $77, $00, $00, $5A   ; 44
                db      $01, $77, $77, $FF, $00, $A5   ; 45
                db      $01, $77, $77, $00, $01, $40   ; 46
                db      $01, $77, $77, $FF, $01, $BF   ; 47
                db      $02, $77, $77, $00, $00, $00   ; 48
                db      $02, $77, $77, $FF, $00, $FF   ; 49
                db      $02, $77, $77, $00, $01, $A0   ; 50
                db      $02, $77, $77, $FF, $01, $E2   ; 51
                db      $02, $77, $77, $00, $00, $5A   ; 52
                db      $02, $77, $77, $FF, $00, $A5   ; 53
                db      $02, $77, $77, $00, $01, $40   ; 54
                db      $02, $77, $77, $FF, $01, $BF   ; 55
                db      $03, $77, $01, $00, $00, $31   ; 56
                db      $03, $77, $00, $00, $00, $31   ; 57
                db      $03, $77, $01, $FF, $01, $31   ; 58
                db      $03, $77, $00, $FF, $01, $31   ; 59
                db      $03, $77, $01, $FF, $00, $31   ; 60
                db      $03, $77, $00, $00, $01, $31   ; 61
                db      $03, $77, $02, $00, $00, $31   ; 62
                db      $03, $77, $02, $FF, $01, $31   ; 63
                db      $FF
