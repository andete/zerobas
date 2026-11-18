; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSET -- docs/bios/SETTXT.md, SETT32.md, SETGRP.md, SETMLT.md round 1 (2026-11-18): the calls that set the VDP up for
; a screen mode from the screen-table cells. Per case (the table `cases` at the end: op, F, interrupts, RG0SAV, RG1SAV,
; table set) the probe first sets, BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := the case's set (`tsets`: 0 the published
;     defaults, 1 moved, 2 moved with junk in the low bits, 3 every cell $FFFF);
;   - RG0SAV / RG1SAV := the case's values, RG2SAV-RG7SAV := $A5; SCRMOD ($FCAF) := $77;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := $5A (a 1 KB block sums to $6800).
; Then BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 (all XOR $FF in odd cases), A $A7, F and interrupts as listed,
; and the call: op 0 SETTXT ($0078), 1 SETT32 ($007B), 2 SETGRP ($007E), 3 SETMLT ($0081).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xset.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 64-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on)
;   +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..29 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +30..61 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after  +62,63 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports, and the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0C80
; @timeout 120
; @vdpsnap E8F0 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $E8F0
STUB    equ     $E8F2
cop     equ     $E910                   ; op, F, ei, RG0SAV, RG1SAV, table set
cF      equ     $E911
cei     equ     $E912
crg0    equ     $E913
crg1    equ     $E914
cts     equ     $E915
mask    equ     $E916
cidx    equ     $E917
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
                ld      bc, $0C7F
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
                ld      bc, 6
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
                ld      a, i
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
                ; VRAM's 16 1-KB sums, read slowly from $0000
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
                xor     a
                call    emit
                call    emit
                ld      hl, cidx
                inc     (hl)
                jp      next

; preset -- the table cells, RG0SAV.., SCRMOD, the VDP registers, VRAM := $5A, the stub
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
                ld      b, 6
p_sav:
                ld      (hl), $A5
                inc     hl
                djnz    p_sav
                ld      a, $77
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
                ld      de, $4000
                ld      a, $5A
f_lp:
                out     ($98), a
                dec     de
                ld      a, d
                or      e
                ld      a, $5A
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
                ret

targets:
                dw      $0078, $007B, $007E, $0081
vpre:
                db      $00, $80, $06, $80, $00, $36, $07, $F4

; the four table sets: TXT NAM COL CGP ATR PAT, T32 ..., GRP ..., MLT ... (20 words each)
tsets:
                dw      $0000, $0000, $0800, $0000, $0000,  $1800, $2000, $0000, $1B00, $3800
                dw      $1800, $2000, $0000, $1B00, $3800,  $0800, $0000, $0000, $1B00, $3800
                dw      $3C00, $0040, $1800, $1F80, $2000,  $0400, $0FC0, $3000, $3F80, $1000
                dw      $3C00, $0000, $2000, $3B80, $1800,  $3800, $1240, $1000, $2F00, $0800
                dw      $3D23, $0071, $1A55, $1FFF, $27FF,  $07FF, $0FFF, $37FF, $3FFF, $17FF
                dw      $3FFF, $3FFF, $3FFF, $3FFF, $3FFF,  $3BFF, $13FF, $17FF, $2F7F, $0FFF
                dw      $FFFF, $FFFF, $FFFF, $FFFF, $FFFF,  $FFFF, $FFFF, $FFFF, $FFFF, $FFFF
                dw      $FFFF, $FFFF, $FFFF, $FFFF, $FFFF,  $FFFF, $FFFF, $FFFF, $FFFF, $FFFF

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

; ---- cases: op, F, interrupts, RG0SAV, RG1SAV, table set; $FF ends ----
cases:
                db      $00, $00, $00, $00, $00, $00   ; 0
                db      $00, $FF, $00, $FF, $FF, $00   ; 1
                db      $00, $00, $01, $5A, $A5, $00   ; 2
                db      $00, $FF, $01, $00, $00, $01   ; 3
                db      $00, $00, $00, $FF, $FF, $01   ; 4
                db      $00, $FF, $00, $5A, $A5, $01   ; 5
                db      $00, $00, $01, $00, $00, $02   ; 6
                db      $00, $FF, $01, $FF, $FF, $02   ; 7
                db      $00, $00, $00, $5A, $A5, $02   ; 8
                db      $00, $FF, $00, $00, $00, $03   ; 9
                db      $00, $00, $01, $FF, $FF, $03   ; 10
                db      $00, $FF, $01, $5A, $A5, $03   ; 11
                db      $01, $00, $00, $00, $00, $00   ; 12
                db      $01, $FF, $00, $FF, $FF, $00   ; 13
                db      $01, $00, $01, $5A, $A5, $00   ; 14
                db      $01, $FF, $01, $00, $00, $01   ; 15
                db      $01, $00, $00, $FF, $FF, $01   ; 16
                db      $01, $FF, $00, $5A, $A5, $01   ; 17
                db      $01, $00, $01, $00, $00, $02   ; 18
                db      $01, $FF, $01, $FF, $FF, $02   ; 19
                db      $01, $00, $00, $5A, $A5, $02   ; 20
                db      $01, $FF, $00, $00, $00, $03   ; 21
                db      $01, $00, $01, $FF, $FF, $03   ; 22
                db      $01, $FF, $01, $5A, $A5, $03   ; 23
                db      $02, $00, $00, $00, $00, $00   ; 24
                db      $02, $FF, $00, $FF, $FF, $00   ; 25
                db      $02, $00, $01, $5A, $A5, $00   ; 26
                db      $02, $FF, $01, $00, $00, $01   ; 27
                db      $02, $00, $00, $FF, $FF, $01   ; 28
                db      $02, $FF, $00, $5A, $A5, $01   ; 29
                db      $02, $00, $01, $00, $00, $02   ; 30
                db      $02, $FF, $01, $FF, $FF, $02   ; 31
                db      $02, $00, $00, $5A, $A5, $02   ; 32
                db      $02, $FF, $00, $00, $00, $03   ; 33
                db      $02, $00, $01, $FF, $FF, $03   ; 34
                db      $02, $FF, $01, $5A, $A5, $03   ; 35
                db      $03, $00, $00, $00, $00, $00   ; 36
                db      $03, $FF, $00, $FF, $FF, $00   ; 37
                db      $03, $00, $01, $5A, $A5, $00   ; 38
                db      $03, $FF, $01, $00, $00, $01   ; 39
                db      $03, $00, $00, $FF, $FF, $01   ; 40
                db      $03, $FF, $00, $5A, $A5, $01   ; 41
                db      $03, $00, $01, $00, $00, $02   ; 42
                db      $03, $FF, $01, $FF, $FF, $02   ; 43
                db      $03, $00, $00, $5A, $A5, $02   ; 44
                db      $03, $FF, $00, $00, $00, $03   ; 45
                db      $03, $00, $01, $FF, $FF, $03   ; 46
                db      $03, $FF, $01, $5A, $A5, $03   ; 47
                db      $FF
