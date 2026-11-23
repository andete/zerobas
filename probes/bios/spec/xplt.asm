; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPLT -- D-MSX2SPEC, docs/msx2/sub/{INIPLT,RSTPLT,GETPLT,SETPLT}.md and concepts/vdp-and-palette.md "The VRAM save
; area": the palette calls (sub-ROM $0141 INIPLT, $0145 RSTPLT, $0149 GETPLT, $014D SETPLT, through EXTROM $015F)
; on the MSX2 / MSX2+ references. A fixed run of steps (the table `steps`: op, A, D, E, SCRMOD, LINL40, the mode's
; VRAM table address): op 0 CHGMOD (main $005F), 1 INIPLT, 2 RSTPLT, 3 GETPLT, 4 SETPLT, 5 the table := a pattern
; by hand (byte k := k x 5 + 3, through the VDP's ports). After every step: A F B C D E, the VDP's palette (32 bytes,
; through the debugger: the registers as last written) and the mode's 48-byte VRAM table (read by hand).
; So: what INIPLT writes, to the VDP and to VRAM; whether SETPLT writes the table; where GETPLT reads (step 5: after
; the pattern, the table's bytes or not) and which bytes are an entry; whether RSTPLT loads the VDP from the table;
; the table's place in SCREEN 1, 0 (40 / 80) and 8.
; The capture (CAP = C001): +0 $A5 when finished, +1 the step count; per step a 96-byte record from +2:
;   +0 A, +1 F, +2 B, +3 C, +4 D, +5 E after; +6..+37 the palette; +38..+85 the table; +86..+95 0.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xplt.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; palette read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0680
; @vdpfull E8F0 E900
; @timeout 120

CHGMOD  equ     $005F
EXTROM  equ     $015F
LINL40  equ     $F3AE
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910                   ; AF, BC, DE after
cur     equ     $E920                   ; the step: op, A, D, E, SCRMOD, LINL40, table (2)
SNAPB   equ     $E000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $067F
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, steps
                ld      (tp), hl
                xor     a
                ld      (cidx), a
s_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 8
                ldir
                ld      (tp), hl
                ld      a, (cur)
                or      a
                jr      nz, s_n0
                ld      a, (cur+5)              ; 0: CHGMOD
                ld      (LINL40), a
                ld      a, (cur+4)
                call    CHGMOD
                jr      s_done
s_n0:
                cp      5
                jr      nz, s_call
                call    tbl_wr                  ; 5: the pattern, by hand
                ld      b, 48
                ld      c, 3
s_pat:
                ld      a, c
                out     ($98), a
                add     a, 5
                ld      c, a
                djnz    s_pat
                jr      s_done
s_call:
                ld      ix, $0141               ; 1 INIPLT
                dec     a
                jr      z, s_go
                ld      ix, $0145               ; 2 RSTPLT
                dec     a
                jr      z, s_go
                ld      ix, $0149               ; 3 GETPLT
                dec     a
                jr      z, s_go
                ld      ix, $014D               ; 4 SETPLT
s_go:
                ld      a, (cur+2)
                ld      d, a
                ld      a, (cur+3)
                ld      e, a
                ld      bc, $5AA5
                ld      a, (cur+1)
                call    EXTROM
s_done:
                di
                push    af
                pop     hl
                ld      (rsave), hl
                ld      (rsave+2), bc
                ld      (rsave+4), de
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ld      de, (ptr)
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (rsave+3)
                ld      (de), a                 ; B
                inc     de
                ld      a, (rsave+2)
                ld      (de), a                 ; C
                inc     de
                ld      a, (rsave+5)
                ld      (de), a                 ; D
                inc     de
                ld      a, (rsave+4)
                ld      (de), a                 ; E
                inc     de
                ld      hl, SNAPB+82            ; the palette (after R#0-63, S#0-15, the pointer)
                ld      bc, 32
                ldir
                push    de
                call    tbl_rd
                pop     de
                ld      b, 48
s_rd:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    s_rd
                ld      hl, (ptr)
                ld      bc, 96
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                jp      s_next
finish:
                ld      a, (cidx)
                ld      (CAP+1), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; the step's table address (16-bit, A16 = 0) for writing / reading through the VDP's ports
tbl_wr:
                ld      c, $40
                jr      tbl_set
tbl_rd:
                ld      c, $00
tbl_set:
                ld      hl, (cur+6)
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

; op, A, D, E, SCRMOD, LINL40, table address
steps:
                db      0, 0, 0, 0, 5, 40
                dw      $7680                   ;  0 SCREEN 5
                db      1, 0, 0, 0, 5, 40
                dw      $7680                   ;  1 INIPLT
                db      4, $73, 5, $04, 5, 40
                dw      $7680                   ;  2 SETPLT 5 := R 7, B 3, G 4
                db      3, 5, 0, 0, 5, 40
                dw      $7680                   ;  3 GETPLT 5
                db      5, 0, 0, 0, 5, 40
                dw      $7680                   ;  4 the table := the pattern
                db      3, 5, 0, 0, 5, 40
                dw      $7680                   ;  5 GETPLT 5: from the table?
                db      2, 0, 0, 0, 5, 40
                dw      $7680                   ;  6 RSTPLT
                db      3, 5, 0, 0, 5, 40
                dw      $7680                   ;  7 GETPLT 5
                db      0, 0, 0, 0, 1, 40
                dw      $2020                   ;  8 SCREEN 1
                db      1, 0, 0, 0, 1, 40
                dw      $2020                   ;  9 INIPLT
                db      0, 0, 0, 0, 0, 40
                dw      $0400                   ; 10 SCREEN 0, width 40
                db      1, 0, 0, 0, 0, 40
                dw      $0400                   ; 11 INIPLT
                db      0, 0, 0, 0, 0, 80
                dw      $0F00                   ; 12 SCREEN 0, width 80
                db      1, 0, 0, 0, 0, 80
                dw      $0F00                   ; 13 INIPLT
                db      0, 0, 0, 0, 8, 40
                dw      $FA80                   ; 14 SCREEN 8
                db      1, 0, 0, 0, 8, 40
                dw      $FA80                   ; 15 INIPLT
                db      4, $73, 5, $04, 8, 40
                dw      $FA80                   ; 16 SETPLT 5 in SCREEN 8
                db      $EE

                ds      $8000 - $, $FF
