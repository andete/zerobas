; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBKYK2 -- D-MSX2SPEC, docs/msx2/sub/KYKLOK.md: the sub-ROM's KYKLOK ($0135) through EXTROM, on the MSX2 / MSX2+
; references, round 2 (round 1: xsubkyk.asm, the same code): KANAST values other than 0 / $FF, PSG R15 preset to
; values whose low bits differ, and MODE ($FAFC) bits flipped for the call (restored after; +26 MODE before, +27 after).
; Its inputs are unknown (MAP lists it, the handbook does not): the candidates are A, the kana / caps cells
; KANAST ($FCAC) and CAPST ($FCAB), row 6 of NEWKEY ($FBEB) / OLDKEY ($FBDA) and row 6 of the key matrix itself
; (bit 3 CAPS, bit 4 KANA / CODE), each given values the others do not share. The probe records what changed.
; Per case (the table `cases`: F, A, KANAST, CAPST, NEWKEY row 6, OLDKEY row 6, matrix row 6 pressed-mask, R15, MODE mask):
; SCREEN 0 stays as the boot left it; interrupts off, SCNCNT := $FF; the key matrix set (@keyset: only row 6, as the
; mask); the cells set; PSG R15 := the preset; MODE ^= the mask; port $AA read; PSG R15 read; the work area $F380-$FFFE copied; the port logs armed (every OUT to
; $AA and $AB, every PSG data write with its register); A F from the table, BC $B1C1, DE $D1E1, HL $4171, IX = $0135; the
; call. Then SP, every register, the interrupt state (read twice), interrupts off, the logs disarmed, port $AA, PSG R15,
; the work-area cells that changed. The probe runs on its own stack (SP := $F37E).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case a $180-byte record from +2:
;   +0 case, +1 A, +2 F, +3 B, +4 C, +5 D, +6 E, +7 H, +8 L, +9 IXh, +10 IXl, +11 IYh, +12 IYl (all after the call),
;   +13 IFF after, +14 port $AA before, +15 after, +16 PSG R15 before, +17 after, +18 the count of changed work-area
;   bytes (255 = 255 or more), +19 the count of OUTs to $AA, +20 to $AB, +21 the PSG log's length in bytes,
;   +22/23 SP before the call, +24/25 SP after, +32..+159 the first 32 changed work-area bytes (address lo, hi, before,
;   after), +160..+191 the bytes OUT to $AA (first 32), +192..+223 to $AB (first 32), +256..+383 the PSG log (5 bytes
;   each: register, byte, time in us, 24-bit).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubkyk2.asm --row msx2all
; Decode: python3 scratchpad/xsubkyk_decode.py scratchpad/AE_xsubkyk2_msx2.out
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the PPI's and PSG's published ports; the key
; matrix set by the debugger.
;
; @cap C000
; @caplen 1300
; @portlog AA E950 E8F1
; @portlog AB E952 E8F1
; @psglog E954 E8F1
; @keyset E8F3 E960
; @timeout 120

EXTROM  equ     $015F
SCNCNT  equ     $F3F6
CAPST   equ     $FCAB
KANAST  equ     $FCAC
NEWK6   equ     $FBEB
OLDK6   equ     $FBDA
MODE    equ     $FAFC
DONE    equ     $C000
CAP     equ     $C001
RECLEN  equ     $0180
WABUF   equ     $DC00
WALEN   equ     $0C7F
ARMFN   equ     $E8F1
KEYFN   equ     $E8F3
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
spb     equ     $E90A
spa     equ     $E90C
wcount  equ     $E910
iffv    equ     $E911
cur     equ     $E920                   ; F, A, KANAST, CAPST, NEWKEY6, OLDKEY6, matrix6, R15, MODE mask = 9
modev   equ     $E912
rsv     equ     $E940                   ; F A C B E D L H IXl IXh IYl IYh after the call
LOGAA   equ     $E950
LOGAB   equ     $E952
LOGPSG  equ     $E954
KLIST   equ     $E960

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $F37E
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $12FF
                ld      (hl), 0
                ldir
                ld      hl, LOGAA
                ld      de, LOGAA+1
                ld      bc, 31
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (ARMFN), a
                ld      (KEYFN), a
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
                cp      $EE
                jp      z, finish
                ld      de, cur
                ld      bc, 9
                ldir
                ld      (tp), hl
                di
                ld      a, $FF
                ld      (SCNCNT), a
                ld      a, (cur+6)
                ld      (KLIST+6), a
                call    KEYFN
                ld      a, (cur+2)
                ld      (KANAST), a
                ld      a, (cur+3)
                ld      (CAPST), a
                ld      a, (cur+4)
                ld      (NEWK6), a
                ld      a, (cur+5)
                ld      (OLDK6), a
                ld      a, 15
                out     ($A0), a
                ld      a, (cur+7)
                out     ($A1), a
                ld      ix, (ptr)
                ld      a, (MODE)
                ld      (modev), a
                ld      (ix+26), a
                ld      b, a
                ld      a, (cur+8)
                xor     b
                ld      (MODE), a
                in      a, ($AA)
                ld      (ix+14), a
                call    rd15
                ld      (ix+16), a
                ld      hl, $F380
                ld      de, WABUF
                ld      bc, WALEN
                ldir
                ld      hl, (ptr)
                ld      bc, 160
                add     hl, bc
                ld      (LOGAA), hl
                ld      bc, 32
                add     hl, bc
                ld      (LOGAB), hl
                ld      bc, 64
                add     hl, bc
                ld      (LOGPSG), hl
                ld      hl, (cur)
                push    hl
                ld      bc, $B1C1
                ld      de, $D1E1
                ld      hl, $4171
                ld      ix, $0135
                pop     af
                ld      (spb), sp
                call    EXTROM
                ld      (spa), sp
                push    af
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ld      a, i
                jp      pe, ie_on
                ld      a, i
