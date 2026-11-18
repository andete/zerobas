; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XGFX3 -- docs/bios/READC.md, SETC.md, NSETCX.md round 6 (2026-11-19; round 1 had cases 0-28 and cell sets 0 / 1 only, round 2 cases 29-46, round 3 47-59, round 4 60-68, round 5 69-77): the calls that read or set pixels at the current
; graphics position. Per case (the table `cases` at the end, xinig.asm's layout with its fields read anew: op, F,
; interrupts, SCRMOD, CMASK, ATRBYT, BAKCLR, BDRCLR, CLOC, HL, cell set, three window addresses, A) the probe first sets,
; BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := one of `tsets` (0 the published defaults: GRPCGP
;     $0000, GRPCOL $2000, MLTCGP $0000; 1 moved: GRPCGP $2000, GRPCOL $0000, MLTCGP $1000; 5 GRPCGP = GRPCOL
;     = $2000, MLTCGP $1000; 6 GRPCGP $0800, GRPCOL $2000);
;   - SCRMOD ($FCAF), CLOC ($F92A), CMASK ($F92C), ATRBYT ($F3F2) := the case's; RG0SAV-RG7SAV := $A5;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := ((address low) XOR (address high) XOR $5A) OR (address high AND $3C);
;   - the VDP status read last.
; Then BC $1357, DE $9BDF, IX $4321, IY $8765 (all XOR $FF when bit 2 of the case number is set), HL, A, F and the
; interrupts as listed, and the call: op 0 READC ($011D), 1 SETC ($0120), 2 NSETCX ($0123).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx3.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 128-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..24 FORCLR / BAKCLR / BDRCLR after
;   +25..32 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +33..64 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after, read with R#1 := $80 first
;   +65..80, +81..96, +97..112 the 16 VRAM bytes from W1, W2, W3 after
;   +113,114 CLOC  +115 CMASK  +116 ATRBYT  after  +117..127 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports, and the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 2E00
; @timeout 180
; @vdpsnap EE00 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $EE00
STUB    equ     $EE02
cop     equ     $EE10                   ; op, F, ei, SCRMOD, RG1SAV, FOR, BAK, BDR, ATRBAS, PATBAS, set, W1, W2, W3, A
cF      equ     $EE11
cei     equ     $EE12
cscr    equ     $EE13
crg1    equ     $EE14
cfor    equ     $EE15
catr    equ     $EE18
cpat    equ     $EE1A
cts     equ     $EE1C
cW1     equ     $EE1D
cW2     equ     $EE1F
cW3     equ     $EE21
cA      equ     $EE23
mask    equ     $EE26
cidx    equ     $EE27
raf     equ     $EE30
rbc     equ     $EE32
rde     equ     $EE34
rhl     equ     $EE36
rix     equ     $EE38
riy     equ     $EE3A
riff    equ     $EE3C
TXTNAM  equ     $F3B3
RG0SAV  equ     $F3DF
FORCLR  equ     $F3E9
PATBAS  equ     $F926
ATRBAS  equ     $F928
SCRMOD  equ     $FCAF

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $2DFF
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
                ld      bc, 20
                ldir
                ld      (tptr), hl
                ld      a, (cidx)
                rrca                            ; the marker set from bit 2 of the case number: apart from
                rrca                            ; entry F (bit 0) and the interrupt state (bit 1)
                rrca
                sbc     a, a
                ld      (mask), a
                call    preset
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
                xor     $9B
                ld      d, a
                ld      a, e
                xor     $DF
                ld      e, a
                ld      hl, (cpat)
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
                jp      pe, i_on                ; LD A,I makes that read show 0
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
                ld      hl, FORCLR
                call    emitm
                inc     hl
                call    emitm
                inc     hl
                call    emitm
                call    SNAP                    ; the debugger appends R#0-R#7
                ld      a, $80                  ; R#1 := $80: 16 KB addressing, display off, for the read-back
                out     ($99), a
                ld      a, $81
                out     ($99), a
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
                ld      hl, (cW1)
                call    window
                ld      hl, (cW2)
                call    window
                ld      hl, (cW3)
                call    window
                ld      hl, $F92A               ; CLOC, CMASK
                call    emitm
                inc     hl
                call    emitm
                inc     hl
                call    emitm
                ld      hl, $F3F2               ; ATRBYT
                call    emitm
                ld      b, 11
