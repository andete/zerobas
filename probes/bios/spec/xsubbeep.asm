; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XSUBBEEP -- D-MSX2SPEC, docs/msx2/sub/BEEP.md: the sub-ROM's BEEP ($017D) through EXTROM, and the main ROM's BEEP
; ($00C0) for comparison, on the MSX2 / MSX2+ references. Per case (the table `cases`: KIND 0 sub-ROM entered with
; DI, 1 main ROM ($00C0) with DI, 2 sub-ROM entered with EI, 3 sub-ROM with DI and the VDP's 50 / 60 Hz bit (R#9 bit 1)
; flipped in the VDP only, 4 the same with RG9SAV ($FFE8) flipped too -- both restored after the call; V = the value written to the clock IC's block 2
; register 10 through its ports before the call, $FF = none; M = MODE (clock register 13) written just before the
; call, $FF = left as the register write restored it; R7 = PSG R7's preset, $FF = psgset's $B8; PC = 1: PPI port C bit 7
; := 1 before the call, 0: := 0; the last three fields and cases 18-26 and kinds 3 / 4 added 2026-11-23, goldfish pass 1):
;   PSG R0-R13 := $A1 $02 $B3 $04 $C5 $06 $17 $B8 $09 $0A $0B $5C $1D $0E through the ports (garbage, so a reset
;   shows), the clock register written (MODE's bank bits := 2, TE / AE kept, MODE restored), the PSG trace armed
;   (@psglog), a marker OUT R14 := $5A, BC $1357 DE $2468 HL $369C IY $8765 A $C3, the call; the registers, the
;   interrupt state (read twice), a marker R14 := $A5, PSG R0-R15 through the ports; then interrupts ON and 10 HALTs
;   (the tail: a tone the timer interrupt ends is caught), a marker R14 := $3C, the trace disarmed, PSG R0-R15 again,
;   PPI port C, MODE and block 2 register 10 (through the ports).
; The capture lives in page 2 (RAM there at INIT on all six machines, measured): DONE = 8000, CAP = 8001: +0 $A5 when
; finished, +1 the case count, +2..+14 block 2 registers 0-12 at INIT (ports); per case a SLOT-byte record from
; +$FF (8100): +0 KIND, +1 V, +2 A, +3 F, +4 C, +5 B, +6 E, +7 D, +8 L, +9 H,
; +10/11 IX, +12/13 IY, +14 / +15 IFF (P/V of LD A,I, read twice), +16 MODE after, +17 block 2 reg 10 after,
; +18 port C after, +19..+34 PSG R0-R15 at return, +35..+50 PSG R0-R15 after the tail, +51 $EE (sentinel),
; +52/53 the trace's end pointer, +54/55 SP after, +56 M, +57 MODE just before the call, +58 R7 preset (the table's),
; +59 port C just before the call, +60 PC, +61 port C at return (before the tail); the trace from +64: 5 bytes
; per OUT $A1 except R15's (register, byte, microseconds 24-bit LE). R15 is skipped: the timer interrupt writes it
; ($8F / $CF) every frame; an unskipped run (the first, 2026-11-23) showed only those pairs.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsubbeep.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the PSG's, PPI's and clock IC's published ports.
;
; @cap 8000
; @caplen 5F80
; @timeout 200
; @psglog EE00 4017 8000

EXTROM  equ     $015F
DONE    equ     $8000
CAP     equ     $8001
SLOT    equ     $0380
LOGP    equ     $EE00
ptr     equ     $EE02
tp      equ     $EE04
cidx    equ     $EE06
kind    equ     $EE07
val     equ     $EE08
mpre    equ     $EE09
r7pre   equ     $EE0A
pcpre   equ     $EE0B
rg9org  equ     $EE0C
RG9SAV  equ     $FFE8
sv_sp   equ     $EE10
sv_af   equ     $EE12
sv_bc   equ     $EE14
sv_de   equ     $EE16
sv_hl   equ     $EE18
sv_ix   equ     $EE1A
sv_iy   equ     $EE1C
sv_if   equ     $EE1E

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, 0
                ld      (LOGP), hl
