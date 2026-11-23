; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XMODE2 -- D-MSX2SPEC goldfish pass 1 (2026-11-23), the separating cases for docs/msx2/sub/{CHGMOD,CHGMDP,SETPAG,
; INITXT,INIT32,INIGRP,INIMLT,SETTXT,SETT32,SETGRP,SETMLT}.md and concepts/screen-modes.md. xmode.asm entered every
; case from SCREEN 0 (a main CHGMOD 0 first), with one garbage value ($A5) in every copy, interrupts off, the default
; colours and widths, and recorded neither the VDP before the call, nor VRAM, the palette, BC..IY, R#32-R#46 or the
; colour / width cells. This probe does all of that.
; Per case (the table `cases`, 24 bytes each): the boot values of LINL40..CRTCNT, RG0SAV-RG7SAV, $FFE7-$FFFC and
; FORCLR / BAKCLR / BDRCLR are put back and DPPAGE / ACPAGE := 0; main CHGMOD ($005F) into the case's PREVIOUS mode;
; interrupts off; then the overrides: LINL40, LINL32; VRAM := $5A over all 128 KB (R#14 set per 16 KB block, flag 2);
; the 16 palette entries := `pgtab` (flag 4); RG0SAV := cv0, RG1SAV-RG7SAV := cvx (unless flag 8); DPPAGE, ACPAGE;
; SCRMOD, OLDSCR, LINLEN, RG9SAV ($FFE8), FORCLR, BAKCLR, BDRCLR where given; SCNCNT := $FF. The whole VDP is
; snapshotted (before), then the call: IX := entry, A / F from the table (F through the stack), BC $1357, DE $9BDF,
; HL $2468, IY $1A2B, BC' $B0C0, DE' $D0E0, HL' $7080, AF' $4142; EI if flag 1; CALL EXTROM ($015F). Entry $0000 is
; the debugger read-back case: no call, R#0-R#7, R#10, R#11 := $FF by OUT ($99), then the record.
; The capture (CAP = 9001, kept below $C000: clearing $C001-$C3FF, or using $8801-$9000, made C-BIOS JP / JP+ lose the
; run): +0 $A5 when finished, +1 the case count; per case a 352-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF (second read), +4 IFF first read, +5 BC DE HL IX IY (10), +15 BC' DE' HL' AF' (8,
;   AF' as F then A), +24 the VDP after (@vdpfull: R#0-R#63, S#0-S#15, VRAM pointer 2, palette 32 = 114),
;   +138 the VDP before (114), +252 RG0SAV-RG7SAV, +260 $FFE7-$FFFC (22), +282 SCRMOD OLDSCR LINLEN CRTCNT LINL40
;   LINL32 FORCLR BAKCLR BDRCLR, +291 $F922-$F92B (10), +301 DPPAGE ACPAGE MODE, +304 VRAM: per 16 KB block (8) the
;   count of bytes != $5A (2) and the last such byte (flag 2 only), +328 8 bytes at ATRBAS (2 sprites), +336 12 bytes
;   (6 entries) at the palette table of SCRMOD after (App. 5: 0 $0400 / $0F00 when LINLEN > 40, 1 3 $2020, 2 4 $1B80,
;   5 6 $7680, 7 8 $FA80), +348 CSRY CSRX, +351 $5E (sentinel).
; Round 2 (appended, cases 30-33): CHGMOD 2 from SCREEN 0 with OLDSCR 6 (OLDSCR untouched vs := SCRMOD when <= 1);
; SETPAG with A / F $00 (F kept vs a constant); SETTXT and INITXT with LINL40 37 and LINLEN 80 (TEXT 2 chosen by LINLEN?).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xmode2.asm --row msx2all
; Decode: python3 scratchpad/xmode2_decode.py scratchpad/AE_xmode2_msx2.out [--side ours]
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP state read
; by the debugger.
;
; @cap 9000
; @caplen 2F00
; @vdpfull EF00 EF02
; @timeout 900

CHGMOD  equ     $005F
EXTROM  equ     $015F
DONE    equ     $9000
CAP     equ     $9001
RECLEN  equ     352
SNAPFN  equ     $EF00
SNAPP   equ     $EF02
ptr     equ     $EE00
tp      equ     $EE02
cidx    equ     $EE04
rsave   equ     $EE10                   ; 22
cur     equ     $EE40                   ; 24
boot    equ     $EE60                   ; 37

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $2EFE
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      de, boot
                ld      hl, $F3AE
                ld      bc, 4
                ldir
                ld      hl, $F3DF
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      bc, 22
                ldir
                ld      hl, $F3E9
                ld      bc, 3
                ldir
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
                ld      bc, 24
                ldir
                ld      (tp), hl
                ld      hl, boot
                ld      de, $F3AE
                ld      bc, 4
                ldir
                ld      de, $F3DF
                ld      bc, 8
                ldir
                ld      de, $FFE7
                ld      bc, 22
                ldir
                ld      de, $F3E9
                ld      bc, 3
                ldir
                xor     a
                ld      ($FAF5), a
                ld      ($FAF6), a
                ld      a, (cur+4)
                call    CHGMOD
                di
                ld      a, (cur+10)
                or      a
                jr      z, c_n40
                ld      ($F3AE), a
c_n40:
                ld      a, (cur+11)
                or      a
                jr      z, c_n32
                ld      ($F3AF), a
c_n32:
                ld      a, (cur+7)
                and     2
                call    nz, vfill
                ld      a, (cur+7)
                and     4
                call    nz, palg
                ld      a, (cur+7)
                and     8
                jr      nz, c_ncp
                ld      a, (cur+5)
                ld      ($F3DF), a
                ld      hl, $F3E0
                ld      b, 7
                ld      a, (cur+6)
c_cp:
                ld      (hl), a
                inc     hl
                djnz    c_cp
c_ncp:
                ld      a, (cur+8)
                ld      ($FAF5), a
                ld      a, (cur+9)
                ld      ($FAF6), a
                ld      a, (cur+12)
                cp      $FF
                jr      z, c_o1
                ld      ($FCAF), a
c_o1:
                ld      a, (cur+13)
                cp      $FF
                jr      z, c_o2
                ld      ($FCB0), a
c_o2:
                ld      a, (cur+14)
                or      a
                jr      z, c_o3
                ld      ($F3B0), a
c_o3:
                ld      a, (cur+15)
                cp      $FF
                jr      z, c_o4
                ld      ($FFE8), a
c_o4:
                ld      hl, cur+16
                ld      de, $F3E9
                ld      b, 3
c_col:
                ld      a, (hl)
                cp      $FF
                jr      z, c_col2
                ld      (de), a
c_col2:
                inc     hl
                inc     de
                djnz    c_col
                ld      a, $FF
                ld      ($F3F6), a              ; SCNCNT: no key scan in the window
                ld      hl, (ptr)
                ld      bc, 138
                add     hl, bc
                ld      (SNAPP), hl
                call    SNAPFN                  ; the VDP before
                ld      hl, (cur)
                ld      a, h
                or      l
                jp      z, c_raw
                exx
                ld      bc, $B0C0
                ld      de, $D0E0
                ld      hl, $7080
                exx
                ld      hl, $4142
                push    hl
                pop     af
                ex      af, af'
                ld      ix, (cur)
                ld      a, (cur+2)
                ld      h, a
                ld      a, (cur+3)
                ld      l, a
                push    hl
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                ld      iy, $1A2B
                ld      a, (cur+7)
                bit     0, a
                jr      z, c_di
                pop     af
                ei
                jr      c_go
c_di:
                pop     af
c_go:
                call    EXTROM
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                push    af
                jp      pe, c_ion
                ld      a, i                    ; an "off" is read again (the NMOS ld a,i erratum)
c_ion:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+3), a
                pop     hl
                ld      (rsave), hl             ; F, A
                pop     hl
                ld      (rsave+4), hl
                pop     hl
                ld      (rsave+6), hl
                pop     hl
                ld      (rsave+8), hl
                pop     hl
                ld      (rsave+10), hl
                pop     hl
                ld      (rsave+12), hl
                exx
                push    bc
                push    de
                push    hl
                exx
                ex      af, af'
                push    af
                ex      af, af'
                pop     hl
                ld      (rsave+20), hl
                pop     hl
                ld      (rsave+18), hl
                pop     hl
                ld      (rsave+16), hl
                pop     hl
                ld      (rsave+14), hl
                jr      c_rec
c_raw:
                ld      hl, rsave
                ld      b, 22
c_rz:
                ld      (hl), 0
                inc     hl
                djnz    c_rz
                ld      c, 0
c_rw:
                ld      a, $FF
                out     ($99), a
                ld      a, c
                or      $80
                out     ($99), a
                inc     c
                ld      a, c
                cp      8
                jr      nz, c_rw2
                ld      c, 10
c_rw2:
                cp      12
                jr      nz, c_rw
c_rec:
                ld      de, (ptr)
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+2)
                ld      (de), a
                inc     de
                ld      a, (rsave+3)
                ld      (de), a
                inc     de
                ld      hl, rsave+4
                ld      bc, 18
                ldir
                ld      hl, (ptr)
                ld      bc, 24
                add     hl, bc
                ld      (SNAPP), hl
                call    SNAPFN                  ; the VDP after
                ld      hl, (ptr)
                ld      bc, 252
                add     hl, bc
                ex      de, hl
                ld      hl, $F3DF
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      bc, 22
                ldir
                ld      hl, cellt
                ld      b, 9
