; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XEXTROM -- D-MSX2SPEC, docs/msx2/main/EXTROM.md and SUBROM.md: the main ROM's EXTROM ($015F) and SUBROM ($015C) on
; the MSX2 / MSX2+ references, with a RAM stub standing in for a sub-ROM routine.
; Setup: the RAM slot is the slot of page 3 (port $A8 bits 7-6, the secondary from ($FFFF) when EXPTBL says expanded);
; its page 0 gets (WRSLT, $0014) the stub at $2000 and at $3ABC, and at $0038 a guard handler that counts interrupts
; (none are expected: R#1's interrupt-enable bit is cleared, in RG1SAV too). SP := $E800; the 256 bytes below it are
; markers ((addr AND $FF) XOR $A5).
; The stub stores everything it receives -- AF, BC, DE, HL, IX, IY, AF', BC', DE', HL', I/IFF read twice, port $A8 and
; ($FFFF) -- with its SP, then by SMODE: 0 returns, 1 loads every register (IX, IY, alternates too) with the clobber
; table and returns, 2 does EI and returns, 3 does DI and returns.
; Per case (table `cases`): EXBRSA := the RAM slot (or the real sub-ROM's slot, saved at INIT), the registers from
; the entry table (A, F, DE, IX per case, the rest fixed), DI or EI, then a CALL to a trampoline in page 1 (ROM) or
; page 2 (RAM, $A000): EXTROM = `call $015F / ret`; SUBROM = the handbook's `push ix / ld ix,(TGT) / jp $015C`.
; After the return the same register dump, the lowest overwritten marker, EXBRSA.
; The capture (CAP = C001): +0 the case count, +1 RAM slot, +2 EXBRSA at INIT, +3..+6 EXPTBL, +7 page-0 RAM read-back
; ok (1), +8 page-2 RAM ok (1), +9 interrupts counted by the guard, +10 $5A; records of 64 bytes from +16:
;   +0 case, +1 kind, +2..+27 the stub's dump, +28/29 the stub's SP, +30..+55 the dump after, +56/57 SP after,
;   +58/59 the lowest overwritten marker (0 = none), +60 EXBRSA after, +61 $5A, +62 port $A8 and +63 ($FFFF) cpl
;   just before the call.
; A dump (26 bytes, low address first): [($FFFF) cpl, port $A8], [F, A] of the 2nd `ld a,i`, [F, A] of the 1st,
;   HL', DE', BC', AF', IY, IX, HL, DE, BC, AF (each low byte first; AF = F then A).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xextrom.asm --row msx2all
;
; CLEAN-ROOM: 100% own code (the stub is ours, in RAM); published BIOS entries and work-area cells. No ROM byte read.
;
; @cap C000
; @caplen 0500
; @timeout 120

RDSLT   equ     $000C
WRSLT   equ     $0014
SUBROM  equ     $015C
EXTROM  equ     $015F
EXBRSA  equ     $FAF8
EXPTBL  equ     $FCC1
RG1SAV  equ     $F3E0
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E906
RAMSLT  equ     $E908
SUBSLT  equ     $E909
SMODE   equ     $E90A
CIDX    equ     $E90B
TP      equ     $E90C
TGT     equ     $E90E
ENTBL   equ     $E910                   ; IX, IY, AF', BC', DE', HL', AF, BC, DE, HL
SDUMP   equ     $E940
SDEND   equ     $E95A                   ; = the stub's SP cell
S_SP    equ     $E95A
RDUMP   equ     $E960
RDEND   equ     $E97A
CLOBT   equ     $E980
JVEC    equ     $E9F0
ICOUNT  equ     $E9F8
PRESL   equ     $E9FA
CUR     equ     $E9E0                   ; the case's 12 bytes
STKTOP  equ     $E800
P2TR    equ     $A000

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, STKTOP
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $04FE
                ld      (hl), 0
                ldir
                xor     a
                ld      (ICOUNT), a
                ld      a, (RG1SAV)
                and     $DF
                ld      (RG1SAV), a
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; the RAM slot = page 3's
                in      a, ($A8)
                rlca
                rlca
                and     3
                ld      c, a
                ld      b, 0
                ld      hl, EXPTBL
                add     hl, bc
                ld      a, (hl)
                and     $80
                jr      z, rs_set
                ld      a, ($FFFF)
                cpl
                rrca
                rrca
                rrca
                rrca
                and     $0C
                or      $80
rs_set:
                or      c
                ld      (RAMSLT), a
                ld      (CAP+1), a
                ld      a, (EXBRSA)
                ld      (SUBSLT), a
                ld      (CAP+2), a
                ld      hl, EXPTBL
                ld      de, CAP+3
                ld      bc, 4
                ldir
                ; page 0 of the RAM slot: write / read back
                ld      a, (RAMSLT)
                ld      hl, $2000
                ld      e, $5A
                call    WRSLT
                ld      a, (RAMSLT)
                ld      hl, $2000
                call    RDSLT
                cp      $5A
                jp      nz, finish
                ld      a, (RAMSLT)
                ld      hl, $2000
                ld      e, $A5
                call    WRSLT
                ld      a, (RAMSLT)
                ld      hl, $2000
                call    RDSLT
                cp      $A5
                jp      nz, finish
                ld      a, 1
                ld      (CAP+7), a
                ; plant: the stub at $2000 and $3ABC, the guard at $0038
                ld      hl, stub_src
                ld      de, $2000
                ld      bc, stub_end - stub_src
                call    plant
                ld      hl, stub_src
                ld      de, $3ABC
                ld      bc, stub_end - stub_src
                call    plant
                ld      hl, guard_src
                ld      de, $0038
                ld      bc, guard_end - guard_src
                call    plant
                ; page 2 RAM?
                ld      hl, P2TR
                ld      (hl), $5A
                ld      a, (hl)
                cp      $5A
                jr      nz, p2_no
                ld      (hl), $A5
                ld      a, (hl)
                cp      $A5
                jr      nz, p2_no
                ld      a, 1
                ld      (CAP+8), a
                ld      hl, tr_ext
                ld      de, P2TR
                ld      bc, 4
                ldir
                ld      hl, tr_sub
                ld      de, P2TR+$10
                ld      bc, tr_sub_end - tr_sub
                ldir
p2_no:
                ld      hl, clob_src
                ld      de, CLOBT
                ld      bc, 20
                ldir
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
                ld      bc, 12
                ldir
                ld      (TP), hl
                ld      a, (CUR+1)              ; kinds 1 / 3 run from page 2 RAM
                and     1
                jr      z, c_k
                ld      a, (CAP+8)
                or      a
                jr      nz, c_k
                jp      c_skip
c_k:
                ; EXBRSA
                ld      a, (CUR+4)
                or      a
                ld      a, (RAMSLT)
                jr      z, c_ex
                ld      a, (SUBSLT)
c_ex:
                ld      (EXBRSA), a
                ld      a, (CUR+3)
                ld      (SMODE), a
                ; the stub's dump := $EE
                ld      hl, SDUMP
                ld      de, SDUMP+1
                ld      bc, 27
                ld      (hl), $EE
                ldir
                ; markers below SP
                ld      hl, STKTOP-256
                ld      b, 0
c_mk:
                ld      a, l
                xor     $A5
                ld      (hl), a
                inc     hl
                djnz    c_mk
                ; the entry table
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      hl, (CUR+10)            ; IX value
                ld      (ENTBL), hl
                ld      a, (CUR+6)              ; F
                ld      (ENTBL+12), a
                ld      a, (CUR+5)              ; A
                ld      (ENTBL+13), a
                ld      hl, (CUR+8)             ; DE
                ld      (ENTBL+16), hl
                ld      hl, (CUR+10)
                ld      (TGT), hl
                ; the trampoline
                ld      a, $C3
                ld      (JVEC), a
                ld      a, (CUR+1)
                ld      hl, tr_ext
                or      a
                jr      z, c_tr
                ld      hl, P2TR
                dec     a
                jr      z, c_tr
                ld      hl, tr_sub
                dec     a
                jr      z, c_tr
                ld      hl, P2TR+$10
c_tr:
                ld      (JVEC+1), hl
                ; SUBROM: IX = the pushed marker, TGT = the target; the table's word at CUR+10 is the target,
                ; CUR+2 says the marker: 0 -> $A5A5, 1 -> $1234
                ld      a, (CUR+1)
                cp      2
                jr      c, c_nomark
                ld      hl, $A5A5
                ld      a, (CUR+2)
                or      a
                jr      z, c_mk2
                ld      hl, $1234
c_mk2:
                ld      (ENTBL), hl
c_nomark:
                in      a, ($A8)                ; the slots before the call
                ld      (PRESL), a
                ld      a, ($FFFF)
                cpl
                ld      (PRESL+1), a
                ld      a, (CUR+7)              ; iff
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
                call    JVEC
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
                ld      sp, STKTOP
                ; the record
                ld      de, (PTR)
                ld      a, (CIDX)
                ld      (de), a
                inc     de
                ld      a, (CUR+1)
                ld      (de), a
                inc     de
                ld      hl, SDUMP
                ld      bc, 28
                ldir
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      hl, (R_SP)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ex      de, hl
                ; the lowest overwritten marker
                ld      hl, STKTOP-256
                ld      b, 0
c_scan:
                ld      a, l
                xor     $A5
                cp      (hl)
                jr      nz, c_found
                inc     hl
                djnz    c_scan
                ld      hl, 0
c_found:
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      a, (EXBRSA)
                ld      (hl), a
                inc     hl
                ld      (hl), $5A
                inc     hl
                ld      a, (PRESL)
                ld      (hl), a
                inc     hl
                ld      a, (PRESL+1)
                ld      (hl), a
c_skip:
                ld      hl, (PTR)
                ld      bc, 64
                add     hl, bc
                ld      (PTR), hl
                ld      a, (CIDX)
                inc     a
                ld      (CIDX), a
                ld      (CAP), a
                jp      c_next

finish:
                ld      a, (SUBSLT)
                ld      (EXBRSA), a
                ld      a, (ICOUNT)
                ld      (CAP+9), a
                ld      a, $5A
                ld      (CAP+10), a
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

; plant BC bytes from HL to DE in page 0 of the RAM slot
plant:
                push    bc
                push    hl
                push    de
                ld      e, (hl)
                pop     hl
                push    hl
                ld      a, (RAMSLT)
                call    WRSLT
                pop     de
                pop     hl
                pop     bc
                inc     hl
                inc     de
                dec     bc
                ld      a, b
                or      c
                jr      nz, plant
                ret

tr_ext:
                call    EXTROM
                ret
tr_sub:
                push    ix
                ld      ix, (TGT)
                jp      SUBROM
tr_sub_end:

guard_src:
                push    af
                ld      a, (ICOUNT)
                inc     a
                ld      (ICOUNT), a
                in      a, ($99)
                pop     af
                ei
                ret
guard_end:

stub_src:
                ld      (S_SP), sp
                ld      sp, SDEND
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
                ld      sp, (S_SP)
                ld      a, (SMODE)
                or      a
                ret     z
                dec     a
                jr      z, st_clob
                dec     a
                jr      z, st_ei
                di
                ret
st_ei:
                ei
                ret
st_clob:
                ld      sp, CLOBT
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
                ld      sp, (S_SP)
                ret
stub_end:

; entry values: IX, IY, AF', BC', DE', HL', AF, BC, DE, HL
ent_src:
                dw      $0000, $1A2B, $3C4D, $5E6F, $7081, $92A3, $A700, $B1C2, $4E5F, $9876
; clobber values, same order
clob_src:
                dw      $C1C2, $C3C4, $C5C6, $C7C8, $C9CA, $CBCC, $CDCE, $CFD0, $D1D2, $D3D4

; case: id, kind (0 EXTROM p1, 1 EXTROM p2, 2 SUBROM p1, 3 SUBROM p2), marker sel (SUBROM: 0 $A5A5, 1 $1234),
;       smode, exsel (0 RAM slot, 1 sub-ROM), A, F, iff (0 DI / 1 EI), DE (word), target (word)
cases:
                db      0, 0, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 0 EXTROM, clobber, DI
                db      1, 0, 0, 1, 0, $A7, $FF, 1
                dw      $4E5F, $2000            ; 1 EXTROM, clobber, EI, F $FF
                db      2, 0, 0, 2, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 2 EXTROM, stub EI, entry DI
                db      3, 0, 0, 3, 0, $A7, $00, 1
                dw      $4E5F, $2000            ; 3 EXTROM, stub DI, entry EI
                db      4, 0, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $3ABC            ; 4 EXTROM, clobber, IX $3ABC
                db      5, 0, 0, 0, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 5 EXTROM, stub returns as it was entered (dump only)
                db      6, 1, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 6 EXTROM from page 2 RAM
                db      7, 2, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 7 SUBROM, marker $A5A5, clobber, DI
                db      8, 2, 1, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 8 SUBROM, marker $1234
                db      9, 2, 0, 1, 0, $A7, $00, 1
                dw      $4E5F, $2000            ; 9 SUBROM, EI
                db      10, 2, 0, 2, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 10 SUBROM, stub EI, entry DI
                db      11, 3, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 11 SUBROM from page 2 RAM
                db      12, 0, 0, 1, 1, $A3, $00, 0
                dw      $0506, $014D            ; 12 EXTROM -> real SETPLT: palette 5 := R $A, B $3, G $6
                db      13, 0, 0, 1, 1, $05, $00, 0
                dw      $4E5F, $0149            ; 13 EXTROM -> real GETPLT, A 5: B $A3, C $06 expected
                db      14, 0, 0, 1, 0, $A7, $00, 0
                dw      $4E5F, $2000            ; 14 EXBRSA back to the RAM slot: the stub runs again
                db      15, 2, 0, 1, 1, $05, $00, 1
                dw      $4E5F, $0149            ; 15 SUBROM -> real GETPLT, EI
                db      $EE

                ds      $8000 - $, $FF
