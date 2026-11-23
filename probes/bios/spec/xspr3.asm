; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSPR3 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), docs/msx2/sub/{CLRSPR,CALPAT,CALATR,GSPSIZ,GETPAT}.md: the cases
; xspr2.asm left open -- the separating cases the review named. Per case (the table `cases`: op 0 CLRSPR 1 CALPAT
; 2 CALATR 3 GSPSIZ 4 GETPAT, A, SCRMOD, the sprite size, a variant): FORCLR := $0F, CHGMOD (main $005F); RG1SAV's
; bit 1 := the size, bit 0 cleared, in RAM; then R#1 := RG1SAV through port $99 (so the VDP AGREES with RG1SAV), and
; the variant:
;   0 none   1 FORCLR $0A   2 FORCLR $FF   3 PATBAS / ATRBAS moved (SCREEN 1: $3000 / $2800; SCREEN 5: $6000 / $6E00)
;   4 R#1 := RG1SAV XOR 2 through port $99 (the VDP DISAGREES with RG1SAV on the size)   5 RG1SAV bit 0 (magnify) set
;   6 CGPNT ($F91F-$F921) := the page-3 RAM slot, $E000, with $11 $22 ... $88 at $E000 + 8 x $41, AND the VRAM
;     pattern of A (CGPBAS + 8 A) := $C3   7 only the VRAM pattern of A := $C3
; Then VRAM is preset: 2048 bytes from PATBAS (+256 more in SCREEN 4 and up) := $A5, 512 bytes from ATRBAS - $200 :=
; $E7, 128 bytes from ATRBAS := $5A; PATWRK := $A5; BC $1357, DE $9BDF, HL $2468, IY $8765, IX = the entry; EXTROM.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 256-byte record from +2:
;   +0 op +1 A in +2 SCRMOD +3 size +4 variant +5..7 0
;   +8 A +9 F +10 B +11 C +12 D +13 E +14 H +15 L +16 IXh +17 IXl +18 IYh +19 IYl (after)
;   +20 RG1SAV after +21 FORCLR after +22,23 0
;   +24..+31 PATWRK
;   +32,33 the count of $00 bytes in the 2048 from PATBAS; +34,35 in the 256 after them (SCREEN 4 and up; else 0)
;   +36,37 the count of bytes still $A5 in the 2048 (low, high); +38..+63 0
;   +64..+95 the colour table's planes 0-1 (ATRBAS - $200); +96..+111 plane 31's; +112..+127 0
;   +128..+255 the 128 attribute bytes from ATRBAS
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xspr3.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 1E00
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
RG1SAV  equ     $F3E0
FORCLR  equ     $F3E9
CGPNT   equ     $F91F
CGPBAS  equ     $F924
PATBAS  equ     $F926
ATRBAS  equ     $F928
PATWRK  equ     $FC40
SCRMOD  equ     $FCAF
EXPTBL  equ     $FCC1
SLTTBL  equ     $FCC5
DONE    equ     $C000
CAP     equ     $C001
FONT    equ     $E000
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rec     equ     $E90A
cgsave  equ     $E90C                   ; CGPNT's 3 bytes
r3slot  equ     $E90F
rsave   equ     $E910                   ; AF BC DE HL IX IY after
cur     equ     $E920                   ; op, A, SCRMOD, size, variant

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1FFE
                ld      (hl), 0
                ldir
                ld      hl, CGPNT
                ld      de, cgsave
                ld      bc, 3
                ldir
                ; the page-3 RAM slot ID
                in      a, ($A8)
                rlca
                rlca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, s_plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rlca
                rlca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
s_plain:
                ld      a, c
                ld      (r3slot), a
                ; the RAM font: $11 $22 ... $88 for character $41
                ld      hl, FONT + 8 * $41
                ld      a, $11
                ld      b, 8
f_lp:
                ld      (hl), a
                add     a, $11
                inc     hl
                djnz    f_lp
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 5
                ldir
                ld      (tp), hl
                ld      hl, cgsave
                ld      de, CGPNT
                ld      bc, 3
                ldir
                ld      a, $0F
                ld      (FORCLR), a
                ld      a, (cur+2)
                call    CHGMOD
                di
                ld      a, (RG1SAV)
                and     $FC
                ld      b, a
                ld      a, (cur+3)
                add     a, a
                or      b
                ld      (RG1SAV), a
                ld      b, a
                ld      a, (cur+4)
                cp      4
                jr      nz, r1_agree
                ld      a, b
                xor     2
                ld      b, a
r1_agree:
                ld      a, b
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ld      a, (cur+4)
                cp      1
                jr      nz, v_2
                ld      a, $0A
                ld      (FORCLR), a
