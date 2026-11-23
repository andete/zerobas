; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCHGCPU -- D-TRSPEC, docs/turbor/main/CHGCPU.md (and GETCPU.md): the turbo R main ROM's CHGCPU ($0180) on the
; two turbo R references (--row turbor: FS-A1GT vs FS-A1ST).
; Per case (table `cases`: start, A, F, iff, $FCB1 override): CHGCPU(start) -- the only published way to reach a start mode, so the
; setup uses the call under test --, DI; read the S1990's register 6 (OUT $E4 / IN $E5) and port $A7; copy the
; work area $F380-$FFFE to $8000; arm the port logs ($A7, $E4, $E5); every register from the entry table (A, F per
; case); DI or EI; CALL $0180; dump every register; disarm; then: the S1990's registers 0-15, port $A7, GETCPU
; ($0183, entry A $5A), the work-area cells that changed (address, before, after; up to 20), and three timed loops
; on the S1990's system timer (ports $E6 / $E7, reset by OUT $E6): 2000 x `dec de / ld a,d / or e / jr nz` in RAM
; ($EA00), 200 x CALL $0183 (page-0 ROM code), the same `dec de` loop in this cartridge (slot 1, page 1). @cpusnap
; marks: right after the call (A), before / after the RAM loop (T0, T1).
; Record (RECLEN = $C0 bytes from CAP+16 = $C011): +0 case, +1 start, +2 A, +3 F, +4 iff (1 = EI), +5 S1990 R#6
; before, +6 $A7 before, +7 $5A, +8..+33 the dump (as xchknew.asm: [($FFFF) cpl, $A8], IFF 2nd, IFF 1st, HL', DE',
; BC', AF', IY, IX, HL, DE, BC, AF), +34..+48 three cpusnaps (cpu, time us x4), +49..+64 S1990 R#0-R#15 after,
; +65 $A7 after, +66 GETCPU's A, +67 page-2 RAM check ($5A ok), +68..+73 timer counts (RAM loop, BIOS loop, ROM
; loop; LE), +74 / +82 / +90 the $A7 / $E4 / $E5 OUT logs (8 each), +98 work-area change count, +99..+178 changes
; (lo, hi, before, after), +179 / +180 / +181 the three logs' byte counts, +191 $5A.
; CAP+0 = cases done; CAP+1..+10 at INIT before any call: S1990 R#6, $FCB1, $A7, ($FFFD) (2), a cpusnap (5);
; CAP+11..+14 at the end: R#6 before / after a closing CHGCPU($82), $FCB1 and GETCPU's A after it.
; $FFFD / $FFFE := (case, ~case) before each call, read back at +182 / +183 (MAP: CHGCPU's temporary stack pointer);
; +184 the $FCB1 override value (iff bit 1 set: $FCB1 := it after the start call, before the snapshot).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchgcpu.asm --row turbor
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
                db      $80, $00, $00, 0, 0
                db      $80, $01, $00, 0, 0
                db      $80, $02, $00, 0, 0
                db      $80, $80, $00, 0, 0
                db      $80, $81, $00, 0, 0
                db      $80, $82, $00, 0, 0
                db      $81, $00, $00, 0, 0
                db      $81, $01, $00, 0, 0
                db      $81, $02, $00, 0, 0
                db      $81, $80, $00, 0, 0
                db      $81, $81, $00, 0, 0
                db      $81, $82, $00, 0, 0
                db      $82, $00, $00, 0, 0
                db      $82, $01, $00, 0, 0
                db      $82, $02, $00, 0, 0
                db      $82, $80, $00, 0, 0
                db      $82, $81, $00, 0, 0
                db      $82, $82, $00, 0, 0
                db      $80, $04, $00, 0, 0        ; 18: bit 2 set
                db      $80, $05, $00, 0, 0
                db      $80, $06, $00, 0, 0
                db      $80, $41, $00, 0, 0        ; 21: bit 6
                db      $80, $7E, $00, 0, 0        ; 22: bits 6-2 set, mode 2, no LED
                db      $80, $FD, $00, 0, 0        ; 23: every bit but 1: LED, mode 1
                db      $80, $81, $FF, 0, 0        ; 24: F $FF
                db      $80, $81, $00, 1, 0        ; 25: EI
                db      $80, $82, $00, 1, 0        ; 26
                db      $82, $80, $00, 1, 0        ; 27
                db      $00, $01, $00, 0, 0        ; 28: starts without the LED bit
                db      $01, $00, $00, 0, 0
                db      $80, $03, $00, 0, 0        ; 30: mode 3 (undefined)
                db      $80, $83, $00, 0, 0
                db      $80, $FF, $00, 0, 0
                db      $80, $00, $00, 2, $80   ; 33: $FCB1 := $80 (LED bit set in the copy only)
                db      $80, $01, $00, 2, $7D   ; 34: $FCB1 := $7D
                db      $81, $80, $00, 2, $7D   ; 35
                db      $82, $01, $00, 2, $FF   ; 36
                db      $80, $04, $FF, 0, 0     ; 37: rejected, F $FF
                db      $80, $03, $00, 1, 0     ; 38: rejected, EI
                db      $82, $83, $00, 0, 0     ; 39: rejected from R800 DRAM
                db      $EE

                ds      $8000-$, $FF
