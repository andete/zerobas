; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMPLY -- D-TRSPEC, docs/turbor/main/PCMPLY.md: the turbo R main ROM's PCMPLY ($0186) on the two turbo R
; references (--row turbor: FS-A1GT vs FS-A1ST).
; Set-up at INIT (Z80, as the boot leaves it): P1 = $10+i (128 bytes) at RAM $8000, P2 (a 64-byte table with runs of
; $00 / $80 / $FF, `p2src`) at RAM $8100, P3 = $90+i (64) at $8200 and $50+i (32) at $8240, P1[0-63] again at $E200
; (page 3); this cartridge holds $A0+i (32) at $7FE0. VRAM: all 128 KB := $55 (no $00 byte anywhere: PCMPLY treats $00 as a
; compression code, xpcmcmp.asm), then $04000 := P1[0-63], $14000 := P3, $0FFE0 := $A0+i (32), $10000 := $E0+i (32),
; $00000 := $50+i (32) (OUT $99 with R#14, in the Z80, before any case). The long cases (length 0, length bit 16)
; play VRAM, so they never run through page 0.
; Per case (table `cases`: start, A, F, iff, HL, BC, D, E, log): CHGCPU(start) (the published way to a CPU mode),
; DI; S1990 R#6, IN $A5; copy the work area $F380-$FFFE to $D500; arm the port logs ($A4, $A5, and $E4 / $E5 -- the
; S1990 -- and $A7; only when log = 1);
; the VDP interrupt off (R#1 bit 5, from RG1SAV; back after the dump); cpusnap B; every register from the entry table (A, F, HL, BC, D, E per case, the rest distinct garbage); DI or EI;
; CALL $0186; cpusnap A; dump every register; DI; disarm; then R#6, GETCPU, IN $A4 / $A5 / $A7, $FCB1, the
; work-area cells that changed.
; Length 0 and D = $FF (VRAM) are in xpcmstop.asm, under CTRL+STOP: neither returned within 140 s of emulated time.
; Record (RECLEN = $200 from CAP+16 = $8411): +0 case, +1 start, +2 A, +3 F, +4 iff, +5 R#6 before, +6 log, +7 $5A,
; +8..+33 the dump (as xchgcpu.asm: [($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL', DE', BC', AF', IY, IX, HL, DE, BC,
; AF), +34..+43 two cpusnaps (before / after the call: cpu, time us x4), +44 R#6 after, +45 GETCPU's A, +46 IN $A4,
; +47 IN $A5, +48 $FCB1, +49 IN $A7, +50..+55 HL, BC, D, E in, +56 / +58 the $A4 / $A5 log byte counts (LE), +60 the
; work-area change count, +61..+104 up to 11 changes (lo, hi, before, after), +105 / +106 / +107 the $E4 / $E5 / $A7
; log counts, +109 IN $A5 before, +110..+141 the $A5 log (32), +142 / +158 / +174 the $E4 / $E5 / $A7 logs (16 each),
; +190..+511 the $A4 log (322). CAP+0 = cases done.
; NO SOURCE IN PAGE 1 (or 0): a first run (not kept) played this cartridge's $6000 and a span crossing $7FFF / $8000,
; and the $A4 log did NOT hold the cartridge's bytes -- page 1 is switched away from the caller's slot during the
; call, so a page-1 source plays another slot's content (a ROM, which the clean room does not read). Those cases and
; their log were removed and the log discarded. The $A0+i table at $7FE0 only feeds VRAM.
; A bits 6-3: a first run with A = $08 (and one with A = $7C) never returned: one $80, the first sample, then nothing
; for 140 s of emulated time, so a hung case ends the run -- those values are in xpcmstop.asm, under CTRL+STOP.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmply.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM and I/O ports. No ROM byte read: every
; source a case plays is this probe's own data (RAM, VRAM or this cartridge) -- never page 0.
;
; @cap 8400
; @caplen 5000
; @timeout 150
; @vram 4000:40
; @vram 14000:40
; @vram FFE0:40
; @vram 0000:20
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
fill55:         db      $55
vtab:           ; VRAM $10000: $E0+i
                db      $E0,$E1,$E2,$E3,$E4,$E5,$E6,$E7,$E8,$E9,$EA,$EB,$EC,$ED,$EE,$EF
                db      $F0,$F1,$F2,$F3,$F4,$F5,$F6,$F7,$F8,$F9,$FA,$FB,$FC,$FD,$FE,$FF

; start, A, F, iff (bit 0 EI), HL, BC, D, E, log, pad
cases:
                db      $82, $00, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 0: R800 DRAM, rate code 0, RAM, 64
                db      $82, $01, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 1
                db      $82, $02, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 2
                db      $82, $03, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 3
                db      $82, $00, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 4: 128 samples (timing against 0-3)
                db      $82, $01, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 5
                db      $82, $02, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 6
                db      $82, $03, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 7
                db      $82, $00, $00, 0
                dw      P2, 64
                db      0, 0, 0, 0              ; 8: P2 (runs of $00 / $80 / $FF; no log -- xpcmcmp.asm has the detail)
                db      $82, $80, $00, 0
                dw      $4000, 64
                db      0, 0, 1, 0              ; 9: VRAM $04000 (P1)
                db      $82, $80, $00, 0
                dw      $4000, 64
                db      0, 1, 1, 0              ; 10: VRAM, E = 1: $14000 (P2)
                db      $82, $04, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 11: A bit 2 (PCMREC's compression bit)
                db      $82, $83, $00, 0
                dw      $4000, 64
                db      0, 0, 1, 0              ; 12: VRAM, rate code 3
                db      $82, $00, $00, 0
                dw      P1C, 64
                db      0, 0, 1, 0              ; 13: RAM in page 3 ($E200, a copy of P1)
                db      $82, $00, $00, 0
                dw      P1, 2
                db      0, 0, 1, 0              ; 14: length 2
                db      $82, $80, $00, 0
                dw      $4000, 2
                db      0, 0, 1, 0              ; 15: VRAM, length 2
                db      $82, $03, $00, 0
                dw      P1, 1
                db      0, 0, 1, 0              ; 16: length 1
                db      $82, $80, $00, 0
                dw      $4000, 64
                db      1, 0, 0, 0              ; 17: VRAM $04000, D = 1 (length bit 16): $10040 (no log; timing)
                db      $82, $80, $00, 0
                dw      $FFE0, 64
                db      0, 0, 1, 0              ; 18: VRAM $0FFE0, crosses $0FFFF / $10000
                db      $82, $00, $00, 1
                dw      P1, 64
                db      0, 0, 1, 0              ; 19: entered EI
                db      $82, $01, $FF, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 20: F $FF
                db      $80, $00, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 21: Z80
                db      $80, $01, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 22
                db      $80, $02, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 23
                db      $80, $03, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 24
                db      $80, $03, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 25: Z80, 128
                db      $81, $00, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 26: R800 ROM
                db      $81, $03, $00, 0
                dw      P1, 64
                db      0, 0, 1, 0              ; 27
                db      $81, $00, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 28
                db      $80, $80, $00, 0
                dw      $4000, 64
                db      0, 0, 1, 0              ; 29: Z80, VRAM $04000
                db      $82, $00, $00, 0
                dw      P1, 64
                db      $FE, $FE, 1, 0          ; 30: RAM, D = E = $FE (bit 0 clear, the rest set)
                db      $82, $80, $00, 0
                dw      $4000, 64
                db      2, 0, 0, 0              ; 31: VRAM, D = 2 (bit 0 clear; no log; timing)
                db      $82, $80, $00, 0
                dw      $3FE0, 64
                db      0, 0, 1, 0              ; 32: VRAM $03FE0, crosses $03FFF / $04000
                db      $82, $80, $00, 0
                dw      $4000, 64
                db      0, $FE, 1, 0            ; 33: VRAM, E = $FE (bit 0 clear)
                db      $80, $00, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 34: Z80, rate code 0, 128
                db      $80, $01, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 35: Z80, rate code 1, 128
                db      $80, $02, $00, 0
                dw      P1, 128
                db      0, 0, 1, 0              ; 36: Z80, rate code 2, 128
                db      $EE

                ds      $7FE0-$, $FF
xtab:           ; $7FE0: $A0+i
                db      $A0,$A1,$A2,$A3,$A4,$A5,$A6,$A7,$A8,$A9,$AA,$AB,$AC,$AD,$AE,$AF
                db      $B0,$B1,$B2,$B3,$B4,$B5,$B6,$B7,$B8,$B9,$BA,$BB,$BC,$BD,$BE,$BF
