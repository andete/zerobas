; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XVA3 -- D-MSX2SPEC, docs/msx2/main/README.md "The shared VRAM address matrix", goldfish pass 1 (2026-11-23): the
; cases xva.asm left out. NSETRD ($016E), NSETWR ($0171), NRDVRM ($0174), NWRVRM ($0177) and BIGFIL ($016B, BC 1) on
; the MSX2 / MSX2+ references, per case (the table `cases`):
;   SCREEN 6 (VA-1 / VA-3 / VA-5, ACPAGE 1); SCREEN 5 ACPAGE 1 with 128 KB; ACPAGE 4 / 5 / $40 / $FF in SCREEN 5 and
;   4 / $40 / $80 / $FF in SCREEN 1; SCREEN 8 / 7 with ACPAGE 2 / 3; VA-3 with MODE bits 2-1 := 00 and 11; SCREEN 1
;   ACPAGE 1 with DPPAGE 2; VC-1 (HL $FFFF, SCREEN 5) and VC-2 (HL $3FFF, SCREEN 1); entry A / F varied (S-REGS);
;   ACPAGE 2 / 4 with H $FF in SCREEN 8 / 5 (does H + the page's high bits carry into A16?).
; Per case and call: LINL40, CHGMOD (main $005F, interrupts then off); MODE ($FAFC) put back to its BOOT value (xva.asm
; let VA-12's MODE leak into its later cases), then its bits 2-1 := the case's where given; ACPAGE, DPPAGE, $FFED by
; hand; $FFE7-$FFF6 copied; on the cases marked `sum`, the whole 128 KB of VRAM summed (16-bit sum and XOR, through
; port $98, R#14 set per 16 KB) and the byte at the case's expected address read; the VDP's R#14 through port $99; the
; port logs armed ($99, $98, $9A, $9B: every OUT); then S-REGS -- BC $5AA5 (BIGFIL: 1), DE $A55A, IX $4321, IY $8765,
; BC' $1111, DE' $2222, HL' $3333, AF' $4444, A / F the case's (pop af) -- interrupts OFF, the call. After it: AF,
; `ld a, i` twice (IFF2), every register; the logs disarmed; the VDP's state through the debugger (@vdpfull); then the
; probe writes R#7 := $5A (port $99: $5A, $87) and takes a second snapshot -- a lone byte the call left in the port $99
; latch would pair with the $5A; a status read then resets the latch. Then $FFE7-$FFF6 compared, and on `sum` cases
; the sums and the expected byte again. On `sum` cases the probe first writes $5A at the expected address itself, so
; the call's byte ($C7) always differs from what was there.
; The capture (CAP = 9001): +0 $A5 when finished, +1 the case count; per case x call a 64-byte record from +2:
;   +0 A, +1 F after; +2 R#14 after; +3 / +4 the VRAM pointer after (low, high); +5 the port $99 writes in the call;
;   +6..+12 the first seven; +13 $FFED after; +14 the case; +15 the call (0 NSETRD, 1 NSETWR, 2 NRDVRM, 3 NWRVRM,
;   4 BIGFIL); +16 / +17 F from `ld a, i` twice (bit 2 IFF2); +18 the port $98 writes, +19 the first of them; +20 the
;   port $9A writes; +21 the port $9B writes; +22 BC, +24 DE, +26 HL, +28 IX, +30 IY, +32 BC', +34 DE', +36 HL',
;   +38 AF' after (words, little-endian; AF' as F, A); +40 R#7 after the probe's R#7 write; +41 / +42 the pointer then;
;   +43 R#14 then; +44 / +45 the VRAM sum before, +46 the XOR before, +47 / +48 the sum after, +49 the XOR after,
;   +50 the expected address's byte before, +51 after (sum cases; else 0); +52 MODE at the call, +53 SCRMOD, +54
;   ACPAGE after, +55 DPPAGE after; +56 / +57 a mask of the save cells $FFE7-$FFF6 that changed (bit n = $FFE7 + n);
;   +58 MODE after; +59..+63 0.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xva3.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers and pointer read by the debugger (hardware state, not a ROM byte).
;
; @cap 9000
; @caplen 2500
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @portlog 98 E90C E8F4
; @portlog 9A E90E E8F4
; @portlog 9B E912 E8F4
; @timeout 300

CHGMOD  equ     $005F
LINL40  equ     $F3AE
SCRMOD  equ     $FCAF
DPPAGE  equ     $FAF5
ACPAGE  equ     $FAF6
MODE    equ     $FAFC
SVC     equ     $FFE7                   ; R#8-R#23's save cells
SV14    equ     $FFED
DONE    equ     $9000
CAP     equ     $9001
SNAPFN  equ     $E8F0                   ; a `ret`: the debugger's snapshot point (@vdpfull)
ARMFN   equ     $E8F4                   ; a `ret`: the port logs' arming point (@portlog)
TRAMP   equ     $E8F8                   ; `jp nnnn`: the call under test
SNAPP   equ     $E900                   ; @vdpfull's pointer word
LOGP    equ     $E902                   ; port $99 log pointer
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
call_i  equ     $E909
bootmd  equ     $E90A
LOGP98  equ     $E90C
LOGP9A  equ     $E90E
spsave  equ     $E910
LOGP9B  equ     $E912
cur     equ     $E920                   ; the case (16 bytes)
regs    equ     $E940                   ; AF, iff1, iff2 (as F words), BC, DE, HL, IX, IY, BC', DE', HL', AF' (24)
sums    equ     $E960                   ; sum0 (2), xor0, sum1 (2), xor1, old, new
lend    equ     $E970                   ; the logs' end pointers: $99, $98, $9A, $9B
svb     equ     $E980                   ; $FFE7-$FFF6 before (16)
mask    equ     $E990
SNAPB   equ     $E000                   ; 114 bytes
LOGB    equ     $E080                   ; port $99 log, 64 bytes
SNAPB2  equ     $E200                   ; the second snapshot
LOGB98  equ     $E300
LOGB9A  equ     $E340
LOGB9B  equ     $E380

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $24FF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      a, $C3
                ld      (TRAMP), a
                ld      hl, 0
                ld      (LOGP), hl
                ld      (LOGP98), hl
                ld      (LOGP9A), hl
                ld      (LOGP9B), hl
                call    ARMFN
                ld      a, (MODE)
                ld      (bootmd), a
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
                ld      bc, 16
                ldir
                ld      (tp), hl
                xor     a
                ld      (call_i), a
k_next:
                ld      a, (cur+3)
                ld      (LINL40), a
                ld      a, (cur+2)
                call    CHGMOD
                di
                ; MODE: the boot value, then the case's bits 2-1
                ld      a, (bootmd)
                ld      (MODE), a
                ld      a, (cur+8)
                cp      $FF
                jr      z, k_nomode
                ld      b, a
                ld      a, (MODE)
                and     $F9
                or      b
                ld      (MODE), a
k_nomode:
                ld      a, (cur+4)
                ld      (ACPAGE), a
                ld      a, (cur+5)
                ld      (DPPAGE), a
                ld      a, (cur+7)
                ld      (SV14), a
                ld      hl, SVC
                ld      de, svb
                ld      bc, 16
                ldir
                ld      hl, sums
                ld      de, sums+1
                ld      bc, 7
                ld      (hl), 0
                ldir
                ld      a, (cur+11)
                or      a
                jr      z, k_nosum0
                call    wrexp                   ; the expected address := $5A (no call's byte)
                call    vsum
                ld      (sums), hl
                ld      a, b
                ld      (sums+2), a
                call    rdexp
                ld      (sums+6), a
k_nosum0:
                ; the call's address into the trampoline
                ld      a, (call_i)
                add     a, a
                ld      e, a
                ld      d, 0
                ld      hl, targets
                add     hl, de
                ld      a, (hl)
                ld      (TRAMP+1), a
                inc     hl
                ld      a, (hl)
                ld      (TRAMP+2), a
                ; the VDP's R#14
                ld      a, (cur+6)
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ; arm the logs
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      hl, LOGB98
                ld      (LOGP98), hl
                ld      hl, LOGB9A
                ld      (LOGP9A), hl
                ld      hl, LOGB9B
                ld      (LOGP9B), hl
                ; S-REGS
                exx
                ld      bc, $1111
                ld      de, $2222
                ld      hl, $3333
                exx
                ld      hl, $4444
                push    hl
                pop     af
                ex      af, af'
                ld      a, (cur+9)
                ld      h, a
                ld      a, (cur+10)
                ld      l, a
                push    hl                      ; the entry AF
                ld      hl, (cur)
                ld      bc, $5AA5
                ld      de, $A55A
                ld      ix, $4321
                ld      iy, $8765
                pop     af
                call    TRAMP
                push    af
                ld      a, i
                push    af
                ld      a, i
                push    af
                di
                ld      (spsave), hl
                ld      hl, (LOGP)
                ld      (lend), hl
                ld      hl, (LOGP98)
                ld      (lend+2), hl
                ld      hl, (LOGP9A)
                ld      (lend+4), hl
                ld      hl, (LOGP9B)
                ld      (lend+6), hl
                ld      hl, 0
                ld      (LOGP), hl
                ld      (LOGP98), hl
                ld      (LOGP9A), hl
                ld      (LOGP9B), hl
                ld      hl, (spsave)
                ld      (regs+10), hl
                ld      (regs+6), bc
                ld      (regs+8), de
                ld      (regs+12), ix
                ld      (regs+14), iy
                exx
                ld      (regs+16), bc
                ld      (regs+18), de
                ld      (regs+20), hl
                exx
                ex      af, af'
                push    af
                pop     hl
                ld      (regs+22), hl
                ex      af, af'
                pop     hl
                ld      (regs+4), hl            ; the second `ld a, i`
                pop     hl
                ld      (regs+2), hl            ; the first
                pop     hl
                ld      (regs), hl              ; AF after the call
                ; the VDP's state
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN
                ; R#7 := $5A, a second snapshot, then reset the latch
                ld      a, $5A
                out     ($99), a
                ld      a, $87
                out     ($99), a
                ld      hl, SNAPB2
                ld      (SNAPP), hl
                call    SNAPFN
                in      a, ($99)
                ; the save cells that changed
                ld      hl, 0
                ld      (mask), hl
                ld      hl, SVC+15
                ld      de, svb+15
                ld      b, 16
k_cmp:
                ld      a, (de)
                cp      (hl)
                scf
                jr      nz, k_chg
                or      a
k_chg:
                push    hl
                ld      hl, (mask)
                adc     hl, hl
                ld      (mask), hl
                pop     hl
                dec     hl
                dec     de
                djnz    k_cmp
                ld      a, (cur+11)
                or      a
                jr      z, k_nosum1
                call    vsum
                ld      (sums+3), hl
                ld      a, b
                ld      (sums+5), a
                call    rdexp
                ld      (sums+7), a
k_nosum1:
                ; the record
                ld      ix, (ptr)
                ld      a, (regs+1)
                ld      (ix+0), a
                ld      a, (regs)
                ld      (ix+1), a
                ld      a, (SNAPB+14)
                ld      (ix+2), a
                ld      a, (SNAPB+80)
                ld      (ix+3), a
                ld      a, (SNAPB+81)
                ld      (ix+4), a
                ld      hl, (lend)
                ld      bc, LOGB
                or      a
                sbc     hl, bc
                ld      (ix+5), l
                push    ix
                pop     de
                ld      hl, 6
                add     hl, de
                ex      de, hl
                ld      hl, LOGB
                ld      bc, 7
                ldir
                ld      a, (SV14)
                ld      (ix+13), a
                ld      a, (cidx)
                ld      (ix+14), a
                ld      a, (call_i)
                ld      (ix+15), a
                ld      a, (regs+2)
                ld      (ix+16), a
                ld      a, (regs+4)
                ld      (ix+17), a
                ld      hl, (lend+2)
                ld      bc, LOGB98
                or      a
                sbc     hl, bc
                ld      (ix+18), l
                ld      a, (LOGB98)
                ld      (ix+19), a
                ld      hl, (lend+4)
                ld      bc, LOGB9A
                or      a
                sbc     hl, bc
                ld      (ix+20), l
                ld      hl, (lend+6)
                ld      bc, LOGB9B
                or      a
                sbc     hl, bc
                ld      (ix+21), l
                push    ix
                pop     de
                ld      hl, 22
                add     hl, de
                ex      de, hl
                ld      hl, regs+6
                ld      bc, 18
                ldir                            ; +22..+39
                ld      a, (SNAPB2+7)
                ld      (ix+40), a
                ld      a, (SNAPB2+80)
                ld      (ix+41), a
                ld      a, (SNAPB2+81)
                ld      (ix+42), a
                ld      a, (SNAPB2+14)
                ld      (ix+43), a
                push    ix
                pop     de
                ld      hl, 44
                add     hl, de
                ex      de, hl
                ld      hl, sums
                ld      bc, 8
                ldir                            ; +44..+51
                ld      a, (cur+8)
                ld      b, a
                ld      a, (bootmd)
                inc     b
                jr      z, k_md
                and     $F9
                dec     b
                or      b
k_md:
                ld      (ix+52), a
                ld      a, (SCRMOD)
                ld      (ix+53), a
                ld      a, (ACPAGE)
                ld      (ix+54), a
                ld      a, (DPPAGE)
                ld      (ix+55), a
                ld      a, (mask)
                ld      (ix+56), a
                ld      a, (mask+1)
                ld      (ix+57), a
                ld      a, (MODE)
                ld      (ix+58), a
                ld      de, 64
                add     ix, de
                ld      (ptr), ix
                ; clear the logs
                ld      hl, LOGB
                ld      de, LOGB+1
                ld      bc, 63
                ld      (hl), 0
                ldir
                ld      hl, LOGB98
                ld      de, LOGB98+1
                ld      bc, $BF
                ld      (hl), 0
                ldir
                ld      a, (call_i)
                inc     a
                ld      (call_i), a
                cp      5
                jp      nz, k_next
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
                ld      a, (bootmd)
                ld      (MODE), a
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; BIGFIL with BC 1
bigf1:
                ld      bc, 1
                jp      $016B

targets:
                dw      $016E, $0171, $0174, $0177, bigf1

; the whole 128 KB of VRAM, read through port $98 (interrupts off): HL = the 16-bit sum, B = the XOR
vsum:
                ld      hl, 0
                ld      b, 0
                ld      d, 0
                ld      c, $98
                xor     a
vs_bank:
                push    af
                out     ($99), a                ; R#14 := the bank
                ld      a, $8E
                out     ($99), a
                xor     a
                out     ($99), a
                out     ($99), a                ; read from the bank's $0000
                exx
                ld      bc, $4000
                exx
vs_byte:
                in      e, (c)
                add     hl, de
                ld      a, e
                xor     b
                ld      b, a
                exx
                dec     bc
                ld      a, b
                or      c
                exx
                jr      nz, vs_byte
                pop     af
                inc     a
                cp      8
                jr      nz, vs_bank
                ret

; the byte at the case's expected 17-bit address (cur+12 low, +13 mid, +14 A16) -> A
rdexp:
                ld      a, (cur+13)
                rlca
                rlca
                and     $03
                ld      b, a
                ld      a, (cur+14)
                add     a, a
                add     a, a
                or      b
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, (cur+12)
                out     ($99), a
                ld      a, (cur+13)
                and     $3F
                out     ($99), a
                ex      (sp), hl                ; time for the VDP's pre-fetch (an immediate read returned a stale byte)
                ex      (sp), hl
                ex      (sp), hl
                ex      (sp), hl
                in      a, ($98)
                ret

; the case's expected address := $5A, through the probe's own ports
wrexp:
                call    rdexp                   ; R#14 and the address set (a read)
                ld      a, (cur+12)
                out     ($99), a
                ld      a, (cur+13)
                and     $3F
                or      $40
                out     ($99), a
                ex      (sp), hl
                ex      (sp), hl
                ld      a, $5A
                out     ($98), a
                ex      (sp), hl
                ex      (sp), hl
                ret

; HL, SCRMOD, LINL40, ACPAGE, DPPAGE, R#14, $FFED, MODE bits 2-1 ($FF = boot), entry A, entry F, sum, the expected
; address (low, mid, A16) for the sum cases, 0
cases:
                db      $34, $12, 5, 40, 0,   0, $06, $A1, $FF, $C7, $00, 1, $34, $12, 0, 0  ;  0 VA-1 S-BASE, sums
                db      $34, $12, 5, 40, 0,   0, $06, $A1, $FF, $00, $FF, 0, 0, 0, 0, 0      ;  1 VA-1 A $00 F $FF
                db      $34, $12, 5, 40, 0,   0, $06, $A1, $FF, $FF, $00, 0, 0, 0, 0, 0      ;  2 VA-1 A $FF F $00
                db      $23, $C1, 5, 40, 1,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  3 S5 AC1 $C123 (128 KB)
                db      $23, $C1, 6, 40, 2,   0, $02, $05, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  4 S6 VA-3
                db      $23, $C1, 6, 40, 3,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  5 S6 VA-5
                db      $23, $C1, 6, 40, 1,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  6 S6 AC1 $C123
                db      $34, $12, 6, 40, 0,   0, $06, $A1, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  7 S6 VA-1
                db      $23, $C1, 5, 40, 4,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  8 S5 AC4
                db      $23, $C1, 5, 40, 5,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ;  9 S5 AC5
                db      $23, $C1, 5, 40, $40, 0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 10 S5 AC $40
                db      $23, $C1, 5, 40, $FF, 0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 11 S5 AC $FF
                db      $23, $C1, 1, 40, 4,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 12 S1 AC4
                db      $23, $C1, 1, 40, $40, 0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 13 S1 AC $40
                db      $23, $C1, 1, 40, $80, 0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 14 S1 AC $80
                db      $23, $C1, 1, 40, $FF, 0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 15 S1 AC $FF
                db      $23, $C1, 1, 40, 3,   0, $00, $00, $FF, $00, $FF, 0, 0, 0, 0, 0      ; 16 S1 AC3, A $00 F $FF
                db      $34, $12, 8, 40, 2,   0, $03, $01, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 17 S8 AC2
                db      $34, $12, 8, 40, 3,   0, $03, $01, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 18 S8 AC3
                db      $34, $12, 7, 40, 2,   0, $03, $01, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 19 S7 AC2
                db      $23, $C1, 5, 40, 2,   0, $02, $05, $00, $C7, $00, 0, 0, 0, 0, 0      ; 20 VA-3 MODE bits 00
                db      $23, $C1, 5, 40, 2,   0, $02, $05, $06, $C7, $00, 0, 0, 0, 0, 0      ; 21 VA-3 MODE bits 11
                db      $23, $C1, 1, 40, 1,   2, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 22 S1 AC1 DP2
                db      $23, $C1, 1, 40, 1,   0, $00, $00, $FF, $C7, $00, 1, $5A, $01, 0, 0  ; 23 VA-11, sums
                db      $23, $C1, 5, 40, 2,   0, $02, $05, $FF, $C7, $00, 1, $23, $C1, 1, 0  ; 24 VA-3, sums
                db      $FF, $FF, 5, 40, 0,   0, $06, $A1, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 25 VC-1
                db      $FF, $3F, 1, 40, 0,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 26 VC-2
                db      $34, $FF, 8, 40, 2,   0, $03, $01, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 27 S8 AC2 HL $FF34: H + 1 carries?
                db      $23, $FF, 5, 40, 4,   0, $00, $00, $FF, $C7, $00, 0, 0, 0, 0, 0      ; 28 S5 AC4 HL $FF23: H + 1 carries?
                db      $EE

                ds      $8000 - $, $FF
