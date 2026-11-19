; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSND1B -- the sound calls' round 5 (2026-11-19): xsnd1.asm's frame (its cases 0-106) with cases of its own, numbered
; from 107 on the pages. Per case (the table `cases` at the end: op, A, F, interrupts, SET, BC, DE,
; HL, WIN) the probe sets, BY HAND:
;   - PSG registers R0-R13 := $A1 $02 $B3 $04 $C5 $06 $17 $B8 $09 $0A $0B $5C $1D $0E (R7 $B8: port A in, port B out)
;     and R15 := $CF, through the PSG's ports $A0 / $A1 (R7 / R8-R10 otherwise by SET, below); R14 (port A, an input)
;     is not written;
;   - the PPI's port C ($AA) := $50 or $2F, with bit 7 (the 1-bit sound) from SET (below);
;   - QUETAB ($F959, 4 queues x 6 bytes: put, get, back flag, size, address), QUEBAK ($F971-$F974), QUEUEN ($FB3E),
;     VOICEN ($FB38), MUSICF ($FB3F), PLYCNT ($FB40) := the `qsets` entry (SET AND $1E) / 2 names;
;   - the queue buffers VOICAQ ($F975, 128), VOICBQ ($F9F5, 128), VOICCQ ($FA75, 128), queue 3's buffer at $E800 (the
;     probe's own RAM: RS2IQ, $FAF5-$FB34, is left alone -- the disk interface's reference keeps something there, and
;     overwriting it stops that machine) and the voice buffers VCBA ($FB41) .. VCBC ($FB8B + 37)
;     and $FB35-$FB37, $FB39-$FB3D := (address low) XOR $A5.
; Then IX $4321, IY $8765 (XOR $FF when bit 2 of the case number is set), A, F, BC, DE, HL and interrupts as listed,
; and calls: op 0 WRTPSG ($0093), 1 RDPSG ($0096), 2 CHGSND ($0135), 3 LFTQ ($00F6), 4 PUTQ ($00F9), 5 GETVCP ($0150),
;  6 GETVC2 ($0153), 7 GICINI ($0090), 8 STRTMS ($0099), 9 BEEP ($00C0).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsnd1b.asm --row both
; SET: bit 0 port C bit 7; bits 1-4 the `qsets` entry; bit 5 R7 := $BF; bit 6 R7 := $3F and R8-R10 := $13 $14 $15;
; bit 7 port C := $2F (else $50) before bit 0. The capture starts at $C100; $C000-$C07F is a queue buffer (set 8).
; The capture: CAP+0 = $A5 when finished; per case an 80-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13..28 PSG R0-R15 after (read through ports $A0 / $A2)  +29 PPI port C ($AA) after
;   +30..53 QUETAB  +54..57 QUEBAK  +58 QUEUEN  +59 VOICEN  +60 MUSICF  +61 PLYCNT  after
;   +62..77 the 16 RAM bytes from WIN after  +78,79 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, the PSG's and the PPI's I/O ports.
;
; @cap C100
; @caplen 0C00
; @timeout 180

DONE    equ     $C100
CAP     equ     $C101
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2
cop     equ     $E910                   ; op, A, F, ei, SET, BC, DE, HL, WIN
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
cset    equ     $E914
cBC     equ     $E915
cDE     equ     $E917
cHL     equ     $E919
cwin    equ     $E91B
mask    equ     $E922
cidx    equ     $E923
raf     equ     $E940
rbc     equ     $E942
rde     equ     $E944
rhl     equ     $E946
rix     equ     $E948
riy     equ     $E94A
riff    equ     $E94C
QUETAB  equ     $F959
QUEBAK  equ     $F971
VOICAQ  equ     $F975
QUEUEN  equ     $FB3E
VOICEN  equ     $FB38
MUSICF  equ     $FB3F
PLYCNT  equ     $FB40
VCBA    equ     $FB41

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0BFF
                ld      (hl), 0
                ldir
                ld      hl, CAP+1
                ld      (ptr), hl
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
                ld      bc, 13
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                rrca
                rrca
                sbc     a, a                    ; the marker set: bit 2 of the case number
                ld      (mask), a
                ; the PSG
                ld      hl, psgpre
                ld      c, 0
p_lp:
                ld      a, c
                out     ($A0), a
                ld      a, (hl)
                out     ($A1), a
                inc     hl
                inc     c
                ld      a, c
                cp      14
                jr      nz, p_lp
                ld      a, (cset)               ; SET bit 5: R7 := $BF instead (every channel off)
                and     $20
                jr      z, r7k
                ld      a, 7
                out     ($A0), a
                ld      a, $BF
                out     ($A1), a
r7k:
                ld      a, (cset)               ; SET bit 6: R7 := $3F and R8-R10 := $13 $14 $15 instead
                and     $40
                jr      z, r5k
                ld      a, 7
                out     ($A0), a
                ld      a, $3F
                out     ($A1), a
                ld      b, $13
                ld      c, 8
