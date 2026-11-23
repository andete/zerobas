; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMPLY2 -- D-TRSPEC goldfish pass 1, docs/turbor/main/PCMPLY.md: xpcmply.asm (same code, same record, same decoder:
; scratchpad/xpcmply_decode.py) with a new case table, on the two turbo R references (--row turbor: FS-A1GT vs
; FS-A1ST). Added data: P4 = `10 00 05 20` (xpcmcmp.asm's case 0) at RAM $8300 (page 2) and at VRAM $08000.
; Added per-case field (the table's 12th byte, unused in xpcmply): non-zero = $FCB1 := it after the start CHGCPU.
;   0-4   the $00 code outside R800 DRAM / RAM / rate code 0: P4 from VRAM (R800 DRAM), from the Z80, from R800 ROM,
;         at rate code 3 (R800 DRAM), and from the Z80 at rate code 3 from VRAM;
;   5     from the Z80 with $FCB1 = $82 (the LED bit set in CHGCPU's copy): what the internal switch writes to $A7
;         and leaves in $FCB1;
;   6-7   from the Z80 entered with F = $FF; entered EI;
;   8-13  R800 DRAM, P4, entry F = $00, $44, $40, $04, $28, $FF (A = 0): what return F bits 5 / 3 follow;
;   14-15 R800 DRAM, entry F $44 with P1 (64 bytes, no $00), entry F $00 with P1 length 4: data / length vs entry F.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmply2.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM and I/O ports. No ROM byte read: every
; source a case plays is this probe's own data in page 2 RAM or VRAM -- never page 0 / 1.
;
; @cap 8400
; @caplen 5000
; @timeout 150
; @vram 4000:40
; @vram 14000:40
; @vram FFE0:40
; @vram 0000:20
; @vram 8000:10
; @cpusnap 4100 E908
; @cpusnap 4108 E908
; @portlog A4 E90E 4118
; @portlog A5 E91E 4118
; @portlog E4 E92E 4118
; @portlog E5 E93E 4118
; @portlog A7 E94E 4118

CHGCPU  equ     $0180
GETCPU  equ     $0183
PCMPLY  equ     $0186
DONE    equ     $8400
CAP     equ     $8401
REC     equ     CAP+16
RECLEN  equ     $200
P1      equ     $8000
P2      equ     $8100
P3      equ     $8200
P4      equ     $8300
P1C     equ     $E200                   ; P1[0-63] again, in page 3
WSAVE   equ     $D500
WBASE   equ     $F380
WLEN    equ     $FFFF-WBASE             ; $F380..$FFFE

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E904
CSPTR   equ     $E908                   ; @cpusnap's pointer word
CIDX    equ     $E90B
TP      equ     $E90C
LGA4    equ     $E90E                   ; @portlog pointer words
LGA5    equ     $E91E
LGE4    equ     $E92E
LGE5    equ     $E93E
LGA7    equ     $E94E
ENTBL   equ     $E960
RDUMP   equ     $E980
RDEND   equ     $E99A
CUR     equ     $E9E0

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                jp      main

; fixed addresses the harness breaks on
                ds      $4100-$, 0
snapB:          ret                     ; before the call
                ds      $4108-$, 0
snapA:          ret                     ; after the call
                ds      $4118-$, 0
armlog:         ret

main:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $4FFE
                ld      (hl), 0
                ldir
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                ld      (LGA7), hl
                call    armlog
                ; P1 = $10+i, 128 bytes
                ld      hl, P1
                ld      a, $10
                ld      b, 128
p1_lp:          ld      (hl), a
                inc     hl
                inc     a
                djnz    p1_lp
                ld      hl, p2src
                ld      de, P2
                ld      bc, 64
                ldir
                ld      hl, P1
                ld      de, P1C
                ld      bc, 64
                ldir
                ld      hl, P3
                ld      a, $90
                ld      b, 64
p3_lp:          ld      (hl), a
                inc     hl
                inc     a
                djnz    p3_lp
                ld      hl, P3+64
                ld      a, $50
                ld      b, 32
p4_lp:          ld      (hl), a
                inc     hl
                inc     a
                djnz    p4_lp
                ; VRAM (in the Z80, as at INIT): all := $55, 8 blocks of 16 KB
                ld      d, 0
vf_blk:
                ld      a, d
                rrca
                rrca
                and     $C0
                ld      h, a
                ld      l, 0
                ld      a, d
                rrca
                rrca
                and     1
                ld      e, a
                push    de
                ld      ix, fill55
                ld      b, 1
                call    vwr                     ; address set, one $55 written
                ld      bc, $3FFF
vf_lp:          ld      a, $55
                out     ($98), a
                dec     bc
                ld      a, b
                or      c
                jr      nz, vf_lp
                pop     de
                inc     d
                ld      a, d
                cp      8
                jr      nz, vf_blk
                ld      e, 0
                ld      hl, $4000
                ld      ix, P1
                ld      b, 64
                call    vwr
                ld      e, 1
                ld      hl, $4000
                ld      ix, P3
                ld      b, 64
                call    vwr
                ld      e, 0
                ld      hl, $0000
                ld      ix, P3+64
                ld      b, 32
                call    vwr
                ld      e, 0
                ld      hl, $FFE0
                ld      ix, $7FE0
                ld      b, 32
                call    vwr
                ld      e, 1
                ld      hl, $0000
                ld      ix, vtab
                ld      b, 32
                call    vwr
                ld      hl, p4src
                ld      de, P4
                ld      bc, 4
                ldir
                ld      e, 0
                ld      hl, $8000
                ld      ix, P4
                ld      b, 4
                call    vwr
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, cases
                ld      (TP), hl
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 12
                ldir
                ld      (TP), hl
                ; CUR: +0 start, +1 A, +2 F, +3 iff, +4 HL, +6 BC, +8 D, +9 E, +10 log
                ld      a, (CUR)
                call    CHGCPU
                di
                ld      a, (CUR+11)
                or      a
                jr      z, c_nofc
                ld      ($FCB1), a
c_nofc:
                ld      ix, (PTR)
                ld      a, (CIDX)
                ld      (ix+0), a
                ld      hl, (CUR)
                ld      (ix+1), l
                ld      (ix+2), h
                ld      hl, (CUR+2)
                ld      (ix+3), l
                ld      (ix+4), h
                ld      a, (CUR+10)
                ld      (ix+6), a
                ld      (ix+7), $5A
                ld      hl, (CUR+4)
                ld      (ix+50), l
                ld      (ix+51), h
                ld      hl, (CUR+6)
                ld      (ix+52), l
                ld      (ix+53), h
                ld      hl, (CUR+8)
                ld      (ix+54), l
                ld      (ix+55), h
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+5), a
                in      a, ($A5)
                ld      (ix+109), a
                ; work-area snapshot
                ld      hl, WBASE
                ld      de, WSAVE
                ld      bc, WLEN
                ldir
                ; the cpusnap pointer and the logs
                push    ix
                pop     hl
                ld      de, 34
                add     hl, de
                ld      (CSPTR), hl
                ld      a, (CUR+10)
                or      a
                jr      z, c_nolog
                push    ix
                pop     hl
                ld      de, 110
                add     hl, de
                ld      (LGA5), hl
                ld      de, 32
                add     hl, de
                ld      (LGE4), hl
                ld      de, 16
                add     hl, de
                ld      (LGE5), hl
                add     hl, de
                ld      (LGA7), hl
                push    ix
                pop     hl
                ld      de, 190
                add     hl, de
                ld      (LGA4), hl
c_nolog:
                ; registers
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+2)
                ld      (ENTBL+12), a           ; F
                ld      a, (CUR+1)
                ld      (ENTBL+13), a           ; A
                ld      hl, (CUR+6)
                ld      (ENTBL+14), hl          ; BC
                ld      a, (CUR+9)
                ld      (ENTBL+16), a           ; E
                ld      a, (CUR+8)
                ld      (ENTBL+17), a           ; D
                ld      hl, (CUR+4)
                ld      (ENTBL+18), hl          ; HL
                ; no VDP interrupt during the case (R#1 bit 5 := 0; RG1SAV restored after): the call returns EI, and an
                ; interrupt taken right after it would add its handler to the timing
                ld      a, ($F3E0)
                and     $DF
                out     ($99), a
                ld      a, $81
                out     ($99), a
                call    snapB
                ld      a, (CUR+3)
                and     1
                jr      z, c_di
                ei
c_di:
                ld      (E_SP), sp
                ld      sp, ENTBL
                pop     ix
                pop     iy
                pop     af
                ex      af, af'
                pop     bc
                pop     de
                pop     hl
                exx
                pop     af
                pop     bc
                pop     de
                pop     hl
                ld      sp, (E_SP)
                call    PCMPLY
                call    snapA
                ld      (R_SP), sp
                ld      sp, RDEND
                push    af
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ex      af, af'
                push    af
                ex      af, af'
                exx
                push    bc
                push    de
                push    hl
                exx
                ld      a, i
                push    af
                ld      a, i
                push    af
                in      a, ($A8)
                ld      h, a
                ld      a, ($FFFF)
                cpl
                ld      l, a
                push    hl
                ld      sp, (R_SP)
                di
                ld      a, ($F3E0)
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; disarm the logs, keep their counts
                ld      ix, (PTR)
                ld      hl, (LGA4)
                ld      a, h
                or      l
                jr      z, c_n4
                push    ix
                pop     de
                or      a
                sbc     hl, de
                ld      de, 190
                or      a
                sbc     hl, de
                ld      (ix+56), l
                ld      (ix+57), h
                ld      hl, (LGA5)
                push    ix
                pop     de
                or      a
                sbc     hl, de
                ld      de, 110
                or      a
                sbc     hl, de
                ld      (ix+58), l
                ld      (ix+59), h
                push    ix
                pop     de
                ld      a, (LGE4)
                sub     e
                sub     142
                ld      (ix+105), a
                ld      a, (LGE5)
                sub     e
                sub     158
                ld      (ix+106), a
                ld      a, (LGA7)
                sub     e
                sub     174
                ld      (ix+107), a
c_n4:
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                ld      (LGA7), hl
                ; dump
                ld      hl, (PTR)
                ld      bc, 8
                add     hl, bc
                ex      de, hl
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      ix, (PTR)
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+44), a
                in      a, ($A4)
                ld      (ix+46), a
                in      a, ($A5)
                ld      (ix+47), a
                in      a, ($A7)
                ld      (ix+49), a
                ld      a, ($FCB1)
                ld      (ix+48), a
                ld      a, $5A
                call    GETCPU
                di
                ld      ix, (PTR)
                ld      (ix+45), a
                call    wdiff
                ; next
                ld      hl, (PTR)
                ld      bc, RECLEN
                add     hl, bc
                ld      (PTR), hl
                ld      hl, CIDX
                inc     (hl)
                ld      a, (hl)
                ld      (CAP), a
                jp      c_next

finish:
                ld      a, $82
                call    CHGCPU
                di
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; VRAM write: E = A16, HL = A15-A0, IX = source, B = count (DI, Z80)
vwr:
                ld      a, e
                and     1
                add     a, a
                add     a, a
                ld      c, a
                ld      a, h
                rlca
                rlca
                and     3
                or      c
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      $40
                out     ($99), a
v_lp:
                ld      a, (ix+0)
                out     ($98), a
                inc     ix
                djnz    v_lp
                ret

; compare $F380..$FFFE with the copy; up to 11 changes to +61, the count to +60
wdiff:
                ld      ix, (PTR)
                push    ix
                pop     hl
                ld      de, 61
                add     hl, de
                ex      de, hl                  ; DE = out
                ld      hl, WBASE
                ld      bc, WSAVE
                xor     a
                ld      (ix+60), a
w_lp:
                ld      a, (bc)
                cp      (hl)
                jr      z, w_same
                push    af
                ld      a, (ix+60)
                inc     a
                jr      z, w_full
                ld      (ix+60), a
                cp      12
                jr      nc, w_full
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
w_full:
                pop     af
w_same:
                inc     hl
                inc     bc
                ld      a, h
                cp      $FF
                jr      nz, w_lp
                ld      a, l
                cp      $FF
                jr      nz, w_lp
                ret

ent_src:        dw      $1A1B, $1C1D            ; IX, IY
                dw      $2829, $2A2B, $2C2D, $2E2F ; AF', BC', DE', HL'
                dw      $3839, $3A3B, $3C3D, $3E3F ; AF, BC, DE, HL (A, F, BC, D, E, HL per case)

p2src:
                db      $00,$00,$00,$00, $80,$80,$80,$80, $FF,$FF,$01,$02, $00,$03,$00,$7F
                db      $81,$FE,$40,$C0, $00,$00,$10,$20, $80,$00,$80,$00, $FF,$00,$FF,$00
                db      $55,$AA,$00,$00, $00,$00,$00,$00, $00,$00,$00,$00, $11,$22,$33,$44
                db      $80,$81,$7F,$7E, $00,$01,$00,$02, $03,$00,$04,$05, $06,$07,$08,$09
p4src:          db      $10, $00, $05, $20
fill55:         db      $55
vtab:           ; VRAM $10000: $E0+i
                db      $E0,$E1,$E2,$E3,$E4,$E5,$E6,$E7,$E8,$E9,$EA,$EB,$EC,$ED,$EE,$EF
                db      $F0,$F1,$F2,$F3,$F4,$F5,$F6,$F7,$F8,$F9,$FA,$FB,$FC,$FD,$FE,$FF

; start, A, F, iff (bit 0 EI), HL, BC, D, E, log, pad
cases:
                db      $82, $80, $00, 0
                dw      $8000, 4
                db      0, 0, 1, $00            ; 0: P4 from VRAM $08000, R800 DRAM
                db      $80, $00, $00, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 1: P4, the Z80
                db      $81, $00, $00, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 2: P4, R800 ROM
                db      $82, $03, $00, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 3: P4, rate code 3
                db      $80, $83, $00, 0
                dw      $8000, 4
                db      0, 0, 1, $00            ; 4: P4 from VRAM, the Z80, rate code 3
                db      $00, $00, $00, 0
                dw      P4, 4
                db      0, 0, 1, $82            ; 5: the Z80, $FCB1 := $82
                db      $80, $00, $FF, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 6: the Z80, F $FF
                db      $80, $00, $00, 1
                dw      P4, 4
                db      0, 0, 1, $00            ; 7: the Z80, EI
                db      $82, $00, $00, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 8: R800 DRAM, F $00
                db      $82, $00, $44, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 9: R800 DRAM, F $44
                db      $82, $00, $40, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 10: R800 DRAM, F $40
                db      $82, $00, $04, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 11: R800 DRAM, F $04
                db      $82, $00, $28, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 12: R800 DRAM, F $28
                db      $82, $00, $FF, 0
                dw      P4, 4
                db      0, 0, 1, $00            ; 13: R800 DRAM, F $FF
                db      $82, $00, $44, 0
                dw      P1, 64
                db      0, 0, 1, $00            ; 14: P1 64, F $44
                db      $82, $00, $00, 0
                dw      P1, 4
                db      0, 0, 1, $00            ; 15: P1 4, F $00
                db      $EE

                ds      $7FE0-$, $FF
xtab:           ; $7FE0: $A0+i
                db      $A0,$A1,$A2,$A3,$A4,$A5,$A6,$A7,$A8,$A9,$AA,$AB,$AC,$AD,$AE,$AF
                db      $B0,$B1,$B2,$B3,$B4,$B5,$B6,$B7,$B8,$B9,$BA,$BB,$BC,$BD,$BE,$BF
