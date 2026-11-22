; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSET -- docs/bios/SETTXT.md, SETT32.md, SETGRP.md, SETMLT.md round 4 (2026-11-18; round 1 had cases 0-47, a $5A fill and no read-back of the
; cells; round 2 a fill whose blocks all summed alike, and no cell set 4; round 3 no status read before the call,
; no set 5 and one RG2SAV-RG6SAV preset, and its interrupt read-out once, not twice): the calls that set the VDP up for a screen mode from the screen-table cells. Per case (the table `cases` at the end: op, F, interrupts, RG0SAV, RG1SAV,
; table set, SCRMOD, RG7SAV, RG2SAV-RG6SAV preset) the probe first sets, BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := the case's set (`tsets`: 0 the published
;     defaults, 1 moved, 2 others with low bits set, 3 every cell $FFFF, 4 $4000 / $8000 / $C000, 5 set 4 with
;     $4000 and $8000 swapped);
;   - the VDP status read last (no VDP interrupt pending at the call);
;   - RG0SAV / RG1SAV := the case's values, RG2SAV-RG6SAV := the case's preset, RG7SAV and SCRMOD ($FCAF) := the
;     case's;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := ((address low) XOR (address high) XOR $5A) OR address / $400 (each 1 KB block sums apart) (display off, so it may be written fast).
; Then BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 (all XOR $FF in odd cases), A $A7, F and interrupts as listed,
; and the call: op 0 SETTXT ($0078), 1 SETT32 ($007B), 2 SETGRP ($007E), 3 SETMLT ($0081).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xset.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 112-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on)
;   +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..29 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +30..61 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after, read with R#1 := $80 first (16 KB
;   addressing, display off)  +62..101 the 20 screen-table cells after  +102..111 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports, and the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 2400
; @timeout 120
; @vdpsnap E8F0 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $E8F0
STUB    equ     $E8F2
cop     equ     $E910                   ; op, F, ei, RG0SAV, RG1SAV, table set, SCRMOD, RG7SAV, RG2-6 preset
cF      equ     $E911
cei     equ     $E912
crg0    equ     $E913
crg1    equ     $E914
cts     equ     $E915
cscr    equ     $E916
crg7    equ     $E917
crgp    equ     $E918
mask    equ     $E919
cidx    equ     $E91A
raf     equ     $E920
rbc     equ     $E922
rde     equ     $E924
rhl     equ     $E926
rix     equ     $E928
riy     equ     $E92A
riff    equ     $E92C
TXTNAM  equ     $F3B3
RG0SAV  equ     $F3DF
SCRMOD  equ     $FCAF

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $23FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAP), a
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
                call    preset
                ld      a, (cF)
                ld      c, a
                ld      b, $A7
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
                ld      a, i                    ; P/V := IFF2 -- read twice: an interrupt accepted during
                jp      pe, i_on                ; LD A,I makes that read show 0 (a Z80 quirk)
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
                ld      hl, RG0SAV
                ld      b, 8
r_lp:
                call    emitm
                inc     hl
                djnz    r_lp
                ld      hl, SCRMOD
                call    emitm
                call    SNAP                    ; the debugger appends R#0-R#7
                ld      a, $80                  ; R#1 := $80: 16 KB addressing for the read-back
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; VRAM's 16 1-KB sums, from $0000
                xor     a
                out     ($99), a
                out     ($99), a
                ld      c, 16
k_lp:
                ld      hl, 0
                ld      de, 1024
s_lp:
                in      a, ($98)
                add     a, l
                ld      l, a
                jr      nc, s_nc
                inc     h
s_nc:
                dec     de
                ld      a, d
                or      e
                jr      nz, s_lp
                ld      a, l
                call    emit
                ld      a, h
                call    emit
                dec     c
                jr      nz, k_lp
                ld      hl, TXTNAM
                ld      b, 40
c_lp:
                call    emitm
                inc     hl
                djnz    c_lp
                ld      b, 10
z_lp:
                xor     a
                call    emit
                djnz    z_lp
                ld      hl, cidx
                inc     (hl)
                jp      next

; preset -- the table cells, RG0SAV.., SCRMOD, the VDP registers, VRAM (the fill), the stub
preset:
                ld      a, (cts)
                ld      l, a
                ld      h, 0
                add     hl, hl                  ; x 40
                add     hl, hl
                add     hl, hl
                ld      d, h
                ld      e, l
                add     hl, hl
                add     hl, hl
                add     hl, de
                ld      de, tsets
                add     hl, de
                ld      de, TXTNAM
                ld      bc, 40
                ldir
                ld      hl, RG0SAV
                ld      a, (crg0)
                ld      (hl), a
                inc     hl
                ld      a, (crg1)
                ld      (hl), a
                inc     hl
                ld      b, 5
                ld      a, (crgp)
p_sav:
                ld      (hl), a
                inc     hl
                djnz    p_sav
                ld      a, (crg7)
                ld      (hl), a
                ld      a, (cscr)
                ld      (SCRMOD), a
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
                xor     a
                out     ($99), a
                ld      a, $40
                out     ($99), a
                ld      de, 0
