; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSPR -- docs/bios/CALPAT.md, CALATR.md, GSPSIZ.md round 3 (2026-11-18; round 1 was cases 0-33, round 2 34-49): the sprite table calls. Per case (the table
; `cases` at the end: op, A, F, interrupts, RG1SAV, PATBAS, ATRBAS) the probe sets RG1SAV ($F3E0), PATBAS ($F926) and
; ATRBAS ($F928) by hand, then BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 (all XOR $FF in odd cases), the
; case's A, F and interrupt state, and calls (cases 34-49 pair entry F with the other register set, and take
; single-bit and mixed F values; cases 50-59 give CALPAT sums with bit 15 set, an overflow and a 16 x 16 wrap to
; zero, and RG1SAV with bits 2-4 or bits 5-7 apart): op 0 CALPAT ($0084), 1 CALATR ($0087), 2 GSPSIZ ($008A).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xspr.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 20-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on)
;   +13 RG1SAV after  +14,15 PATBAS after  +16,17 ATRBAS after (low, high)  +18,19 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area RAM.
;
; @cap C000
; @caplen 0600
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
STUB    equ     $E8F2
cop     equ     $E910                   ; op, A, F, ei, RG1SAV, PATBAS (2), ATRBAS (2)
cA      equ     $E911
cF      equ     $E912
cei     equ     $E913
crg1    equ     $E914
cpat    equ     $E915
catr    equ     $E917
mask    equ     $E919
cidx    equ     $E91A
raf     equ     $E920
rbc     equ     $E922
rde     equ     $E924
rhl     equ     $E926
rix     equ     $E928
riy     equ     $E92A
riff    equ     $E92C
RG1SAV  equ     $F3E0
PATBAS  equ     $F926
ATRBAS  equ     $F928

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
                ld      bc, 9
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca
                sbc     a, a
                ld      (mask), a
                ld      a, (crg1)
                ld      (RG1SAV), a
                ld      hl, (cpat)
                ld      (PATBAS), hl
                ld      hl, (catr)
                ld      (ATRBAS), hl
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
                ld      a, e
                xor     $13
                ld      b, a
                ld      a, e
                xor     $57
                ld      c, a
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
                ld      a, i
                jp      pe, $+5                 ; off? read again: an interrupt accepted DURING `ld a,i` reads
                ld      a, i                    ; P/V 0 (the NMOS erratum, D-IFFREAD1)
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
                ld      hl, RG1SAV
                call    emitm
                ld      hl, PATBAS
                call    emitm
                inc     hl
                call    emitm
                inc     hl
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
                dw      $0084, $0087, $008A

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

