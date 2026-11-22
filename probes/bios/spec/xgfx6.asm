; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XGFX6 -- docs/bios/PNTINI.md, SCANR.md, SCANL.md round 10 (2026-11-19; case numbers as the pages use them: round 1 had cases 0-30, round 3 31-47, round 4 48-62,
; round 5 63-78, round 6 a B sweep (one case kept, 79), rounds 7-9 80-81 (an alternate-register sweep, cut to two),
; round 10 82-88; round 2, a work-area poke sweep that changed nothing, dropped; from round 7 the
; alternate registers, the 64 bytes below the call's stack and the 16 from SP up are preset): the PAINT helpers. xgfx3.asm's frame, its case
; fields read anew: op, F, interrupts, SCRMOD, CMASK, ATRBYT, BDRATR, B, CLOC, DE, ALT, W1, W2, HL, A. ALT picks
; the alternate registers BC', DE', HL' from `altset` and seeds the stale-stack fill below (the table cells are always
; the published defaults).
; Per case the probe first sets, BY HAND:
;   - the 20 screen-table cells TXTNAM ($F3B3) .. MLTPAT ($F3D9) := one of `tsets` (0 the published defaults);
;   - SCRMOD ($FCAF), CLOC ($F92A), CMASK ($F92C), ATRBYT ($F3F2), BDRATR ($FCB2) := the case's; RG0SAV-RG7SAV := $A5;
;     the 41 bytes $F92D-$F955 (MINDEL .. RTPROG, the graphics work area) := (i x $1D) XOR $A5 for i = 0..40;
;   - the VDP registers R#0-R#7 := $00 $80 $06 $80 $00 $36 $07 $F4 (display off, so VRAM may be written fast);
;   - every VRAM byte := ((address low) XOR (address high) XOR $5A) OR (address high AND $3C);
;   - the VDP status read last.
; Then B, DE and HL := the case's, C $57 (XOR $FF when bit 2 of the case number is set), IX $4321, IY $8765 (also
; complemented by that bit), A, F and the interrupts as listed, and the call: op 0 PNTINI ($0129), 1 SCANR ($012C),
; 2 SCANL ($012F).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xgfx6.asm --row both
; The capture: CAP+0 = $A5 when finished; per case a 128-byte record from CAP+1:
;   +0 A  +1 F  +2 B  +3 C  +4 D  +5 E  +6 H  +7 L  +8,9 IX  +10,11 IY  after the call  +12 interrupts after (1 on;
;   read twice)  +13..20 RG0SAV-RG7SAV after  +21 SCRMOD after  +22..24 FORCLR / BAKCLR / BDRCLR after
;   +25..32 VDP R#0-R#7 after (the debugger, @vdpsnap)
;   +33..64 the 16-bit sums (low, high) of VRAM's 16 1-KB blocks after, read with R#1 := $80 first
;   +65..80, +81..96 the 16 VRAM bytes from W1, W2 after  +97..112 RAM $F942-$F951 after (CSAVEA .. MOVCNT)
;   +113,114 CLOC  +115 CMASK  +116 ATRBYT  +117 BDRATR  +118..124 RAM $F92D-$F933 after  +125..127 RAM $F952-$F954
; then $C3.
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM through the VDP's ports, and the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 2D00
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
altp    equ     $EE28
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
BDRATR  equ     $FCB2
GWORK   equ     $F92D
cbdr    equ     $EE16
cb      equ     $EE17

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $2CFF
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
                ld      a, (cts)                ; the alternate registers BC', DE', HL' := the case's `altset` entry
                ld      l, a
                ld      h, 0
                add     hl, hl
                ld      d, h
                ld      e, l
                add     hl, hl
                add     hl, de
                ld      de, altset
                add     hl, de
                ld      (altp), hl
                exx
                ld      hl, (altp)
                ld      c, (hl)
                inc     hl
                ld      b, (hl)
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                exx
                ld      hl, 0                   ; the 64 bytes below the call's stack (SP - 68 .. SP - 5 here; the call
                add     hl, sp                  ; and STUB push two return addresses) := (64 - j) XOR (ALT x 16), j from
                ld      de, -68                 ; the lowest: the calls read stale stack there
                add     hl, de
                ld      a, (cts)
                rlca
                rlca
                rlca
                rlca
                ld      c, a
                ld      b, 64
