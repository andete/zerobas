; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBBLTD -- D-MSX2SPEC, docs/msx2/sub/{BLTVD,BLTDV,BLTMD,BLTDM}.md: the sub-ROM's block transfers that involve a DISK
; FILE -- $019D BLTVD (file -> VRAM), $01A1 BLTDV (VRAM -> file), $01A5 BLTMD (file -> RAM), $01A9 BLTDM (RAM -> file)
; -- through EXTROM with IX = the entry and HL = the block (normally $F562), on the MSX2 / MSX2+ references.
; The program runs from H.STKE (after every ROM, the disk ROM included, has initialised; xbblk1's frame), on its own
; stack ($8FF0), with H.ERRO hooked (RST 30h into this cartridge): an error reaching BASIC's error handler is recorded
; (E) and the case abandoned by restoring SP -- the handbook's way for a caller outside BASIC.
; Drive A = scratchpad/xsubbltd.py's image (host-made RAWDATA.BIN, BSAVED.BIN, ARR.PIC, LONG.BIN); the files the calls
; write are read back from the image after the run (BIOSL_KEEP_DSK; `xsubbltd.py decode`).
; Per case (the generated table `cases`: entry, HL, SCRMOD, the 15-byte block, the window's preset, wx, wy, ram
; (0 a VRAM window, 1 RAM, 2 a VRAM window read only, 3 RAM read only), raddr): R#45 := 0; CHGMOD, interrupts off; the VRAM source rectangle (8, 8) 8 x 4 := distinct bytes ($10 + row x 16 + column;
; SCREEN 5: $12 $34 $56 $78 per row); RAM $9000-$90FF := (i x 7 + $11) & $FF; the window (6 VRAM lines x 16 bytes
; from (wx, wy), or 96 RAM bytes from raddr := $EE) preset; the block -> $F562 (and the second block -> $9F00);
; BC $BC0C, DE $DE0E, A $5A, F $01 (carry set); EI; the call; the engine waited for; the record.
; The capture (CAP = A001): +0 $A5 when finished, +1 the case count; per case a 256-byte record from +2:
;   +0 the case, +1 1 = H.ERRO was reached, +2 E there, +3 IFF after (read twice), +4..+15 AF BC DE HL IX IY
;   (little-endian words; at H.ERRO when it was reached), +16..+30 the block $F562-$F570 after, +31 S#2 as first
;   read after the return (before the probe's own wait for CE = 0),
;   +32..+127 the window after, +128..+241 the VDP state right after the call (@vdpfull: R#0-R#63 as last written,
;   S#0-S#15, the VRAM pointer, the palette), then R#45 := 0 before the window is read; +242..+247 $F55E-$F561 and
;   $F571-$F572 (the block's neighbours, preset $A0-$A5 before the call), +248 LOGOPR ($FB02, preset $0E: a no-op code).
; Run (python3 scratchpad/xsubbltd.py mkdsk $ZEROBAS_TMP/xsubbltd.dsk first):
;   BIOSL_KEEP_DSK=$ZEROBAS_TMP/xsubbltd-out python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubbltd.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS / sub-ROM entries, hooks and work-area cells, the VDP's published ports.
;
; @disk $ZEROBAS_TMP/xsubbltd.dsk
; @cap A000
; @caplen 2310
; @vdpfull 9F7F 9F98
; @timeout 240

CHGMOD  equ     $005F
EXTROM  equ     $015F
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA
H_ERRO  equ     $FFB1
BLK     equ     $F562
DONE    equ     $A000
CAP     equ     $A001
SRC     equ     $9000
NAMES   equ     $9E00
ALT     equ     $9F00
ptr     equ     $9F80
tp      equ     $9F82
cidx    equ     $9F84
myslot  equ     $9F85
raf     equ     $9F86
rbc     equ     $9F88
rde     equ     $9F8A
rhl     equ     $9F8C
rix     equ     $9F8E
riy     equ     $9F90
riff    equ     $9F92
errf    equ     $9F93
erre    equ     $9F94
savesp  equ     $9F96
vptr    equ     $9F98                   ; @vdpfull's pointer: the record's +128
vdpbp   equ     $9F7F                   ; a RET in RAM: @vdpfull's breakpoint
s2pre   equ     $9F9A                   ; S#2 as first read after the call
LOGOPR  equ     $FB02
cur     equ     $9FA0                   ; entry (2), HL (2), SCRMOD, block (15), preset, wx (2), wy, ram, raddr (2) = 27
c_hl    equ     cur+2
c_scr   equ     cur+4
c_blk   equ     cur+5
c_pre   equ     cur+20
c_wx    equ     cur+21
c_wy    equ     cur+23
c_ram   equ     cur+24
c_ra    equ     cur+25

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h calls in H.STKE / H.ERRO
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, c
                ld      (myslot), a
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                di
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      sp, $8FF0
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $2400
                ld      (hl), 0
                ldir
                ld      hl, names_rom
                ld      de, NAMES
                ld      bc, names_end - names_rom
                ldir
                ld      hl, alt_rom
                ld      de, ALT
                ld      bc, 15
                ldir
                ld      a, $C9
                ld      (vdpbp), a
                ld      a, (myslot)         ; H.ERRO := RST 30h, our slot, err_h, RET
                ld      (H_ERRO+1), a
                ld      hl, err_h
                ld      (H_ERRO+2), hl
                ld      a, $C9
                ld      (H_ERRO+4), a
                ld      a, $F7
                ld      (H_ERRO), a
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                inc     hl
                or      (hl)
                dec     hl
                jp      z, finish
                ld      de, cur
                ld      bc, 27
                ldir
                ld      (tp), hl
                ld      a, (c_scr)
                call    CHGMOD
                di
                call    src_set
                ld      c, $40
                call    win
                ld      a, (c_ram)          ; a RAM window: 96 x $EE
                cp      1
                jr      nz, c_nor
                ld      hl, (c_ra)
                ld      b, 96
c_ee:
                ld      (hl), $EE
                inc     hl
                djnz    c_ee
c_nor:
                ld      hl, SRC             ; the RAM source, every case
                ld      b, 0
                ld      a, $11
c_src:
                ld      (hl), a
                add     a, 7
                inc     hl
                djnz    c_src
                ld      hl, c_blk
                ld      de, BLK
                ld      bc, 15
                ldir
                ld      hl, BLK - 4         ; the block's neighbours := $A0-$A3, $A4 $A5; LOGOPR := $0E
                ld      a, $A0
                ld      b, 4
c_nb:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_nb
                ld      ($F571), a
                inc     a
                ld      ($F572), a
                ld      a, $0E
                ld      (LOGOPR), a
                xor     a
                ld      (errf), a
                ld      (erre), a
                ld      ix, (cur)
                ld      hl, $5A01
                push    hl
                ld      bc, $BC0C
                ld      de, $DE0E
                ld      hl, (c_hl)
                ld      (savesp), sp        ; with the AF word still pushed: err_h pops it
                pop     af
                ei
                call    EXTROM
                jr      after
err_h:
                ld      (rhl), hl           ; reached from BASIC's error handler through H.ERRO
                ld      a, e
                ld      (erre), a
                ld      a, 1
                ld      (errf), a
                ld      hl, (rhl)
                ld      sp, (savesp)
                inc     sp
                inc     sp
after:
                ld      (rhl), hl
                ld      (rde), de
                ld      (rbc), bc
                ld      (rix), ix
                ld      (riy), iy
                push    af
                pop     hl
                ld      (raf), hl
                ld      a, i
                jp      pe, i_on
                ld      a, i
i_on:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (riff), a
                call    cewait
                ld      hl, (ptr)           ; the VDP state as the call left it -> the record's +128
                ld      bc, 128
                add     hl, bc
                ld      (vptr), hl
                call    vdpbp
                call    r45z                ; then R#45 := 0: our own CPU reads must reach VRAM, not expansion RAM
                ld      de, (ptr)
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (errf)
                ld      (de), a
                inc     de
                ld      a, (erre)
                ld      (de), a
                inc     de
                ld      a, (riff)
                ld      (de), a
                inc     de
                ld      hl, raf
                ld      bc, 12
                ldir
                ld      hl, BLK
                ld      bc, 15
                ldir
                ld      a, (s2pre)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 32
                add     hl, bc
                ld      (ptr), hl
                ld      a, (c_ram)
                cp      1
                jr      z, c_rr
                cp      3
                jr      nz, c_vr
c_rr:
                ld      hl, (c_ra)
                ld      de, (ptr)
                ld      bc, 96
                ldir
                jr      c_rec
c_vr:
                ld      c, $00
                call    win
c_rec:
                ld      hl, (ptr)           ; +242: the neighbours and LOGOPR
                ld      bc, 210
                add     hl, bc
                ex      de, hl
                ld      hl, BLK - 4
                ld      bc, 4
                ldir
                ld      hl, $F571
                ld      bc, 2
                ldir
                ld      a, (LOGOPR)
                ld      (de), a
                ld      hl, (ptr)
                ld      bc, 96 + 128
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      a, $C9
                ld      (H_ERRO), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
fin:
                jr      fin

r45z:
                xor     a
                out     ($99), a
                ld      a, $80 + 45
                out     ($99), a
                ret

cewait:
                ld      a, 2
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                in      a, ($99)
                ld      (s2pre), a
cw_lp:
                in      a, ($99)
                rrca
                jr      c, cw_lp
                xor     a
                out     ($99), a
                ld      a, $8F
                out     ($99), a
                ret

; the line Y = A's address (HL) at pixel X = DE: SCREEN 8 Y x 256 + X; SCREEN 5 Y x 128 + X / 2
lineaddr:
                ld      b, a
                ld      a, (c_scr)
                cp      8
                jr      nz, la5
                ld      h, b
                ld      l, 0
                add     hl, de
                ret
la5:
                ld      h, 0
                ld      l, b
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                srl     d
                rr      e
                add     hl, de
                ret
; HL for writing (C $40) / reading (C $00), A16 = 0
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

; the source rectangle (8, 8), four lines (R#45 := 0 first: CPU access to VRAM)
src_set:
                call    r45z
                ld      a, 8
ss_lp:
                push    af
                ld      de, 8
                call    lineaddr
                ld      c, $40
                call    vset
                pop     af
                push    af
                sub     8
                add     a, a
                add     a, a
                add     a, a
                add     a, a
                add     a, $10
                ld      c, a
                ld      a, (c_scr)
                cp      8
                jr      nz, ss5
                ld      b, 8
ss8:
                ld      a, c
                out     ($98), a
                inc     c
                djnz    ss8
                jr      ss_nx
ss5:
                ld      hl, s5row
                ld      b, 4
ss5b:
                ld      a, (hl)
                out     ($98), a
                inc     hl
                djnz    ss5b
ss_nx:
                pop     af
                inc     a
                cp      12
                jr      nz, ss_lp
                ret
s5row:          db      $12, $34, $56, $78

; the VRAM window: 6 lines from wy x 16 bytes from wx; write (C $40) the preset or read (C $00) into (ptr)
win:
                ld      a, (c_ram)
                cp      1
                ret     z
                cp      3
                ret     z
                cp      2                   ; 2: a read-only window (the source itself)
                jr      nz, w_go
                ld      a, c
                or      a
                ret     nz
w_go:
                ld      a, (c_wy)
                ld      b, 6
                ld      ix, (ptr)
w_line:
                push    bc
                push    af
                push    bc
                ld      de, (c_wx)
                call    lineaddr
                pop     bc
                call    vset
                ld      b, 16
w_b:
                ld      a, c
                or      a
                jr      z, w_rd
                ld      a, (c_pre)
                out     ($98), a
                jr      w_nx
w_rd:
                in      a, ($98)
                ld      (ix+0), a
                inc     ix
w_nx:
                djnz    w_b
                pop     af
                inc     a
                pop     bc
                djnz    w_line
                ret

; ---- CASES BEGIN (generated: python3 scratchpad/xsubbltd.py table) ----
names_rom:
                db      $22, $44, $4D, $31, $2E, $42, $49, $4E, $22, 0   ; dm1 "DM1.BIN"
                db      $22, $44, $4D, $32, $2E, $42, $49, $4E, $22, 0   ; dm2 "DM2.BIN"
                db      $44, $4D, $33, $2E, $42, $49, $4E, 0   ; dm3 DM3.BIN
                db      $22, $4E, $4F, $46, $49, $4C, $45, $2E, $42, $49, $4E, $22, 0   ; nof "NOFILE.BIN"
                db      $22, $42, $53, $41, $56, $45, $44, $2E, $42, $49, $4E, $22, 0   ; bsv "BSAVED.BIN"
                db      $22, $52, $41, $57, $44, $41, $54, $41, $2E, $42, $49, $4E, $22, 0   ; raw "RAWDATA.BIN"
                db      $22, $44, $56, $31, $2E, $50, $49, $43, $22, 0   ; dv1 "DV1.PIC"
                db      $22, $44, $56, $35, $2E, $50, $49, $43, $22, 0   ; dv5 "DV5.PIC"
                db      $22, $41, $52, $52, $2E, $50, $49, $43, $22, 0   ; arr "ARR.PIC"
                db      $22, $46, $49, $58, $2E, $42, $49, $4E, $22, 0   ; fix "FIX.BIN"
                db      $22, $48, $4C, $42, $2E, $42, $49, $4E, $22, 0   ; hlb "HLB.BIN"
                db      $22, $4C, $4F, $4E, $47, $2E, $42, $49, $4E, $22, 0   ; long "LONG.BIN"
                db      $22, $44, $56, $58, $2E, $50, $49, $43, $22, 0   ; dvx "DVX.PIC"
                db      $22, $44, $56, $47, $2E, $50, $49, $43, $22, 0   ; dvg "DVG.PIC"
                db      $22, $44, $56, $36, $2E, $50, $49, $43, $22, 0   ; dv6 "DV6.PIC"
                db      $22, $4C, $4F, $4E, $47, $4E, $41, $4D, $45, $2E, $50, $49, $43, $22, 0   ; lng "LONGNAME.PIC"
                db      $22, $44, $56, $50, $2E, $50, $49, $43, $22, 0   ; dvp "DVP.PIC"
                db      $22, $41, $3A, $44, $56, $41, $2E, $50, $49, $43, $22, 0   ; dva "A:DVA.PIC"
names_end:
alt_rom:        db      $20, $90, $29, $90, $6C, $9E, $A1, $A2, $A3, $A4, $A5, $A6, $A7, $A8, $A9
cases:
                dw      $01A9, $F562   ; 0 BLTDM $9000-$903F -> "DM1.BIN"
                db      8, $00, $90, $3F, $90, $00, $9E, $57, $58, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $9000
                dw      $01A9, $F562   ; 1 BLTDM $9010-$9010 -> "DM2.BIN"
                db      8, $10, $90, $10, $90, $0A, $9E, $57, $58, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $9000
                dw      $01A9, $F562   ; 2 BLTDM $9000-$900F -> DM3.BIN unquoted
                db      8, $00, $90, $0F, $90, $14, $9E, $57, $58, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $9000
                dw      $01A5, $F562   ; 3 BLTMD "DM1.BIN" -> $9200-$9263
                db      8, $00, $9E, $53, $54, $00, $92, $63, $92, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $91F8
                dw      $01A5, $F562   ; 4 BLTMD "DM1.BIN" -> $9300-$930F (range < file)
                db      8, $00, $9E, $53, $54, $00, $93, $0F, $93, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $92F8
                dw      $01A5, $F562   ; 5 BLTMD "BSAVED.BIN" ($FE, $9420-$942F) -> $9400-$94FF
                db      8, $29, $9E, $53, $54, $00, $94, $FF, $94, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $93F8
                dw      $01A5, $F562   ; 6 BLTMD "RAWDATA.BIN" (no header) -> $9500-$95FF
                db      8, $36, $9E, $53, $54, $00, $95, $FF, $95, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $94F8
                dw      $01A5, $F562   ; 7 BLTMD "NOFILE.BIN" (missing) -> $9600-$96FF
                db      8, $1C, $9E, $53, $54, $00, $96, $FF, $96, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $95F8
                dw      $01A5, $F562   ; 8 BLTMD "DM1.BIN" -> $9600-$96FF (after the error)
                db      8, $00, $9E, $53, $54, $00, $96, $FF, $96, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $95F8
                dw      $01A1, $F562   ; 9 BLTDV SCREEN 8 (8,8) 8x4 -> "DV1.PIC"
                db      8, $08, $00, $08, $00, $44, $9E, $57, $58, $08, $00, $04, $00, $5D, $00, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $019D, $F562   ; 10 BLTVD "DV1.PIC" -> (40,8) LOGOP 0
                db      8, $44, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 11 BLTVD "DV1.PIC" -> (40,8) LOGOP 3 over $FF
                db      8, $44, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $03, $FF
                dw      36
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 12 BLTVD "ARR.PIC" (RAM array, no $FE) -> (40,8)
                db      8, $58, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $01A1, $F562   ; 13 BLTDV SCREEN 5 (8,8) 7x3 -> "DV5.PIC"
                db      5, $08, $00, $08, $00, $4E, $9E, $57, $58, $07, $00, $03, $00, $5D, $00, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $019D, $F562   ; 14 BLTVD "DV5.PIC" -> SCREEN 5 (40,8)
                db      5, $4E, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      32
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 15 BLTVD "NOFILE.BIN" (missing) -> (40,8)
                db      8, $1C, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $01A9, $9F00   ; 16 BLTDM HL=$9F00 ("HLB.BIN" $9020-$9029, +6..+14 $A1..); $F562: "FIX.BIN" $9000-$903F
                db      8, $00, $90, $3F, $90, $62, $9E, $57, $58, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 3
                dw      $9F00
                dw      $01A9, $F562   ; 17 BLTDM $9000-$900F -> "LONG.BIN" (exists, 300 B)
                db      8, $00, $90, $0F, $90, $76, $9E, $57, $58, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $9000
                dw      $01A5, $F562   ; 18 BLTMD "DM1.BIN" -> $9700-$96FF (EPTR < SPTR)
                db      8, $00, $9E, $53, $54, $00, $97, $FF, $96, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $96F8
                dw      $019D, $F562   ; 19 BLTVD "DV1.PIC" -> (252,8): past the right edge
                db      8, $44, $9E, $53, $54, $FC, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      240
                db      7, 0
                dw      $0000
                dw      $01A1, $F562   ; 20 BLTDV SCREEN 8 (15,8) 8x4 ARG $04 (DIX) -> "DVX.PIC"
                db      8, $0F, $00, $08, $00, $81, $9E, $57, $58, $08, $00, $04, $00, $5D, $04, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $01A1, $F562   ; 21 BLTDV SCREEN 8 (8,8) 8x4 ARG $5E (MXC MXS DIY DIX EQ) -> "DVG.PIC"
                db      8, $08, $00, $08, $00, $8B, $9E, $57, $58, $08, $00, $04, $00, $5D, $5E, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $01A1, $F562   ; 22 BLTDV SCREEN 5 (8,8) 7x3 -> "DV6.PIC" (right after DVG's 32 x $FF)
                db      5, $08, $00, $08, $00, $95, $9E, $57, $58, $07, $00, $03, $00, $5D, $00, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $019D, $F562   ; 23 BLTVD "DV1.PIC" -> (252,8), the window at x 0-15 over $99
                db      8, $44, $9E, $53, $54, $FC, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $99
                dw      0
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 24 BLTVD "DV1.PIC" -> (40,8) LOGOP 0 over $55, dummy $0123
                db      8, $44, $9E, $23, $01, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $55
                dw      36
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 25 BLTVD "DV1.PIC" -> (40,100) LOGOP 3 over $55
                db      8, $44, $9E, $53, $54, $28, $00, $64, $00, $59, $5A, $5B, $5C, $5D, $00, $03, $55
                dw      36
                db      99, 0
                dw      $0000
                dw      $019D, $F562   ; 26 BLTVD "DV1.PIC" -> (47,8) ARG $04 (DIX)
                db      8, $44, $9E, $53, $54, $2F, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $04, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 27 BLTVD "DV5.PIC" -> SCREEN 5 (40,8) over $99
                db      5, $4E, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $99
                dw      32
                db      7, 0
                dw      $0000
                dw      $019D, $F562   ; 28 BLTVD "LONGNAME.PIC" (14-byte name) -> (40,8)
                db      8, $9F, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $01A1, $F562   ; 29 BLTDV SCREEN 8 (9,9) 4x2 LOGOP $03, dummy $0123 -> "DVP.PIC"
                db      8, $09, $00, $09, $00, $AE, $9E, $23, $01, $04, $00, $02, $00, $5D, $00, $03, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $01A1, $F562   ; 30 BLTDV SCREEN 8 (8,8) 8x4 -> "A:DVA.PIC" (drive prefix)
                db      8, $08, $00, $08, $00, $B8, $9E, $57, $58, $08, $00, $04, $00, $5D, $00, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $01A1, $F562   ; 31 BLTDV SCREEN 8 (8,8) 8x4 -> DM3.BIN unquoted
                db      8, $08, $00, $08, $00, $14, $9E, $57, $58, $08, $00, $04, $00, $5D, $00, $5F, $00
                dw      8
                db      7, 2
                dw      $0000
                dw      $019D, $F562   ; 32 BLTVD DM3.BIN unquoted -> (40,8)
                db      8, $14, $9E, $53, $54, $28, $00, $08, $00, $59, $5A, $5B, $5C, $5D, $00, $00, $00
                dw      36
                db      7, 0
                dw      $0000
                dw      $01A5, $F562   ; 33 BLTMD DM3.BIN unquoted -> $9800-$98FF
                db      8, $14, $9E, $53, $54, $00, $98, $FF, $98, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $97F8
                dw      $01A5, $F562   ; 34 BLTMD "DM1.BIN" -> $9702-$9700 (EPTR = SPTR - 2)
                db      8, $00, $9E, $53, $54, $02, $97, $00, $97, $59, $5A, $5B, $5C, $5D, $5E, $5F, $00
                dw      0
                db      0, 1
                dw      $96F8
                dw      0
; ---- CASES END ----


                ds      $8000 - $, $FF
