; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XGFX5 -- docs/bios/GRPPRT.md round 2 (2026-11-19; round 1 had cases 0-23): the call that draws a character on a graphics screen. xgfx3.asm's
; frame, its case fields read anew: op, F, interrupts, SCRMOD, FORCLR, LOGOPR, ATRBYT, (unused), GRPACX, GRPACY, cell
; set, three window addresses, A (the character). Per case the probe first sets, BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := one of `tsets` (0 the published defaults; 1 moved:
;     GRPCGP $2000, GRPCOL $0000, MLTCGP $1000);
;   - SCRMOD ($FCAF), FORCLR ($F3E9), LOGOPR ($FB02), ATRBYT ($F3F2), GRPACX ($FCB7), GRPACY ($FCB9) := the case's;
;     CLOC ($F92A) := $5A5A, CMASK ($F92C) := $A5; RG0SAV-RG7SAV := $A5;
;   - CGPNT ($F91F slot, $F920 address) := the RAM slot, FONT: the probe's own 2 KB font in RAM (character c's line j is
;     (c x 7) XOR (j x $33) XOR $96), so no ROM font byte reaches VRAM;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := ((address low) XOR (address high) XOR $5A) OR (address high AND $3C);
;   - the VDP status read last.
; Then BC $1357, DE $9BDF, IX $4321, IY $8765 (all XOR $FF when bit 2 of the case number is set), HL $2468, A, F and
; the interrupts as listed, and the call: op 0 GRPPRT ($008D).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx5.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 128-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..24 FORCLR / BAKCLR / BDRCLR after
;   +25..32 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +33..64 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after, read with R#1 := $80 first
;   +65..80, +81..96, +97..112 the 16 VRAM bytes from W1, W2, W3 after
;   +113,114 CLOC  +115 CMASK  +116 ATRBYT  +117,118 GRPACX  +119,120 GRPACY  +121 FORCLR  +122 LOGOPR  after  +123..127 0
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, the slot registers, VRAM through the VDP's ports,
; and the VDP's registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 1800
; @timeout 180
; @vdpsnap E8F0 EF00

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
tptr    equ     $EF02
SNAP    equ     $E8F0
STUB    equ     $E8F2
cop     equ     $E910                   ; op, F, ei, SCRMOD, RG1SAV, FOR, BAK, BDR, ATRBAS, PATBAS, set, W1, W2, W3, A
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
cA      equ     $E923
mask    equ     $E926
cidx    equ     $E927
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
GRPACX  equ     $FCB7
GRPACY  equ     $FCB9
LOGOPR  equ     $FB02
CGPNT   equ     $F91F
FONT    equ     $D800
ramid   equ     $E928

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
                ld      (SNAP), a
                ld      hl, CAP+1
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
                xor     a
                ld      (cidx), a
                ld      hl, FONT                ; the font: character c's line j := (c x 7) XOR (j x $33) XOR $96
                ld      c, 0
fo_c:
                ld      a, c
                add     a, a
                add     a, a
                add     a, a
                sub     c
                ld      e, a                    ; c x 7
                ld      d, 0                    ; j x $33
                ld      b, 8
fo_j:
                ld      a, e
                xor     d
                xor     $96
                ld      (hl), a
                inc     hl
                ld      a, d
                add     a, $33
                ld      d, a
                djnz    fo_j
                inc     c
                jr      nz, fo_c
                in      a, ($A8)                ; the RAM slot ID: page 3's primary slot, and its secondary
                rlca                            ; selection (SLTTBL) where that slot is expanded (EXPTBL)
                rlca
                and     3
                ld      e, a
                ld      hl, $FCC1               ; EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, rid
                ld      a, e
                ld      hl, $FCC5               ; SLTTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                rrca
                rrca
                rrca
                rrca
                and     $0C
                or      e
                or      $80
                ld      e, a
rid:
                ld      a, e
                ld      (ramid), a
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
                ld      hl, $2468
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
                ld      hl, GRPACX
                call    emitm
                inc     hl
                call    emitm
                ld      hl, GRPACY
                call    emitm
                inc     hl
                call    emitm
                ld      hl, FORCLR
                call    emitm
                ld      hl, LOGOPR
                call    emitm
                ld      b, 5
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
                ld      a, $A5
                ld      ($F92C), a              ; CMASK
                ld      hl, $5A5A
                ld      ($F92A), hl             ; CLOC
                ld      a, (cscr)
                ld      (SCRMOD), a
                ld      a, (crg1)
                ld      (FORCLR), a
                ld      a, (cfor)
                ld      (LOGOPR), a
                ld      a, (cfor+1)
                ld      ($F3F2), a              ; ATRBYT
                ld      hl, (catr)
                ld      (GRPACX), hl
                ld      hl, (cpat)
                ld      (GRPACY), hl
                ld      a, (ramid)
                ld      (CGPNT), a
                ld      hl, FONT
                ld      (CGPNT+1), hl
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
                dw      $008D
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