st_lp:
                ld      a, b
                xor     c
                ld      (hl), a
                inc     hl
                djnz    st_lp
                ld      hl, 0                   ; and the 16 bytes from SP up (the caller's frame) := $C0 + j XOR (ALT x 16)
                add     hl, sp
                ld      b, 16
                ld      e, $C0
sa_lp:
                ld      a, e
                xor     c
                ld      (hl), a
                inc     hl
                inc     e
                djnz    sa_lp
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
                ld      a, (cb)
                ld      b, a
                ld      a, e
                xor     $57
                ld      c, a
                ld      de, (cpat)
                ld      hl, (cW3)
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
                ld      hl, $F942               ; CSAVEA .. MOVCNT
                ld      b, 16
r3_lp:
                call    emitm
                inc     hl
                djnz    r3_lp
                ld      hl, $F92A               ; CLOC, CMASK
                call    emitm
                inc     hl
                call    emitm
                inc     hl
                call    emitm
                ld      hl, $F3F2               ; ATRBYT
                call    emitm
                ld      hl, BDRATR
                call    emitm
                ld      hl, GWORK               ; MINDEL .. $F933
                ld      b, 7
r4_lp:
                call    emitm
                inc     hl
                djnz    r4_lp
                ld      hl, $F952
                ld      b, 3
r5_lp:
                call    emitm
                inc     hl
                djnz    r5_lp
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
                xor     a                       ; the table cells: always set 0, the published defaults
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
                ld      a, (cbdr)
                ld      (BDRATR), a
                ld      hl, GWORK               ; MINDEL .. RTPROG := (i x $1D) XOR $A5
                ld      b, 41
                ld      c, 0
g_lp:
                ld      a, c
                xor     $A5
                ld      (hl), a
                inc     hl
                ld      a, c
                add     a, $1D
                ld      c, a
                djnz    g_lp
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
                dw      $0129, $012C, $012F
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

; the alternate-register presets: BC', DE', HL'
altset:
                dw      $0000, $0000, $0000
                dw      $0005, $0000, $0000
                dw      $0000, $0005, $0000
                dw      $0000, $0000, $0005
                dw      $0005, $0005, $0005
                dw      $0100, $0000, $0000
                dw      $0000, $0100, $0000
                dw      $0000, $0000, $0100

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

; ---- cases: op, F, interrupts, SCRMOD, CMASK, ATRBYT, BDRATR, B; CLOC, DE; set; W1, W2, 0; A; $FF ends ----
cases:
                db      $00, $00, $00, $02, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 0
                db      $00, $00, $00, $02, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $0F   ; 1
                db      $00, $00, $00, $02, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $10   ; 2
                db      $00, $00, $00, $02, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $FF   ; 3
                db      $00, $00, $00, $03, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 4
                db      $00, $00, $00, $03, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $10   ; 5
                db      $00, $00, $00, $03, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $FF   ; 6
                db      $00, $FF, $01, $02, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 7
                db      $00, $FF, $01, $03, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $09   ; 8
                db      $01, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 9
                db      $01, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 10
                db      $01, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 11
                db      $01, $00, $00, $02, $10, $0C, $03, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 12
                db      $01, $00, $00, $02, $80, $0C, $0F, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 13
                db      $01, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0003
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 14
                db      $01, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0003
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 15
                db      $01, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0100
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 16
                db      $01, $FF, $01, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 17
                db      $01, $00, $00, $03, $F0, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0360, $2468
                db      $A7   ; 18
                db      $01, $00, $00, $03, $F0, $0C, $0E, $01
                dw      $0264, $0000
                db      $00
                dw      $0260, $0360, $2468
                db      $A7   ; 19
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 20
                db      $02, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 21
                db      $02, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 22
                db      $02, $00, $00, $02, $10, $0C, $03, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 23
                db      $02, $00, $00, $02, $80, $0C, $0F, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 24
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0003
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 25
                db      $02, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0003
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 26
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0100
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 27
                db      $02, $FF, $01, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 28
                db      $02, $00, $00, $03, $F0, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0360, $2468
                db      $A7   ; 29
                db      $02, $00, $00, $03, $F0, $0C, $0E, $01
                dw      $0264, $0000
                db      $00
                dw      $0260, $0360, $2468
                db      $A7   ; 30
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 31
                db      $02, $00, $00, $02, $40, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 32
                db      $02, $00, $00, $02, $20, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 33
                db      $02, $00, $00, $02, $10, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 34
                db      $02, $00, $00, $02, $08, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 35
                db      $02, $00, $00, $02, $04, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 36
                db      $02, $00, $00, $02, $02, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 37
                db      $02, $00, $00, $02, $01, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 38
                db      $02, $00, $00, $02, $02, $0C, $06, $00
                dw      $066A, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 39
                db      $02, $00, $00, $02, $40, $0C, $06, $00
                dw      $066A, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 40
                db      $02, $00, $00, $02, $80, $0C, $0E, $00
                dw      $0672, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 41
                db      $02, $00, $00, $02, $01, $0C, $0E, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 42
                db      $02, $00, $00, $02, $80, $0C, $03, $00
                dw      $066A, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 43
                db      $02, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0001
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 44
                db      $02, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0008
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 45
                db      $02, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $FFFF
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 46
                db      $02, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0000
                db      $00
                dw      $0650, $0660, $2468
                db      $A7   ; 47
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $00   ; 48
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $FF   ; 49
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $0000
                db      $A7   ; 50
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $FFFF
                db      $A7   ; 51
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $0003
                db      $A7   ; 52
                db      $02, $00, $00, $02, $02, $0C, $0D, $00
                dw      $06FA, $0000
                db      $00
                dw      $06F0, $26F0, $2468
                db      $A7   ; 53
                db      $02, $00, $00, $02, $80, $0C, $0D, $00
                dw      $06FA, $0000
                db      $00
                dw      $06F0, $26F0, $2468
                db      $A7   ; 54
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0602, $0000
                db      $00
                dw      $0600, $2600, $2468
                db      $A7   ; 55
                db      $02, $00, $00, $03, $F0, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0270, $2468
                db      $A7   ; 56
                db      $02, $00, $00, $03, $0F, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0270, $2468
                db      $A7   ; 57
                db      $01, $FF, $00, $03, $F0, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0270, $2468
                db      $A7   ; 58
                db      $01, $00, $00, $03, $0F, $0C, $0C, $01
                dw      $02F4, $0000
                db      $00
                dw      $02F0, $0300, $2468
                db      $A7   ; 59
                db      $01, $00, $00, $02, $02, $0C, $0D, $01
                dw      $06FA, $0000
                db      $00
                dw      $06F0, $26F0, $2468
                db      $A7   ; 60
                db      $01, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $0000
                db      $00   ; 61
                db      $01, $00, $00, $02, $10, $0C, $03, $01
                dw      $0662, $0005
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 62
                db      $01, $00, $00, $02, $10, $0C, $03, $00
                dw      $0662, $0001
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 63
                db      $01, $00, $00, $02, $10, $0C, $03, $00
                dw      $0662, $0002
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 64
                db      $01, $00, $00, $02, $10, $0E, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 65
                db      $01, $00, $00, $02, $10, $03, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 66
                db      $00, $00, $00, $02, $80, $00, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 67
                db      $00, $00, $00, $02, $80, $0A, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 68
                db      $00, $00, $00, $02, $80, $1A, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 69
                db      $01, $00, $00, $02, $80, $0C, $06, $02
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 70
                db      $01, $00, $00, $02, $80, $0C, $06, $80
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 71
                db      $00, $00, $00, $00, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 72
                db      $00, $00, $00, $01, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $05   ; 73
                db      $02, $00, $00, $02, $02, $0C, $0D, $00
                dw      $06FA, $0000
                db      $00
                dw      $0700, $2700, $2468
                db      $A7   ; 74
                db      $02, $00, $00, $02, $40, $0C, $03, $00
                dw      $066A, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 75
                db      $00, $00, $00, $03, $80, $07, $33, $00
                dw      $0662, $9BDF
                db      $00
                dw      $0660, $2660, $2468
                db      $80   ; 76
                db      $01, $00, $00, $02, $80, $0C, $03, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 77
                db      $02, $00, $00, $02, $08, $0C, $06, $02
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 78
                db      $02, $00, $00, $02, $80, $0C, $06, $02
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 79
                db      $02, $00, $00, $02, $08, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 80
                db      $02, $00, $00, $02, $80, $0C, $06, $00
                dw      $0662, $0000
                db      $04
                dw      $0660, $2660, $2468
                db      $A7   ; 81
                db      $01, $00, $00, $02, $80, $0C, $06, $01
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 82
                db      $01, $00, $00, $02, $10, $0C, $0E, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 83
                db      $02, $00, $00, $02, $08, $0C, $06, $00
                dw      $0662, $0000
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 84
                db      $01, $00, $00, $02, $10, $0C, $03, $00
                dw      $0662, $0101
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 85
                db      $01, $00, $00, $02, $10, $0C, $03, $01
                dw      $0662, $0001
                db      $00
                dw      $0660, $2660, $2468
                db      $A7   ; 86
                db      $02, $00, $00, $03, $F0, $0C, $00, $00
                dw      $0264, $0000
                db      $00
                dw      $0250, $0260, $2468
                db      $A7   ; 87
                db      $01, $00, $00, $03, $0F, $0C, $0E, $00
                dw      $0264, $0000
                db      $00
                dw      $0260, $0270, $2468
                db      $A7   ; 88
                db      $FF