f_lp:
                ld      a, d                    ; OR the block number (address / $400), so every block sums apart
                rrca
                rrca
                and     $0F
                ld      c, a
                ld      a, d
                xor     e
                xor     $5A
                or      c
                out     ($98), a
                inc     de
                ld      a, d
                cp      $40
                jr      nz, f_lp
                ld      a, (cei)
                or      a
                ld      a, $00
                jr      z, p3
                ld      a, $FB
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
                in      a, ($99)                ; the VDP status read: no VDP interrupt pending at the call
                ret

targets:
                dw      $0078, $007B, $007E, $0081
vpre:
                db      $00, $80, $06, $80, $00, $36, $07, $F4

; the six table sets (sets 4 / 5: bits 14 / 15 apart): TXT NAM COL CGP ATR PAT, T32 ..., GRP ..., MLT ... (20 words each)
tsets:
                dw      $0000, $0000, $0800, $0000, $0000,  $1800, $2000, $0000, $1B00, $3800
                dw      $1800, $2000, $0000, $1B00, $3800,  $0800, $0000, $0000, $1B00, $3800
                dw      $3C00, $0040, $1800, $1F80, $2000,  $0400, $0FC0, $3000, $3F80, $1000
                dw      $3C00, $0000, $2000, $3B80, $1800,  $3800, $1240, $1000, $2F00, $0800
                dw      $3D23, $0071, $1A55, $1FFF, $27FF,  $07FF, $0FFF, $37FF, $3FFF, $17FF
                dw      $3FFF, $3FFF, $3FFF, $3FFF, $3FFF,  $3BFF, $13FF, $17FF, $2F7F, $0FFF
                dw      $FFFF, $FFFF, $FFFF, $FFFF, $FFFF,  $FFFF, $FFFF, $FFFF, $FFFF, $FFFF
                dw      $FFFF, $FFFF, $FFFF, $FFFF, $FFFF,  $FFFF, $FFFF, $FFFF, $FFFF, $FFFF
                dw      $4000, $4000, $8000, $8000, $C000,  $8000, $4000, $4000, $C000, $8000
                dw      $4000, $4000, $8000, $8000, $C000,  $8000, $4000, $4000, $C000, $8000
                dw      $8000, $8000, $4000, $4000, $C000,  $4000, $8000, $8000, $C000, $4000
                dw      $8000, $8000, $4000, $4000, $C000,  $4000, $8000, $8000, $C000, $4000

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

