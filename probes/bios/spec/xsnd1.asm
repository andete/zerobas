; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSND1 -- docs/bios/WRTPSG.md, RDPSG.md, CHGSND.md, LFTQ.md, PUTQ.md, GETVCP.md, GETVC2.md, GICINI.md, STRTMS.md, BEEP.md
; round 4 (2026-11-19; round 1 had cases 0-57, round 2 58-71, round 3 72-74): the sound region's calls. Per case (the table `cases` at the end: op, A, F, interrupts, SET, BC, DE,
; HL, WIN) the probe sets, BY HAND:
;   - PSG registers R0-R13 := $A1 $02 $B3 $04 $C5 $06 $17 $B8 $09 $0A $0B $5C $1D $0E (R7 $B8: port A in, port B out)
;     and R15 := $CF, through the PSG's ports $A0 / $A1 (R7 := $BF with bit 4 of SET); R14 (port A, an input) is not
;     written;
;   - the PPI's port C ($AA) := $50, or $D0 with bit 0 of SET (bit 7 the 1-bit sound);
;   - QUETAB ($F959, 4 queues x 6 bytes: put, get, back flag, size, address), QUEBAK ($F971-$F974), QUEUEN ($FB3E),
;     VOICEN ($FB38), MUSICF ($FB3F), PLYCNT ($FB40) := the `qsets` entry (SET AND $0E) / 2 names;
;   - the queue buffers VOICAQ ($F975, 128), VOICBQ ($F9F5, 128), VOICCQ ($FA75, 128), queue 3's buffer at $E800 (the
;     probe's own RAM: RS2IQ, $FAF5-$FB34, is left alone -- the disk interface's reference keeps something there, and
;     overwriting it stops that machine) and the voice buffers VCBA ($FB41) .. VCBC ($FB8B + 37) := (address low) XOR $A5.
; Then IX $4321, IY $8765 (XOR $FF when bit 2 of the case number is set), A, F, BC, DE, HL and interrupts as listed,
; and calls: op 0 WRTPSG ($0093), 1 RDPSG ($0096), 2 CHGSND ($0135), 3 LFTQ ($00F6), 4 PUTQ ($00F9), 5 GETVCP ($0150),
;  6 GETVC2 ($0153), 7 GICINI ($0090), 8 STRTMS ($0099), 9 BEEP ($00C0).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsnd1.asm --row both
; The capture: CAP+0 = $A5 when finished; per case an 80-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13..28 PSG R0-R15 after (read through ports $A0 / $A2)  +29 PPI port C ($AA) after
;   +30..53 QUETAB  +54..57 QUEBAK  +58 QUEUEN  +59 VOICEN  +60 MUSICF  +61 PLYCNT  after
;   +62..77 the 16 RAM bytes from WIN after  +78,79 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, the PSG's and the PPI's I/O ports.
;
; @cap C000
; @caplen 2700
; @timeout 180

DONE    equ     $C000
CAP     equ     $C001
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
                ld      bc, $26FF
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
                ld      a, (cset)               ; SET bit 4: R7 := $BF instead (every channel off)
                and     $10
                jr      z, r7k
                ld      a, 7
                out     ($A0), a
                ld      a, $BF
                out     ($A1), a
r7k:
                ld      a, 15                   ; R15 := $CF (port B: what the BIOS leaves there)
                out     ($A0), a
                ld      a, $CF
                out     ($A1), a
                ; the PPI port C
                ld      a, (cset)
                rrca
                and     $80
                or      $50
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
                ld      hl, $E800
                ld      b, 64
