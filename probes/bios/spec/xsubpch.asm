; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPCH -- D-MSX2SPEC, docs/msx2/sub/PUTCHR.md: the sub-ROM entry $0139 (PUTCHR, a name from MAP only) through EXTROM
; on the MSX2 / MSX2+ references. xeol.asm's frame (the span diff as runs), the call made through EXTROM.
; Per case (table `cases`): FORCLR 15, BAKCLR 4, LINL40 / LINL32 := the width, CHGMOD ($005F), DI; the VRAM span
; [base, base + len) := p(a) = ((a AND $FF) XOR (a >> 8) XOR $5A) OR $80 -- address-dependent, never a space;
; CSRX / CSRY per case, CRTCNT := 24, CNSDFG := 0, LINTTB[i] := $C0 + i, GRPACX := 40, GRPACY := 50, ESCCNT := 0;
; every register from the entry table (A / H / L per case, IX := $0139); DI or EI; CALL EXTROM ($015F).
; Recorded: the register dump, CSRX, CSRY, CNSDFG, LINTTB, the span's changes as runs (start, length, first new
; value), up to 20 runs, with the total count of changed bytes; GRPACX, GRPACY, ESCCNT.
; The capture (CAP = C001): +0 case count, +1 $5A; records of 176 bytes from +16: +0 case, +1..+26 the dump
; ([($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL', DE', BC', AF', IY, IX, HL, DE, BC, AF), +27 CSRX, +28 CSRY,
; +29 CNSDFG, +30..+53 LINTTB, +54/55 changed bytes, +56 runs, +57.. 20 x (start lo, hi, length lo, hi, first value),
; +160 GRPACX (2), +162 GRPACY (2), +164 ESCCNT, +175 $5A.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpch.asm --row msx2all
; Decode: python3 scratchpad/xsubpch_decode.py
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports. No ROM byte read.
;
; @cap C000
; @caplen 1000
; @timeout 300

CHGMOD  equ     $005F
EXTROM  equ     $015F
GRPACX  equ     $FCB7
GRPACY  equ     $FCB9
ESCCNT  equ     $FCA7
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
RECLEN  equ     176

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

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0FFE
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
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 13
                ldir
                ld      (TP), hl
                ; CUR: +0 id, +1 mode, +2 width, +3 H, +4 L, +5 CSRX, +6 CSRY, +7 iff, +8/9 base, +10/11 len, +12 A
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
                ld      a, (CUR+5)
                ld      (CSRX), a
                ld      a, (CUR+6)
                ld      (CSRY), a
                ld      a, 24
                ld      (CRTCNT), a
                xor     a
                ld      (CNSDFG), a
                ld      (ESCCNT), a
                ld      hl, 40
                ld      (GRPACX), hl
                ld      hl, 50
                ld      (GRPACY), hl
                ld      hl, LINTTB
                ld      b, 24
                ld      a, $C0
c_lt:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_lt
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+4)
                ld      (ENTBL+18), a           ; L
                ld      a, (CUR+3)
                ld      (ENTBL+19), a           ; H
                ld      a, (CUR+12)
                ld      (ENTBL+13), a           ; A
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
                call    EXTROM
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
                ld      bc, 160
                add     hl, bc
                ld      de, (GRPACX)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      de, (GRPACY)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      a, (ESCCNT)
                ld      (hl), a
                ld      hl, (PTR)
                ld      bc, RECLEN-1
                add     hl, bc
                ld      (hl), $5A
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
                dw      $0139, $1A2B, $3C4D, $5E6F, $7081, $92A3, $A7C5, $B1C2, $4E5F, $9876

; id, mode, width, H, L, CSRX, CSRY, iff, base, len, A  (12 bytes, as CUR)
cases:
                db      0, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $51                     ;  0 SCREEN 0 w40, A 'Q', cursor (10, 5), HL $140C
                db      1, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $52                     ;  1 A 'R'
                db      2, 0, 40, 20, 12, 3, 18, 0
                dw      $0000, 1080
                db      $51                     ;  2 cursor (3, 18)
                db      3, 0, 40, 3, 3, 10, 5, 0
                dw      $0000, 1080
                db      $51                     ;  3 HL $0303
                db      4, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $0D                     ;  4 CR
                db      5, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $0A                     ;  5 LF
                db      6, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $08                     ;  6 BS
                db      7, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $0C                     ;  7 FF (CLS as CHPUT)
                db      8, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $1B                     ;  8 ESC
                db      9, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $7F                     ;  9 DEL
                db      10, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $01                     ; 10 the graphic-character prefix
                db      11, 0, 40, 20, 12, 40, 5, 0
                dw      $0000, 1080
                db      $51                     ; 11 cursor (40, 5), the last column
                db      12, 0, 40, 20, 12, 40, 24, 0
                dw      $0000, 1080
                db      $51                     ; 12 cursor (40, 24), bottom right
                db      13, 0, 80, 20, 12, 10, 5, 0
                dw      $0000, 2160
                db      $51                     ; 13 width 80
                db      14, 1, 32, 20, 12, 10, 5, 0
                dw      $1800, 768
                db      $51                     ; 14 SCREEN 1
                db      15, 0, 40, 20, 12, 10, 5, 1
                dw      $0000, 1080
                db      $51                     ; 15 EI
                db      16, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $20                     ; 16 A space
                db      17, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $FF                     ; 17 A $FF
                db      18, 0, 40, 20, 12, 10, 5, 0
                dw      $0000, 1080
                db      $09                     ; 18 TAB
                db      19, 5, 40, 20, 12, 10, 5, 0
                dw      $0000, $6A00
                db      $51                     ; 19 SCREEN 5
                db      $EE

                ds      $8000 - $, $FF