c_cl:
                push    hl
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ld      a, (hl)
                ld      (de), a
                inc     de
                pop     hl
                inc     hl
                inc     hl
                djnz    c_cl
                ld      hl, $F922
                ld      bc, 10
                ldir
                ld      a, ($FAF5)
                ld      (de), a
                inc     de
                ld      a, ($FAF6)
                ld      (de), a
                inc     de
                ld      a, ($FAFC)
                ld      (de), a
                inc     de
                ld      a, (cur+7)
                and     2
                call    nz, vcheck
                ld      hl, (ptr)
                ld      bc, 328
                add     hl, bc
                ex      de, hl
                ld      hl, ($F928)
                ld      b, 8
                call    vread
                ld      a, ($FCAF)
                cp      9
                jr      c, c_pt
                ld      a, 8
c_pt:
                add     a, a
                ld      c, a
                ld      b, 0
                ld      hl, ptab
                add     hl, bc
                ld      a, (hl)
                inc     hl
                ld      h, (hl)
                ld      l, a
                ld      a, ($FCAF)
                or      a
                jr      nz, c_pt2
                ld      a, ($F3B0)
                cp      41
                jr      c, c_pt2
                ld      hl, $0F00
c_pt2:
                ld      b, 12
                call    vread
                ld      a, ($F3DC)
                ld      (de), a
                inc     de
                ld      a, ($F3DD)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, RECLEN - 1
                add     hl, bc
                ld      (hl), $5E
                inc     hl
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a              ; progress, so a run that dies still says how far it got
                jp      c_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                di                              ; and stay quiet: no mode call or interrupt after the record
