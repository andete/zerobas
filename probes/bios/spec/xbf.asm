; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBF -- D-MSX2SPEC, docs/msx2/main/BIGFIL.md: BIGFIL ($016B, A = the byte, HL = the address, BC = the length) on the
; MSX2 / MSX2+ references. Per case (the table `cases`: HL, BC, SCRMOD, ACPAGE, R#14, interrupts at entry, then four
; VRAM windows -- a 17-bit address and a length): CHGMOD (main $005F), ACPAGE ($FAF6) and the VDP's R#14 by hand;
; every window preset to $5A through the VDP's own ports (R#14 set explicitly); then A $C7, DE $A55A, IX $4321,
; IY $8765, the call; then each window read back the same way. The windows hold every rival's predicted span and the
; bytes just past its ends, so the bytes that read $C7 name the rule and the end bytes the length.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case an 80-byte record from +2:
;   +0 A, +1 F, +2 B, +3 C, +4 D, +5 E, +6 H, +7 L after; +8 IX low, +9 IY low after; +10 R#14 after (debugger);
;   +11 IFF after (1 on); +12 the number of port $99 writes during the call; +13..+15 0; +16..+79 the four windows
;   (16 bytes each; a shorter window leaves zeros).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbf.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0400
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @timeout 120

CHGMOD  equ     $005F
BIGFIL  equ     $016B
ACPAGE  equ     $FAF6
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0
ARMFN   equ     $E8F4
SNAPP   equ     $E900
LOGP    equ     $E902
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
rsave   equ     $E910                   ; AF, BC, DE, HL, IX, IY after (12)
cur     equ     $E920                   ; the case: HL, BC, SCRMOD, ACPAGE, R14, ei, 4 x (lo, mid, hi, len) = 24
SNAPB   equ     $E000
LOGB    equ     $E080                   ; the port log; only its length is recorded (the fill writes no $99 itself)

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                call    ARMFN
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE                     ; the table's end
                jp      z, finish
                ld      de, cur
                ld      bc, 24
                ldir
                ld      (tp), hl
                ld      a, (cur+4)
                call    CHGMOD
                di
                ld      a, (cur+5)
                ld      (ACPAGE), a
                ; preset the windows to $5A
                ld      ix, cur+8
                ld      b, 4
pw_lp:
                push    bc
                call    win_wr
                ld      a, (ix+3)
                or      a
                jr      z, pw_skip
                ld      b, a
pw_b:
                ld      a, $5A
                out     ($98), a
                djnz    pw_b
pw_skip:
                ld      de, 4
                add     ix, de
                pop     bc
                djnz    pw_lp
                ; the VDP's R#14, then the call
                ld      a, (cur+6)
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      a, (cur+7)
                or      a
                jr      z, c_di
                ei
c_di:
                ld      hl, (cur)
                ld      bc, (cur+2)
                ld      de, $A55A
                ld      ix, $4321
                ld      iy, $8765
                ld      a, $C7
                call    BIGFIL
                push    af
                ld      a, i                    ; IFF2 into P/V, before anything else changes it
                di
                ld      (rsave+2), bc
                ld      (rsave+4), de
                ld      (rsave+6), hl
                ld      (rsave+8), ix
                ld      (rsave+10), iy
                push    af
                pop     hl                      ; L bit 2 = IFF2
                pop     bc
                ld      (rsave), bc             ; AF after the call
                ld      a, l
                rrca
                rrca
                and     1
                ld      (rsave+12), a           ; IFF
                ld      hl, (LOGP)
                ld      bc, LOGB
                or      a
                sbc     hl, bc
                ld      a, l
                ld      (rsave+13), a
                ld      hl, 0
                ld      (LOGP), hl
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ; the record
                ld      de, (ptr)
                ld      a, (rsave+1)
                ld      (de), a                 ; A
                inc     de
                ld      a, (rsave)
                ld      (de), a                 ; F
                inc     de
                ld      hl, rsave+3             ; B C D E H L: the high byte first
                ld      b, 3
r_pairs:
                ld      a, (hl)
                ld      (de), a
                inc     de
                dec     hl
                ld      a, (hl)
                ld      (de), a
                inc     de
                inc     hl
                inc     hl
                inc     hl
                djnz    r_pairs
                ld      a, (rsave+8)
                ld      (de), a                 ; IX low
                inc     de
                ld      a, (rsave+10)
                ld      (de), a                 ; IY low
                inc     de
                ld      a, (SNAPB+14)
                ld      (de), a                 ; R#14
                inc     de
                ld      a, (rsave+12)
                ld      (de), a                 ; IFF
                inc     de
                ld      a, (rsave+13)
                ld      (de), a                 ; port $99 writes
                inc     de
                inc     de
                inc     de
                inc     de
                ld      (ptr), de
                ; read the windows back
                ld      ix, cur+8
                ld      b, 4
