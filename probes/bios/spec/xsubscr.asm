; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBSCR -- D-MSX2SPEC, docs/msx2/sub/SDFSCR.md / SETSCR.md: the sub-ROM's SDFSCR ($0185) and SETSCR ($0189) through
; EXTROM, on the MSX2 / MSX2+ references. Run with agent_wt.py --fresh (an empty clock chip at power-on).
; Per case (the table `cases`): the clock chip's block 2 (and for some SETSCR cases block 3) is first written through
; the published WRTCLK (sub-ROM $01F9; C = $20 + register / $30 + register, A = the nibble) from the table `sets`
; (a nibble $FF = leave that register as found); then the screen state is garbled: CHGMOD (main $005F) into the case's
; previous mode with LINL40 37 / LINL32 29 set first; FORCLR / BAKCLR / BDRCLR := $3A / $C5 / $F9, CNSDFG and CLIKSW
; := $5A, CSRY / CSRX := 9 / 7, FNKSTR key k := 15 x ('A' + k), R#18 := 0 (RG18SAV too), R#9's IL / EO bits cleared;
; then A and F from the table (loaded through the stack, so each is its own input), BC DE HL := $B1C1 $D1E1 $4151,
; interrupts as the table says, the call. After it: A F IFF (read twice, spec-method 3a) BC DE HL IX IY, the work-area
; cells, RG0SAV-RG23SAV, the clock chip's blocks 2 and 3 read through ports $B4 / $B5 (never through REDCLK), the whole
; VDP state (@vdpfull), the name table's row 0 and row CRTCNT-1 (80 bytes each; base and row length chosen from
; SCRMOD and RG0SAV after the call).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 384-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF, +4..+13 C B E D L H IXl IXh IYl IYh, +14 IFF first read, +15 0
;   +16 SCRMOD OLDSCR LINL40 LINL32 LINLEN CRTCNT CLMLST CNSDFG CLIKSW FORCLR BAKCLR BDRCLR CSRY CSRX PUTPNT.l GETPNT.l
;   +32 RG0SAV-RG7SAV, +40 RG8SAV-RG23SAV, +56 block 2 regs 0-12 after, +69 MODE (reg 13) after,
;   +72 block 3 regs 0-12 after, +88 @vdpfull (114), +208 row 0 (80), +288 row CRTCNT-1 (80),
;   +368 name base (2), +370 row length, +371 block 2 regs 0-12 BEFORE the call (13),
;   +384 work-area diff count, +385 keys injected, +386 port-$98 log length (2), +388 offset of "SXA" in it (2, $FFFF
;   none), +390 0, +392 the log's 32 bytes from that offset - 8 (or from 0), +424 up to 21 work-area diffs (addr lo,
;   addr hi, old, new), +511 $5E (sentinel).
; The case flags: b0 interrupts on at the call; b1 snapshot $F380-$FFFF after the call (to $A000); b2 diff it against
; the previous snapshot; b3 H.TIMI queues a key ('K') in KEYBUF whenever it is empty (at most 4) -- so a key wait
; cannot hang the run, and the record says whether one was taken; b4 log every OUT to port $98 during the call
; (@portlog, to $8000) -- every byte written to VRAM, so text shown and then erased is still seen.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubscr.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's and the clock chip's published
; ports, the VDP's state read by the debugger.
;
; @cap C000
; @caplen 2A00
; @vdpfull E8F0 E900
; @portlog 98 E948 E8F1
; @timeout 240

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     512
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910                   ; AF (2), IFF, BC DE HL IX IY (10), IFF first read
cur     equ     $E930                   ; entry (2), prev mode, set index, block-3 index, A, F, EI flag
cc      equ     $E940
nbase   equ     $E942
rlen    equ     $E944
ARMFN   equ     $E8F1
LOGP    equ     $E948
logend  equ     $E94A
injc    equ     $E94C
INJ     equ     $E960
LOGB    equ     $8000
SNAPA   equ     $A000
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $29FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                call    ARMFN
                ld      hl, injsrc
                ld      de, INJ
                ld      bc, injend-injsrc
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
                inc     hl
                or      (hl)
                dec     hl
                jp      z, finish
                ld      de, cur
                ld      bc, 8
                ldir
                ld      (tp), hl
                ; the clock chip: block 2 from sets[set], block 3 from sets3[b3]
                ld      a, (cur+3)
                ld      hl, sets
                call    pick13
                ld      c, $20
                call    wrblk
                ld      a, (cur+4)
                ld      hl, sets3
                call    pick13
                ld      c, $30
                call    wrblk
                ; block 2 before the call, into the record
                ld      hl, (ptr)
                ld      de, 371
                add     hl, de
                ex      de, hl
                ld      c, $20
                call    rdblk
                ; the screen state
                ld      a, 37
                ld      ($F3AE), a              ; LINL40
                ld      a, 29
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur+2)
                call    CHGMOD
                di
                ld      hl, fkeys
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                ld      a, $3A
                ld      ($F3E9), a
                ld      a, $C5
                ld      ($F3EA), a
                ld      a, $F9
                ld      ($F3EB), a
                ld      a, $5A
                ld      ($F3DE), a              ; CNSDFG
                ld      ($F3DB), a              ; CLIKSW
                ld      a, 9
                ld      ($F3DC), a              ; CSRY
                ld      a, 7
                ld      ($F3DD), a              ; CSRX
                xor     a
                ld      ($FFF1), a              ; RG18SAV
                out     ($99), a
                ld      a, $80+18
                out     ($99), a
                ld      a, ($FFE8)              ; RG9SAV
                and     $F3
                ld      ($FFE8), a
                out     ($99), a
                ld      a, $80+9
                out     ($99), a
                ; the call
                ld      ix, (cur)
                ld      a, (cur+6)
                ld      l, a
                ld      a, (cur+5)
                ld      h, a
                push    hl
                ld      bc, $B1C1
                ld      de, $D1E1
                ld      hl, $4151
                xor     a
                ld      (injc), a
                ld      a, (cur+7)
                bit     3, a
                jr      z, c_noinj
                ld      a, $C3
                ld      ($FD9F), a
                ld      hl, INJ
                ld      ($FDA0), hl