r5l:
                ld      a, c
                out     ($A0), a
                ld      a, b
                out     ($A1), a
                inc     b
                inc     c
                ld      a, c
                cp      11
                jr      nz, r5l
r5k:
                ld      a, 15                   ; R15 := $CF (port B: what the BIOS leaves there)
                out     ($A0), a
                ld      a, $CF
                out     ($A1), a
                ; the PPI port C
                ld      a, (cset)
                ld      b, $50
                bit     7, a
                jr      z, pc1
                ld      b, $2F
pc1:
                rrca
                and     $80
                or      b
                out     ($AA), a
                ; the queue and voice buffers: (address low) XOR $A5
                ld      hl, VOICAQ
                ld      bc, 384
b_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, b_lp
                ld      hl, $C000               ; set 8's queue 0 buffer: (address low) XOR $A5
                ld      b, 128
k_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    k_lp
                ld      hl, $E800
                ld      b, 64
d_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    d_lp
                ld      hl, $FB35               ; $FB35-$FB37 and $FB39-$FB3D (PRSCNT, SAVSP, SAVVOL, MCLLEN, MCLPTR):
                ld      b, 9                    ; (address low) XOR $A5, VOICEN at $FB38 skipped below
c_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    c_lp
                ld      hl, VCBA
                ld      b, 111
v_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    v_lp
                ; the queue table and cells from qsets (32 bytes per set)
                ld      a, (cset)
                and     $1E
                rrca
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ld      de, qsets
                add     hl, de
                ld      de, QUETAB
                ld      bc, 28
                ldir
                ld      a, (hl)
                ld      (QUEUEN), a
                inc     hl
                ld      a, (hl)
                ld      (VOICEN), a
                inc     hl
                ld      a, (hl)
                ld      (MUSICF), a
                inc     hl
                ld      a, (hl)
                ld      (PLYCNT), a
                ; the stub: ei / nop, call target, ret
                ld      a, (cei)
                or      a
                ld      a, $00
                jr      z, s1
                ld      a, $FB
s1:
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
                jr      nc, s2
                inc     h
s2:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                ld      (STUB+2), de
                ; the registers
                ld      a, (cF)
                ld      c, a
                ld      a, (cA)
                ld      b, a
                push    bc
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
                ld      bc, (cBC)
                ld      de, (cDE)
                ld      hl, (cHL)
                pop     af
                call    STUB
                ld      (rhl), hl
                ld      (rde), de
                ld      (rbc), bc
                ld      (rix), ix
                ld      (riy), iy
                push    af
                pop     hl
                ld      (raf), hl
                ld      a, i                    ; P/V := IFF2, read twice (an interrupt during LD A,I reads 0)
                jp      pe, i_on
                ld      a, i
i_on:
                di
                push    af
                pop     hl
                ld      a, l
                and     4
                jr      z, i0
                ld      a, 1
i0:
                ld      (riff), a
                ld      hl, raf+1
                call    emitm
                ld      hl, raf
                call    emitm
                ld      hl, rbc+1
                call    emitm
                ld      hl, rbc
                call    emitm
                ld      hl, rde+1
                call    emitm
                ld      hl, rde
                call    emitm
                ld      hl, rhl+1
                call    emitm
                ld      hl, rhl
                call    emitm
                ld      hl, rix+1
                call    emitm
                ld      hl, rix
                call    emitm
                ld      hl, riy+1
                call    emitm
                ld      hl, riy
                call    emitm
                ld      hl, riff
                call    emitm
                ld      c, 0                    ; PSG R0-R15
r_lp:
                ld      a, c
                out     ($A0), a
                in      a, ($A2)
                call    emit
                inc     c
                ld      a, c
                cp      16
                jr      nz, r_lp
                in      a, ($AA)
                call    emit
                ld      hl, QUETAB
                ld      b, 28
q_lp:
                call    emitm
                inc     hl
                djnz    q_lp
                ld      hl, QUEUEN
                call    emitm
                ld      hl, VOICEN
                call    emitm
                ld      hl, MUSICF
                call    emitm
                ld      hl, PLYCNT
                call    emitm
                ld      hl, (cwin)
                ld      b, 16
w_lp:
                call    emitm
                inc     hl
                djnz    w_lp
                xor     a
                call    emit
                call    emit
                ld      hl, cidx
                inc     (hl)
                jp      next

targets:
                dw      $0093, $0096, $0135, $00F6, $00F9, $0150, $0153, $0090, $0099, $00C0
psgpre:
                db      $A1, $02, $B3, $04, $C5, $06, $17, $B8, $09, $0A, $0B, $5C, $1D, $0E