z_lp:
                xor     a
                call    emit
                djnz    z_lp
                ld      hl, cidx
                inc     (hl)
                jp      next

; window -- 16 VRAM bytes from HL
window:
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ld      b, 16
wv:
                in      a, ($98)
                call    emit
                djnz    wv
                ret

; preset -- the table cells, the work-area cells, the VDP registers, VRAM, the stub
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
                ld      a, $A5
                ld      hl, RG0SAV
                ld      b, 8
p_sav:
                ld      (hl), a
                inc     hl
                djnz    p_sav
                ld      a, (crg1)
                ld      ($F92C), a              ; CMASK
                ld      a, (cscr)
                ld      (SCRMOD), a
                ld      a, (cfor)
                ld      ($F3F2), a              ; ATRBYT
                ld      hl, (catr)
                ld      ($F92A), hl             ; CLOC
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
                ld      a, d                    ; OR (address / $400) x 4: every block sums apart, none to 0
                and     $3C
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
                dw      $011D, $0120, $0123
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
                dw      $0000, $0000, $0800, $0000, $0000,  $1800, $2000, $0000, $1B00, $3800
                dw      $2000, $2000, $0000, $1B00, $3800,  $3FFF, $3FFF, $3FFF, $3FFF, $3FFF
                dw      $0000, $0000, $0800, $0000, $0000,  $1800, $2000, $0000, $1B00, $3800
                dw      $1800, $2000, $2000, $1B00, $3800,  $0800, $0000, $1000, $1B00, $3800
                dw      $0000, $0000, $0800, $0000, $0000,  $1800, $2000, $0000, $1B00, $3800
                dw      $1800, $2000, $0800, $1B00, $3800,  $0800, $0000, $0000, $1B00, $3800

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

