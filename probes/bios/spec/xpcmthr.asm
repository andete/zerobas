; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMTHR -- D-TRSPEC, docs/turbor/main/PCMREC.md: PCMREC ($0189) with a threshold (A bits 6-3 = 0001) and NO key, in
; openMSX with nothing plugged into the PCM's input -- a case that may never return, so it has a run of its own (one
; such case per run: the harness has no way out of a call that does not return). The engine, record and decoder are
; xpcmrec.asm's (scratchpad/xpcmrec_decode.py). Two references (--row turbor: FS-A1GT vs FS-A1ST).
; Set-up at INIT (Z80): VRAM $04000-$0403F := $5A (OUT $99 with R#14).
; Per case (table `cases`: start, A, HL, BC, D, E, keys): CHGCPU(start), DI; the buffer $8000-$80FF := $5A; the VDP
; interrupt off (R#1 bit 5, from RG1SAV; back after the case -- no keyboard scan, no timer interrupt); the keyboard
; matrix := the case's keys through @keyset (none; CTRL+STOP; STOP alone), held from before the call to after it;
; arm the port logs ($A4 into a 4 KB scratch at $C000 and $A5 into one at $D000 -- only their counts and first 64 /
; 16 bytes are kept --, $E4, $E5, $A7); cpusnap; every register from the entry table (A, HL, BC, D, E per case, F $00, the rest distinct garbage);
; CALL $0189; cpusnap; dump every register; DI; keys released; then R#6, IN $A4 / $A5, the buffer's first 48 bytes.
; Record (RECLEN = $100 from CAP+16 = $8811): +0 case, +1 start, +2 A, +3 keys, +4..+9 HL, BC, D, E in, +10 R#6
; before, +11 $5A, +12..+21 two cpusnaps (cpu, time us x4), +22..+47 the dump (as xchgcpu.asm: [($FFFF) cpl, $A8],
; IFF 2nd, IFF 1st, HL', DE', BC', AF', IY, IX, HL, DE, BC, AF), +48 / +50 the $A4 / $A5 log counts (LE), +52 R#6
; after, +53 IN $A4, +54 IN $A5, +55 / +56 / +57 the $E4 / $E5 / $A7 log counts, +58..+73 the $A5 log (16), +74..+81
; $E4 (8), +82..+89 $E5 (8), +90..+97 $A7 (8), +98..+145 the buffer $8000-$802F after, +146..+209 the first 64 bytes
; of the $A4 log. CAP+0 = cases done.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmthr.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM and I/O ports. No ROM byte read.
;
; @cap 8800
; @caplen 0400
; @timeout 60
; @vram 4000:40
; @cpusnap 4100 E908
; @keyset 4110 E960
; @portlog A4 E90E 4118
; @portlog A5 E91E 4118
; @portlog E4 E92E 4118
; @portlog E5 E93E 4118
; @portlog A7 E94E 4118

CHGCPU  equ     $0180
CALLPCM equ     $0189                   ; PCMREC
DONE    equ     $8800
CAP     equ     $8801
REC     equ     CAP+16
RECLEN  equ     $100
BUF     equ     $8000
A4LOG   equ     $C000
A5LOG   equ     $D000

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E904
CSPTR   equ     $E908
CIDX    equ     $E90B
TP      equ     $E90C
LGA4    equ     $E90E
LGA5    equ     $E91E
LGE4    equ     $E92E
LGE5    equ     $E93E
LGA7    equ     $E94E
KEYS    equ     $E960                   ; @keyset's 11-byte matrix (bit set = pressed)
ENTBL   equ     $E980
RDUMP   equ     $E9A0
RDEND   equ     $E9BA
CUR     equ     $E9E0

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                jp      main

                ds      $4100-$, 0
snap:           ret
                ds      $4110-$, 0
keyset:         ret
                ds      $4118-$, 0
armlog:         ret

main:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FE
                ld      (hl), 0
                ldir
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                ld      (LGA7), hl
                call    armlog
                ld      hl, KEYS
                ld      b, 11
k_clr:          ld      (hl), 0
                inc     hl
                djnz    k_clr
                call    keyset
                ; VRAM $04000-$0403F := $5A
                ld      a, 1
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                xor     a
                out     ($99), a
                ld      a, $40
                out     ($99), a
                ld      b, 64
                ld      a, $5A
v_lp:           out     ($98), a
                djnz    v_lp
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
                ld      bc, 9
                ldir
                ld      (TP), hl
                ; CUR: +0 start, +1 A, +2 HL, +4 BC, +6 D, +7 E, +8 keys (0 none, 1 CTRL+STOP, 2 STOP, 3 CTRL)
                ld      a, (CUR)
                call    CHGCPU
                di
                ld      ix, (PTR)
                ld      a, (CIDX)
                ld      (ix+0), a
                ld      a, (CUR)
                ld      (ix+1), a
                ld      a, (CUR+1)
                ld      (ix+2), a
                ld      a, (CUR+8)
                ld      (ix+3), a
                push    ix
                pop     de
                ld      hl, 4
                add     hl, de
                ex      de, hl
                ld      hl, CUR+2
                ld      bc, 6
                ldir
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+10), a
                ld      (ix+11), $5A
                ; the buffer
                ld      hl, BUF
                ld      de, BUF+1
                ld      bc, 255
                ld      (hl), $5A
                ldir
                ; the VDP interrupt off
                ld      a, ($F3E0)
                and     $DF
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; keys
                ld      a, (CUR+8)
                call    setkeys
                call    keyset
                ; logs, snaps
                push    ix
                pop     hl
                ld      de, 12
                add     hl, de
                ld      (CSPTR), hl
                ld      hl, A4LOG
                ld      (LGA4), hl
                ld      hl, A5LOG
                ld      (LGA5), hl
                push    ix
                pop     hl
                ld      de, 74
                add     hl, de
                ld      (LGE4), hl
                ld      de, 8
                add     hl, de
                ld      (LGE5), hl
                add     hl, de
                ld      (LGA7), hl
                ; registers
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+1)
                ld      (ENTBL+13), a           ; A (F $00)
                ld      hl, (CUR+4)
                ld      (ENTBL+14), hl          ; BC
                ld      a, (CUR+7)
                ld      (ENTBL+16), a           ; E
                ld      a, (CUR+6)
                ld      (ENTBL+17), a           ; D
                ld      hl, (CUR+2)
                ld      (ENTBL+18), hl          ; HL
                call    snap
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
                call    CALLPCM
                call    snap
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
                ; keys released, the VDP interrupt back
                xor     a
                call    setkeys
                call    keyset
                ld      a, ($F3E0)
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; log counts
                ld      ix, (PTR)
                ld      hl, (LGA4)
                ld      de, A4LOG
                or      a
                sbc     hl, de
                ld      (ix+48), l
                ld      (ix+49), h
                ld      hl, (LGA5)
                ld      de, A5LOG
                or      a
                sbc     hl, de
                ld      (ix+50), l
                ld      (ix+51), h
                push    ix
                pop     de
                ld      a, (LGE4)
                sub     e
                sub     74
                ld      (ix+55), a
                ld      a, (LGE5)
                sub     e
                sub     82
                ld      (ix+56), a
                ld      a, (LGA7)
                sub     e
                sub     90
                ld      (ix+57), a
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                ld      (LGA7), hl
                ; dump
                ld      hl, 22
                add     hl, de
                ex      de, hl
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+52), a
                in      a, ($A4)
                ld      (ix+53), a
                in      a, ($A5)
                ld      (ix+54), a
                ; the buffer's first 48 bytes, the A4 log's first 64
                push    ix
                pop     hl
                ld      de, 98
                add     hl, de
                ex      de, hl
                ld      hl, BUF
                ld      bc, 48
                ldir
                ld      hl, A4LOG
                ld      bc, 64
                ldir
                push    ix
                pop     hl
                ld      de, 58
                add     hl, de
                ex      de, hl
                ld      hl, A5LOG
                ld      bc, 16
                ldir
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