ie_on:
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      (iffv), a
                ld      ix, (ptr)
                ld      hl, (LOGAA)
                ld      de, (ptr)
                or      a
                sbc     hl, de
                ld      a, l
                sub     160
                ld      (ix+19), a
                ld      hl, (LOGAB)
                or      a
                sbc     hl, de
                ld      a, l
                sub     192
                ld      (ix+20), a
                ld      hl, (LOGPSG)
                or      a
                sbc     hl, de
                dec     h
                ld      (ix+21), l
                ld      hl, 0
                ld      (LOGAA), hl
                ld      (LOGAB), hl
                ld      (LOGPSG), hl
                pop     hl
                ld      (rsv+10), hl
                pop     hl
                ld      (rsv+8), hl
                pop     hl
                ld      (rsv+6), hl
                pop     hl
                ld      (rsv+4), hl
                pop     hl
                ld      (rsv+2), hl
                pop     hl
                ld      (rsv+0), hl
                call    wadiff
                ld      ix, (ptr)
                ld      a, (MODE)
                ld      (ix+27), a
                ld      a, (modev)
                ld      (MODE), a
                ld      ix, (ptr)
                in      a, ($AA)
                ld      (ix+15), a
                call    rd15
                ld      (ix+17), a
                ld      a, (cidx)
                ld      (ix+0), a
                ld      a, (rsv+1)
                ld      (ix+1), a
                ld      a, (rsv+0)
                ld      (ix+2), a
                ld      a, (rsv+3)
                ld      (ix+3), a
                ld      a, (rsv+2)
                ld      (ix+4), a
                ld      a, (rsv+5)
                ld      (ix+5), a
                ld      a, (rsv+4)
                ld      (ix+6), a
                ld      a, (rsv+7)
                ld      (ix+7), a
                ld      a, (rsv+6)
                ld      (ix+8), a
                ld      a, (rsv+9)
                ld      (ix+9), a
                ld      a, (rsv+8)
                ld      (ix+10), a
                ld      a, (rsv+11)
                ld      (ix+11), a
                ld      a, (rsv+10)
                ld      (ix+12), a
                ld      a, (iffv)
                ld      (ix+13), a
                ld      hl, (spb)
                ld      (ix+22), l
                ld      (ix+23), h
                ld      hl, (spa)
                ld      (ix+24), l
                ld      (ix+25), h
                ld      hl, (ptr)
                ld      bc, RECLEN
                add     hl, bc
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP+1), a
                jp      c_next
finish:
                xor     a
                ld      (KLIST+6), a
                call    KEYFN
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

; rd15: A := PSG R15
rd15:
                ld      a, 15
                out     ($A0), a
                in      a, ($A2)
                ret

; wadiff: the work-area bytes $F380-$FFFE that differ from the copy -> count at +18, first 32 at +32
wadiff:
                ld      iy, (ptr)
                ld      bc, 32
                add     iy, bc
                xor     a
                ld      (wcount), a
                ld      hl, $F380
                ld      de, WABUF
                ld      bc, WALEN
wd_l:
                ld      a, (de)
                cp      (hl)
                call    nz, wd_rec
                inc     hl
                inc     de
                dec     bc
                ld      a, b
                or      c
                jr      nz, wd_l
                ld      ix, (ptr)
                ld      a, (wcount)
                ld      (ix+18), a
                ret
wd_rec:
                ld      a, (wcount)
                cp      255
                jr      z, wr_s
                inc     a
                ld      (wcount), a
wr_s:
                cp      33
                ret     nc
                ld      (iy+0), l
                ld      (iy+1), h
                ld      a, (de)
                ld      (iy+2), a
                ld      a, (hl)
                ld      (iy+3), a
                inc     iy
                inc     iy
                inc     iy
                inc     iy
                ret

; F, A, KANAST, CAPST, NEWKEY row 6, OLDKEY row 6, matrix row 6 (pressed mask), PSG R15 preset, MODE ($FAFC) XOR mask
cases:
                db      $00, $00, $01, $00, $FF, $FF, $00, $00, $00       ; 0 KANAST 1
                db      $00, $00, $40, $00, $FF, $FF, $00, $80, $00       ; 1 KANAST $40
                db      $00, $00, $80, $00, $FF, $FF, $00, $3A, $00       ; 2 KANAST $80
                db      $00, $00, $FE, $00, $FF, $FF, $00, $BA, $00       ; 3 KANAST $FE
                db      $00, $00, $00, $00, $FF, $FF, $00, $15, $00       ; 4 KANAST 0, R15 $15
                db      $00, $00, $FF, $00, $FF, $FF, $00, $95, $00       ; 5 KANAST $FF, R15 $95
                db      $00, $00, $00, $00, $FF, $FF, $00, $4F, $80       ; 6 MODE bit 7 flipped
                db      $00, $00, $00, $00, $FF, $FF, $00, $4F, $01       ; 7 MODE bit 0 flipped
                db      $00, $00, $00, $00, $FF, $FF, $00, $4F, $70       ; 8 MODE bits 4-6 flipped
                db      $00, $00, $00, $00, $FF, $FF, $00, $4F, $0E       ; 9 MODE bits 1-3 flipped
                db      $EE

                ds      $8000 - $, $FF
