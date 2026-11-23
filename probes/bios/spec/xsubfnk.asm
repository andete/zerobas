; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBFNK -- D-MSX2SPEC, docs/msx2/sub/DSPFNK.md: the sub-ROM's DSPFNK ($011D) through EXTROM, on the MSX2 / MSX2+
; references. FNKSTR ($F87F, 10 x 16) := key k's string = 15 x ('A' + k) -- so the screen says which keys and how many
; characters. Per case (the table `cases`: SCRMOD, LINL40 / LINL32, the VRAM address read back, its length): CHGMOD
; (main $005F) with the width set first, CNSDFG ($F3DE) := 0, CRTCNT 24, interrupts off, the call, then CNSDFG, A / F /
; IFF and the VRAM span (the key row of the text modes; SCREEN 5's line 204, in case it draws on the bitmap).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a 112-byte record from +2:
;   +0 the case, +1 A, +2 F, +3 IFF, +4 CNSDFG after, +5..+15 0, +16..+111 the span (up to 96 bytes).
; Goldfish pass 1 (2026-11-23): cases 4-19 appended (0-3 unchanged). The case table now gives each case SCRMOD,
; LINL40, LINL32, a LINLEN written after CHGMOD (0 = none), CRTCNT, CNSDFG on entry, the FNKSTR set (0: key k =
; 15 x ('A' + k); 1: 3 x ('A' + k); 2: 'A' + k then "123456789abcdef", 16 bytes, no 0), flags (bit 0: ALL 128 KB
; of VRAM := an address-dependent pattern before the call and compared after it; bit 1: entered with EI), the span.
; With bit 0 the record's +5..+7 hold the number of VRAM bytes that differ from the pattern after the call (24-bit),
; +8..+10 the first such address, +11..+13 the last (17-bit, low byte first), +14 LINLEN after; the pattern at
; 17-bit address bank x $4000 + o is (o low) XOR (o high) XOR key[bank] (decoder: xsubfnk_decode.py). IFF is read
; twice (spec-method §3a).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubfnk.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports.
;
; @cap C000
; @caplen 0900
; @timeout 300

CHGMOD  equ     $005F
EXTROM  equ     $015F
FNKSTR  equ     $F87F
CNSDFG  equ     $F3DE
LINLEN  equ     $F3B0
DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910
cnt     equ     $E914                   ; 3: mismatches
first   equ     $E917                   ; 3
last    equ     $E91A                   ; 3
cur     equ     $E920                   ; SCRMOD, LINL40, LINL32, LINLEN, CRTCNT, CNSDFG, set, flags, address (2), length

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $08FF
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 11
                ldir
                ld      (tp), hl
                ld      a, (cur+1)
                ld      ($F3AE), a              ; LINL40
                ld      a, (cur+2)
                ld      ($F3AF), a              ; LINL32
                ld      a, (cur)
                call    CHGMOD
                di
                ld      a, (cur+3)
                or      a
                jr      z, c_nolen
                ld      (LINLEN), a
c_nolen:
                ld      a, (cur+6)              ; the FNKSTR set
                ld      hl, fkeys
                ld      bc, 160
                or      a
                jr      z, c_set
                ld      hl, fkeys1
                dec     a
                jr      z, c_set
                ld      hl, fkeys2
c_set:
                ld      de, FNKSTR
                ldir
                ld      a, (cur+7)
                and     1
                call    nz, vfill
                ld      a, (cur+5)
                ld      (CNSDFG), a
                ld      a, (cur+4)
                ld      ($F3B1), a              ; CRTCNT
                ld      a, (cur+7)
                and     2
                jr      z, c_di
                ei
c_di:
                ld      ix, $011D
                call    EXTROM
                push    af
                ld      a, i
                jp      pe, c_iff
                ld      a, i                    ; the second read decides (spec-method 3a)
c_iff:
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
                ld      a, (CNSDFG)
                ld      (de), a
                ld      a, (cur+7)
                and     1
                jr      z, c_span
                call    vscan
                ld      hl, cnt
                ld      de, (ptr)
                inc     de
                inc     de
                inc     de
                inc     de
                inc     de
                ld      bc, 9
                ldir
                ld      a, (LINLEN)
                ld      (de), a
c_span:
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ex      de, hl
                ld      hl, (cur+8)
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
                ld      a, (cur+10)
                ld      b, a
c_rd:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    c_rd
                ld      hl, (ptr)
                ld      bc, 112
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

; C := the pattern key of bank B
bkey:
                push    hl
                push    de
                ld      hl, keys
                ld      e, b
                ld      d, 0
                add     hl, de
                ld      c, (hl)
                pop     de
                pop     hl
                ret
keys:           db      $5A, $7F, $14, $31, $C6, $E3, $88, $AD

; R#14 := B, the VRAM address 0 for writing (A = $40) or reading (A = $00)
vbank:
                push    af
                ld      a, b
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                xor     a
                out     ($99), a
                pop     af
                out     ($99), a
                ret

; all 128 KB := the pattern
vfill:
                ld      b, 0
vf_bank:
                ld      a, $40
                call    vbank
                call    bkey
                ld      hl, 0
vf_lp:
                ld      a, l
                xor     h
                xor     c
                out     ($98), a
                inc     hl
                ld      a, h
                cp      $40
                jr      nz, vf_lp
                inc     b
                ld      a, b
                cp      8
                jr      nz, vf_bank
                ret

; all 128 KB compared with the pattern: cnt, first, last
vscan:
                ld      hl, cnt
                ld      de, cnt+1
                ld      bc, 8
                ld      (hl), 0
                ldir
                ld      b, 0
vs_bank:
                xor     a
                call    vbank
                call    bkey
                ld      hl, 0
vs_lp:
                in      a, ($98)
                xor     l
                xor     h
                xor     c
                jr      nz, vs_bad
vs_nx:
                inc     hl
                ld      a, h
                cp      $40
                jr      nz, vs_lp
                inc     b
                ld      a, b
                cp      8
                jr      nz, vs_bank
                xor     a
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ret
vs_bad:
                push    de
                ld      a, b                    ; D := the middle byte, E := the high
                and     3
                rrca
                rrca
                or      h
                ld      d, a
                ld      a, b
                srl     a
                srl     a
                ld      e, a
                ld      a, (cnt)
                push    hl
                ld      hl, cnt+1
                or      (hl)
                inc     hl
                or      (hl)
                pop     hl
                jr      nz, vs_nf
                ld      a, l
                ld      (first), a
                ld      a, d
                ld      (first+1), a
                ld      a, e
                ld      (first+2), a
vs_nf:
                ld      a, l
                ld      (last), a
                ld      a, d
                ld      (last+1), a
                ld      a, e
                ld      (last+2), a
                push    hl
                ld      hl, cnt
                inc     (hl)
                jr      nz, vs_c
                inc     hl
                inc     (hl)
                jr      nz, vs_c
                inc     hl
                inc     (hl)
vs_c:
                pop     hl
                pop     de
                jr      vs_nx

fkeys:
                db      "AAAAAAAAAAAAAAA", 0
                db      "BBBBBBBBBBBBBBB", 0
                db      "CCCCCCCCCCCCCCC", 0
                db      "DDDDDDDDDDDDDDD", 0
                db      "EEEEEEEEEEEEEEE", 0
                db      "FFFFFFFFFFFFFFF", 0
                db      "GGGGGGGGGGGGGGG", 0
                db      "HHHHHHHHHHHHHHH", 0
                db      "IIIIIIIIIIIIIII", 0
                db      "JJJJJJJJJJJJJJJ", 0
fkeys1:
                db      "AAA", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "BBB", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "CCC", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "DDD", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "EEE", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "FFF", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "GGG", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "HHH", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "III", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "JJJ", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
fkeys2:
                db      "A123456789abcdef"
                db      "B123456789abcdef"
                db      "C123456789abcdef"
                db      "D123456789abcdef"
                db      "E123456789abcdef"
                db      "F123456789abcdef"
                db      "G123456789abcdef"
                db      "H123456789abcdef"
                db      "I123456789abcdef"
                db      "J123456789abcdef"

; SCRMOD, LINL40, LINL32, LINLEN (0 = as CHGMOD left it), CRTCNT, CNSDFG, FNKSTR set, flags, span address, length
cases:
                db      0, 40, 40, 0, 24, 0, 0, 0
                dw      $0398
                db      40      ; 0 SCREEN 0 width 40, row 23
                db      0, 80, 80, 0, 24, 0, 0, 0
                dw      $0730
                db      80      ; 1 SCREEN 0 width 80, row 23
                db      1, 32, 32, 0, 24, 0, 0, 0
                dw      $1AE0
                db      32      ; 2 SCREEN 1, row 23
                db      5, 40, 40, 0, 24, 0, 0, 0
                dw      $6600
                db      96      ; 3 SCREEN 5, line 204
                ; goldfish pass 1 (2026-11-23)
                db      0, 40, 32, 0, 24, 0, 1, 1
                dw      $0398
                db      40      ; 4 SCREEN 0 width 40, 3-character strings, VRAM diffed
                db      0, 80, 32, 0, 24, 0, 1, 1
                dw      $0730
                db      80      ; 5 SCREEN 0 width 80, 3-character strings
                db      0, 80, 32, 0, 24, 0, 2, 1
                dw      $0730
                db      80      ; 6 SCREEN 0 width 80, 16-character strings, no 0
                db      0, 37, 32, 0, 24, 0, 0, 1
                dw      $0398
                db      40      ; 7 SCREEN 0 width 37
                db      1, 40, 29, 0, 24, 0, 0, 1
                dw      $1AE0
                db      32      ; 8 SCREEN 1, LINL32 29 (LINL40 40)
                db      0, 40, 32, 36, 24, 0, 0, 1
                dw      $0398
                db      40      ; 9 SCREEN 0, LINL40 40, LINLEN := 36 after CHGMOD
                db      0, 40, 32, 0, 13, 0, 0, 1
                dw      $01E0
                db      40      ; 10 SCREEN 0 width 40, CRTCNT 13: row 12
                db      0, 40, 32, 0, 24, $FF, 0, 1
                dw      $0398
                db      40      ; 11 SCREEN 0 width 40, CNSDFG $FF on entry
                db      0, 40, 32, 0, 24, 0, 0, 2
                dw      $0398
                db      40      ; 12 SCREEN 0 width 40, entered with EI
                db      5, 40, 32, 0, 24, 0, 0, 1
                dw      $6600
                db      96      ; 13 SCREEN 5, VRAM diffed
                db      2, 40, 32, 0, 24, 0, 0, 1
                dw      $1AE0
                db      32      ; 14 SCREEN 2
                db      3, 40, 32, 0, 24, 0, 0, 1
                dw      $0AE0
                db      32      ; 15 SCREEN 3
                db      4, 40, 32, 0, 24, 0, 0, 1
                dw      $1AE0
                db      32      ; 16 SCREEN 4
                db      6, 40, 32, 0, 24, 0, 0, 1
                dw      $6600
                db      96      ; 17 SCREEN 6, line 204
                db      7, 40, 32, 0, 24, 0, 0, 1
                dw      $CC00
                db      96      ; 18 SCREEN 7, line 204
                db      8, 40, 32, 0, 24, 0, 0, 1
                dw      $CC00
                db      96      ; 19 SCREEN 8, line 204
                db      $EE

                ds      $8000 - $, $FF