c_noinj:
                ld      hl, LOGB
                ld      a, (cur+7)
                bit     4, a
                jr      nz, c_log
                ld      hl, 0
c_log:
                ld      (LOGP), hl
                ld      hl, $4151
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
                ld      (rsave+13), a
                pop     hl
                ld      (rsave), hl
                pop     hl
                ld      (rsave+3), hl
                pop     hl
                ld      (rsave+5), hl
                pop     hl
                ld      (rsave+7), hl
                pop     hl
                ld      (rsave+9), hl
                pop     hl
                ld      (rsave+11), hl
                ld      hl, (LOGP)
                ld      (logend), hl
                ld      hl, 0
                ld      (LOGP), hl
                ld      a, $C9
                ld      ($FD9F), a
                ld      ($FDA0), a
                ld      ($FDA1), a
                ; the VDP state, straight into the record
                ld      hl, (ptr)
                ld      de, 88
                add     hl, de
                ld      (SNAPP), hl
                call    SNAPFN
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
                ld      hl, rsave+3
                ld      bc, 10
                ldir
                ld      a, (rsave+13)
                rrca
                rrca
                and     1
                ld      (de), a
                inc     de
                inc     de
                ld      hl, cells
                ld      b, 16
c_cell:
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
                djnz    c_cell
                ld      hl, $F3DF
                ld      bc, 8
                ldir
                ld      hl, $FFE7
                ld      bc, 16
                ldir
                ld      c, $20
                call    rdblk                   ; +56..+68
                call    mode_rd
                ld      (de), a                 ; +69
                inc     de
                inc     de
                inc     de
                ld      c, $30
                call    rdblk                   ; +72..+84
                ; the name table: base / row length from SCRMOD and RG0SAV
                ld      a, ($FCAF)
                ld      hl, ($F3B3)             ; TXTNAM
                ld      c, 40
                or      a
                jr      nz, c_n1
                ld      a, ($F3DF)
                and     4
                jr      z, c_nset
                ld      c, 80
                jr      c_nset