fin:
                jr      fin

; VRAM := $5A over 128 KB, R#14 set per 16 KB block (no reliance on the counter's carry)
vfill:
                ld      c, 0
vf_b:
                ld      a, c
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                xor     a
                out     ($99), a
                ld      a, $40
                out     ($99), a
                ld      d, 64
                ld      b, 0
                ld      a, $5A
vf_l:
                out     ($98), a
                push    af
                pop     af
                djnz    vf_l
                dec     d
                jr      nz, vf_l
                inc     c
                ld      a, c
                cp      8
                jr      nz, vf_b
                ret

; per 16 KB block: the count of bytes != $5A and the last one, at DE (24 bytes)
vcheck:
                ld      c, 0
vc_b:
                ld      a, c
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                xor     a
                out     ($99), a
                out     ($99), a
                push    de
                ld      hl, 0
                ld      e, 0
                ld      d, 64
                ld      b, 0
vc_l:
                in      a, ($98)
                cp      $5A
                jr      nz, vc_d
vc_n:
                djnz    vc_l
                dec     d
                jr      nz, vc_l
                ld      a, e
                pop     de
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), a
                inc     hl
                ex      de, hl
                inc     c
                ld      a, c
                cp      8
                jr      nz, vc_b
                ret
vc_d:
                inc     hl
                ld      e, a
                jr      vc_n