; ---- cases: op, F, interrupts, SCRMOD, FORCLR, LOGOPR, ATRBYT, 0; GRPACX, GRPACY; set; W1, W2, W3; A; $FF ends ----
cases:
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0000, $0000
                db      $00
                dw      $0000, $2000, $0100
                db      $41   ; 0
                db      $00, $FF, $01, $02, $0F, $00, $77, $00
                dw      $0064, $0032
                db      $00
                dw      $0660, $2660, $0760
                db      $41   ; 1
                db      $00, $00, $00, $02, $09, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $41   ; 2
                db      $00, $00, $00, $02, $04, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $00   ; 3
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $20   ; 4
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $FF   ; 5
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $0D   ; 6
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $0A   ; 7
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $08   ; 8
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $1F   ; 9
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $00FA, $000A
                db      $00
                dw      $01F0, $21F0, $02F0
                db      $41   ; 10
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $00FC, $00BC
                db      $00
                dw      $17F0, $37F0, $18F0
                db      $41   ; 11
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0000, $00BE
                db      $00
                dw      $1700, $3700, $1800
                db      $41   ; 12
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $012C, $0032
                db      $00
                dw      $0620, $2620, $0720
                db      $41   ; 13
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0064, $00C8
                db      $00
                dw      $1960, $3960, $1A60
                db      $41   ; 14
                db      $00, $00, $00, $02, $0F, $03, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $41   ; 15
                db      $00, $00, $00, $02, $1A, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $41   ; 16
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $01
                dw      $2660, $0660, $2760
                db      $41   ; 17
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $0000, $0000
                db      $00
                dw      $0000, $0100, $0010
                db      $41   ; 18
                db      $00, $FF, $01, $03, $09, $00, $77, $00
                dw      $0064, $0032
                db      $00
                dw      $0690, $0790, $06A0
                db      $41   ; 19
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0680, $0780, $0690
                db      $0D   ; 20
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $00FC, $00BC
                db      $00
                dw      $07F0, $08F0, $0800
                db      $41   ; 21
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $01
                dw      $1680, $1780, $1690
                db      $41   ; 22
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $FFF8, $0030
                db      $00
                dw      $06F0, $26F0, $07F0
                db      $41   ; 23
                db      $00, $00, $00, $02, $09, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $3A   ; 24
                db      $00, $00, $00, $02, $03, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $3A   ; 25
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $00F8, $0030
                db      $00
                dw      $06F0, $26F0, $07F0
                db      $41   ; 26
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $00F7, $0030
                db      $00
                dw      $06F0, $26F0, $07F0
                db      $41   ; 27
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $00F8, $00B8
                db      $00
                dw      $17F0, $37F0, $18F0
                db      $41   ; 28
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0064, $00BF
                db      $00
                dw      $1760, $3760, $1860
                db      $41   ; 29
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $0002, $0006
                db      $00
                dw      $0000, $0100, $0010
                db      $41   ; 30
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $00E0, $0000
                db      $00
                dw      $00E0, $01E0, $00F0
                db      $41   ; 31
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $00C0, $00A0
                db      $00
                dw      $05C0, $06C0, $05D0
                db      $41   ; 32
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $7F   ; 33
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $0C   ; 34
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $1B   ; 35
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $80   ; 36
                db      $00, $00, $00, $02, $03, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $41   ; 37
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0060, $FFFF
                db      $00
                dw      $1F60, $3F60, $2060
                db      $41   ; 38
                db      $00, $00, $01, $02, $0F, $00, $77, $00
                dw      $0060, $0030
                db      $00
                dw      $0660, $2660, $0760
                db      $0A   ; 39
                db      $00, $00, $00, $02, $0F, $00, $77, $00
                dw      $0064, $00BA
                db      $00
                dw      $1760, $3760, $1860
                db      $0D   ; 40
                db      $00, $00, $00, $03, $0F, $00, $77, $00
                dw      $0064, $00AA
                db      $00
                dw      $0560, $0660, $0570
                db      $0D   ; 41
                db      $FF