; ---- cases: op, F, interrupts, RG0SAV, RG1SAV, table set, SCRMOD, RG7SAV, RG2SAV-RG6SAV preset; $FF ends ----
cases:
                db      $00, $00, $00, $00, $00, $00, $77, $A5, $A5   ; 0
                db      $00, $FF, $00, $FF, $FF, $00, $77, $A5, $A5   ; 1
                db      $00, $00, $01, $5A, $A5, $00, $77, $A5, $A5   ; 2
                db      $00, $FF, $01, $00, $00, $01, $77, $A5, $A5   ; 3
                db      $00, $00, $00, $FF, $FF, $01, $77, $A5, $A5   ; 4
                db      $00, $FF, $00, $5A, $A5, $01, $77, $A5, $A5   ; 5
                db      $00, $00, $01, $00, $00, $02, $77, $A5, $A5   ; 6
                db      $00, $FF, $01, $FF, $FF, $02, $77, $A5, $A5   ; 7
                db      $00, $00, $00, $5A, $A5, $02, $77, $A5, $A5   ; 8
                db      $00, $FF, $00, $00, $00, $03, $77, $A5, $A5   ; 9
                db      $00, $00, $01, $FF, $FF, $03, $77, $A5, $A5   ; 10
                db      $00, $FF, $01, $5A, $A5, $03, $77, $A5, $A5   ; 11
                db      $01, $00, $00, $00, $00, $00, $77, $A5, $A5   ; 12
                db      $01, $FF, $00, $FF, $FF, $00, $77, $A5, $A5   ; 13
                db      $01, $00, $01, $5A, $A5, $00, $77, $A5, $A5   ; 14
                db      $01, $FF, $01, $00, $00, $01, $77, $A5, $A5   ; 15
                db      $01, $00, $00, $FF, $FF, $01, $77, $A5, $A5   ; 16
                db      $01, $FF, $00, $5A, $A5, $01, $77, $A5, $A5   ; 17
                db      $01, $00, $01, $00, $00, $02, $77, $A5, $A5   ; 18
                db      $01, $FF, $01, $FF, $FF, $02, $77, $A5, $A5   ; 19
                db      $01, $00, $00, $5A, $A5, $02, $77, $A5, $A5   ; 20
                db      $01, $FF, $00, $00, $00, $03, $77, $A5, $A5   ; 21
                db      $01, $00, $01, $FF, $FF, $03, $77, $A5, $A5   ; 22
                db      $01, $FF, $01, $5A, $A5, $03, $77, $A5, $A5   ; 23
                db      $02, $00, $00, $00, $00, $00, $77, $A5, $A5   ; 24
                db      $02, $FF, $00, $FF, $FF, $00, $77, $A5, $A5   ; 25
                db      $02, $00, $01, $5A, $A5, $00, $77, $A5, $A5   ; 26
                db      $02, $FF, $01, $00, $00, $01, $77, $A5, $A5   ; 27
                db      $02, $00, $00, $FF, $FF, $01, $77, $A5, $A5   ; 28
                db      $02, $FF, $00, $5A, $A5, $01, $77, $A5, $A5   ; 29
                db      $02, $00, $01, $00, $00, $02, $77, $A5, $A5   ; 30
                db      $02, $FF, $01, $FF, $FF, $02, $77, $A5, $A5   ; 31
                db      $02, $00, $00, $5A, $A5, $02, $77, $A5, $A5   ; 32
                db      $02, $FF, $00, $00, $00, $03, $77, $A5, $A5   ; 33
                db      $02, $00, $01, $FF, $FF, $03, $77, $A5, $A5   ; 34
                db      $02, $FF, $01, $5A, $A5, $03, $77, $A5, $A5   ; 35
                db      $03, $00, $00, $00, $00, $00, $77, $A5, $A5   ; 36
                db      $03, $FF, $00, $FF, $FF, $00, $77, $A5, $A5   ; 37
                db      $03, $00, $01, $5A, $A5, $00, $77, $A5, $A5   ; 38
                db      $03, $FF, $01, $00, $00, $01, $77, $A5, $A5   ; 39
                db      $03, $00, $00, $FF, $FF, $01, $77, $A5, $A5   ; 40
                db      $03, $FF, $00, $5A, $A5, $01, $77, $A5, $A5   ; 41
                db      $03, $00, $01, $00, $00, $02, $77, $A5, $A5   ; 42
                db      $03, $FF, $01, $FF, $FF, $02, $77, $A5, $A5   ; 43
                db      $03, $00, $00, $5A, $A5, $02, $77, $A5, $A5   ; 44
                db      $03, $FF, $00, $00, $00, $03, $77, $A5, $A5   ; 45
                db      $03, $00, $01, $FF, $FF, $03, $77, $A5, $A5   ; 46
                db      $03, $FF, $01, $5A, $A5, $03, $77, $A5, $A5   ; 47
                db      $00, $FF, $00, $01, $00, $01, $00, $00, $A5   ; 48
                db      $00, $00, $01, $FE, $FF, $01, $01, $FF, $A5   ; 49
                db      $00, $00, $01, $01, $00, $01, $02, $5A, $A5   ; 50
                db      $00, $FF, $00, $FE, $FF, $01, $03, $00, $A5   ; 51
                db      $01, $FF, $00, $01, $00, $01, $00, $00, $A5   ; 52
                db      $01, $00, $01, $FE, $FF, $01, $01, $FF, $A5   ; 53
                db      $01, $00, $01, $01, $00, $01, $02, $5A, $A5   ; 54
                db      $01, $FF, $00, $FE, $FF, $01, $03, $00, $A5   ; 55
                db      $02, $FF, $00, $01, $00, $01, $00, $00, $A5   ; 56
                db      $02, $00, $01, $FE, $FF, $01, $01, $FF, $A5   ; 57
                db      $02, $00, $01, $01, $00, $01, $02, $5A, $A5   ; 58
                db      $02, $FF, $00, $FE, $FF, $01, $03, $00, $A5   ; 59
                db      $03, $FF, $00, $01, $00, $01, $00, $00, $A5   ; 60
                db      $03, $00, $01, $FE, $FF, $01, $01, $FF, $A5   ; 61
                db      $03, $00, $01, $01, $00, $01, $02, $5A, $A5   ; 62
                db      $03, $FF, $00, $FE, $FF, $01, $03, $00, $A5   ; 63
                db      $00, $00, $00, $00, $00, $04, $77, $A5, $A5   ; 64
                db      $01, $FF, $00, $00, $00, $04, $77, $A5, $A5   ; 65
                db      $02, $00, $01, $00, $00, $04, $77, $A5, $A5   ; 66
                db      $03, $FF, $01, $00, $00, $04, $77, $A5, $A5   ; 67
                db      $00, $00, $00, $00, $00, $05, $77, $A5, $A5   ; 68
                db      $01, $FF, $00, $00, $00, $05, $77, $A5, $A5   ; 69
                db      $02, $00, $01, $00, $00, $05, $77, $A5, $A5   ; 70
                db      $03, $FF, $01, $00, $00, $05, $77, $A5, $A5   ; 71
                db      $00, $FF, $00, $5A, $A5, $01, $77, $A5, $5A   ; 72
                db      $01, $00, $01, $5A, $A5, $01, $77, $A5, $5A   ; 73
                db      $02, $FF, $00, $5A, $A5, $01, $77, $A5, $5A   ; 74
                db      $03, $00, $01, $5A, $A5, $01, $77, $A5, $5A   ; 75
                db      $FF
