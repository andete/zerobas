; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBPCH2 -- D-MSX2SPEC, docs/msx2/sub/PUTCHR.md, round 2: the sub-ROM entry $0139 (PUTCHR) through EXTROM, on the
; MSX2 / MSX2+ references. Round 1 (xsubpch.asm) saw no VRAM change and HL coming back $FBF1, $FBF2, ... on the
; HB-F900 / FS-A1WSX: the key buffer KEYBUF ($FBF0, 40 bytes) with PUTPNT ($F3F8) / GETPNT ($F3FA).
; Per case (table `cases`): SCREEN 0 (CHGMOD $005F, width 40); DI; KEYBUF[i] := $80 + i, $FC18..$FC1A := $E1 $E2 $E3;
; PUTPNT / GETPNT from the table; BC $B1C2, DE $4E5F, HL $140C, IY $1A2B, A from the table, F $C5 (stack); DI or EI;
; IX := $0139; CALL EXTROM ($015F). Recorded: the registers, IFF (read twice), PUTPNT, GETPNT, CSRX, CSRY, KEYBUF and
; $FC18..$FC1A; then CHSNS ($009C): whether a character waits, and if one does CHGET ($009F)'s character and the
; pointers after it.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case an 80-byte record from +2:
;   +0 case, +1 A, +2 F, +3 IFF, +4..+13 C B E D L H IXl IXh IYl IYh, +14 IFF first read,
;   +16 PUTPNT (2), +18 GETPNT (2), +20 CSRX, +21 CSRY, +22 CHSNS (1 = a character waits), +23 CHGET's character,
;   +24 PUTPNT, +26 GETPNT after CHGET, +28 KEYBUF (40), +68 $FC18..$FC1A, +79 $5E (sentinel).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubpch2.asm --row msx2all
; Decode: python3 scratchpad/xsubpch_decode.py --r2 scratchpad/AE_xsubpch2_msx2.out
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells. No ROM byte read.
;
; @cap C000
; @caplen 0400
; @timeout 120

CHGMOD  equ     $005F
CHSNS   equ     $009C
CHGET   equ     $009F
EXTROM  equ     $015F
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA
KEYBUF  equ     $FBF0
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     80
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cur     equ     $E930                   ; A, PUTPNT (2), GETPNT (2), flags = 6

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FE
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
                ld      a, 40
                ld      ($F3AE), a
                xor     a
                call    CHGMOD
c_next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 6
                ldir
                ld      (tp), hl
                ld      hl, KEYBUF
                ld      b, 40
                ld      a, $80
c_kb:
                ld      (hl), a
                inc     hl
                inc     a
                djnz    c_kb
                ld      (hl), $E1
                inc     hl
                ld      (hl), $E2
                inc     hl
                ld      (hl), $E3
                ld      hl, (cur+1)
                ld      (PUTPNT), hl
                ld      hl, (cur+3)
                ld      (GETPNT), hl
                ; the call
                ld      ix, $0139
                ld      a, (cur)
                ld      h, a
                ld      l, $C5
                push    hl
                ld      bc, $B1C2
                ld      de, $4E5F
                ld      hl, $140C
                ld      iy, $1A2B
                ld      a, (cur+5)
                bit     0, a
                jr      z, c_di
                pop     af
                ei
                jr      c_go
c_di:
                pop     af
c_go:
                call    EXTROM
                push    iy
                push    ix
                push    hl
                push    de
                push    bc
                push    af
                ld      a, i
                push    af
                jp      pe, c_ion
                ld      a, i                    ; an "off" is read again (the NMOS ld a,i erratum)
c_ion:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+2), a
                pop     hl
                ld      a, l
                ld      (rsave+13), a
                pop     hl
                ld      (rsave), hl
                pop     hl
                ld      (rsave+3), hl
                pop     hl
                ld      (rsave+5), hl
                pop     hl
                ld      (rsave+7), hl
                pop     hl
                ld      (rsave+9), hl
                pop     hl
                ld      (rsave+11), hl
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
                ld      hl, rsave+3
                ld      bc, 10
                ldir
                ld      a, (rsave+13)
                rrca
                rrca
                and     1
                ld      (de), a
                inc     de
                inc     de                      ; +16
                ld      hl, (PUTPNT)
                ex      de, hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      de, (GETPNT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      a, ($F3DD)
                ld      (hl), a                 ; +20 CSRX
                inc     hl
                ld      a, ($F3DC)
                ld      (hl), a                 ; +21 CSRY
                ld      hl, (ptr)
                ld      bc, 28
                add     hl, bc
                ex      de, hl
                ld      hl, KEYBUF
                ld      bc, 43
                ldir                            ; +28 KEYBUF, +68 $FC18..$FC1A
                ; does a character wait?
                call    CHSNS
                di
                ld      hl, (ptr)
                ld      bc, 22
                add     hl, bc
                jr      z, c_none
                ld      (hl), 1
                push    hl
                call    CHGET
                di
                pop     hl
                inc     hl
                ld      (hl), a                 ; +23
                inc     hl
                ld      de, (PUTPNT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      de, (GETPNT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
c_none:
                ld      hl, (ptr)
                ld      bc, RECLEN-1
                add     hl, bc
                ld      (hl), $5E
                inc     hl
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                ld      hl, KEYBUF
                ld      (PUTPNT), hl
                ld      (GETPNT), hl
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

; A, PUTPNT, GETPNT, flags (b0 EI)
cases:
                db      $51
                dw      $FBF0, $FBF0
                db      0                       ;  0 empty buffer
                db      $52
                dw      $FC05, $FBF0
                db      0                       ;  1 PUTPNT mid-buffer
                db      $53
                dw      $FC17, $FC00
                db      0                       ;  2 PUTPNT at the last byte
                db      $54
                dw      $FBF5, $FBF6
                db      0                       ;  3 full (PUTPNT + 1 = GETPNT)
                db      $55
                dw      $FC17, $FBF0
                db      0                       ;  4 full across the wrap
                db      $00
                dw      $FBF0, $FBF0
                db      0                       ;  5 A 0
                db      $0D
                dw      $FBF0, $FBF0
                db      0                       ;  6 A CR
                db      $FF
                dw      $FBF0, $FBF0
                db      0                       ;  7 A $FF
                db      $51
                dw      $FBF0, $FBF0
                db      1                       ;  8 EI
                db      $56
                dw      $FC18, $FBF0
                db      0                       ;  9 PUTPNT past the buffer
                db      $57
                dw      $FC10, $FC10
                db      0                       ; 10 empty, mid-buffer
                db      $EE

                ds      $8000 - $, $FF