; B bytes of VRAM at HL (A16 = 0) to DE
vread:
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
                out     ($99), a
vr_l:
                push    af
                pop     af
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    vr_l
                ret

; the 16 palette entries := pgtab (R#16 := 0, then 32 bytes to port $9A)
palg:
                xor     a
                out     ($99), a
                ld      a, $90
                out     ($99), a
                ld      hl, pgtab
                ld      b, 32
pg_l:
                ld      a, (hl)
                out     ($9A), a
                inc     hl
                push    af
                pop     af
                djnz    pg_l
                ret

pgtab:
                db      $31, $02, $04, $01, $57, $00, $22, $07, $75, $06, $40, $05, $13, $04, $66, $03
                db      $32, $05, $05, $04, $50, $03, $23, $02, $76, $01, $41, $00, $14, $07, $67, $06
ptab:
                dw      $0400, $2020, $1B80, $2020, $1B80, $7680, $7680, $FA80, $FA80
cellt:
                dw      $FCAF, $FCB0, $F3B0, $F3B1, $F3AE, $F3AF, $F3E9, $F3EA, $F3EB

; entry; A, F in, previous mode, cv0 (RG0SAV), cvx (RG1SAV-RG7SAV), flags (1 EI, 2 VRAM, 4 palette, 8 copies kept),
; DPPAGE, ACPAGE, LINL40, LINL32 (0 = leave), SCRMOD, OLDSCR ($FF = leave), LINLEN (0 = leave), RG9SAV, FORCLR,
; BAKCLR, BDRCLR ($FF = leave); 5 spare
cases:
                ; CHGMOD
                dw      $00D1
                db      $05, $00, 0, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $00, $0A, $05, $03, 0, 0, 0, 0, 0   ;  0 A5 from 0, copies 00
                dw      $00D1
                db      $05, $FF, 1, $8F, $FF, 7, 0, 0, 0, 0, $FF, $FF, 0, $08, $0E, $0C, $09, 0, 0, 0, 0, 0   ;  1 A5 from 1, copies FF, EI
                dw      $00D1
                db      $02, $00, 1, $8F, $FF, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0A, $05, $03, 0, 0, 0, 0, 0   ;  2 A2 from 1
                dw      $00D1
                db      $00, $00, 8, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0   ;  3 A0 from 8
                dw      $00D1
                db      $00, $FF, 8, $8F, $FF, 2, 0, 0, 80, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0  ;  4 A0 from 8, LINL40 80
                dw      $00D1
                db      $08, $00, 0, $8F, $FF, 6, 0, 0, 0, 0, $FF, $FF, 0, $00, $0A, $05, $03, 0, 0, 0, 0, 0   ;  5 A8 from 0
                dw      $00D1
                db      $09, $00, 0, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ;  6 A9 from 0
                dw      $00D1
                db      $04, $00, 7, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0   ;  7 A4 from 7
                dw      $00D1
                db      $01, $00, 5, $8F, $FF, 2, 0, 0, 0, 33, $FF, $FF, 20, $FF, $0A, $05, $03, 0, 0, 0, 0, 0 ;  8 A1 from 5, LINL32 33
                ; CHGMDP
                dw      $01B5
                db      $05, $00, 0, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ;  9 A5 from 0
                dw      $01B5
                db      $00, $00, 5, $00, $00, 7, 0, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 10 A0 from 5, EI
                dw      $01B5
                db      $08, $00, 0, $00, $00, 6, 0, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 11 A8 from 0
                ; SETPAG
                dw      $013D
                db      $33, $FF, 7, $00, $00, 0, 1, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 12 SCREEN 7 DP1 AC0
                dw      $013D
                db      $33, $FF, 8, $8F, $FF, 0, 2, 1, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 13 SCREEN 8 DP2 AC1
                dw      $013D
                db      $33, $FF, 5, $00, $00, 1, 2, 3, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 14 SCREEN 5 DP2 AC3 EI
                dw      $013D
                db      $33, $FF, 5, $8F, $FF, 0, 4, 5, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 15 SCREEN 5 DP4 AC5
                dw      $013D
                db      $33, $FF, 5, $00, $00, 8, 1, 2, 0, 0, 7, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0     ; 16 SCREEN 5, SCRMOD 7
                dw      $013D
                db      $33, $FF, 0, $00, $00, 0, 1, 1, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 17 SCREEN 0 DP1
                ; INIT*
                dw      $00D5
                db      $FF, $FF, 5, $00, $00, 6, 0, 0, 33, 0, 7, 6, 20, $FF, $0A, $05, $03, 0, 0, 0, 0, 0     ; 18 INITXT from 5
                dw      $00D5
                db      $FF, $FF, 8, $8F, $FF, 3, 0, 0, 80, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0  ; 19 INITXT from 8, 80
                dw      $00D9
                db      $FF, $FF, 5, $00, $00, 6, 0, 0, 0, 33, 7, 6, 20, $FF, $0A, $05, $03, 0, 0, 0, 0, 0     ; 20 INIT32 from 5
                dw      $00DD
                db      $FF, $FF, 5, $8F, $FF, 2, 0, 0, 0, 0, 7, 6, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0       ; 21 INIGRP from 5
                dw      $00E1
                db      $FF, $FF, 8, $00, $00, 2, 0, 0, 0, 0, 7, 6, 0, $FF, $0A, $05, $03, 0, 0, 0, 0, 0       ; 22 INIMLT from 8
                ; SET*
                dw      $00E5
                db      $FF, $FF, 5, $8F, $FF, 2, 0, 0, 33, 0, $FF, $FF, 20, $FF, $0A, $05, $03, 0, 0, 0, 0, 0 ; 23 SETTXT from 5
                dw      $00E5
                db      $FF, $FF, 0, $00, $00, 1, 0, 0, 80, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0  ; 24 SETTXT LINL40 80, EI
                dw      $00E9
                db      $FF, $FF, 5, $8F, $FF, 2, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0   ; 25 SETT32 from 5
                dw      $00ED
                db      $FF, $FF, 4, $8F, $FF, 2, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0A, $05, $03, 0, 0, 0, 0, 0   ; 26 SETGRP from 4
                dw      $00F1
                db      $FF, $FF, 0, $8F, $FF, 0, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0E, $0C, $09, 0, 0, 0, 0, 0   ; 27 SETMLT copies FF
                dw      $00F1
                db      $00, $00, 0, $00, $00, 0, 0, 0, 0, 0, $FF, $FF, 0, $FF, $0A, $05, $03, 0, 0, 0, 0, 0   ; 28 SETMLT copies 00
                ; the debugger's read-back
                dw      $0000
                db      $00, $00, 0, $00, $00, 8, 0, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 29 raw $FF
                ; round 2 (appended): the rules the first 30 left coinciding
                dw      $00D1
                db      $02, $00, 0, $00, $00, 0, 0, 0, 0, 0, $FF, 6, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0     ; 30 A2 from 0, OLDSCR 6
                dw      $013D
                db      $00, $00, 5, $00, $00, 8, 1, 0, 0, 0, $FF, $FF, 0, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0   ; 31 SETPAG SCR5 DP1, A/F 00
                dw      $00E5
                db      $FF, $FF, 0, $00, $00, 8, 0, 0, 37, 0, $FF, $FF, 80, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0 ; 32 SETTXT LINL40 37, LINLEN 80
                dw      $00D5
                db      $FF, $FF, 0, $00, $00, 8, 0, 0, 37, 0, $FF, $FF, 80, $FF, $FF, $FF, $FF, 0, 0, 0, 0, 0 ; 33 INITXT LINL40 37, LINLEN 80
                db      $EE

                ds      $8000 - $, $FF
