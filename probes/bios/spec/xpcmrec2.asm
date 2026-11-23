; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMREC2 -- D-TRSPEC goldfish pass 1, docs/turbor/main/PCMREC.md: xpcmrec.asm (same code and record; decoded by
; scratchpad/xpcmrec_decode.py --entryf) with one more per-case field, the entry F (the table's 10th byte; the record
; keeps it at +210), and a new case table, on the two turbo R references (--row turbor: FS-A1GT vs FS-A1ST), with
; nothing plugged into the PCM's input:
;   0-3   STOP held from the Z80 and from R800 ROM mode, rate code 1: CTRL+STOP, then STOP alone, each;
;   4-5   CTRL+STOP held, recording into VRAM ($04000): R800 DRAM, then the Z80 (rate code 1);
;   6-8   a plain recording (R800 DRAM, rate code 1, 16 bytes) entered with F = $FF, $28, $44;
;   9-10  CTRL+STOP held, entry F = $FF, $28;
;   11    a plain recording in RAM with D = E = $FE: DE on return;
;   12    the control: case 6 with entry F $00.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmrec2.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM, VRAM and I/O ports. No ROM byte read.
;
; @cap 8800
; @caplen 1B00
; @timeout 120
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
                ld      bc, $1AFE
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
                ld      bc, 10
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
                ld      (ENTBL+13), a           ; A
                ld      a, (CUR+9)
                ld      (ENTBL+12), a           ; F
                push    ix
                pop     hl
                ld      de, 210
                add     hl, de
                ld      (hl), a                 ; +210 (beyond an (ix+d) reach)
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

; start, A, HL, BC, D, E, keys, F
cases:
                db      $80, $01
                dw      BUF, 16
                db      $00, $00, 1, $00          ; 0: the Z80, rate code 1, CTRL+STOP
                db      $80, $01
                dw      BUF, 16
                db      $00, $00, 2, $00          ; 1: the Z80, STOP alone
                db      $81, $01
                dw      BUF, 16
                db      $00, $00, 1, $00          ; 2: R800 ROM, CTRL+STOP
                db      $81, $01
                dw      BUF, 16
                db      $00, $00, 2, $00          ; 3: R800 ROM, STOP alone
                db      $82, $81
                dw      $4000, 16
                db      $00, $00, 1, $00          ; 4: VRAM, R800 DRAM, CTRL+STOP
                db      $80, $81
                dw      $4000, 16
                db      $00, $00, 1, $00          ; 5: VRAM, the Z80, CTRL+STOP
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 0, $FF          ; 6: F $FF
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 0, $28          ; 7: F $28
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 0, $44          ; 8: F $44
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 1, $FF          ; 9: CTRL+STOP, F $FF
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 1, $28          ; 10: CTRL+STOP, F $28
                db      $82, $01
                dw      BUF, 16
                db      $FE, $FE, 0, $00          ; 11: RAM, D = E = $FE
                db      $82, $01
                dw      BUF, 16
                db      $00, $00, 0, $00          ; 12: control, F $00
                db      $EE

                ds      $8000-$, $FF