; KEYS := the matrix for code A (0 none, 1 CTRL+STOP, 2 STOP, 3 CTRL): CTRL = row 6 bit 1, STOP = row 7 bit 4
setkeys:
                ld      b, 0
                ld      c, 0
                cp      1
                jr      nz, sk_2
                ld      b, $02
                ld      c, $10
sk_2:           cp      2
                jr      nz, sk_3
                ld      c, $10
sk_3:           cp      3
                jr      nz, sk_w
                ld      b, $02
sk_w:           ld      a, b
                ld      (KEYS+6), a
                ld      a, c
                ld      (KEYS+7), a
                ret

ent_src:        dw      $1A1B, $1C1D            ; IX, IY
                dw      $2829, $2A2B, $2C2D, $2E2F ; AF', BC', DE', HL'
                dw      $0000, $3A3B, $3C3D, $3E3F ; AF (A per case, F $00), BC, DE, HL (per case)

; start, A, HL, BC, D, E, keys
cases:
                db      $82, $00
                dw      BUF, 16
                db      0, 0, 0                 ; 0: R800 DRAM, rate code 0, RAM, 16 (as xpcmrec's case 0)
                db      $82, $08
                dw      BUF, 16
                db      0, 0, 0                 ; 1: threshold 1, no key
                db      $EE

                ds      $8000-$, $FF
