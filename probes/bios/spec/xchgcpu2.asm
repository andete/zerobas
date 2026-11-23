; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCHGCPU2 -- D-TRSPEC goldfish pass 1, docs/turbor/main/CHGCPU.md: xchgcpu.asm (same code, same record, same
; decoder: scratchpad/xchgcpu_decode.py) with a new case table for what the first run left unpinned, on the two turbo
; R references (--row turbor: FS-A1GT vs FS-A1ST):
;   0-3   A = $08, $10, $20, $88 from the Z80 (bits 3 / 4 / 5 alone, and bit 3 with the LED bit): the accept rule
;         "A AND $7F in 0-2" against "reject on bit 2 / bit 6 / mode 3 only";
;   4-6   rejected A ($03, $04, $41) from R800 ROM mode;
;   7-9   A = $00, $01, $82 from R800 DRAM mode WITHOUT the LED bit (start CHGCPU($02), then $FCB1 := $00: a
;         CHGCPU($02) keeps bit 7, and the previous case leaves it set -- a first run without the override started
;         these three with $FCB1 = $80);
;   10-11 accepted Z80 -> R800 with the caller's SP = $B000 / $A000 (page 2): ($FFFD) against the caller's SP;
;   12-14 I := $3C on the Z80, then CHGCPU($81); I := $C3 on the R800, then CHGCPU($80); I := $5A on the R800, then
;         CHGCPU($82): what `ld a,i` reads on the CPU the call returns on (the dump's two IFF words are `ld a,i` /
;         `push af`: their high byte is I). After each case's dump I := 0 on the CPU then running.
; Differences from xchgcpu.asm: c_next starts with `ld sp, $E800`; flag (iff) bit 2 -- I := the case's 5th byte before
; the call; bit 3 -- the CALL is made with SP := the 5th byte x 256 (the rest of the case then runs on that stack).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchgcpu2.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM and I/O ports. No ROM byte read.
;
; @cap C000
; @caplen 1F00
; @timeout 200
; @cpusnap 4100 E908
; @cpusnap 4108 E908
; @cpusnap 4110 E908
; @cpusnap 4120 E908
; @portlog A7 E90E 4118
; @portlog E4 E91E 4118
; @portlog E5 E92E 4118

CHGCPU  equ     $0180
GETCPU  equ     $0183
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16
RECLEN  equ     $C0
WSAVE   equ     $8000
WBASE   equ     $F380
WLEN    equ     $FFFF-WBASE             ; $F380..$FFFE

E_SP    equ     $E900
R_SP    equ     $E902
PTR     equ     $E904
CSPTR   equ     $E908                   ; @cpusnap's pointer word
CIDX    equ     $E90B
TP      equ     $E90C
LGA7    equ     $E90E                   ; @portlog pointer words
LGE4    equ     $E91E
LGE5    equ     $E92E
ENTBL   equ     $E940
RDUMP   equ     $E960
RDEND   equ     $E97A
CUR     equ     $E9E0
RAMLP   equ     $EA00
INITS   equ     $EA80                   ; INIT state, 10 bytes

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
snapA:          ret                     ; after CHGCPU
                ds      $4108-$, 0
snapT0:         ret
                ds      $4110-$, 0
snapT1:         ret
                ds      $4118-$, 0
armlog:         ret
                ds      $4120-$, 0
snapI:          ret                     ; at INIT, before anything

main:
                ; INIT state first (nothing called yet): S1990 R#6, $FCB1, $A7, ($FFFD), a cpusnap -- kept in
                ; INITS below the capture, copied to CAP+1..+10 after the clear
                ld      hl, INITS+5
                ld      (CSPTR), hl
                call    snapI
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (INITS+0), a
                ld      a, ($FCB1)
                ld      (INITS+1), a
                in      a, ($A7)
                ld      (INITS+2), a
                ld      hl, ($FFFD)
                ld      (INITS+3), hl
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $1EFE
                ld      (hl), 0
                ldir
                ld      hl, INITS
                ld      de, CAP+1
                ld      bc, 10
                ldir
                ld      hl, 0
                ld      (LGA7), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                call    armlog
                ld      hl, ramsrc
                ld      de, RAMLP
                ld      bc, ramend-ramsrc
                ldir
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, cases
                ld      (TP), hl