v_2:
                cp      2
                jr      nz, v_3
                ld      a, $FF
                ld      (FORCLR), a
v_3:
                cp      3
                jr      nz, v_5
                ld      hl, $3000
                ld      de, $2800
                ld      a, (cur+2)
                cp      4
                jr      c, v_3s
                ld      hl, $6000
                ld      de, $6E00
v_3s:
                ld      (PATBAS), hl
                ld      (ATRBAS), de
v_5:
                ld      a, (cur+4)
                cp      5
                jr      nz, v_6
                ld      hl, RG1SAV
                set     0, (hl)
v_6:
                ld      a, (cur+4)
                cp      6
                jr      nz, v_7
                ld      a, (r3slot)
                ld      (CGPNT), a
                ld      hl, FONT
                ld      (CGPNT+1), hl
                jr      v_7g
v_7:
                cp      7
                jr      nz, v_end
v_7g:
                ld      a, (cur+1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ld      de, (CGPBAS)
                add     hl, de
                ld      bc, 8
                ld      a, $C3
                call    vfill
v_end:
                ; VRAM presets
                ld      hl, (PATBAS)
                ld      bc, 2048
                call    bigmode
                jr      c, pp_s
                ld      bc, 2048 + 256
pp_s:
                ld      a, $A5
                call    vfill
                ld      hl, (ATRBAS)
                ld      de, -$200
                add     hl, de
                ld      bc, 512
                ld      a, $E7
                call    vfill
                ld      hl, (ATRBAS)
                ld      bc, 128
                ld      a, $5A
                call    vfill
                ld      hl, PATWRK
                ld      b, 8
pw:
                ld      (hl), $A5
                inc     hl
                djnz    pw
                ld      a, (cur)
                ld      ix, $00F5
                or      a
                jr      z, go
                ld      ix, $00F9
                dec     a
                jr      z, go
                ld      ix, $00FD
                dec     a
                jr      z, go
                ld      ix, $0101
                dec     a
                jr      z, go
                ld      ix, $0105
go:
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      iy, $8765
                ld      a, (cur+1)
                call    EXTROM
                di
                ld      (rsave+12), iy
                ld      (rsave+10), ix
                ld      (rsave+8), hl
                ld      (rsave+6), de
                ld      (rsave+4), bc
                push    af
                pop     bc
                ld      (rsave+2), bc
                ; the record
                ld      hl, (ptr)
                ld      (rec), hl
                ex      de, hl
                ld      hl, cur
                ld      bc, 5
                ldir
                ld      hl, (rec)
                ld      de, 8
                add     hl, de
                ex      de, hl                  ; DE = rec + 8
                ld      hl, rsave+2             ; A F B C D E H L IXh IXl IYh IYl: the high byte first
                ld      b, 6
rg_lp:
                inc     hl
                ld      a, (hl)
                ld      (de), a
                inc     de
                dec     hl
                ld      a, (hl)
                ld      (de), a
                inc     de
                inc     hl
                inc     hl
                djnz    rg_lp
                ld      a, (RG1SAV)
                ld      (de), a
                inc     de
                ld      a, (FORCLR)
                ld      (de), a
                ld      hl, (rec)
                ld      de, 24
                add     hl, de
                ex      de, hl
                ld      hl, PATWRK
                ld      bc, 8
                ldir
                ; pattern-area counts
                ld      hl, (PATBAS)
                ld      bc, 2048
                call    vzcount
                ld      hl, (rec)
                ld      de, 32
                add     hl, de
                ld      (hl), c
                inc     hl
                ld      (hl), b
                inc     hl
                inc     hl
                inc     hl
                ld      a, (a5cnt)
                ld      (hl), a
                inc     hl
                ld      a, (a5cnt+1)
                ld      (hl), a
                call    bigmode
                jr      c, pz_s
                ld      hl, (PATBAS)
                ld      de, 2048
                add     hl, de
                ld      bc, 256
                call    vzcount
                ld      hl, (rec)
                ld      de, 34
                add     hl, de
                ld      (hl), c
                inc     hl
                ld      (hl), b
pz_s:
                ; the colour table: planes 0-1, plane 31
                ld      hl, (ATRBAS)
                ld      de, -$200
                add     hl, de
                ld      de, 64
                ld      bc, 32
                call    vread
                ld      hl, (ATRBAS)
                ld      de, $FFF0                ; - $10: plane 31 = ATRBAS - $200 + 31 x 16
                add     hl, de
                ld      de, 96
                ld      bc, 16
                call    vread
                ld      hl, (ATRBAS)
                ld      de, 128
                ld      bc, 128
                call    vread
                ld      hl, (rec)
                inc     h
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                jp      c_next
finish:
                ld      hl, cgsave
                ld      de, CGPNT
                ld      bc, 3
                ldir
                ld      a, (cidx)
                ld      (CAP+1), a
                ld      a, $0F
                ld      (FORCLR), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; carry set when SCRMOD < 4 (the 16 KB modes: no extra 256 bytes past the pattern area)
bigmode:
                ld      a, (SCRMOD)
                cp      4
                ret

; VRAM address HL (A16 = 0) for writing (C $40) or reading (C $00)
vset:
                ld      a, h
                rlca
                rlca
                and     3
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      c
                out     ($99), a
                ret

; fill BC bytes of VRAM from HL with A
vfill:
                push    af
                push    bc
                ld      c, $40
                call    vset
                pop     bc
                pop     af
                ld      e, a
vf_lp:
                ld      a, e
                out     ($98), a
                dec     bc
                ld      a, b
                or      c
                jr      nz, vf_lp
                ret

; read BC bytes of VRAM from HL into (rec) + DE
vread:
                push    bc
                push    de
                ld      c, $00
                call    vset
                pop     de
                ld      hl, (rec)
                add     hl, de
                pop     bc
vr_lp:
                in      a, ($98)
                ld      (hl), a
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, vr_lp
                ret

; count the $00 bytes (-> BC) and the $A5 bytes (-> a5cnt) in BC bytes of VRAM from HL
vzcount:
                push    bc
                ld      c, $00
                call    vset
                pop     de
                ld      bc, 0
                ld      hl, 0
                ld      (a5cnt), hl
vz_lp:
                in      a, ($98)
                or      a
                jr      nz, vz_n
                inc     bc
                jr      vz_d
vz_n:
                cp      $A5
                jr      nz, vz_d
                ld      hl, (a5cnt)
                inc     hl
                ld      (a5cnt), hl
vz_d:
                dec     de
                ld      a, d
                or      e
                jr      nz, vz_lp
                ret

a5cnt   equ     $E930

; op, A, SCRMOD, size, variant
cases:
                ; CALPAT
                db      1, $03, 1, 0, 0         ; the register baseline
                db      1, $03, 5, 0, 3         ; PATBAS $6000: $6018 (the cell) vs $7818 (the default)
                db      1, $03, 1, 0, 4         ; RG1SAV 8 x 8, R#1 16 x 16: $3818 vs $3860
                db      1, $03, 1, 1, 4         ; RG1SAV 16 x 16, R#1 8 x 8
                db      1, $FF, 7, 1, 0         ; PATBAS $F000 + $1FE0: the 16-bit wrap
                ; CALATR
                db      2, $05, 1, 0, 0         ; the register baseline
                db      2, $05, 1, 1, 0         ; 16 x 16
                db      2, $05, 5, 0, 3         ; ATRBAS $6E00: $6E14 vs $7614
                db      2, $FF, 8, 0, 0         ; ATRBAS $FA00: $FDFC (16-bit) vs $FAFC (8-bit) vs $FA7C (5 bits)
                ; GSPSIZ
                db      3, $00, 1, 0, 5         ; RG1SAV $x1
                db      3, $00, 1, 1, 5         ; RG1SAV $x3
                db      3, $00, 1, 0, 4         ; RG1SAV 8 x 8, R#1 16 x 16
                db      3, $00, 1, 1, 4         ; RG1SAV 16 x 16, R#1 8 x 8
                ; GETPAT
                db      4, $41, 1, 0, 0         ; the register baseline
                db      4, $41, 1, 0, 7         ; the VRAM pattern garbage
                db      4, $41, 1, 0, 6         ; CGPNT -> the RAM font (and the VRAM pattern garbage)
                db      4, $41, 5, 0, 0         ; SCREEN 5
                ; CLRSPR
                db      0, $00, 1, 0, 0
                db      0, $00, 1, 1, 0
                db      0, $00, 5, 0, 0
                db      0, $00, 5, 1, 0
                db      0, $00, 1, 0, 1         ; FORCLR $0A
                db      0, $00, 5, 0, 1
                db      0, $00, 1, 0, 2         ; FORCLR $FF
                db      0, $00, 5, 0, 2
                db      0, $00, 1, 0, 3         ; tables moved
                db      0, $00, 5, 0, 3
                db      0, $00, 1, 0, 4         ; RG1SAV 8 x 8, R#1 16 x 16
                db      0, $00, 1, 1, 4         ; RG1SAV 16 x 16, R#1 8 x 8
                db      $EE

                ds      $8000 - $, $FF