armpt:                                  ; $4011 (@psglog's ARM): LOGP is 0 here
                nop
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $3EFF
                ld      (hl), 0
                ldir
                ld      de, CAP+2       ; block 2 registers 0-12 as found
                ld      c, 0
b2dump:
                ld      a, c
                call    rtc_rd
                ld      (de), a
                inc     de
                inc     c
                ld      a, c
                cp      13
                jr      nz, b2dump
                ld      hl, CAP+$FF
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $EE
                jp      z, finish
                ld      (kind), a
                inc     hl
                ld      a, (hl)
                ld      (val), a
                inc     hl
                ld      a, (hl)
                ld      (mpre), a
                inc     hl
                ld      a, (hl)
                ld      (r7pre), a
                inc     hl
                ld      a, (hl)
                ld      (pcpre), a
                inc     hl
                ld      (tp), hl
                ld      hl, (ptr)
                ld      a, (kind)
                ld      (hl), a
                inc     hl
                ld      a, (val)
                ld      (hl), a
                ; PSG garbage
                ld      hl, psgset
                ld      c, 0
pg:
                ld      a, c
                out     ($A0), a
                ld      a, (hl)
                out     ($A1), a
                inc     hl
                inc     c
                ld      a, c
                cp      14
                jr      nz, pg
                ld      a, (r7pre)
                cp      $FF
                jr      z, r7def
                ld      b, a
                ld      a, 7
                out     ($A0), a
                ld      a, b
                out     ($A1), a
r7def:
                ; the clock register
                ld      a, (val)
                cp      $FF
                jr      z, noclk
                ld      b, a
                ld      a, 10
                call    rtc_wr
noclk:
                ; arm the trace at the record's +64
                ld      hl, (ptr)
                ld      de, 64
                add     hl, de
                ld      (LOGP), hl
                ld      a, (mpre)
                cp      $FF
                jr      z, nomode
                ld      b, a
                ld      a, 13
                out     ($B4), a
                ld      a, b
                out     ($B5), a
nomode:
                call    mode_rd
                ld      hl, (ptr)
                ld      de, 57
                add     hl, de
                ld      (hl), a
                dec     hl
                ld      a, (mpre)
                ld      (hl), a
                ; PPI port C bit 7 := PC; +58 R7 preset, +59 port C, +60 PC
                in      a, ($AA)
                and     $7F
                ld      b, a
                ld      a, (pcpre)
                rrca
                and     $80
                or      b
                out     ($AA), a
                ld      hl, (ptr)
                ld      de, 58
                add     hl, de
                ld      a, (r7pre)
                ld      (hl), a
                inc     hl
                in      a, ($AA)
                ld      (hl), a
                inc     hl
                ld      a, (pcpre)
                ld      (hl), a
                ld      a, (RG9SAV)
                ld      (rg9org), a
                ld      a, (kind)
                cp      3
                jr      c, nohz
                ld      a, (rg9org)
                xor     2
                out     ($99), a
                ld      b, a
                ld      a, $89
                out     ($99), a
                ld      a, (kind)
                cp      4
                jr      nz, nohz
                ld      a, b
                ld      (RG9SAV), a
nohz:
                ld      a, $5A
                call    mark
                ld      a, (kind)
                cp      1
                jr      z, do_main
                cp      2
                jr      nz, do_sub
                ei
do_sub:
                ld      bc, $1357
                ld      de, $2468
                ld      hl, $369C
                ld      iy, $8765
                ld      ix, $017D
                ld      a, $C3
                call    EXTROM
                jr      after
do_main:
                ld      bc, $1357
                ld      de, $2468
                ld      hl, $369C
                ld      iy, $8765
                ld      ix, $4321
                ld      a, $C3
                call    $00C0
after:
                ld      (sv_sp), sp
                push    af
                ld      (sv_bc), bc
                ld      (sv_de), de
                ld      (sv_hl), hl
                ld      (sv_ix), ix
                ld      (sv_iy), iy
                pop     hl
                ld      (sv_af), hl
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if), a
                ld      a, i
                di
                push    af
                pop     hl
                ld      a, l
                ld      (sv_if+1), a
                ld      a, $A5
                call    mark
                ld      a, (rg9org)     ; R#9 / RG9SAV back (kinds 3, 4; a no-op otherwise)
                ld      (RG9SAV), a
                out     ($99), a
                ld      a, $89
                out     ($99), a
                ; registers into the record
                ld      de, (ptr)
                inc     de
                inc     de
                ld      hl, sv_af+1
                ldi                     ; A
                dec     hl
                dec     hl
                ldi                     ; F
                inc     hl
                ld      bc, 10          ; C B E D L H IX IY
                ldir
                ld      a, (sv_if)
                rrca
                rrca
                and     1
                ld      (de), a
                inc     de
                ld      a, (sv_if+1)
                rrca
                rrca
                and     1
                ld      (de), a
                ld      hl, (ptr)
                ld      de, 19
                add     hl, de
                call    psgdump
                ld      hl, (ptr)
                ld      de, 61
                add     hl, de
                in      a, ($AA)
                ld      (hl), a         ; +61 port C at return
                ; the tail
                ei
                ld      b, 10