; the queue sets: QUETAB (24: per queue put, get, back flag, size, address), QUEBAK (4), QUEUEN, VOICEN, MUSICF,
; PLYCNT; 32 bytes each
qsets:
                db      $00, $00, $00, $7F
                dw      $F975
                db      $05, $02, $00, $7F
                dw      $F9F5
                db      $7E, $7F, $00, $7F
                dw      $FA75
                db      $03, $04, $00, $3F
                dw      $E800
                db      $11, $22, $33, $44
                db      $01, $00, $00, $00
                db      $10, $10, $01, $7F
                dw      $F975
                db      $7F, $00, $00, $7F
                dw      $F9F5
                db      $00, $01, $00, $7F
                dw      $FA75
                db      $3F, $00, $01, $3F
                dw      $E800
                db      $55, $66, $77, $88
                db      $02, $01, $07, $03
                db      $40, $3F, $00, $7F
                dw      $F975
                db      $00, $00, $01, $7F
                dw      $F9F5
                db      $20, $20, $00, $7F
                dw      $FA75
                db      $3E, $3F, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $02, $00, $00
                db      $00, $00, $00, $7F
                dw      $F975
                db      $05, $02, $00, $7F
                dw      $F9F5
                db      $00, $00, $00, $7F
                dw      $FA75
                db      $00, $00, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $00, $00, $03
                db      $00, $00, $00, $7F
                dw      $F975
                db      $00, $00, $00, $7F
                dw      $F9F5
                db      $00, $00, $00, $7F
                dw      $FA75
                db      $00, $00, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $00, $07, $00
                db      $0F, $00, $00, $7F
                dw      $F9F0
                db      $7F, $05, $00, $7F
                dw      $F9F5
                db      $03, $50, $00, $7E
                dw      $FA75
                db      $3F, $05, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $03, $00, $00
                db      $00, $00, $00, $7F
                dw      $F975
                db      $00, $00, $00, $7F
                dw      $F9F5
                db      $00, $00, $00, $7F
                dw      $FA75
                db      $00, $00, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $00, $03, $05
                db      $00, $00, $00, $7F
                dw      $F975
                db      $00, $00, $00, $7F
                dw      $F9F5
                db      $00, $00, $00, $7F
                dw      $FA75
                db      $00, $00, $00, $3F
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $00, $00, $01
                db      $03, $50, $00, $7F
                dw      $C000
                db      $02, $50, $00, $7E
                dw      $F9F5
                db      $02, $50, $00, $7E
                dw      $FA75
                db      $00, $05, $00, $3E
                dw      $E800
                db      $00, $00, $00, $00
                db      $00, $01, $00, $00

finish:
                ld      a, $C3
                call    emit
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emitm:
                ld      a, (hl)
emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; ---- cases: op, A, F, interrupts, SET; BC, DE, HL; WIN; $FF ends ----
cases:
                db      $07, $A7, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $FB41   ; 107
                db      $07, $A7, $00, $00, $0A
                dw      $1357, $9BDF, $2468, $F9F5   ; 108
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FA75   ; 109
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FAE5   ; 110
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F9E5   ; 111
                db      $07, $A7, $00, $00, $40
                dw      $1357, $9BDF, $2468, $FB30   ; 112
                db      $08, $A7, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $FB41   ; 113
                db      $08, $A7, $FF, $00, $0C
                dw      $1357, $9BDF, $2468, $FB41   ; 114
                db      $08, $A7, $00, $00, $0E
                dw      $1357, $9BDF, $2468, $FB41   ; 115
                db      $08, $A7, $00, $00, $06
                dw      $1357, $9BDF, $2468, $FB66   ; 116
                db      $08, $A7, $00, $00, $06
                dw      $1357, $9BDF, $2468, $FB8B   ; 117
                db      $09, $A7, $00, $00, $21
                dw      $1357, $9BDF, $2468, $FB51   ; 118
                db      $09, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB71   ; 119
                db      $09, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB91   ; 120
                db      $09, $00, $FF, $00, $40
                dw      $2468, $9B00, $2468, $FB30   ; 121
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB30   ; 122
                db      $02, $00, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $F975   ; 123
                db      $02, $00, $00, $00, $80
                dw      $1357, $9BDF, $2468, $F975   ; 124
                db      $02, $01, $00, $00, $80
                dw      $1357, $9BDF, $2468, $F975   ; 125
                db      $05, $00, $FF, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 126
                db      $05, $21, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 127
                db      $06, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2405, $F975   ; 128
                db      $04, $02, $FF, $01, $01
                dw      $1357, $9B5A, $2468, $FA75   ; 129
                db      $04, $00, $00, $00, $10
                dw      $1357, $9B5A, $2468, $C000   ; 130
                db      $04, $01, $00, $00, $10
                dw      $1357, $9B5A, $2468, $F9F5   ; 131
                db      $04, $03, $00, $00, $10
                dw      $1357, $9B5A, $2468, $E800   ; 132
                db      $03, $01, $00, $00, $10
                dw      $1357, $9BDF, $2468, $F975   ; 133
                db      $03, $02, $00, $00, $10
                dw      $1357, $9BDF, $2468, $F975   ; 134
                db      $FF