c_n1:
                ld      hl, ($F3BD)             ; T32NAM
                ld      c, 32
                dec     a
                jr      z, c_nset
                ld      hl, 0
                ld      c, 80
c_nset:
                ld      (nbase), hl
                ld      a, c
                ld      (rlen), a
                ld      hl, (ptr)
                ld      de, 368
                add     hl, de
                ld      de, (nbase)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), a
                ld      hl, (ptr)
                ld      de, 208
                add     hl, de
                ex      de, hl
                ld      hl, (nbase)
                call    rd80
                ld      hl, (ptr)
                ld      bc, 288
                add     hl, bc
                ex      de, hl
                ld      a, ($F3B1)              ; CRTCNT
                dec     a
                ld      b, a
                ld      hl, (nbase)
                ld      a, (rlen)
                ld      c, a
                ld      a, b
                ld      b, 0
                or      a
                jr      z, c_rw
c_ra:
                add     hl, bc
                dec     a
                jr      nz, c_ra
c_rw:
                call    rd80
                call    tail
                ld      hl, (ptr)
                ld      bc, RECLEN-1
                add     hl, bc
                ld      (hl), $5E
                inc     hl
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; 80 bytes of VRAM from HL (< $4000) to DE
rd80:
                push    de
                ld      a, 0
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                pop     de
                ld      b, 80
rd80l:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    rd80l
                ret

; HL := table + 13 * A
pick13:
                or      a
                ret     z
                ld      de, 13
pk:
                add     hl, de
                dec     a
                jr      nz, pk
                ret

; write the 13 nibbles at HL through WRTCLK, C = block base ($20 / $30); $FF = skip
wrblk:
                ld      b, 13
wb:
                ld      a, (hl)
                cp      $FF
                jr      z, wb_s
                push    bc
                push    hl
                ld      ix, $01F9
                call    EXTROM
                di
                pop     hl
                pop     bc
wb_s:
                inc     hl
                inc     c
                djnz    wb
                ret

; read 13 registers of the block C ($20 / $30) through the ports into DE.., DE advanced
rdblk:
                ld      b, 0
rb:
                ld      a, c
                or      b
                ld      (cc), a
                push    bc
                call    port_rd
                pop     bc
                ld      (de), a
                inc     de
                inc     b
                ld      a, b
                cp      13
                jr      nz, rb
                ret

mode_rd:
                ld      a, 13
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ret
mode_wr:
                push    af
                ld      a, 13
                out     ($B4), a
                pop     af
                out     ($B5), a
                ret
; the register (cc) read through the ports; MODE's block bits := its block for the read, then put back
port_rd:
                call    mode_rd
                push    af
                and     $0C
                ld      b, a
                ld      a, (cc)
                rrca
                rrca
                rrca
                rrca
                and     3
                or      b
                call    mode_wr
                ld      a, (cc)
                and     $0F
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ld      b, a
                pop     af
                call    mode_wr
                ld      a, b
                ret

; the record's tail: keys injected, the port log, the work-area diff / snapshot
tail:
                ld      ix, (ptr)
                ld      de, 384
                add     ix, de
                ld      a, (injc)
                ld      (ix+1), a
                ld      hl, (logend)
                ld      a, h
                or      l
                jr      z, t_nolog
                ld      de, LOGB
                or      a
                sbc     hl, de
t_nolog:
                ld      (ix+2), l
                ld      (ix+3), h
                ld      (ix+4), $FF
                ld      (ix+5), $FF
                ld      a, h
                or      l
                jr      z, t_snap
                ; search "SXA" in LOGB .. logend
                ld      hl, LOGB
t_s:
                push    hl
                ld      de, (logend)
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, t_copy0
                ld      a, (hl)
                cp      'S'
                jr      nz, t_sn
                inc     hl
                ld      a, (hl)
                dec     hl
                cp      'X'
                jr      nz, t_sn
                inc     hl
                inc     hl
                ld      a, (hl)
                dec     hl
                dec     hl
                cp      'A'
                jr      z, t_hit
t_sn:
                inc     hl
                jr      t_s