d_lp:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    d_lp
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
                and     $0E
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
                db      $00, $00, $00, $00, $00
                dw      $1357, $9B55, $2468, $F975   ; 0
                db      $00, $07, $00, $00, $00
                dw      $1357, $9BB8, $2468, $F975   ; 1
                db      $00, $08, $00, $00, $00
                dw      $1357, $9B1F, $2468, $F975   ; 2
                db      $00, $0D, $00, $00, $00
                dw      $1357, $9B09, $2468, $F975   ; 3
                db      $00, $0F, $00, $00, $00
                dw      $1357, $9B8F, $2468, $F975   ; 4
                db      $00, $0E, $00, $00, $00
                dw      $1357, $9BAA, $2468, $F975   ; 5
                db      $00, $10, $00, $00, $00
                dw      $1357, $9B33, $2468, $F975   ; 6
                db      $00, $40, $00, $00, $00
                dw      $1357, $9B66, $2468, $F975   ; 7
                db      $00, $01, $FF, $01, $00
                dw      $1357, $9B0F, $2468, $F975   ; 8
                db      $01, $00, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 9
                db      $01, $07, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 10
                db      $01, $08, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 11
                db      $01, $0D, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 12
                db      $01, $0E, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 13
                db      $01, $0F, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 14
                db      $01, $10, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 15
                db      $01, $40, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 16
                db      $01, $03, $FF, $01, $00
                dw      $1357, $9BDF, $2468, $F975   ; 17
                db      $02, $00, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 18
                db      $02, $01, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 19
                db      $02, $00, $00, $00, $01
                dw      $1357, $9BDF, $2468, $F975   ; 20
                db      $02, $01, $00, $00, $01
                dw      $1357, $9BDF, $2468, $F975   ; 21
                db      $02, $FF, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 22
                db      $02, $80, $00, $00, $01
                dw      $1357, $9BDF, $2468, $F975   ; 23
                db      $02, $02, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 24
                db      $03, $00, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 25
                db      $03, $01, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 26
                db      $03, $02, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 27
                db      $03, $03, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 28
                db      $03, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468, $F975   ; 29
                db      $03, $01, $00, $00, $02
                dw      $1357, $9BDF, $2468, $F975   ; 30
                db      $03, $02, $00, $00, $02
                dw      $1357, $9BDF, $2468, $F975   ; 31
                db      $03, $03, $00, $00, $02
                dw      $1357, $9BDF, $2468, $F975   ; 32
                db      $03, $00, $00, $00, $04
                dw      $1357, $9BDF, $2468, $F975   ; 33
                db      $03, $01, $00, $00, $04
                dw      $1357, $9BDF, $2468, $F975   ; 34
                db      $03, $02, $00, $00, $04
                dw      $1357, $9BDF, $2468, $F975   ; 35
                db      $03, $03, $00, $00, $04
                dw      $1357, $9BDF, $2468, $F975   ; 36
                db      $04, $00, $00, $00, $00
                dw      $1357, $9B5A, $2468, $F975   ; 37
                db      $04, $01, $00, $00, $00
                dw      $1357, $9B5A, $2468, $F9F0   ; 38
                db      $04, $02, $00, $00, $00
                dw      $1357, $9B5A, $2468, $FAE5   ; 39
                db      $04, $03, $00, $00, $00
                dw      $1357, $9B5A, $2468, $E800   ; 40
                db      $04, $00, $00, $00, $02
                dw      $1357, $9B5A, $2468, $F980   ; 41
                db      $04, $01, $00, $00, $02
                dw      $1357, $9B5A, $2468, $FA68   ; 42
                db      $04, $02, $00, $00, $02
                dw      $1357, $9B5A, $2468, $FA75   ; 43
                db      $04, $03, $00, $00, $02
                dw      $1357, $9B5A, $2468, $E830   ; 44
                db      $04, $00, $00, $00, $04
                dw      $1357, $9B5A, $2468, $F9B0   ; 45
                db      $04, $03, $00, $00, $04
                dw      $1357, $9B5A, $2468, $E830   ; 46
                db      $05, $00, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 47
                db      $05, $01, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 48
                db      $05, $02, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 49
                db      $05, $03, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 50
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2400, $F975   ; 51
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2405, $F975   ; 52
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2424, $F975   ; 53
                db      $06, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2400, $F975   ; 54
                db      $06, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2407, $F975   ; 55
                db      $06, $A7, $00, $00, $04
                dw      $1357, $9BDF, $2400, $F975   ; 56
                db      $06, $A7, $00, $00, $04
                dw      $1357, $9BDF, $2424, $F975   ; 57
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB41   ; 58
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB51   ; 59
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB61   ; 60
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB71   ; 61
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB81   ; 62
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB91   ; 63
                db      $07, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FBA1   ; 64
                db      $07, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $F975   ; 65
                db      $07, $A7, $00, $00, $04
                dw      $1357, $9BDF, $2468, $FB30   ; 66
                db      $08, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB41   ; 67
                db      $08, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $FB41   ; 68
                db      $08, $A7, $00, $00, $04
                dw      $1357, $9BDF, $2468, $FB41   ; 69
                db      $08, $A7, $00, $00, $06
                dw      $1357, $9BDF, $2468, $FB41   ; 70
                db      $08, $A7, $00, $00, $08
                dw      $1357, $9BDF, $2468, $FB41   ; 71
                db      $07, $A7, $00, $00, $10
                dw      $1357, $9BDF, $2468, $FB41   ; 72
                db      $09, $A7, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB41   ; 73
                db      $09, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $FB41   ; 74
                db      $02, $01, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $F975   ; 75
                db      $03, $01, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $F9F5   ; 76
                db      $04, $00, $FF, $01, $01
                dw      $1357, $9B5A, $2468, $F975   ; 77
                db      $05, $01, $FF, $01, $01
                dw      $1357, $9BDF, $2468, $FB66   ; 78
                db      $06, $A7, $FF, $01, $01
                dw      $1357, $9BDF, $2405, $FB41   ; 79
                db      $00, $02, $00, $00, $01
                dw      $1357, $9B33, $2468, $F975   ; 80
                db      $01, $02, $00, $00, $01
                dw      $1357, $9BDF, $2468, $F975   ; 81
                db      $04, $01, $00, $00, $0A
                dw      $1357, $9B5A, $2468, $F9F5   ; 82
                db      $04, $00, $00, $00, $0A
                dw      $1357, $9B5A, $2468, $F9F8   ; 83
                db      $04, $03, $00, $00, $0A
                dw      $1357, $9B5A, $2468, $E800   ; 84
                db      $04, $01, $00, $00, $02
                dw      $1357, $9B5A, $2468, $F9F5   ; 85
                db      $04, $03, $00, $00, $02
                dw      $1357, $9B5A, $2468, $E800   ; 86
                db      $04, $02, $00, $00, $00
                dw      $2468, $9B5A, $2468, $FA75   ; 87
                db      $03, $01, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F9F5   ; 88
                db      $03, $02, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FA75   ; 89
                db      $03, $03, $00, $00, $00
                dw      $1357, $9BDF, $2468, $E800   ; 90
                db      $03, $02, $00, $00, $0A
                dw      $1357, $9BDF, $2468, $F975   ; 91
                db      $03, $00, $00, $00, $0A
                dw      $1357, $9BDF, $2468, $F975   ; 92
                db      $03, $04, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 93
                db      $05, $04, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 94
                db      $05, $06, $00, $00, $00
                dw      $1357, $9BDF, $2468, $F975   ; 95
                db      $05, $00, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB41   ; 96
                db      $05, $02, $00, $00, $00
                dw      $1357, $9BDF, $2468, $FB8B   ; 97
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $24C0, $F975   ; 98
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $0005, $F975   ; 99
                db      $06, $A7, $00, $00, $00
                dw      $1357, $9BDF, $FF05, $F975   ; 100
                db      $06, $A7, $00, $00, $0A
                dw      $1357, $9BDF, $2405, $F975   ; 101
                db      $06, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2405, $FB66   ; 102
                db      $00, $07, $00, $00, $00
                dw      $1357, $9BBF, $2468, $F975   ; 103
                db      $00, $07, $00, $00, $00
                dw      $1357, $9B3F, $2468, $F975   ; 104
                db      $00, $0F, $00, $00, $00
                dw      $1357, $9B80, $2468, $F975   ; 105
                db      $00, $0F, $00, $00, $00
                dw      $1357, $9BC0, $2468, $F975   ; 106
                db      $FF
