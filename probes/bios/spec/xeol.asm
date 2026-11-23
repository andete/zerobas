; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XEOL -- D-MSX2SPEC, docs/msx2/main/EOL.md: the main ROM's EOL ($0168) on the MSX2 / MSX2+ references.
; Per case (table `cases`): FORCLR 15, BAKCLR 4, LINL40 / LINL32 := the width, CHGMOD ($005F), DI; the VRAM span
; [base, base + len) := p(a) = ((a AND $FF) XOR (a >> 8) XOR $5A) OR $80 -- address-dependent, never a space, never a
; colour pair; CSRX := 20, CSRY := 10, CRTCNT := 24, CNSDFG := per case, LINTTB[i] := $C0 + i with one entry := 0 in
; some cases; every register from the entry table (H / L per case, A $A7); DI or EI; CALL $0168.
; Recorded: the register dump, CSRX, CSRY, CNSDFG, LINTTB, and the span's changes as runs (start, length, first new
; value), up to 20 runs, with the total count of changed bytes.
; The capture (CAP = C001): +0 case count, +1 $5A; records of 160 bytes from +16: +0 case, +1..+26 the dump (as
; xextrom.asm: [($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL', DE', BC', AF', IY, IX, HL, DE, BC, AF), +27 CSRX, +28 CSRY,
; +29 CNSDFG, +30..+53 LINTTB, +54/55 changed bytes, +56 runs, +57.. 20 x (start lo, hi, length lo, hi, first value),
; +157 ($FCB1) and +158 ($FBCA) after the call (both preset $3C: LINTTB + 255 / + 24, what L 0 / L 25 would index),
; +159 $5A, +160 ($FBB1) after the call (preset $3C: LINTTB - 1, what (LINTTB - 1) + L gives for L 0); records are
; 168 bytes apart.
; Cases 21-30 (goldfish pass 1, 2026-11-23): the graphic-mode count with LINLEN 30 (each graphic case preceded by a
; SCREEN 0 width-30 case, which sets LINLEN), the centring margin at an odd difference (width 39, 29, 75, SCREEN 1 29),
; H 42 / 255 at width 40.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xeol.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports. No ROM byte read.
;
; @cap C000
; @caplen 1480
; @timeout 300

CHGMOD  equ     $005F
EOL     equ     $0168
LINL40  equ     $F3AE
LINL32  equ     $F3AF
CRTCNT  equ     $F3B1
CSRY    equ     $F3DC
CSRX    equ     $F3DD
CNSDFG  equ     $F3DE
FORCLR  equ     $F3E9
BAKCLR  equ     $F3EA
LINTTB  equ     $FBB2
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16
RECLEN  equ     168

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E906
CIDX    equ     $E90B
TP      equ     $E90C
ENTBL   equ     $E910
RDUMP   equ     $E960
RDEND   equ     $E97A
VADDR   equ     $E980
VCNT    equ     $E982
NCHG    equ     $E984
NRUNS   equ     $E986
INRUN   equ     $E987
RUNP    equ     $E988
RSTART  equ     $E98A
CUR     equ     $E9E0
SVBR    equ     $E98C                   ; ($FBB1) as booted

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $147E
                ld      (hl), 0
                ldir
                ld      a, $5A
                ld      (CAP+1), a
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, cases
                ld      (TP), hl
                xor     a
                ld      (CIDX), a
                ld      a, ($FBB1)
                ld      (SVBR), a
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 12
                ldir
                ld      (TP), hl
                ; CUR: +0 id, +1 mode, +2 width, +3 H, +4 L, +5 CNSDFG, +6 LINTTB index := 0 (FF none), +7 iff,
                ;      +8/9 base, +10/11 len
                ld      a, 15
                ld      (FORCLR), a
                ld      a, 4
                ld      (BAKCLR), a
                ld      a, (CUR+2)
                ld      (LINL40), a
                ld      (LINL32), a
                ld      a, (CUR+1)
                call    CHGMOD
                di
                ; fill
                ld      hl, (CUR+8)
                ld      (VADDR), hl
                ld      hl, (CUR+10)
                ld      (VCNT), hl
                ld      hl, (VADDR)
                call    setwr
f_lp:
                ld      a, l
                xor     h
                xor     $5A
                or      $80
                out     ($98), a
                inc     hl
                ld      a, l
                or      a
                jr      nz, f_nb
                ld      a, h
                and     $3F
                call    z, setwr
f_nb:
                ld      bc, (VCNT)
                dec     bc
                ld      (VCNT), bc
                ld      a, b
                or      c
                jr      nz, f_lp
                ; the state
                ld      a, 20
                ld      (CSRX), a
                ld      a, 10
                ld      (CSRY), a
                ld      a, 24
                ld      (CRTCNT), a
                ld      a, (CUR+5)
                ld      (CNSDFG), a
                ld      hl, LINTTB
                ld      b, 24
                ld      a, $C0
c_lt:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_lt
                ld      a, (CUR+6)
                cp      $FF
                jr      z, c_nlt
                ld      e, a
                ld      d, 0
                ld      hl, LINTTB
                add     hl, de
                ld      (hl), 0
c_nlt:
                ld      a, $3C
                ld      ($FCB1), a
                ld      ($FBCA), a
                ld      ($FBB1), a
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+4)
                ld      (ENTBL+18), a           ; L
                ld      a, (CUR+3)
                ld      (ENTBL+19), a           ; H
                ld      a, (CUR+7)
                or      a
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
                call    EOL
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
                ld      de, (PTR)
                ld      a, (CIDX)
                ld      (de), a
                inc     de
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      a, (CSRX)
                ld      (de), a
                inc     de
                ld      a, (CSRY)
                ld      (de), a
                inc     de
                ld      a, (CNSDFG)
                ld      (de), a
                inc     de
                ld      hl, LINTTB
                ld      bc, 24
                ldir
                ; the diff: runs from +57
                ld      hl, (PTR)
                ld      bc, 57
                add     hl, bc
                ld      (RUNP), hl
                ld      hl, 0
                ld      (NCHG), hl
                xor     a
                ld      (NRUNS), a
                ld      (INRUN), a
                ld      hl, (CUR+10)
                ld      (VCNT), hl
                ld      hl, (CUR+8)
                call    setrd
d_lp:
                in      a, ($98)
                ld      b, a
                ld      a, l
                xor     h
                xor     $5A
                or      $80
                cp      b
                jr      z, d_same
                ld      de, (NCHG)
                inc     de
                ld      (NCHG), de
                ld      a, (INRUN)
                or      a
                jr      nz, d_next
                ld      a, 1
                ld      (INRUN), a
                ld      a, (NRUNS)
                inc     a
                ld      (NRUNS), a
                cp      21
                jr      nc, d_next
                ld      (RSTART), hl
                ld      de, (RUNP)
                ld      a, l
                ld      (de), a
                inc     de
                ld      a, h
                ld      (de), a
                inc     de
                inc     de
                inc     de
                ld      a, b
                ld      (de), a
                jr      d_next
d_same:
                call    endrun
d_next:
                inc     hl
                ld      a, l
                or      a
                jr      nz, d_nb
                ld      a, h
                and     $3F
                call    z, setrd
d_nb:
                ld      bc, (VCNT)
                dec     bc
                ld      (VCNT), bc
                ld      a, b
                or      c
                jr      nz, d_lp
                call    endrun
                ld      hl, (PTR)
                ld      bc, 54
                add     hl, bc
                ld      de, (NCHG)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      a, (NRUNS)
                ld      (hl), a
                ld      hl, (PTR)
                ld      bc, 157
                add     hl, bc
                ld      a, ($FCB1)
                ld      (hl), a
                inc     hl
                ld      a, ($FBCA)
                ld      (hl), a
                inc     hl
                ld      (hl), $5A
                inc     hl
                ld      a, ($FBB1)
                ld      (hl), a
                ld      a, (SVBR)
                ld      ($FBB1), a
                ld      hl, (PTR)
                ld      bc, RECLEN
                add     hl, bc
                ld      (PTR), hl
                ld      a, (CIDX)
                inc     a
                ld      (CIDX), a
                ld      (CAP), a
                jp      c_next

; close an open run at HL (its end, exclusive): length := HL - start, RUNP += 5
endrun:
                ld      a, (INRUN)
                or      a
                ret     z
                xor     a
                ld      (INRUN), a
                ld      a, (NRUNS)
                cp      21
                ret     nc
                push    hl
                ld      de, (RSTART)
                or      a
                sbc     hl, de
                ex      de, hl                  ; DE = length
                ld      hl, (RUNP)
                inc     hl
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                inc     hl
                ld      (RUNP), hl
                pop     hl
                ret

; VRAM address HL (16-bit): R#14 := HL >> 14, then the low 14 bits, write / read
setwr:
                push    af
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
                or      $40
                out     ($99), a
                pop     af
                ret
setrd:
                push    af
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
                pop     af
                ret

finish:
                ld      a, 40
                ld      (LINL40), a
                xor     a
                call    CHGMOD
                di
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

ent_src:
                dw      $5A6B, $1A2B, $3C4D, $5E6F, $7081, $92A3, $A700, $B1C2, $4E5F, $9876

; id, mode, width, H, L, CNSDFG, LINTTB index := 0 (FF none), iff, base, len
cases:
                db      0, 1, 32, 5, 3, 0, $FF, 0
                dw      $1800, 768
                db      1, 0, 40, 1, 1, 0, $FF, 0
                dw      $0000, 1080
                db      2, 0, 80, 30, 3, 0, $FF, 0
                dw      $0000, 2160
                db      3, 0, 30, 5, 3, 0, $FF, 0
                dw      $0000, 1080
                db      4, 0, 40, 5, 3, 0, 2, 0
                dw      $0000, 1080
                db      5, 0, 40, 5, 3, 0, 3, 0
                dw      $0000, 1080
                db      6, 0, 40, 0, 3, 0, $FF, 0
                dw      $0000, 1080
                db      7, 0, 40, 41, 3, 0, $FF, 0
                dw      $0000, 1080
                db      8, 0, 40, 40, 3, 0, $FF, 0
                dw      $0000, 1080
                db      9, 0, 80, 80, 3, 0, $FF, 0
                dw      $0000, 2160
                db      10, 0, 40, 5, 24, 0, $FF, 0
                dw      $0000, 1080
                db      11, 0, 40, 5, 24, $FF, $FF, 0
                dw      $0000, 1080
                db      12, 0, 40, 5, 0, 0, $FF, 0
                dw      $0000, 1080
                db      13, 0, 40, 5, 25, 0, $FF, 0
                dw      $0000, 1080
                db      14, 5, 40, 5, 3, 0, $FF, 0
                dw      $0000, $6A00
                db      15, 2, 32, 5, 3, 0, $FF, 0
                dw      $0000, $3800
                db      16, 8, 40, 5, 3, 0, $FF, 0
                dw      $0000, $D400
                db      17, 0, 40, 5, 3, 0, $FF, 1
                dw      $0000, 1080
                db      18, 1, 32, 32, 3, 0, $FF, 0
                dw      $1800, 768
                db      19, 0, 40, 5, 4, 0, 3, 0
                dw      $0000, 1080
                db      20, 0, 40, 5, 3, 0, $FF, 0
                dw      $0000, 1080
                db      21, 0, 30, 5, 3, 0, $FF, 0      ; LINLEN := 30 for case 22
                dw      $0000, 1080
                db      22, 2, 30, 5, 3, 0, $FF, 0      ; SCREEN 2 after LINLEN 30
                dw      $1800, $0400
                db      23, 0, 30, 5, 3, 0, $FF, 0      ; LINLEN := 30 for case 24
                dw      $0000, 1080
                db      24, 5, 30, 5, 3, 0, $FF, 0      ; SCREEN 5 after LINLEN 30
                dw      $0000, $0800
                db      25, 0, 39, 1, 3, 0, $FF, 0      ; margin, odd difference 1
                dw      $0000, 1080
                db      26, 0, 29, 1, 3, 0, $FF, 0      ; margin, odd difference 11
                dw      $0000, 1080
                db      27, 0, 75, 1, 3, 0, $FF, 0      ; 80 columns, LINLEN 75
                dw      $0000, 2160
                db      28, 1, 29, 1, 3, 0, $FF, 0      ; SCREEN 1, LINLEN 29
                dw      $1800, 768
                db      29, 0, 40, 42, 3, 0, $FF, 0     ; H 42
                dw      $0000, 1080
                db      30, 0, 40, 255, 3, 0, $FF, 0    ; H 255
                dw      $0000, 1080
                db      $EE

                ds      $8000 - $, $FF