t_hit:
                push    hl
                ld      de, LOGB
                or      a
                sbc     hl, de
                ld      (ix+4), l
                ld      (ix+5), h
                pop     hl
                ld      de, -8
                add     hl, de
                jr      t_copy
t_copy0:
                ld      hl, LOGB
t_copy:
                push    ix
                pop     de
                ld      a, 8
                add     a, e
                ld      e, a
                jr      nc, t_c1
                inc     d
t_c1:
                ld      bc, 32
                ldir
t_snap:
                ld      a, (cur+7)
                bit     2, a
                jr      z, t_nodiff
                ld      (ix+0), 0
                push    ix
                pop     de
                ld      hl, 40
                add     hl, de
                ex      de, hl                  ; DE = the diff list
                ld      hl, $F380
                ld      bc, SNAPA
t_d:
                ld      a, (bc)
                cp      (hl)
                jr      z, t_dn
                ld      a, (ix+0)
                inc     (ix+0)
                cp      21
                jr      nc, t_dn
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                ld      a, (bc)
                ld      (de), a
                inc     de
                ld      a, (hl)
                ld      (de), a
                inc     de
t_dn:
                inc     bc
                inc     hl
                ld      a, h
                or      l
                jr      nz, t_d
t_nodiff:
                ld      a, (cur+7)
                bit     1, a
                ret     z
                ld      hl, $F380
                ld      de, SNAPA
                ld      bc, $0C80               ; $F380-$FFFF
                ldir
                ret

; H.TIMI: queue 'K' when KEYBUF is empty, at most 4 times (copied to INJ)
injsrc:
                push    af
                push    hl
                ld      a, (injc)
                cp      4
                jr      nc, inj_x
                ld      hl, (PUTPNT)
                ld      a, (GETPNT)
                cp      l
                jr      nz, inj_x
                ld      a, (GETPNT+1)
                cp      h
                jr      nz, inj_x
                ld      (hl), 'K'
                inc     hl
                ld      a, l
                cp      $18
                jr      nz, inj_p
                ld      a, h
                cp      $FC
                jr      nz, inj_p
                ld      hl, $FBF0
inj_p:
                ld      (PUTPNT), hl
                ld      hl, injc
                inc     (hl)
inj_x:
                pop     hl
                pop     af
                ret
injend:

cells:
                dw      $FCAF, $FCB0, $F3AE, $F3AF, $F3B0, $F3B1, $F3B2, $F3DE
                dw      $F3DB, $F3E9, $F3EA, $F3EB, $F3DC, $F3DD, $F3F8, $F3FA

fkeys:
                db      "AAAAAAAAAAAAAAA", 0
                db      "BBBBBBBBBBBBBBB", 0
                db      "CCCCCCCCCCCCCCC", 0
                db      "DDDDDDDDDDDDDDD", 0
                db      "EEEEEEEEEEEEEEE", 0
                db      "FFFFFFFFFFFFFFF", 0
                db      "GGGGGGGGGGGGGGG", 0
                db      "HHHHHHHHHHHHHHH", 0
                db      "IIIIIIIIIIIIIII", 0
                db      "JJJJJJJJJJJJJJJ", 0

; block 2, registers 0-12: ID, adjust X, adjust Y, mode (b0 SCREEN, b1 interlace), width lo, width hi, FORCLR,
; BAKCLR, BDRCLR, b0 key / b1 click / b2 printer / b3 cassette, beep, title colour, country
sets:
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ;  0 as found
                db      $FF,  3,$0E,  3,$0E,  1,  6,  7,  8,  0,$FF,$FF,$FF   ;  1 SCREEN 1 IL, width 30, 6/7/8, key 0
                db      $FF,  0,  0,  0,  0,  5,$0C,  3,  9,  1,$FF,$FF,$FF   ;  2 SCREEN 0, width 80, 12/3/9, key 1
                db      $FF,  0,  0,  0,  5,  2,$0A,$0B,$0D,  3,$FF,$FF,$FF   ;  3 SCREEN 0, width 37, 10/11/13, key 1 click 1
                db      $FF,  5,  0,  0,  4,  6,  2,  5,  4,$0E,$FF,$FF,$FF   ;  4 SCREEN 0, width 100, 2/5/4, key 0 + b1-b3
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,  5,$FF,$FF,$FF   ;  5 (after 2) + printer bit
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$0D,$FF,$FF,$FF   ;  6 + cassette bit
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$0A,$FF,$FF   ;  7 + beep $A
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,  3,$FF   ;  8 + title colour 3
                db        5,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ;  9 + ID 5
                db      $0A,  0,  0,  1,  2,  1,  6,  7,  8,  0,  0,  0,$FF   ; 10 ID $A, SCREEN 1 width 18, 6/7/8
                db        5,  0,  0,  1,  2,  1,  6,  7,  8,  0,  0,  0,$FF   ; 11 the same with ID 5
