; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XCLR -- docs/bios/CLRSPR.md, CHGCLR.md round 2 (2026-11-18; round 1's fill had every block sum alike): the sprite clear and the colour change. Per case (the
; table `cases` at the end: op, F, interrupts, SCRMOD, RG1SAV, FORCLR, BAKCLR, BDRCLR, ATRBAS, PATBAS, cell set, three
; window addresses) the probe first sets, BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := set 0 (the published defaults) or set 1 (moved;
;     `tsets`, as in xset.asm);
;   - SCRMOD ($FCAF), RG1SAV ($F3E0), FORCLR / BAKCLR / BDRCLR ($F3E9-$F3EB), ATRBAS ($F928), PATBAS ($F926) := the
;     case's; RG0SAV, RG2SAV-RG7SAV := $A5;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := ((address low) XOR (address high) XOR $5A) OR address / $400 (each 1 KB block sums apart).
; Then BC $1357, DE $9BDF, HL $2468, IX $4321, IY $8765 (all XOR $FF in odd cases), A $A7, F and interrupts as listed,
; and the call: op 0 CLRSPR ($0069), 1 CHGCLR ($0062).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xclr.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 128-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on)
;   +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..24 FORCLR / BAKCLR / BDRCLR after
;   +25..32 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +33..64 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after, read with R#1 := $80 first
;   +65..80, +81..96, +97..112 the 16 VRAM bytes from W1, W2, W3 after  +113..127 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports, and the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0D00
; @timeout 120
; @vdpsnap E8F0 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $E8F0
STUB    equ     $E8F2
cop     equ     $E910                   ; op, F, ei, SCRMOD, RG1SAV, FOR, BAK, BDR, ATRBAS, PATBAS, set, W1, W2, W3
cF      equ     $E911
cei     equ     $E912
cscr    equ     $E913
crg1    equ     $E914
cfor    equ     $E915
catr    equ     $E918
cpat    equ     $E91A
cts     equ     $E91C
cW1     equ     $E91D
cW2     equ     $E91F
cW3     equ     $E921
mask    equ     $E924
cidx    equ     $E925
raf     equ     $E930
rbc     equ     $E932
rde     equ     $E934
rhl     equ     $E936
rix     equ     $E938
riy     equ     $E93A
riff    equ     $E93C
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
                ld      bc, $0CFF
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
                ld      bc, 19
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
                ld      b, 15
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
                ld      hl, RG0SAV
                ld      b, 8
p_sav:
                ld      (hl), $A5
                inc     hl
                djnz    p_sav
                ld      a, (crg1)
                ld      (RG0SAV+1), a
                ld      a, (cscr)
                ld      (SCRMOD), a
                ld      hl, cfor
                ld      de, FORCLR
                ld      bc, 3
                ldir
                ld      hl, (catr)
                ld      (ATRBAS), hl
                ld      hl, (cpat)
                ld      (PATBAS), hl
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
                ret

targets:
                dw      $0069, $0062
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

; ---- cases: op, F, interrupts, SCRMOD, RG1SAV, FORCLR, BAKCLR, BDRCLR; ATRBAS, PATBAS; set; W1, W2, W3; $FF ends ----
cases:
                db      $00, $00, $00, $01, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 0
                db      $00, $FF, $00, $01, $E2, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 1
                db      $00, $00, $01, $02, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 2
                db      $00, $FF, $01, $03, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 3
                db      $00, $00, $00, $00, $F0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 4
                db      $00, $FF, $00, $01, $E0, $0F, $04, $07
                dw      $1F80, $2000
                db      $00
                dw      $1F80, $1B00, $2000   ; 5
                db      $00, $00, $01, $01, $E0, $0F, $04, $07
                dw      $1F80, $2000
                db      $00
                dw      $1FF0, $3800, $27F0   ; 6
                db      $00, $FF, $01, $01, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $01
                dw      $3F80, $1B00, $1000   ; 7
                db      $00, $00, $00, $01, $E0, $0A, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 8
                db      $00, $FF, $00, $01, $E0, $FF, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 9
                db      $00, $00, $01, $02, $E3, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 10
                db      $00, $FF, $01, $77, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $1B00, $1B70, $3800   ; 11
                db      $01, $00, $00, $00, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 12
                db      $01, $FF, $00, $01, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 13
                db      $01, $00, $01, $02, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 14
                db      $01, $FF, $01, $03, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 15
                db      $01, $00, $00, $00, $E0, $1A, $25, $3C
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 16
                db      $01, $FF, $00, $01, $E0, $1A, $25, $3C
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 17
                db      $01, $00, $01, $02, $E0, $1A, $25, $3C
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 18
                db      $01, $FF, $01, $03, $E0, $1A, $25, $3C
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 19
                db      $01, $00, $00, $01, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $01
                dw      $0FC0, $0FD0, $2000   ; 20
                db      $01, $FF, $00, $77, $E0, $0F, $04, $07
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 21
                db      $01, $00, $01, $01, $E0, $00, $00, $00
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 22
                db      $01, $FF, $01, $00, $E0, $0F, $0F, $0F
                dw      $1B00, $3800
                db      $00
                dw      $2000, $2010, $0000   ; 23
                db      $FF