tail:
                halt
                djnz    tail
                di
                ld      a, $3C
                call    mark
                ld      hl, (LOGP)
                ex      de, hl
                ld      hl, 0
                ld      (LOGP), hl
                ld      hl, (ptr)
                ld      bc, 52
                add     hl, bc
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      de, (sv_sp)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ld      hl, (ptr)
                ld      de, 35
                add     hl, de
                call    psgdump
                ld      (hl), $EE       ; +51
                ld      hl, (ptr)
                ld      de, 16
                add     hl, de
                push    hl
                call    mode_rd
                pop     hl
                ld      (hl), a         ; +16 MODE
                inc     hl
                push    hl
                ld      a, 10
                call    rtc_rd
                pop     hl
                ld      (hl), a         ; +17
                inc     hl
                in      a, ($AA)
                ld      (hl), a         ; +18
                and     $7F             ; port C bit 7 back to 0 for the next case
                out     ($AA), a
                ld      hl, (ptr)
                ld      de, SLOT
                add     hl, de
                ld      (ptr), hl
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                ld      (CAP), a        ; temporarily the count at +0, moved at the end
                jp      c_next
finish:
                ld      a, (cidx)
                ld      (CAP), a
                ld      a, (CAP)
                ld      (CAP+1), a
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
                ei
fin:
                jr      fin

; OUT R14 := A (a marker in the trace; R14 is the input port, its latch is harmless)
mark:
                push    af
                ld      a, 14
                out     ($A0), a
                pop     af
                out     ($A1), a
                ret
; PSG R0-R15 through the ports to (HL)..; HL past
psgdump:
                ld      c, 0
pd:
                ld      a, c
                out     ($A0), a
                in      a, ($A2)
                ld      (hl), a
                inc     hl
                inc     c
                ld      a, c
                cp      16
                jr      nz, pd
                ret
mode_rd:
                ld      a, 13
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ret
; block 2 register A -> A (MODE restored)
rtc_rd:
                push    bc
                ld      c, a
                call    mode_rd
                ld      b, a
                and     $0C
                or      2
                out     ($B5), a
                ld      a, c
                out     ($B4), a
                in      a, ($B5)
                and     $0F
                ld      c, a
                ld      a, 13
                out     ($B4), a
                ld      a, b
                out     ($B5), a
                ld      a, c
                pop     bc
                ret
; block 2 register A := B (MODE restored)
rtc_wr:
                push    bc
                ld      c, a
                call    mode_rd
                push    af
                and     $0C
                or      2
                out     ($B5), a
                ld      a, c
                out     ($B4), a
                ld      a, b
                out     ($B5), a
                ld      a, 13
                out     ($B4), a
                pop     af
                out     ($B5), a
                pop     bc
                ret

psgset:
                db      $A1, $02, $B3, $04, $C5, $06, $17, $B8, $09, $0A, $0B, $5C, $1D, $0E
cases:
                db      0, $00, $FF, $FF, 0
                db      0, $01, $FF, $FF, 0
                db      0, $02, $FF, $FF, 0
                db      0, $03, $FF, $FF, 0
                db      0, $04, $FF, $FF, 0
                db      0, $05, $FF, $FF, 0
                db      0, $06, $FF, $FF, 0
                db      0, $07, $FF, $FF, 0
                db      0, $08, $FF, $FF, 0
                db      0, $09, $FF, $FF, 0
                db      0, $0A, $FF, $FF, 0
                db      0, $0B, $FF, $FF, 0
                db      0, $0C, $FF, $FF, 0
                db      0, $0D, $FF, $FF, 0
                db      0, $0E, $FF, $FF, 0
                db      0, $0F, $FF, $FF, 0
                db      1, $0F, $FF, $FF, 0     ; 16: the main ROM's BEEP, the same setting as case 15
                db      2, $06, $07, $FF, 0     ; 17: entered with EI; MODE := TE 0, AE 1, block 3
                db      0, $00, $FF, $47, 0     ; 18: sound 00, R7 preset $47 (dirs 01, tones+noise on): R7 writes constant or kept
                db      0, $04, $FF, $47, 0     ; 19: sound 01, the same
                db      0, $08, $FF, $47, 0     ; 20: sound 10, the same
                db      0, $0C, $FF, $47, 0     ; 21: sound 11, the same
                db      0, $0F, $FF, $FF, 1     ; 22: port C bit 7 := 1 before the call (BP-6)
                db      2, $06, $0B, $FF, 0     ; 23: entered with EI, MODE := $0B (block 3 / TE 1 / AE 0, as at boot) just before
                db      2, $06, $FF, $FF, 0     ; 24: entered with EI, MODE left as found ($0B from 23, not written): EI alone
                db      3, $04, $FF, $FF, 0     ; 25: sound 01, R#9 bit 1 flipped in the VDP only: frame-paced or not
                db      4, $04, $FF, $FF, 0     ; 26: sound 01, R#9 bit 1 and RG9SAV flipped: paced by RG9SAV's setting or not
                db      $EE

                ds      $8000 - $, $FF