; ---- cases: op, F, interrupts, SCRMOD, CMASK, ATRBYT, BAKCLR, BDRCLR; CLOC, HL; set; W1, W2, W3; A; $FF ends ----
cases:
                db      $00, $00, $00, $02, $08, $05, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 0
                db      $00, $FF, $00, $02, $04, $05, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 1
                db      $00, $00, $01, $02, $80, $05, $04, $07
                dw      $0000, $2468
                db      $00
                dw      $0000, $2000, $0010
                db      $A7   ; 2
                db      $00, $FF, $01, $02, $01, $05, $04, $07
                dw      $0000, $2468
                db      $00
                dw      $0000, $2000, $0010
                db      $A7   ; 3
                db      $00, $00, $00, $02, $01, $05, $04, $07
                dw      $17FF, $2468
                db      $00
                dw      $17F0, $37F0, $1800
                db      $A7   ; 4
                db      $00, $FF, $00, $02, $80, $05, $04, $07
                dw      $0141, $2468
                db      $00
                dw      $0140, $2140, $0150
                db      $A7   ; 5
                db      $01, $00, $01, $02, $08, $05, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 6
                db      $01, $FF, $01, $02, $04, $0F, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 7
                db      $01, $00, $00, $02, $80, $00, $04, $07
                dw      $0000, $2468
                db      $00
                dw      $0000, $2000, $0010
                db      $A7   ; 8
                db      $01, $FF, $00, $02, $01, $1A, $04, $07
                dw      $17FF, $2468
                db      $00
                dw      $17F0, $37F0, $1800
                db      $A7   ; 9
                db      $02, $00, $01, $02, $08, $09, $04, $07
                dw      $0662, $0001
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 10
                db      $02, $FF, $01, $02, $08, $09, $04, $07
                dw      $0662, $0005
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 11
                db      $02, $00, $00, $02, $80, $09, $04, $07
                dw      $0662, $0008
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 12
                db      $02, $FF, $00, $02, $08, $09, $04, $07
                dw      $0662, $0014
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 13
                db      $02, $00, $01, $02, $20, $09, $04, $07
                dw      $01FA, $000C
                db      $00
                dw      $01F0, $21F0, $0200
                db      $A7   ; 14
                db      $02, $FF, $01, $02, $08, $09, $04, $07
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 15
                db      $00, $00, $00, $02, $08, $0C, $04, $07
                dw      $2662, $2468
                db      $01
                dw      $2660, $0660, $2670
                db      $A7   ; 16
                db      $01, $FF, $00, $02, $08, $0C, $04, $07
                dw      $2662, $2468
                db      $01
                dw      $2660, $0660, $2670
                db      $A7   ; 17
                db      $02, $00, $01, $02, $08, $0C, $04, $07
                dw      $2662, $000A
                db      $01
                dw      $2660, $0660, $2670
                db      $A7   ; 18
                db      $00, $FF, $01, $03, $0F, $05, $04, $07
                dw      $0164, $2468
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 19
                db      $00, $00, $00, $03, $F0, $05, $04, $07
                dw      $016C, $2468
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 20
                db      $00, $FF, $00, $03, $F0, $05, $04, $07
                dw      $0000, $2468
                db      $00
                dw      $0000, $0010, $0010
                db      $A7   ; 21
                db      $00, $00, $01, $03, $0F, $05, $04, $07
                dw      $05FF, $2468
                db      $00
                dw      $05F0, $0600, $0600
                db      $A7   ; 22
                db      $01, $FF, $01, $03, $0F, $05, $04, $07
                dw      $0164, $2468
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 23
                db      $01, $00, $00, $03, $F0, $0F, $04, $07
                dw      $016C, $2468
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 24
                db      $01, $FF, $00, $03, $F0, $1A, $04, $07
                dw      $0000, $2468
                db      $00
                dw      $0000, $0010, $0010
                db      $A7   ; 25
                db      $02, $00, $01, $03, $0F, $09, $04, $07
                dw      $0164, $0001
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 26
                db      $02, $FF, $01, $03, $0F, $09, $04, $07
                dw      $0164, $0006
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 27
                db      $02, $00, $00, $03, $F0, $09, $04, $07
                dw      $0164, $0009
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 28
                db      $00, $00, $00, $02, $08, $05, $04, $07
                dw      $2642, $2468
                db      $01
                dw      $2640, $0640, $2650
                db      $A7   ; 29
                db      $01, $FF, $00, $02, $01, $0C, $04, $07
                dw      $2662, $2468
                db      $01
                dw      $2660, $0660, $2670
                db      $A7   ; 30
                db      $01, $00, $00, $02, $04, $0B, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $00   ; 31
                db      $02, $00, $01, $02, $08, $1A, $04, $07
                dw      $0662, $0014
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 32
                db      $01, $FF, $00, $03, $0F, $1A, $04, $07
                dw      $0164, $2468
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 33
                db      $00, $00, $00, $02, $80, $05, $04, $07
                dw      $000A, $2468
                db      $00
                dw      $0000, $2000, $0010
                db      $A7   ; 34
                db      $01, $00, $01, $02, $08, $05, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $00   ; 35
                db      $02, $00, $00, $03, $F0, $09, $04, $07
                dw      $01FC, $0003
                db      $00
                dw      $01F0, $0200, $0200
                db      $A7   ; 36
                db      $02, $00, $00, $02, $01, $09, $04, $07
                dw      $17FF, $0002
                db      $00
                dw      $17F0, $37F0, $0000
                db      $A7   ; 37
                db      $02, $00, $00, $03, $0F, $09, $04, $07
                dw      $0164, $0000
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 38
                db      $02, $00, $00, $02, $04, $09, $04, $07
                dw      $00A0, $0003
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 39
                db      $00, $FF, $00, $02, $08, $05, $04, $07
                dw      $2662, $2468
                db      $05
                dw      $2660, $0660, $0000
                db      $A7   ; 40
                db      $01, $00, $00, $02, $01, $0C, $04, $07
                dw      $2662, $2468
                db      $05
                dw      $2660, $0660, $0000
                db      $A7   ; 41
                db      $00, $00, $00, $02, $08, $05, $04, $07
                dw      $0E62, $2468
                db      $06
                dw      $0E60, $2660, $2E60
                db      $A7   ; 42
                db      $01, $FF, $00, $02, $01, $0C, $04, $07
                dw      $0E62, $2468
                db      $06
                dw      $0E60, $2660, $2E60
                db      $A7   ; 43
                db      $00, $00, $00, $03, $0F, $09, $04, $07
                dw      $1164, $0004
                db      $01
                dw      $1160, $1170, $0160
                db      $A7   ; 44
                db      $01, $FF, $00, $03, $0F, $09, $04, $07
                dw      $1164, $0004
                db      $01
                dw      $1160, $1170, $0160
                db      $A7   ; 45
                db      $02, $00, $00, $03, $0F, $09, $04, $07
                dw      $1164, $0004
                db      $01
                dw      $1160, $1170, $0160
                db      $A7   ; 46
                db      $01, $00, $00, $02, $04, $09, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 47
                db      $01, $00, $00, $02, $04, $0F, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 48
                db      $01, $00, $00, $02, $02, $0A, $04, $07
                dw      $00A0, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 49
                db      $01, $00, $00, $02, $04, $0F, $04, $07
                dw      $00A0, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 50
                db      $02, $00, $00, $02, $04, $0A, $04, $07
                dw      $00A0, $0002
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 51
                db      $02, $00, $00, $02, $04, $09, $04, $07
                dw      $00A0, $0002
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 52
                db      $02, $00, $00, $02, $04, $0F, $04, $07
                dw      $00A0, $0003
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 53
                db      $02, $00, $00, $03, $0F, $09, $04, $07
                dw      $0164, $0100
                db      $00
                dw      $0160, $0170, $0560
                db      $A7   ; 54
                db      $02, $00, $00, $03, $0F, $09, $04, $07
                dw      $0164, $0102
                db      $00
                dw      $0160, $0170, $0560
                db      $A7   ; 55
                db      $02, $00, $00, $03, $0F, $09, $04, $07
                dw      $0164, $0101
                db      $00
                dw      $0160, $0170, $0560
                db      $A7   ; 56
                db      $02, $00, $00, $02, $04, $09, $04, $07
                dw      $00A0, $0000
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 57
                db      $02, $00, $00, $02, $80, $09, $04, $07
                dw      $00A0, $0100
                db      $00
                dw      $00A0, $20A0, $0190
                db      $A7   ; 58
                db      $02, $00, $00, $02, $01, $0C, $04, $07
                dw      $2662, $0002
                db      $05
                dw      $2660, $0660, $2668
                db      $A7   ; 59
                db      $00, $00, $00, $02, $08, $05, $04, $07
                dw      $2642, $2468
                db      $05
                dw      $2640, $0640, $2650
                db      $A7   ; 60
                db      $00, $00, $00, $02, $08, $05, $04, $07
                dw      $0E4A, $2468
                db      $06
                dw      $0E40, $2E40, $2640
                db      $A7   ; 61
                db      $01, $00, $00, $02, $10, $09, $04, $07
                dw      $2481, $2468
                db      $01
                dw      $2480, $0480, $2490
                db      $A7   ; 62
                db      $02, $00, $00, $02, $80, $0F, $04, $07
                dw      $00A0, $0008
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 63
                db      $02, $00, $00, $02, $80, $0A, $04, $07
                dw      $00A0, $0008
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 64
                db      $01, $00, $00, $02, $04, $1A, $04, $07
                dw      $00A0, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 65
                db      $01, $00, $00, $02, $10, $0F, $04, $07
                dw      $00A5, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 66
                db      $02, $00, $00, $03, $0F, $1A, $04, $07
                dw      $0164, $0002
                db      $00
                dw      $0160, $0170, $0170
                db      $A7   ; 67
                db      $01, $00, $00, $02, $01, $01, $04, $07
                dw      $005B, $2468
                db      $00
                dw      $0050, $2050, $0060
                db      $A7   ; 68
                db      $02, $00, $00, $02, $04, $0A, $04, $07
                dw      $00A0, $0000
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 69
                db      $02, $00, $00, $02, $04, $0F, $04, $07
                dw      $00A0, $0000
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 70
                db      $02, $00, $00, $02, $10, $09, $04, $07
                dw      $2481, $0000
                db      $01
                dw      $2480, $0480, $2490
                db      $A7   ; 71
                db      $02, $00, $00, $02, $04, $09, $04, $07
                dw      $00A0, $0005
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 72
                db      $02, $00, $00, $02, $01, $09, $04, $07
                dw      $015C, $0003
                db      $00
                dw      $0158, $2158, $0168
                db      $A7   ; 73
                db      $01, $00, $00, $02, $40, $1A, $04, $07
                dw      $00D1, $2468
                db      $00
                dw      $00D0, $20D0, $00E0
                db      $A7   ; 74
                db      $00, $00, $00, $02, $80, $05, $04, $07
                dw      $0808, $2468
                db      $06
                dw      $0800, $2800, $2000
                db      $A7   ; 75
                db      $02, $00, $00, $02, $10, $0F, $04, $07
                dw      $00A5, $0002
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 76
                db      $01, $00, $00, $02, $04, $1A, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 77
                db      $01, $FF, $00, $02, $04, $0F, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 78
                db      $01, $FF, $00, $02, $01, $01, $04, $07
                dw      $005B, $2468
                db      $00
                dw      $0050, $2050, $0060
                db      $A7   ; 79
                db      $01, $FF, $00, $02, $04, $09, $04, $07
                dw      $00A1, $2468
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 80
                db      $02, $00, $00, $02, $40, $1A, $04, $07
                dw      $00D1, $0002
                db      $00
                dw      $00D0, $20D0, $00E0
                db      $A7   ; 81
                db      $02, $00, $00, $02, $10, $1A, $04, $07
                dw      $00B5, $0001
                db      $00
                dw      $00B0, $20B0, $00C0
                db      $A7   ; 82
                db      $01, $00, $00, $03, $0F, $1A, $04, $07
                dw      $05FF, $2468
                db      $00
                dw      $05F0, $0600, $0600
                db      $A7   ; 83
                db      $01, $00, $00, $02, $10, $1A, $04, $07
                dw      $00B5, $2468
                db      $00
                dw      $00B0, $20B0, $00C0
                db      $A7   ; 84
                db      $01, $00, $00, $02, $08, $0E, $04, $07
                dw      $0662, $2468
                db      $00
                dw      $0660, $2660, $0670
                db      $A7   ; 85
                db      $02, $00, $00, $02, $04, $09, $04, $07
                dw      $00A1, $0000
                db      $00
                dw      $00A0, $20A0, $00B0
                db      $A7   ; 86
                db      $00, $00, $00, $03, $0F, $05, $04, $07
                dw      $2164, $2468
                db      $00
                dw      $2160, $0160, $2170
                db      $A7   ; 87
                db      $01, $00, $00, $03, $0F, $09, $04, $07
                dw      $2164, $2468
                db      $00
                dw      $2160, $0160, $2170
                db      $A7   ; 88
                db      $FF