rw_lp:
                push    bc
                call    win_rd
                ld      de, (ptr)
                ld      a, (ix+3)
                or      a
                jr      z, rw_skip
                ld      b, a
rw_b:
                in      a, ($98)
                ld      (de), a
                inc     de
                djnz    rw_b
rw_skip:
                ld      hl, (ptr)
                ld      bc, 16
                add     hl, bc
                ld      (ptr), hl
                ld      de, 4
                add     ix, de
                pop     bc
                djnz    rw_lp
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                jp      c_next
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

; the window at IX (lo, mid, hi: a 17-bit address) set for writing / reading through the VDP's ports
win_wr:
                ld      c, $40
                jr      win_set
win_rd:
                ld      c, $00
win_set:
                ld      a, (ix+1)               ; A15-A8
                rlca
                rlca
                and     3                       ; A15-A14
                ld      b, a
                ld      a, (ix+2)
                and     1
                add     a, a
                add     a, a
                or      b                       ; R#14 = A16-A14
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, (ix+0)
                out     ($99), a
                ld      a, (ix+1)
                and     $3F
                or      c
                out     ($99), a
                ret

; HL, BC, SCRMOD, ACPAGE, R#14, ei; four windows (address lo, mid, hi; length <= 16)
cases:
                db      $31, $12, $08, $00, 5, 0, $06, 0,  $29, $12, 0, 16,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0     ;  0 VA-1
                db      $20, $C1, $08, $00, 5, 2, $06, 0,  $1C, $C1, 1, 16,  $1C, $C1, 0, 16,  $1C, $41, 1, 16,  $1C, $41, 0, 16 ;  1 VA-3 AC 2
                db      $20, $C1, $08, $00, 5, 3, $06, 0,  $1C, $41, 1, 16,  $1C, $C1, 1, 16,  $1C, $41, 0, 16,  $1C, $C1, 0, 16 ;  2 VA-5 AC 3
                db      $20, $C1, $08, $00, 1, 1, $00, 0,  $1C, $C1, 0, 16,  $1C, $01, 0, 16,  $56, $01, 0, 16,  $1C, $41, 1, 16 ;  3 VA-11 S1 AC 1
                db      $20, $C1, $08, $00, 1, 0, $00, 0,  $1C, $C1, 0, 16,  $1C, $01, 0, 16,  $1C, $41, 0, 16,  $1C, $C1, 1, 16 ;  4 VA-8 S1
                db      $F8, $FF, $10, $00, 5, 0, $06, 0,  $F4, $FF, 0, 12,  $00, $00, 1, 12,  $00, $00, 0, 12,  $F4, $FF, 1, 12 ;  5 BF-1 across $FFFF
                db      $F8, $3F, $10, $00, 5, 0, $06, 0,  $F4, $3F, 0, 12,  $00, $40, 0, 12,  $00, $00, 0, 12,  $00, $C0, 1, 12 ;  6 BF-2 across a 16 KB bank
                db      $F8, $3F, $10, $00, 1, 0, $00, 0,  $F4, $3F, 0, 12,  $00, $40, 0, 12,  $00, $00, 0, 12,  $00, $00, 1, 12 ;  7 BF-3 SCREEN 1
                db      $00, $80, $00, $00, 5, 0, $06, 0,  $FC, $7F, 0, 8,  $FC, $FF, 0, 8,  $FC, $7F, 1, 8,  $00, $80, 1, 4      ;  8 BF-4 BC 0
                db      $00, $80, $01, $00, 5, 0, $06, 0,  $FC, $7F, 0, 8,  $00, $80, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0             ;  9 BF-5 BC 1
                db      $00, $80, $00, $01, 5, 0, $06, 0,  $F8, $80, 0, 16,  $F8, $7F, 0, 16,  0, 0, 0, 0,  0, 0, 0, 0           ; 10 BF-5 BC $100
                db      $31, $12, $08, $00, 5, 0, $06, 1,  $29, $12, 0, 16,  0, 0, 0, 0,  0, 0, 0, 0,  0, 0, 0, 0               ; 11 BF-6 entered with EI
                db      $EE

                ds      $8000 - $, $FF
