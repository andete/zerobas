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
; Added 2026-11-23 (goldfish pass 1), steps 17-59 after the old ones (unchanged): +86 R#16 and +87 / +88 the VDP's
; VRAM pointer (openMSX's 14-bit counter, low byte first) as the debugger held them right after the step -- so
; after RSTPLT / GETPLT the pointer says how far the call read; op 6 fills the 48-byte table with A's value; op 7
; does nothing (it records the table at its address: the other places, after INIPLT / SETPLT). D / E enter as
; $C3 / $3C in the new RSTPLT / GETPLT steps.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xplt.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; palette read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 1700
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
                ld      bc, $16FF
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
                cp      7
                jr      z, s_done               ; 7: nothing (record the table at the step's address)
                cp      6
                jr      nz, s_n5
                call    tbl_wr                  ; 6: the table := A's value, 48 bytes
                ld      b, 48
                ld      a, (cur+1)
s_fill:
                out     ($98), a
                djnz    s_fill
                jr      s_done
s_n5:
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
                ld      a, (SNAPB+16)           ; +86 R#16
                ld      (de), a
                inc     de
                ld      a, (SNAPB+80)           ; +87 / +88 the VRAM pointer
                ld      (de), a
                inc     de
                ld      a, (SNAPB+81)
                ld      (de), a
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
                db      0, $00, $00, $00, 1, 40
                dw      $2020                   ; 17 SCREEN 1
                db      5, $00, $00, $00, 1, 40
                dw      $2020                   ; 18 the table := the pattern
                db      2, $00, $C3, $3C, 1, 40
                dw      $2020                   ; 19 RSTPLT, D $C3 E $3C
                db      3, $05, $C3, $3C, 1, 40
                dw      $2020                   ; 20 GETPLT 5, D $C3 E $3C
                db      4, $73, $05, $04, 1, 40
                dw      $2020                   ; 21 SETPLT 5 := R 7, B 3, G 4
                db      0, $00, $00, $00, 0, 40
                dw      $0400                   ; 22 SCREEN 0, width 40
                db      5, $00, $00, $00, 0, 40
                dw      $0400                   ; 23 the table := the pattern
                db      2, $00, $C3, $3C, 0, 40
                dw      $0400                   ; 24 RSTPLT, D $C3 E $3C
                db      3, $05, $C3, $3C, 0, 40
                dw      $0400                   ; 25 GETPLT 5, D $C3 E $3C
                db      4, $73, $05, $04, 0, 40
                dw      $0400                   ; 26 SETPLT 5 := R 7, B 3, G 4
                db      0, $00, $00, $00, 0, 80
                dw      $0F00                   ; 27 SCREEN 0, width 80
                db      5, $00, $00, $00, 0, 80
                dw      $0F00                   ; 28 the table := the pattern
                db      2, $00, $C3, $3C, 0, 80
                dw      $0F00                   ; 29 RSTPLT, D $C3 E $3C
                db      3, $05, $C3, $3C, 0, 80
                dw      $0F00                   ; 30 GETPLT 5, D $C3 E $3C
                db      0, $00, $00, $00, 8, 40
                dw      $FA80                   ; 31 SCREEN 8
                db      5, $00, $00, $00, 8, 40
                dw      $FA80                   ; 32 the table := the pattern
                db      2, $00, $C3, $3C, 8, 40
                dw      $FA80                   ; 33 RSTPLT, D $C3 E $3C
                db      3, $05, $C3, $3C, 8, 40
                dw      $FA80                   ; 34 GETPLT 5, D $C3 E $3C
                db      0, $00, $00, $00, 5, 40
                dw      $7680                   ; 35 SCREEN 5
                db      6, $FF, $00, $00, 5, 40
                dw      $7680                   ; 36 the table := $FF
                db      3, $05, $C3, $3C, 5, 40
                dw      $7680                   ; 37 GETPLT 5: bits 3 / 7
                db      2, $00, $C3, $3C, 5, 40
                dw      $7680                   ; 38 RSTPLT from $FF
                db      6, $88, $00, $00, 5, 40
                dw      $7680                   ; 39 the table := $88
                db      3, $05, $C3, $3C, 5, 40
                dw      $7680                   ; 40 GETPLT 5
                db      5, $00, $00, $00, 5, 40
                dw      $0400                   ; 41 the pattern at $0400
                db      5, $00, $00, $00, 5, 40
                dw      $0F00                   ; 42 the pattern at $0F00
                db      5, $00, $00, $00, 5, 40
                dw      $2020                   ; 43 the pattern at $2020
                db      5, $00, $00, $00, 5, 40
                dw      $1B80                   ; 44 the pattern at $1B80
                db      5, $00, $00, $00, 5, 40
                dw      $7680                   ; 45 the pattern at $7680
                db      5, $00, $00, $00, 5, 40
                dw      $FA80                   ; 46 the pattern at $FA80
                db      1, $00, $00, $00, 5, 40
                dw      $7680                   ; 47 INIPLT (SCREEN 5)
                db      7, $00, $00, $00, 5, 40
                dw      $0400                   ; 48 read $0400
                db      7, $00, $00, $00, 5, 40
                dw      $0F00                   ; 49 read $0F00
                db      7, $00, $00, $00, 5, 40
                dw      $2020                   ; 50 read $2020
                db      7, $00, $00, $00, 5, 40
                dw      $1B80                   ; 51 read $1B80
                db      7, $00, $00, $00, 5, 40
                dw      $FA80                   ; 52 read $FA80
                db      5, $00, $00, $00, 5, 40
                dw      $7680                   ; 53 the pattern at $7680
                db      4, $73, $05, $04, 5, 40
                dw      $7680                   ; 54 SETPLT 5 (SCREEN 5)
                db      7, $00, $00, $00, 5, 40
                dw      $0400                   ; 55 read $0400
                db      7, $00, $00, $00, 5, 40
                dw      $0F00                   ; 56 read $0F00
                db      7, $00, $00, $00, 5, 40
                dw      $2020                   ; 57 read $2020
                db      7, $00, $00, $00, 5, 40
                dw      $1B80                   ; 58 read $1B80
                db      7, $00, $00, $00, 5, 40
                dw      $FA80                   ; 59 read $FA80
                db      $EE

                ds      $8000 - $, $FF