; block 3, registers 0-12: ID, then 6 characters as low / high nibble
sets3:
                db      $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; 0 as found
                db      0, 3,5, 8,5, 1,4, 0,0, 0,0, 0,0                     ; 1 ID 0 (title) "SXA"
                db      2, 3,5, 8,5, 1,4, 0,0, 0,0, 0,0                     ; 2 ID 2 (prompt) "SXA"
                db      0, 3,5, 8,5, 1,4, 3,5, 8,5, 1,4                     ; 3 ID 0 (title) "SXASXA"
                db      1, 3,5, 8,5, 1,4, 0,0, 0,0, 0,0                     ; 4 ID 1 (password) "SXA"

; entry, previous mode, block-2 set, block-3 set, A, F, flags (b0 EI, b1 snap, b2 diff, b3 inject keys, b4 log $98)
cases:
                dw      $0185
                db      0, 0, 0, $00, $00, $00  ;  0 SDFSCR, as found, from SCREEN 0
                dw      $0185
                db      5, 0, 0, $00, $00, $00  ;  1 SDFSCR, as found, from SCREEN 5
                dw      $0185
                db      0, 1, 0, $00, $00, $00  ;  2 SDFSCR, set 1 (SCREEN 1 width 30 key off)
                dw      $0185
                db      0, 1, 0, $00, $00, $01  ;  3 SDFSCR, set 1, EI
                dw      $0185
                db      0, 3, 0, $00, $00, $01  ;  4 SDFSCR, set 3 (width 37), EI
                dw      $0185
                db      5, 3, 0, $00, $00, $00  ;  5 SDFSCR, set 3, from SCREEN 5
                dw      $0185
                db      0, 2, 0, $00, $00, $00  ;  6 SDFSCR, set 2 (width 80 key on), A 0 F 0
                dw      $0185
                db      0, 2, 0, $00, $01, $00  ;  7 SDFSCR, set 2, carry
                dw      $0185
                db      0, 2, 0, $00, $40, $00  ;  8 SDFSCR, set 2, Z
                dw      $0185
                db      0, 2, 0, $FF, $00, $01  ;  9 SDFSCR, set 2, A $FF, EI
                dw      $0185
                db      1, 4, 0, $00, $00, $00  ; 10 SDFSCR, set 4 (width 100) from SCREEN 1
                dw      $0185
                db      0, 2, 0, $00, $00, $02  ; 11 SDFSCR, set 2, snapshot
                dw      $0185
                db      0, 0, 0, $00, $00, $06  ; 12 SDFSCR, the same again: the diff is the noise
                dw      $0185
                db      0, 5, 0, $00, $00, $06  ; 13 SDFSCR, + printer bit
                dw      $0185
                db      0, 6, 0, $00, $00, $06  ; 14 SDFSCR, + cassette bit
                dw      $0185
                db      0, 7, 0, $00, $00, $06  ; 15 SDFSCR, + beep $A
                dw      $0185
                db      0, 8, 0, $00, $00, $06  ; 16 SDFSCR, + title colour 3
                dw      $0185
                db      0, 9, 0, $00, $00, $06  ; 17 SDFSCR, + ID 5
                dw      $0185
                db      0,10, 0, $00, $00, $02  ; 18 SDFSCR, set 10 (ID $A, SCREEN 1 width 18)
                dw      $0185
                db      0,11, 0, $00, $00, $04  ; 19 SDFSCR, set 11 (the same, ID 5)
                dw      0

                ds      $8000 - $, $FF
