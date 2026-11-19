; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XINP1 -- the input region's BIOS calls round 2 (2026-11-19; round 1 had cases 0-62, run with the frame interrupt on): SNSMAT, KILBUF, CHGCAP, GTSTCK, GTTRIG, BREAKX, ISCNTC,
; CKCNTC, GTPAD, GTPDL. At the start the probe turns the VDP's frame interrupt off (R#1 := RG1SAV AND $DF), so no timer
; interrupt runs (and scans the keys) whatever the calls do with IFF. Per case (the table `cases` at the end: op, A, F,
; interrupts, ROW1, MASK1, ROW2, MASK2, INTFLG, PORTC; BC, DE, HL) the probe sets, BY HAND:
;   - the keyboard matrix: no key, except MASK1 in ROW1 and MASK2 in ROW2 (bit set = pressed; ROW $FF none), through
;     the debugger at KSET (@keyset: hardware input, as a person would press the keys);
;   - PUTPNT ($F3F8) := KEYBUF + 5, GETPNT ($F3FA) := KEYBUF + 2 (three keys queued), INTFLG ($FC9B) := the case's,
;     CAPST ($FCAB) := $00, TRGFLG ($F3E8) := $F1, NEWKEY ($FBE5) / OLDKEY ($FBDA) := $FF x 11;
;   - the PPI's port C ($AA) := PORTC (bit 6 the CAPS lamp, bit 7 the 1-bit sound);
;   - PSG R15 := $CF.
; Then IX $4321, IY $8765 (XOR $FF when bit 2 of the case number is set), A, F, BC, DE, HL and interrupts as listed,
; and calls: op 0 SNSMAT ($0141), 1 KILBUF ($0156), 2 CHGCAP ($0132), 3 GTSTCK ($00D5), 4 GTTRIG ($00D8), 5 BREAKX
; ($00B7), 6 ISCNTC ($00BA), 7 CKCNTC ($00BD), 8 GTPAD ($00DB), 9 GTPDL ($00DE). Nothing is plugged into the joystick
; ports. ISCNTC / CKCNTC run with INTFLG 0 only (a break pending leaves the call for BASIC's break handling).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xinp1.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 48-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13 PPI port C ($AA)  +14,15 PSG R14 / R15  +16,17 PUTPNT  +18,19 GETPNT  +20 INTFLG  +21 CAPST
;   +22 TRGFLG  +23..33 NEWKEY  +34..44 OLDKEY  +45..47 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, the PPI's and the PSG's I/O ports, and the key
; matrix set through the debugger (input, not a ROM byte).
;
; @cap C000
; @caplen 1800
; @timeout 180
; @keyset E8F0 E8E0

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
KSET    equ     $E8F0
KLIST   equ     $E8E0
STUB    equ     $E8F2
cop     equ     $E910                   ; op, A, F, ei, ROW1, MASK1, ROW2, MASK2, INTFLG, BC, DE, HL
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
crow1   equ     $E914
cmask1  equ     $E915
crow2   equ     $E916
cmask2  equ     $E917
cint    equ     $E918
cpc     equ     $E919
cBC     equ     $E91A
cDE     equ     $E91C
cHL     equ     $E91E
mask    equ     $E922
cidx    equ     $E923
raf     equ     $E940
rbc     equ     $E942
rde     equ     $E944
rhl     equ     $E946
rix     equ     $E948
riy     equ     $E94A
riff    equ     $E94C
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA
KEYBUF  equ     $FBF0
INTFLG  equ     $FC9B
CAPST   equ     $FCAB
TRGFLG  equ     $F3E8
NEWKEY  equ     $FBE5
OLDKEY  equ     $FBDA

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $17FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (KSET), a
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
                xor     a
                ld      (cidx), a
                ld      a, ($F3E0)              ; RG1SAV: the frame interrupt off
                and     $DF
                out     ($99), a
                ld      a, $81
                out     ($99), a
next:
                di
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, finish
                ld      de, cop
                ld      bc, 16
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                rrca
                rrca
                sbc     a, a                    ; the marker set: bit 2 of the case number
                ld      (mask), a
                ; the key matrix list: all 0, MASK1 at ROW1, MASK2 at ROW2
                ld      hl, KLIST
                ld      b, 11
kz:
                ld      (hl), 0
                inc     hl
                djnz    kz
                ld      a, (crow1)
                ld      b, a
                ld      a, (cmask1)
                call    kput
                ld      a, (crow2)
                ld      b, a
                ld      a, (cmask2)
                call    kput
                call    KSET
                ; the work area
                ld      hl, KEYBUF+5
                ld      (PUTPNT), hl
                ld      hl, KEYBUF+2
                ld      (GETPNT), hl
                ld      a, (cint)
                ld      (INTFLG), a
                xor     a
                ld      (CAPST), a
                ld      a, $F1
                ld      (TRGFLG), a
                ld      hl, NEWKEY
                ld      b, 11
nk:
                ld      (hl), $FF
                inc     hl
                djnz    nk
                ld      hl, OLDKEY
                ld      b, 11
ok:
                ld      (hl), $FF
                inc     hl
                djnz    ok
                ld      a, (cpc)
                out     ($AA), a
                ld      a, 15
                out     ($A0), a
                ld      a, $CF
                out     ($A1), a
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
                in      a, ($AA)
                call    emit
                ld      a, 14
                out     ($A0), a
                in      a, ($A2)
                call    emit
                ld      a, 15
                out     ($A0), a
                in      a, ($A2)
                call    emit
                ld      hl, PUTPNT
                ld      b, 4
w1:
                call    emitm
                inc     hl
                djnz    w1
                ld      hl, INTFLG
                call    emitm
                ld      hl, CAPST
                call    emitm
                ld      hl, TRGFLG
                call    emitm
                ld      hl, NEWKEY
                ld      b, 11
w2:
                call    emitm
                inc     hl
                djnz    w2
                ld      hl, OLDKEY
                ld      b, 11
w3:
                call    emitm
                inc     hl
                djnz    w3
                xor     a
                call    emit
                call    emit
                call    emit
                ld      hl, cidx
                inc     (hl)
                jp      next

; kput -- KLIST[B] := A (B $FF: none)
kput:
                ld      c, a
                ld      a, b
                cp      11
                ret     nc
                ld      e, a
                ld      d, 0
                ld      hl, KLIST
                add     hl, de
                ld      (hl), c
                ret

targets:
                dw      $0141, $0156, $0132, $00D5, $00D8, $00B7, $00BA, $00BD, $00DB, $00DE

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

; ---- cases: op, A, F, interrupts, ROW1, MASK1, ROW2, MASK2, INTFLG, PORTC; BC, DE, HL; $FF ends ----
cases:
                db      $00, $00, $00, $00, $00, $02, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 0
                db      $00, $01, $00, $00, $01, $80, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 1
                db      $00, $02, $00, $00, $02, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 2
                db      $00, $05, $00, $00, $05, $40, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 3
                db      $00, $06, $00, $00, $06, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 4
                db      $00, $07, $00, $00, $07, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 5
                db      $00, $08, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 6
                db      $00, $08, $00, $00, $08, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 7
                db      $00, $09, $00, $00, $09, $08, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 8
                db      $00, $0A, $00, $00, $0A, $04, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 9
                db      $00, $08, $FF, $01, $08, $F0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 10
                db      $00, $0B, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 11
                db      $00, $FF, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 12
                db      $01, $A7, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 13
                db      $01, $00, $FF, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 14
                db      $02, $00, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 15
                db      $02, $01, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 16
                db      $02, $FF, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 17
                db      $02, $80, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 18
                db      $02, $00, $FF, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 19
                db      $03, $00, $00, $00, $08, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 20
                db      $03, $00, $00, $00, $08, $20, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 21
                db      $03, $00, $00, $00, $08, $A0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 22
                db      $03, $00, $00, $00, $08, $80, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 23
                db      $03, $00, $00, $00, $08, $C0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 24
                db      $03, $00, $00, $00, $08, $40, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 25
                db      $03, $00, $00, $00, $08, $50, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 26
                db      $03, $00, $00, $00, $08, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 27
                db      $03, $00, $00, $00, $08, $30, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 28
                db      $03, $00, $00, $00, $08, $60, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 29
                db      $03, $00, $00, $00, $08, $90, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 30
                db      $03, $00, $00, $00, $08, $F0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 31
                db      $03, $00, $00, $00, $08, $70, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 32
                db      $03, $01, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 33
                db      $03, $02, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 34
                db      $03, $03, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 35
                db      $03, $00, $FF, $01, $08, $20, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 36
                db      $04, $00, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 37
                db      $04, $00, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 38
                db      $04, $01, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 39
                db      $04, $02, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 40
                db      $04, $03, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 41
                db      $04, $04, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 42
                db      $04, $05, $00, $00, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 43
                db      $04, $00, $FF, $01, $08, $01, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 44
                db      $05, $A7, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 45
                db      $05, $A7, $00, $00, $06, $02, $07, $10, $00, $50
                dw      $1357, $9BDF, $2468   ; 46
                db      $05, $A7, $00, $00, $07, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 47
                db      $05, $A7, $00, $00, $06, $02, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 48
                db      $05, $A7, $FF, $01, $06, $02, $07, $10, $00, $50
                dw      $1357, $9BDF, $2468   ; 49
                db      $06, $A7, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 50
                db      $06, $A7, $FF, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 51
                db      $07, $A7, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 52
                db      $07, $A7, $FF, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 53
                db      $08, $00, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 54
                db      $08, $01, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 55
                db      $08, $02, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 56
                db      $08, $03, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 57
                db      $08, $04, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 58
                db      $08, $07, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 59
                db      $09, $01, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 60
                db      $09, $02, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 61
                db      $09, $0C, $00, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 62
                db      $09, $01, $00, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 63
                db      $08, $00, $00, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 64
                db      $08, $01, $00, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 65
                db      $02, $01, $FF, $00, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 66
                db      $02, $00, $00, $00, $FF, $00, $FF, $00, $00, $A0
                dw      $1357, $9BDF, $2468   ; 67
                db      $02, $01, $00, $00, $FF, $00, $FF, $00, $00, $A0
                dw      $1357, $9BDF, $2468   ; 68
                db      $05, $A7, $00, $01, $FF, $00, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 69
                db      $05, $A7, $00, $00, $06, $01, $07, $10, $00, $50
                dw      $1357, $9BDF, $2468   ; 70
                db      $00, $12, $00, $00, $02, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 71
                db      $00, $08, $00, $00, $08, $01, $FF, $00, $00, $5A
                dw      $1357, $9BDF, $2468   ; 72
                db      $00, $03, $00, $00, $03, $20, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 73
                db      $00, $04, $00, $00, $04, $08, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 74
                db      $00, $02, $00, $00, $02, $10, $FF, $00, $00, $D0
                dw      $1357, $9BDF, $2468   ; 75
                db      $04, $00, $00, $00, $08, $10, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 76
                db      $03, $00, $00, $00, $08, $B0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 77
                db      $03, $00, $00, $00, $08, $D0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 78
                db      $03, $00, $00, $00, $08, $E0, $FF, $00, $00, $50
                dw      $1357, $9BDF, $2468   ; 79
                db      $03, $00, $00, $00, $08, $20, $FF, $00, $00, $D0
                dw      $1357, $9BDF, $2468   ; 80
                db      $FF
