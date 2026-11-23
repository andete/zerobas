; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBCLS -- D-MSX2SPEC, docs/msx2/sub/CHGCLR.md / CLS.md: the sub-ROM's CHGCLR ($0111) and CLS ($0115) through EXTROM,
; on the MSX2 / MSX2+ references. Per case (the table `cases`: the entry, SCRMOD, FORCLR, BAKCLR, BDRCLR, three VRAM
; windows): CHGMOD (main $005F), the colour cells ($F3E9-$F3EB), the three 16-byte windows := $5A by hand, interrupts
; off, A $00 with Z set (CLS's MSX1 input), the call; then R#7 (debugger), A / F / IFF, the colour cells, the windows.
; The windows: the cleared area's start, its last 16 bytes, the 16 just past it (or the colour table).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 64-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4 R#7, +5..+7 FORCLR BAKCLR BDRCLR after, +8..+15 0, +16..+63 the windows.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubcls.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger.
;
; @cap C000
; @caplen 0600
; @vdpfull E8F0 E900
; @timeout 180

CHGMOD  equ     $005F
EXTROM  equ     $015F
FORCLR  equ     $F3E9
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
SNAPP   equ     $E900
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E920                   ; entry (2), SCRMOD, FORCLR, BAKCLR, BDRCLR, 3 windows (6) = 12
SNAPB   equ     $E000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $05FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
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
                ld      bc, 12
                ldir
                ld      (tp), hl
                ld      a, (cur+2)
                call    CHGMOD
                di
                ld      hl, cur+3
                ld      de, FORCLR
                ld      bc, 3
                ldir
                ld      ix, cur+6
                ld      b, 3
c_w:
                push    bc
                ld      l, (ix+0)
                ld      h, (ix+1)
                ld      c, $40
                call    vset
                ld      b, 16
c_wb:
                ld      a, $5A
                out     ($98), a
                djnz    c_wb
                inc     ix
                inc     ix
                pop     bc
                djnz    c_w
                ld      ix, (cur)
                xor     a                       ; A 0, Z set
                call    EXTROM
                push    af
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      (rsave), hl
                ld      hl, SNAPB
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
                ld      a, (SNAPB+7)
                ld      (de), a
                inc     de
                ld      hl, FORCLR
                ld      bc, 3
                ldir
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ex      de, hl
                ld      ix, cur+6
                ld      b, 3
c_r:
                push    bc
                push    de
                ld      l, (ix+0)
                ld      h, (ix+1)
                ld      c, $00
                call    vset
                pop     de
                ld      b, 16
c_rb:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    c_rb
                inc     ix
                inc     ix
                pop     bc
                djnz    c_r
                ld      hl, (ptr)
                ld      bc, 64
                add     hl, bc
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

; HL (16-bit, A16 = 0) for writing (C $40) / reading (C $00) through the VDP's ports
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

; the entry, SCRMOD, FORCLR, BAKCLR, BDRCLR, three windows
cases:
                dw      $0111
                db      0, $3A, $C5, $F9
                dw      $0000, $03B0, $03C0   ;  0 CHGCLR SCREEN 0 BAKCLR $C5
                dw      $0111
                db      1, $3A, $C5, $F9
                dw      $1800, $1AF0, $2000   ;  1 CHGCLR SCREEN 1 BAKCLR $C5
                dw      $0111
                db      2, $3A, $C5, $F9
                dw      $1800, $0000, $2000   ;  2 CHGCLR SCREEN 2 BAKCLR $C5
                dw      $0111
                db      5, $3A, $C5, $F9
                dw      $0000, $69F0, $6A00   ;  3 CHGCLR SCREEN 5 BAKCLR $C5
                dw      $0111
                db      8, $3A, $C5, $F9
                dw      $0000, $D3F0, $D400   ;  4 CHGCLR SCREEN 8 BAKCLR $C5
                dw      $0115
                db      0, $3A, $06, $F9
                dw      $0000, $03B0, $03C0   ;  5 CLS SCREEN 0 BAKCLR $06
                dw      $0115
                db      0, $3A, $C5, $F9
                dw      $0000, $03B0, $03C0   ;  6 CLS SCREEN 0 BAKCLR $C5
                dw      $0115
                db      1, $3A, $06, $F9
                dw      $1800, $1AF0, $2000   ;  7 CLS SCREEN 1 BAKCLR $06
                dw      $0115
                db      1, $3A, $C5, $F9
                dw      $1800, $1AF0, $2000   ;  8 CLS SCREEN 1 BAKCLR $C5
                dw      $0115
                db      2, $3A, $06, $F9
                dw      $1800, $0000, $2000   ;  9 CLS SCREEN 2 BAKCLR $06
                dw      $0115
                db      2, $3A, $C5, $F9
                dw      $1800, $0000, $2000   ; 10 CLS SCREEN 2 BAKCLR $C5
                dw      $0115
                db      3, $3A, $06, $F9
                dw      $0800, $0000, $0AF0   ; 11 CLS SCREEN 3 BAKCLR $06
                dw      $0115
                db      3, $3A, $C5, $F9
                dw      $0800, $0000, $0AF0   ; 12 CLS SCREEN 3 BAKCLR $C5
                dw      $0115
                db      5, $3A, $06, $F9
                dw      $0000, $69F0, $6A00   ; 13 CLS SCREEN 5 BAKCLR $06
                dw      $0115
                db      5, $3A, $C5, $F9
                dw      $0000, $69F0, $6A00   ; 14 CLS SCREEN 5 BAKCLR $C5
                dw      $0115
                db      6, $3A, $06, $F9
                dw      $0000, $69F0, $6A00   ; 15 CLS SCREEN 6 BAKCLR $06
                dw      $0115
                db      6, $3A, $C5, $F9
                dw      $0000, $69F0, $6A00   ; 16 CLS SCREEN 6 BAKCLR $C5
                dw      $0115
                db      7, $3A, $06, $F9
                dw      $0000, $D3F0, $D400   ; 17 CLS SCREEN 7 BAKCLR $06
                dw      $0115
                db      7, $3A, $C5, $F9
                dw      $0000, $D3F0, $D400   ; 18 CLS SCREEN 7 BAKCLR $C5
                dw      $0115
                db      8, $3A, $06, $F9
                dw      $0000, $D3F0, $D400   ; 19 CLS SCREEN 8 BAKCLR $06
                dw      $0115
                db      8, $3A, $C5, $F9
                dw      $0000, $D3F0, $D400   ; 20 CLS SCREEN 8 BAKCLR $C5
                dw      0

                ds      $8000 - $, $FF
