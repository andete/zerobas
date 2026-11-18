; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XGFX1 -- docs/bios/FETCHC.md, STOREC.md, SETATR.md, GTASPC.md, MAPXYC.md round 2 (2026-11-19; round 1 had cases 0-31): the graphics calls
; that move values between the registers and the work area. Per case (the table `cases` at the end: op, A, F,
; interrupts, SCRMOD, BC, DE, HL) the probe sets, BY HAND: CLOC ($F92A) := $5A5A, CMASK ($F92C) := $A5, ATRBYT ($F3F2)
; := $77, ASPCT1 / ASPCT2 ($F40B / $F40D) := $1234 / $5678 (or $0100 / $00C0 in GTASPC's second case), GRPCGP ($F3CB)
; := $2000, MLTCGP ($F3D5) := $1000, SCRMOD ($FCAF) := the case's; then IX $4321, IY $8765 (XOR $FF when bit 2 of the
; case number is set), A, F, BC, DE, HL and interrupts as listed, and calls: op 0 FETCHC ($0114), 1 STOREC ($0117),
; 2 SETATR ($011A), 3 GTASPC ($0126), 4 MAPXYC ($0111).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx1.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 24-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13,14 CLOC  +15 CMASK  +16 ATRBYT  +17,18 ASPCT1  +19,20 ASPCT2 (low, high)  +21 SCRMOD  after
;   +22,23 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area RAM.
;
; @cap C000
; @caplen 0600
; @timeout 60

GTB     equ     12                      ; GTASPC's second case: ASPCT1 / ASPCT2 $0100 / $00C0
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2
cop     equ     $E910                   ; op, A, F, ei, SCRMOD, BC (2), DE (2), HL (2)
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
cscr    equ     $E914
cBC     equ     $E915
cDE     equ     $E917
cHL     equ     $E919
mask    equ     $E91B
cidx    equ     $E91C
raf     equ     $E920
rbc     equ     $E922
rde     equ     $E924
rhl     equ     $E926
rix     equ     $E928
riy     equ     $E92A
riff    equ     $E92C
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
                ld      bc, $05FF
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
                ld      bc, 11
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                rrca
                rrca
                sbc     a, a                    ; the marker set: bit 2 of the case number
                ld      (mask), a
                ld      hl, $5A5A
                ld      (CLOC), hl
                ld      a, $A5
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
                ld      hl, $2000
                ld      (GRPCGP), hl
                ld      hl, $1000
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
                xor     a
                call    emit
                call    emit
                ld      hl, cidx
                inc     (hl)
                jp      next

targets:
                dw      $0114, $0117, $011A, $0126, $0111

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

; ---- cases: op, A, F, interrupts, SCRMOD; BC, DE, HL; $FF ends ----
cases:
                db      $00, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468   ; 0
                db      $00, $00, $FF, $01, $03
                dw      $1357, $9BDF, $2468   ; 1
                db      $01, $10, $00, $01, $02
                dw      $1357, $9BDF, $2345   ; 2
                db      $01, $00, $FF, $00, $02
                dw      $1357, $9BDF, $0000   ; 3
                db      $01, $FF, $A5, $01, $03
                dw      $1357, $9BDF, $FFFF   ; 4
                db      $02, $00, $00, $00, $02
                dw      $1357, $9BDF, $2468   ; 5
                db      $02, $05, $FF, $01, $02
                dw      $1357, $9BDF, $2468   ; 6
                db      $02, $0F, $01, $00, $02
                dw      $1357, $9BDF, $2468   ; 7
                db      $02, $10, $00, $01, $02
                dw      $1357, $9BDF, $2468   ; 8
                db      $02, $FF, $FE, $00, $02
                dw      $1357, $9BDF, $2468   ; 9
                db      $02, $80, $5A, $01, $02
                dw      $1357, $9BDF, $2468   ; 10
                db      $03, $A7, $00, $00, $02
                dw      $1357, $9BDF, $2468   ; 11
                db      $03, $A7, $FF, $01, $02
                dw      $1357, $9BDF, $2468   ; 12
                db      $04, $A7, $00, $00, $02
                dw      $0000, $0000, $2468   ; 13
                db      $04, $A7, $FF, $00, $02
                dw      $0007, $0000, $2468   ; 14
                db      $04, $A7, $00, $01, $02
                dw      $0008, $0000, $2468   ; 15
                db      $04, $A7, $FF, $01, $02
                dw      $0009, $0001, $2468   ; 16
                db      $04, $A7, $00, $00, $02
                dw      $00FF, $00BF, $2468   ; 17
                db      $04, $A7, $FF, $00, $02
                dw      $0064, $0032, $2468   ; 18
                db      $04, $A7, $00, $01, $02
                dw      $0000, $0008, $2468   ; 19
                db      $04, $A7, $FF, $01, $02
                dw      $0100, $0000, $2468   ; 20
                db      $04, $A7, $00, $00, $02
                dw      $0000, $00C0, $2468   ; 21
                db      $04, $A7, $FF, $00, $02
                dw      $FFFF, $FFFF, $2468   ; 22
                db      $04, $A7, $00, $00, $03
                dw      $0000, $0000, $2468   ; 23
                db      $04, $A7, $FF, $00, $03
                dw      $0003, $0000, $2468   ; 24
                db      $04, $A7, $00, $01, $03
                dw      $0004, $0000, $2468   ; 25
                db      $04, $A7, $FF, $01, $03
                dw      $00FF, $00BF, $2468   ; 26
                db      $04, $A7, $00, $00, $03
                dw      $0064, $0032, $2468   ; 27
                db      $04, $A7, $FF, $00, $03
                dw      $0004, $0004, $2468   ; 28
                db      $04, $A7, $00, $01, $03
                dw      $0000, $0008, $2468   ; 29
                db      $04, $A7, $00, $00, $01
                dw      $0064, $0032, $2468   ; 30
                db      $04, $A7, $FF, $01, $00
                dw      $0064, $0032, $2468   ; 31
                db      $04, $A7, $00, $00, $03
                dw      $001F, $0000, $2468   ; 32
                db      $04, $A7, $FF, $00, $03
                dw      $0020, $0000, $2468   ; 33
                db      $04, $A7, $00, $01, $03
                dw      $003F, $0000, $2468   ; 34
                db      $04, $A7, $FF, $01, $03
                dw      $0040, $0000, $2468   ; 35
                db      $04, $A7, $00, $00, $03
                dw      $007F, $0000, $2468   ; 36
                db      $04, $A7, $FF, $00, $03
                dw      $0000, $0007, $2468   ; 37
                db      $04, $A7, $00, $01, $03
                dw      $0000, $003F, $2468   ; 38
                db      $04, $A7, $FF, $01, $03
                dw      $0000, $0040, $2468   ; 39
                db      $04, $A7, $00, $00, $03
                dw      $0000, $007F, $2468   ; 40
                db      $04, $A7, $FF, $00, $03
                dw      $0000, $0080, $2468   ; 41
                db      $04, $A7, $00, $01, $03
                dw      $0041, $0041, $2468   ; 42
                db      $FF