; ---- cases: op, A, F, interrupts, RG1SAV; PATBAS, ATRBAS; $FF ends ----
cases:
                db      $00, $00, $00, $00, $E0
                dw      $3800, $1B00   ; 0
                db      $00, $01, $FF, $00, $E0
                dw      $3800, $1B00   ; 1
                db      $00, $07, $00, $01, $E0
                dw      $3800, $1B00   ; 2
                db      $00, $1F, $FF, $01, $E0
                dw      $3800, $1B00   ; 3
                db      $00, $20, $00, $00, $E0
                dw      $3800, $1B00   ; 4
                db      $00, $7F, $FF, $00, $E0
                dw      $3800, $1B00   ; 5
                db      $00, $FF, $00, $01, $E0
                dw      $3800, $1B00   ; 6
                db      $00, $00, $FF, $01, $E2
                dw      $3800, $1B00   ; 7
                db      $00, $01, $00, $00, $E2
                dw      $3800, $1B00   ; 8
                db      $00, $07, $FF, $00, $E2
                dw      $3800, $1B00   ; 9
                db      $00, $1F, $00, $01, $E2
                dw      $3800, $1B00   ; 10
                db      $00, $20, $FF, $01, $E2
                dw      $3800, $1B00   ; 11
                db      $00, $7F, $00, $00, $E2
                dw      $3800, $1B00   ; 12
                db      $00, $FF, $FF, $00, $E2
                dw      $3800, $1B00   ; 13
                db      $00, $01, $00, $01, $E0
                dw      $FFF8, $1B00   ; 14
                db      $00, $03, $FF, $01, $E3
                dw      $1234, $1B00   ; 15
                db      $00, $05, $00, $00, $E1
                dw      $1234, $1B00   ; 16
                db      $00, $02, $FF, $00, $E2
                dw      $FFF0, $1B00   ; 17
                db      $01, $00, $00, $01, $E0
                dw      $3800, $1B00   ; 18
                db      $01, $01, $FF, $01, $E0
                dw      $3800, $1B00   ; 19
                db      $01, $1F, $00, $00, $E0
                dw      $3800, $1B00   ; 20
                db      $01, $20, $FF, $00, $E0
                dw      $3800, $1B00   ; 21
                db      $01, $FF, $00, $01, $E0
                dw      $3800, $1B00   ; 22
                db      $01, $01, $FF, $01, $E0
                dw      $3800, $FFFE   ; 23
                db      $01, $05, $00, $00, $E2
                dw      $3800, $ABCD   ; 24
                db      $01, $40, $FF, $00, $E3
                dw      $3800, $1234   ; 25
                db      $02, $A7, $00, $01, $E0
                dw      $3800, $1B00   ; 26
                db      $02, $A7, $FF, $01, $E1
                dw      $3800, $1B00   ; 27
                db      $02, $A7, $00, $00, $E2
                dw      $3800, $1B00   ; 28
                db      $02, $A7, $FF, $00, $E3
                dw      $3800, $1B00   ; 29
                db      $02, $A7, $00, $01, $00
                dw      $3800, $1B00   ; 30
                db      $02, $A7, $FF, $01, $FF
                dw      $3800, $1B00   ; 31
                db      $02, $A7, $00, $00, $FD
                dw      $3800, $1B00   ; 32
                db      $02, $A7, $FF, $00, $02
                dw      $3800, $1B00   ; 33
                db      $00, $03, $FF, $00, $00
                dw      $3800, $1B00   ; 34
                db      $00, $03, $00, $01, $02
                dw      $3800, $1B00   ; 35
                db      $00, $09, $80, $00, $FD
                dw      $3800, $1B00   ; 36
                db      $00, $09, $40, $01, $FF
                dw      $3800, $1B00   ; 37
                db      $00, $05, $FF, $01, $E1
                dw      $1234, $1B00   ; 38
                db      $00, $05, $00, $00, $E3
                dw      $1234, $1B00   ; 39
                db      $01, $40, $04, $00, $00
                dw      $3800, $0F00   ; 40
                db      $01, $03, $00, $01, $FF
                dw      $3800, $1B00   ; 41
                db      $01, $07, $A5, $00, $02
                dw      $3800, $3F00   ; 42
                db      $01, $80, $5A, $01, $FD
                dw      $3800, $1B00   ; 43
                db      $02, $00, $FF, $00, $E0
                dw      $3800, $1B00   ; 44
                db      $02, $FF, $00, $01, $E2
                dw      $3800, $1B00   ; 45
                db      $02, $00, $80, $00, $80
                dw      $3800, $1B00   ; 46
                db      $02, $FF, $04, $01, $20
                dw      $3800, $1B00   ; 47
                db      $02, $5A, $40, $00, $40
                dw      $3800, $1B00   ; 48
                db      $02, $A5, $A5, $01, $A2
                dw      $3800, $1B00   ; 49
                db      $00, $01, $00, $00, $E0
                dw      $8000, $1B00   ; 50
                db      $00, $01, $FF, $01, $E0
                dw      $7FF8, $1B00   ; 51
                db      $00, $80, $00, $00, $E2
                dw      $F000, $1B00   ; 52
                db      $00, $80, $FF, $01, $E2
                dw      $F000, $1B00   ; 53
                db      $00, $03, $00, $00, $1E
                dw      $3800, $1B00   ; 54
                db      $00, $03, $FF, $01, $82
                dw      $3800, $1B00   ; 55
                db      $00, $03, $00, $00, $22
                dw      $3800, $1B00   ; 56
                db      $02, $A7, $00, $01, $04
                dw      $3800, $1B00   ; 57
                db      $02, $A7, $FF, $00, $08
                dw      $3800, $1B00   ; 58
                db      $02, $A7, $00, $01, $10
                dw      $3800, $1B00   ; 59
                db      $FF