c_next:
                ld      sp, $E800
                ld      hl, (TP)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, CUR
                ld      bc, 5
                ldir
                ld      (TP), hl
                ; CUR: start, A, F, iff (bit 0 EI, bit 1 $FCB1 := CUR+4 after the start), $FCB1 value
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
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+5), a
                in      a, ($A7)
                ld      (ix+6), a
                ld      (ix+7), $5A
                ld      a, (CUR+3)
                bit     1, a
                jr      z, c_nfc
                ld      a, (CUR+4)
                ld      ($FCB1), a
c_nfc:
                ; $FFFD / $FFFE (MAP: CHGCPU's temporary stack pointer) := garbage that differs per case
                ld      a, (CIDX)
                ld      h, a
                cpl
                ld      l, a
                ld      ($FFFD), hl
                ; page-2 RAM check
                ld      a, $5A
                ld      (WSAVE), a
                ld      a, (WSAVE)
                ld      (ix+67), a
                ; work-area snapshot
                ld      hl, WBASE
                ld      de, WSAVE
                ld      bc, WLEN
                ldir
                ; arm the logs and the cpusnap pointer
                push    ix
                pop     hl
                ld      de, 34
                add     hl, de
                ld      (CSPTR), hl
                push    ix
                pop     hl
                ld      de, 74
                add     hl, de
                ld      (LGA7), hl
                ld      de, 8
                add     hl, de
                ld      (LGE4), hl
                add     hl, de
                ld      (LGE5), hl
                ; registers
                ld      hl, ent_src
                ld      de, ENTBL
                ld      bc, 20
                ldir
                ld      a, (CUR+2)
                ld      (ENTBL+12), a           ; F
                ld      a, (CUR+1)
                ld      (ENTBL+13), a           ; A
                ld      a, (CUR+3)
                bit     2, a
                jr      z, c_noi
                ld      a, (CUR+4)
                ld      i, a
c_noi:
                ld      a, (CUR+3)
                and     1
                jr      z, c_di
                ei
c_di:
                ld      (E_SP), sp
                ld      a, (CUR+3)
                bit     3, a
                jr      z, c_nosp
                ld      a, (CUR+4)
                ld      (E_SP+1), a
                xor     a
                ld      (E_SP), a
c_nosp:
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
                call    CHGCPU
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
                xor     a
                ld      i, a
                ; disarm the logs, keep their counts
                call    logcounts
                ; dump
                ld      hl, (PTR)
                ld      bc, 8
                add     hl, bc
                ex      de, hl
                ld      hl, RDUMP
                ld      bc, 26
                ldir
                ld      ix, (PTR)
                ; S1990 R#0-R#15
                ld      b, 0
s_lp:
                ld      a, b
                out     ($E4), a
                in      a, ($E5)
                push    ix
                pop     hl
                ld      de, 49
                add     hl, de
                ld      e, b
                ld      d, 0
                add     hl, de
                ld      (hl), a
                inc     b
                ld      a, b
                cp      16
                jr      nz, s_lp
                in      a, ($A7)
                ld      (ix+65), a
                ld      a, $5A
                call    GETCPU
                di
                ld      ix, (PTR)
                ld      (ix+66), a
                ; work-area changes
                call    wdiff
                ; timed loops
                ld      ix, (PTR)
                call    snapT0
                out     ($E6), a
                call    RAMLP
                call    rdtimer
                ld      (ix+68), l
                ld      (ix+69), h
                call    snapT1
                out     ($E6), a
                ld      b, 200
b_lp:
                push    bc
                call    GETCPU
                pop     bc
                djnz    b_lp
                di
                call    rdtimer
                ld      (ix+70), l
                ld      (ix+71), h
                out     ($E6), a
                call    romloop
                call    rdtimer
                ld      (ix+72), l
                ld      (ix+73), h
                ld      iy, (PTR)
                ld      de, 128
                add     iy, de
                ld      (iy+RECLEN-129), $5A
                ld      hl, ($FFFD)
                ld      (iy+54), l
                ld      (iy+55), h
                ld      a, (CUR+4)
                ld      (iy+56), a
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
                ld      a, 6                    ; CAP+11 / +12: R#6 before / after the closing CHGCPU($82),
                out     ($E4), a                ; +13 $FCB1 after, +14 GETCPU's A after
                in      a, ($E5)
                ld      (CAP+11), a
                ld      a, $82
                call    CHGCPU
                di
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (CAP+12), a
                ld      a, ($FCB1)
                ld      (CAP+13), a
                call    GETCPU
                di
                ld      (CAP+14), a
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; the three logs' byte counts to +179..+181, pointer words back to 0
logcounts:
                ld      iy, (PTR)
                push    iy
                pop     de
                ld      bc, 128
                add     iy, bc
                ld      hl, (LGA7)
                or      a
                sbc     hl, de
                ld      a, l
                sub     74
                ld      (iy+51), a
                ld      hl, (LGE4)
                or      a
                sbc     hl, de
                ld      a, l
                sub     82
                ld      (iy+52), a
                ld      hl, (LGE5)
                or      a
                sbc     hl, de
                ld      a, l
                sub     90
                ld      (iy+53), a
                ld      hl, 0
                ld      (LGA7), hl
                ld      (LGE4), hl
                ld      (LGE5), hl
                ret

; HL := the S1990 timer (low $E6, high $E7)
rdtimer:
                in      a, ($E6)
                ld      l, a
                in      a, ($E7)
                ld      h, a
                ret

; compare $F380..$FFFE with the copy; up to 20 changes to +99, the count to +98
wdiff:
                ld      ix, (PTR)
                push    ix
                pop     hl
                ld      de, 99
                add     hl, de
                ex      de, hl                  ; DE = out
                ld      hl, WBASE
                ld      bc, WSAVE
                xor     a
                ld      (ix+98), a
w_lp:
                ld      a, (bc)
                cp      (hl)
                jr      z, w_same
                push    af
                ld      a, (ix+98)
                inc     a
                jr      z, w_full
                ld      (ix+98), a
                cp      21
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
                or      l
                jr      nz, w_lp1
                ret
w_lp1:
                ld      a, h
                cp      $FF
                jr      nz, w_lp
                ld      a, l
                cp      $FF
                jr      nz, w_lp
                ret

romloop:
                ld      de, 2000
r_lp:
                dec     de
                ld      a, d
                or      e
                jr      nz, r_lp
                ret

ramsrc:
                ld      de, 2000
                dec     de
                ld      a, d
                or      e
                jr      nz, $-3
                ret
ramend:

ent_src:        dw      $1A1B, $1C1D            ; IX, IY
                dw      $2829, $2A2B, $2C2D, $2E2F ; AF', BC', DE', HL'
                dw      $3839, $3A3B, $3C3D, $3E3F ; AF (A, F per case), BC, DE, HL

; start, A, F, iff (bit 0 EI, bit 1 $FCB1 override), $FCB1 value
cases:
                db      $80, $08, $00, 0, 0     ; 0: bit 3 alone
                db      $80, $10, $00, 0, 0     ; 1: bit 4 alone
                db      $80, $20, $00, 0, 0     ; 2: bit 5 alone
                db      $80, $88, $00, 0, 0     ; 3: bit 3 with the LED bit
                db      $81, $03, $00, 0, 0     ; 4: rejected from R800 ROM
                db      $81, $04, $00, 0, 0     ; 5
                db      $81, $41, $00, 0, 0     ; 6
                db      $02, $00, $00, 2, $00   ; 7: from R800 DRAM without the LED bit ($FCB1 := $00)
                db      $02, $01, $00, 2, $00   ; 8
                db      $02, $82, $00, 2, $00   ; 9
                db      $80, $81, $00, 8, $B0   ; 10: SP = $B000 at the CALL
                db      $80, $81, $00, 8, $A0   ; 11: SP = $A000
                db      $80, $81, $00, 4, $3C   ; 12: I := $3C on the Z80, to the R800
                db      $81, $80, $00, 4, $C3   ; 13: I := $C3 on the R800, to the Z80
                db      $81, $82, $00, 4, $5A   ; 14: I := $5A on the R800, to R800 DRAM
                db      $EE

                ds      $8000-$, $FF
