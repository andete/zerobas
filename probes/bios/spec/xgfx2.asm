; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XGFX2 -- docs/bios/RIGHTC.md, LEFTC.md, UPC.md, TUPC.md, DOWNC.md, TDOWNC.md round 3 (2026-11-18; round 1 had cases 0-125, round 2 0-251): the calls that move
; the current graphics position (CLOC $F92A, CMASK $F92C) one pixel. Per case (the table `cases` at the end: op, A, F,
; interrupts, SCRMOD, BC, DE, HL, CLOC, CMASK, GRPCGP, MLTCGP) the probe sets, BY HAND: CLOC, CMASK, GRPCGP ($F3CB),
; MLTCGP ($F3D5), SCRMOD ($FCAF) := the case's -- CLOC / CMASK a pixel's position as MAPXYC gives it -- ATRBYT
; ($F3F2) := $77, ASPCT1 / ASPCT2 ($F40B / $F40D) := $1234 / $5678; then IX $4321, IY $8765 (XOR $FF when bit 2 of the
; case number is set), A, F, BC, DE, HL and interrupts as listed, and calls: op 0 RIGHTC ($00FC), 1 LEFTC ($00FF),
; 2 UPC ($0102), 3 TUPC ($0105), 4 DOWNC ($0108), 5 TDOWNC ($010B).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx2.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 28-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13,14 CLOC  +15 CMASK  +16 ATRBYT  +17,18 ASPCT1  +19,20 ASPCT2 (low, high)  +21 SCRMOD
;   +22,23 GRPCGP  +24,25 MLTCGP  after  +26,27 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area RAM.
;
; @cap C000
; @caplen 1F00
; @timeout 60

GTB     equ     $FF                     ; (case 255 gets ASPCT1 / ASPCT2 $0100 / $00C0)
;                      ; GTASPC's second case: ASPCT1 / ASPCT2 $0100 / $00C0
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2
cop     equ     $E910                   ; op, A, F, ei, SCRMOD, BC, DE, HL, CLOC (2), CMASK, GRPCGP (2), MLTCGP (2)
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
cscr    equ     $E914
cBC     equ     $E915
cDE     equ     $E917
cHL     equ     $E919
cclo    equ     $E91B
ccm     equ     $E91D
cgcg    equ     $E91E
cmcg    equ     $E920
mask    equ     $E922
cidx    equ     $E923
raf     equ     $E940
rbc     equ     $E942
rde     equ     $E944
rhl     equ     $E946
rix     equ     $E948
riy     equ     $E94A
riff    equ     $E94C
CLOC    equ     $F92A
CMASK   equ     $F92C
ATRBYT  equ     $F3F2
ASPCT1  equ     $F40B
ASPCT2  equ     $F40D
GRPCGP  equ     $F3CB
MLTCGP  equ     $F3D5
SCRMOD  equ     $FCAF

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1EFF
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
                ld      bc, 18
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                rrca
                rrca
                sbc     a, a                    ; the marker set: bit 2 of the case number
                ld      (mask), a
                ld      hl, (cclo)
                ld      (CLOC), hl
                ld      a, (ccm)
                ld      (CMASK), a
                ld      a, $77
                ld      (ATRBYT), a
                ld      hl, $1234
                ld      de, $5678
                ld      a, (cidx)
                cp      GTB
                jr      nz, asp
                ld      hl, $0100
                ld      de, $00C0
asp:
                ld      (ASPCT1), hl
                ld      (ASPCT2), de
                ld      hl, (cgcg)
                ld      (GRPCGP), hl
                ld      hl, (cmcg)
                ld      (MLTCGP), hl
                ld      a, (cscr)
                ld      (SCRMOD), a
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
                ld      hl, CLOC
                call    emitm
                inc     hl
                call    emitm
                inc     hl
                call    emitm                   ; CMASK
                ld      hl, ATRBYT
                call    emitm
                ld      hl, ASPCT1
                ld      b, 4
