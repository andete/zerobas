; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XGFX4 -- docs/bios/SCALXY.md round 1 (2026-11-19): the call that clips a graphics coordinate to the screen. xgfx1.asm's
; frame with its own table. Per case (the table `cases` at the end: op, A, F, interrupts, SCRMOD, BC, DE, HL, CLOC,
; CMASK, GRPCGP, MLTCGP) the probe sets, BY HAND: CLOC ($F92A), CMASK ($F92C), GRPCGP ($F3CB), MLTCGP ($F3D5), SCRMOD
; ($FCAF) := the case's; ATRBYT ($F3F2) := $77, ASPCT1 / ASPCT2 ($F40B / $F40D) := $1234 / $5678; then IX $4321, IY
; $8765 (XOR $FF when bit 2 of the case number is set), A, F, BC, DE, HL and interrupts as listed, and calls: op 0
; SCALXY ($010E).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx4.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 28-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13,14 CLOC  +15 CMASK  +16 ATRBYT  +17,18 ASPCT1  +19,20 ASPCT2 (low, high)  +21 SCRMOD
;   +22,23 GRPCGP  +24,25 MLTCGP  after  +26,27 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area RAM.
;
; @cap C000
; @caplen 0900
; @timeout 60

GTB     equ     $FF                     ; (no case gets GTASPC's second ASPCT1 / ASPCT2 preset)
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
                ld      bc, $08FF
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
                dw      $010E

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
                db      $00, $00, $00, $00, $02
                dw      $0064, $0032, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 0
                db      $00, $A7, $FF, $01, $02
                dw      $0000, $0000, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 1
                db      $00, $A7, $00, $00, $02
                dw      $00FF, $00BF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 2
                db      $00, $00, $00, $01, $02
                dw      $0100, $00BF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 3
                db      $00, $A7, $FF, $00, $02
                dw      $00FF, $00C0, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 4
                db      $00, $A7, $00, $01, $02
                dw      $0100, $00C0, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 5
                db      $00, $00, $00, $00, $02
                dw      $FFFF, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 6
                db      $00, $A7, $FF, $01, $02
                dw      $0064, $FFFF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 7
                db      $00, $A7, $00, $00, $02
                dw      $8000, $8000, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 8
                db      $00, $00, $00, $01, $02
                dw      $7FFF, $7FFF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 9
                db      $00, $A7, $FF, $00, $02
                dw      $012C, $012C, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 10
                db      $00, $A7, $00, $01, $02
                dw      $FF00, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 11
                db      $00, $00, $00, $00, $02
                dw      $01FF, $0000, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 12
                db      $00, $A7, $FF, $01, $02
                dw      $0080, $00C0, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 13
                db      $00, $00, $00, $00, $03
                dw      $0064, $0032, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 14
                db      $00, $A7, $FF, $01, $03
                dw      $0000, $0000, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 15
                db      $00, $A7, $00, $00, $03
                dw      $00FF, $00BF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 16
                db      $00, $00, $00, $01, $03
                dw      $0100, $00BF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 17
                db      $00, $A7, $FF, $00, $03
                dw      $00FF, $00C0, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 18
                db      $00, $A7, $00, $01, $03
                dw      $0100, $00C0, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 19
                db      $00, $00, $00, $00, $03
                dw      $FFFF, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 20
                db      $00, $A7, $FF, $01, $03
                dw      $0064, $FFFF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 21
                db      $00, $A7, $00, $00, $03
                dw      $8000, $8000, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 22
                db      $00, $00, $00, $01, $03
                dw      $7FFF, $7FFF, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 23
                db      $00, $A7, $FF, $00, $03
                dw      $012C, $012C, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 24
                db      $00, $A7, $00, $01, $03
                dw      $FF00, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 25
                db      $00, $00, $00, $00, $03
                dw      $01FF, $0000, $FFFF, $5A5A
                db      $A5
                dw      $2000, $1000   ; 26
                db      $00, $A7, $FF, $01, $03
                dw      $0080, $00C0, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 27
                db      $00, $A7, $00, $00, $00
                dw      $0064, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 28
                db      $00, $A7, $00, $00, $00
                dw      $012C, $012C, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 29
                db      $00, $A7, $00, $00, $01
                dw      $0064, $0032, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 30
                db      $00, $A7, $00, $00, $01
                dw      $012C, $012C, $2468, $5A5A
                db      $A5
                dw      $2000, $1000   ; 31
                db      $FF