a_lp:
                call    emitm
                inc     hl
                djnz    a_lp
                ld      hl, SCRMOD
                call    emitm
                ld      hl, GRPCGP
                call    emitm
                inc     hl
                call    emitm
                ld      hl, MLTCGP
                call    emitm
                inc     hl
                call    emitm
                xor     a
                call    emit
                call    emit
                ld      hl, cidx
                inc     (hl)
                jp      next

targets:
                dw      $00FC, $00FF, $0102, $0105, $0108, $010B

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

; ---- cases: op, A, F, interrupts, SCRMOD; BC, DE, HL; CLOC; CMASK; GRPCGP, MLTCGP; $FF ends ----
cases:
                db      $00, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 0
                db      $00, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 1
                db      $00, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 2
                db      $00, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 3
                db      $00, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 4
                db      $00, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 5
                db      $00, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 6
                db      $00, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 7
                db      $00, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 8
                db      $00, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 9
                db      $00, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 10
                db      $00, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 11
                db      $00, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 12
                db      $00, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 13
                db      $00, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 14
                db      $00, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 15
                db      $00, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 16
                db      $00, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 17
                db      $00, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 18
                db      $00, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 19
                db      $00, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 20
                db      $01, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 21
                db      $01, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 22
                db      $01, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 23
                db      $01, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 24
                db      $01, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 25
                db      $01, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 26
                db      $01, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 27
                db      $01, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 28
                db      $01, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 29
                db      $01, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 30
                db      $01, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 31
                db      $01, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 32
                db      $01, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 33
                db      $01, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 34
                db      $01, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 35
                db      $01, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 36
                db      $01, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 37
                db      $01, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 38
                db      $01, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 39
                db      $01, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 40
                db      $01, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 41
                db      $02, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 42
                db      $02, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 43
                db      $02, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 44
                db      $02, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 45
                db      $02, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 46
                db      $02, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 47
                db      $02, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 48
                db      $02, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 49
                db      $02, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 50
                db      $02, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 51
                db      $02, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 52
                db      $02, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 53
                db      $02, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 54
                db      $02, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 55
                db      $02, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 56
                db      $02, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 57
                db      $02, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 58
                db      $02, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 59
                db      $02, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 60
                db      $02, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 61
                db      $02, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 62
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 63
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 64
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 65
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 66
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 67
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 68
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 69
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 70
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 71
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 72
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 73
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 74
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 75
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 76
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 77
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 78
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 79
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 80
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 81
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 82
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 83
                db      $04, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 84
                db      $04, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 85
                db      $04, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 86
                db      $04, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 87
                db      $04, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 88
                db      $04, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 89
                db      $04, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 90
                db      $04, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 91
                db      $04, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 92
                db      $04, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 93
                db      $04, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 94
                db      $04, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 95
                db      $04, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 96
                db      $04, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 97
                db      $04, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 98
                db      $04, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 99
                db      $04, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 100
                db      $04, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 101
                db      $04, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 102
                db      $04, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 103
                db      $04, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 104
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $80
                dw      $2000, $1000   ; 105
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2000
                db      $01
                dw      $2000, $1000   ; 106
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2000, $1000   ; 107
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $01
                dw      $2000, $1000   ; 108
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $20F8
                db      $80
                dw      $2000, $1000   ; 109
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2007
                db      $80
                dw      $2000, $1000   ; 110
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2000, $1000   ; 111
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3707
                db      $80
                dw      $2000, $1000   ; 112
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2662
                db      $08
                dw      $2000, $1000   ; 113
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $37FF
                db      $01
                dw      $2000, $1000   ; 114
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $3700
                db      $80
                dw      $2000, $1000   ; 115
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $F0
                dw      $2000, $1000   ; 116
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1000
                db      $0F
                dw      $2000, $1000   ; 117
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1008
                db      $F0
                dw      $2000, $1000   ; 118
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $0F
                dw      $2000, $1000   ; 119
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $10F8
                db      $F0
                dw      $2000, $1000   ; 120
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1007
                db      $F0
                dw      $2000, $1000   ; 121
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1100
                db      $F0
                dw      $2000, $1000   ; 122
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1507
                db      $F0
                dw      $2000, $1000   ; 123
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1164
                db      $0F
                dw      $2000, $1000   ; 124
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $15FF
                db      $0F
                dw      $2000, $1000   ; 125
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $0008
                db      $40
                dw      $0000, $1000   ; 126
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $0009
                db      $40
                dw      $0000, $1000   ; 127
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $0108
                db      $40
                dw      $0000, $1000   ; 128
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $000F
                db      $40
                dw      $0000, $1000   ; 129
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $010F
                db      $40
                dw      $0000, $1000   ; 130
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $160F
                db      $40
                dw      $0000, $1000   ; 131
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $1708
                db      $40
                dw      $0000, $1000   ; 132
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $170E
                db      $40
                dw      $0000, $1000   ; 133
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $170F
                db      $40
                dw      $0000, $1000   ; 134
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $40
                dw      $2000, $1000   ; 135
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2009
                db      $40
                dw      $2000, $1000   ; 136
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2108
                db      $40
                dw      $2000, $1000   ; 137
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $200F
                db      $40
                dw      $2000, $1000   ; 138
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $210F
                db      $40
                dw      $2000, $1000   ; 139
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $360F
                db      $40
                dw      $2000, $1000   ; 140
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $3708
                db      $40
                dw      $2000, $1000   ; 141
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $370E
                db      $40
                dw      $2000, $1000   ; 142
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $370F
                db      $40
                dw      $2000, $1000   ; 143
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $1808
                db      $40
                dw      $1800, $1000   ; 144
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $1809
                db      $40
                dw      $1800, $1000   ; 145
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $1908
                db      $40
                dw      $1800, $1000   ; 146
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $180F
                db      $40
                dw      $1800, $1000   ; 147
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $190F
                db      $40
                dw      $1800, $1000   ; 148
                db      $03, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2E0F
                db      $40
                dw      $1800, $1000   ; 149
                db      $03, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2F08
                db      $40
                dw      $1800, $1000   ; 150
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2F0E
                db      $40
                dw      $1800, $1000   ; 151
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2F0F
                db      $40
                dw      $1800, $1000   ; 152
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0020
                db      $0F
                dw      $2000, $0000   ; 153
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0021
                db      $0F
                dw      $2000, $0000   ; 154
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0027
                db      $0F
                dw      $2000, $0000   ; 155
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0120
                db      $0F
                dw      $2000, $0000   ; 156
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0127
                db      $0F
                dw      $2000, $0000   ; 157
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0427
                db      $0F
                dw      $2000, $0000   ; 158
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0520
                db      $0F
                dw      $2000, $0000   ; 159
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0526
                db      $0F
                dw      $2000, $0000   ; 160
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0527
                db      $0F
                dw      $2000, $0000   ; 161
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1020
                db      $0F
                dw      $2000, $1000   ; 162
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1021
                db      $0F
                dw      $2000, $1000   ; 163
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1027
                db      $0F
                dw      $2000, $1000   ; 164
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1120
                db      $0F
                dw      $2000, $1000   ; 165
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1127
                db      $0F
                dw      $2000, $1000   ; 166
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1427
                db      $0F
                dw      $2000, $1000   ; 167
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1520
                db      $0F
                dw      $2000, $1000   ; 168
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1526
                db      $0F
                dw      $2000, $1000   ; 169
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1527
                db      $0F
                dw      $2000, $1000   ; 170
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1020
                db      $0F
                dw      $0000, $1000   ; 171
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1021
                db      $0F
                dw      $0000, $1000   ; 172
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1027
                db      $0F
                dw      $0000, $1000   ; 173
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1120
                db      $0F
                dw      $0000, $1000   ; 174
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1127
                db      $0F
                dw      $0000, $1000   ; 175
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1427
                db      $0F
                dw      $0000, $1000   ; 176
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1520
                db      $0F
                dw      $0000, $1000   ; 177
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1526
                db      $0F
                dw      $0000, $1000   ; 178
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1527
                db      $0F
                dw      $0000, $1000   ; 179
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0820
                db      $0F
                dw      $1800, $0800   ; 180
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0821
                db      $0F
                dw      $1800, $0800   ; 181
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0827
                db      $0F
                dw      $1800, $0800   ; 182
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0920
                db      $0F
                dw      $1800, $0800   ; 183
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0927
                db      $0F
                dw      $1800, $0800   ; 184
                db      $03, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0C27
                db      $0F
                dw      $1800, $0800   ; 185
                db      $03, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0D20
                db      $0F
                dw      $1800, $0800   ; 186
                db      $03, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0D26
                db      $0F
                dw      $1800, $0800   ; 187
                db      $03, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0D27
                db      $0F
                dw      $1800, $0800   ; 188
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $0008
                db      $40
                dw      $0000, $1000   ; 189
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $0009
                db      $40
                dw      $0000, $1000   ; 190
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $0108
                db      $40
                dw      $0000, $1000   ; 191
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $000F
                db      $40
                dw      $0000, $1000   ; 192
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $010F
                db      $40
                dw      $0000, $1000   ; 193
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $160F
                db      $40
                dw      $0000, $1000   ; 194
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $1708
                db      $40
                dw      $0000, $1000   ; 195
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $170E
                db      $40
                dw      $0000, $1000   ; 196
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $170F
                db      $40
                dw      $0000, $1000   ; 197
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $40
                dw      $2000, $1000   ; 198
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2009
                db      $40
                dw      $2000, $1000   ; 199
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2108
                db      $40
                dw      $2000, $1000   ; 200
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $200F
                db      $40
                dw      $2000, $1000   ; 201
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $210F
                db      $40
                dw      $2000, $1000   ; 202
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $360F
                db      $40
                dw      $2000, $1000   ; 203
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3708
                db      $40
                dw      $2000, $1000   ; 204
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $370E
                db      $40
                dw      $2000, $1000   ; 205
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $370F
                db      $40
                dw      $2000, $1000   ; 206
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $1808
                db      $40
                dw      $1800, $1000   ; 207
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $1809
                db      $40
                dw      $1800, $1000   ; 208
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $1908
                db      $40
                dw      $1800, $1000   ; 209
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $180F
                db      $40
                dw      $1800, $1000   ; 210
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $190F
                db      $40
                dw      $1800, $1000   ; 211
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2E0F
                db      $40
                dw      $1800, $1000   ; 212
                db      $05, $A7, $FF, $00, $02
                dw      $1357, $9BDF, $2468, $2F08
                db      $40
                dw      $1800, $1000   ; 213
                db      $05, $A7, $00, $01, $02
                dw      $1357, $9BDF, $2468, $2F0E
                db      $40
                dw      $1800, $1000   ; 214
                db      $05, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468, $2F0F
                db      $40
                dw      $1800, $1000   ; 215
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0020
                db      $0F
                dw      $2000, $0000   ; 216
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0021
                db      $0F
                dw      $2000, $0000   ; 217
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0027
                db      $0F
                dw      $2000, $0000   ; 218
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0120
                db      $0F
                dw      $2000, $0000   ; 219
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0127
                db      $0F
                dw      $2000, $0000   ; 220
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0427
                db      $0F
                dw      $2000, $0000   ; 221
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0520
                db      $0F
                dw      $2000, $0000   ; 222
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0526
                db      $0F
                dw      $2000, $0000   ; 223
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0527
                db      $0F
                dw      $2000, $0000   ; 224
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1020
                db      $0F
                dw      $2000, $1000   ; 225
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1021
                db      $0F
                dw      $2000, $1000   ; 226
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1027
                db      $0F
                dw      $2000, $1000   ; 227
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1120
                db      $0F
                dw      $2000, $1000   ; 228
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1127
                db      $0F
                dw      $2000, $1000   ; 229
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1427
                db      $0F
                dw      $2000, $1000   ; 230
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1520
                db      $0F
                dw      $2000, $1000   ; 231
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1526
                db      $0F
                dw      $2000, $1000   ; 232
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1527
                db      $0F
                dw      $2000, $1000   ; 233
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1020
                db      $0F
                dw      $0000, $1000   ; 234
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1021
                db      $0F
                dw      $0000, $1000   ; 235
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1027
                db      $0F
                dw      $0000, $1000   ; 236
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1120
                db      $0F
                dw      $0000, $1000   ; 237
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1127
                db      $0F
                dw      $0000, $1000   ; 238
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $1427
                db      $0F
                dw      $0000, $1000   ; 239
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $1520
                db      $0F
                dw      $0000, $1000   ; 240
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $1526
                db      $0F
                dw      $0000, $1000   ; 241
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $1527
                db      $0F
                dw      $0000, $1000   ; 242
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0820
                db      $0F
                dw      $1800, $0800   ; 243
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0821
                db      $0F
                dw      $1800, $0800   ; 244
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0827
                db      $0F
                dw      $1800, $0800   ; 245
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0920
                db      $0F
                dw      $1800, $0800   ; 246
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0927
                db      $0F
                dw      $1800, $0800   ; 247
                db      $05, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0C27
                db      $0F
                dw      $1800, $0800   ; 248
                db      $05, $A7, $FF, $00, $03
                dw      $1357, $9BDF, $2468, $0D20
                db      $0F
                dw      $1800, $0800   ; 249
                db      $05, $A7, $00, $01, $03
                dw      $1357, $9BDF, $2468, $0D26
                db      $0F
                dw      $1800, $0800   ; 250
                db      $05, $A7, $FF, $01, $03
                dw      $1357, $9BDF, $2468, $0D27
                db      $0F
                dw      $1800, $0800   ; 251
                db      $03, $FF, $00, $00, $02
                dw      $1357, $9BDF, $2468, $0700
                db      $80
                dw      $0000, $1000   ; 252
                db      $03, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468, $0800
                db      $80
                dw      $0000, $1000   ; 253
                db      $03, $FF, $00, $00, $02
                dw      $1357, $9BDF, $2468, $0F00
                db      $80
                dw      $0000, $1000   ; 254
                db      $03, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468, $1000
                db      $80
                dw      $0000, $1000   ; 255
                db      $03, $FF, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2700
                db      $80
                dw      $2000, $1000   ; 256
                db      $03, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2800
                db      $80
                dw      $2000, $1000   ; 257
                db      $03, $FF, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2F00
                db      $80
                dw      $2000, $1000   ; 258
                db      $03, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3000
                db      $80
                dw      $2000, $1000   ; 259
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2100
                db      $80
                dw      $2100, $1000   ; 260
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2008
                db      $80
                dw      $2004, $1000   ; 261
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $2004
                db      $80
                dw      $2004, $1000   ; 262
                db      $05, $FF, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $0707
                db      $80
                dw      $0000, $1000   ; 263
                db      $05, $00, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $0807
                db      $80
                dw      $0000, $1000   ; 264
                db      $05, $FF, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $0F07
                db      $80
                dw      $0000, $1000   ; 265
                db      $05, $00, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $1007
                db      $80
                dw      $0000, $1000   ; 266
                db      $05, $FF, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $2707
                db      $80
                dw      $2000, $1000   ; 267
                db      $05, $00, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $2807
                db      $80
                dw      $2000, $1000   ; 268
                db      $05, $FF, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $2F07
                db      $80
                dw      $2000, $1000   ; 269
                db      $05, $00, $00, $00, $02
                dw      $ECA8, $6420, $DB97, $3007
                db      $80
                dw      $2000, $1000   ; 270
                db      $05, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468, $3807
                db      $80
                dw      $2100, $1000   ; 271
                db      $05, $00, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0607
                db      $F0
                dw      $2000, $0000   ; 272
                db      $05, $00, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0707
                db      $F0
                dw      $2000, $0000   ; 273
                db      $05, $00, $00, $00, $03
                dw      $1357, $9BDF, $2468, $8507
                db      $F0
                dw      $2000, $0000   ; 274
                db      $00, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0100
                db      $F1
                dw      $2000, $0000   ; 275
                db      $01, $A7, $00, $00, $03
                dw      $1357, $9BDF, $2468, $0100
                db      $1F
                dw      $2000, $0000   ; 276
                db      $FF
