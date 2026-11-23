; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XVA14 -- D-MSX2SPEC, docs/msx2/main/README.md "The shared VRAM address matrix", case VA-14: where NSETRD ($016E),
; NSETWR ($0171), NRDVRM ($0174), NWRVRM ($0177) and BIGFIL ($016B, with BC 1) put the 17-bit VRAM address in the
; MSX2+ modes SCREEN 10 / 11 / 12, on the FS-A1WSX (run on the msx2p row only: an MSX2 has no SCREEN 10-12).
; xva.asm's method and code; the record grows to 32 bytes to show which mode the VDP and SCRMOD were in.
; Per case (the table `cases`: HL, SCRMOD, LINL40, ACPAGE, DPPAGE, R#14, $FFED, MODE's bits 2-1 or $FF, R#25 or $FF,
; SCRMOD by hand or $FF) and per call,
; the probe sets, BY HAND after CHGMOD (main $005F, interrupts then off): ACPAGE ($FAF6), DPPAGE ($FAF5), $FFED, MODE
; ($FAFC) bits 2-1 where given, the VDP's R#14 through port $99; then A $C7 (NWRVRM's byte), BC $5AA5 (BIGFIL: 1), DE $A55A,
; the call, and right after it the VDP's whole state through the debugger (@vdpfull).
; The address is READ from the VDP: R#14 (A16-A14) and the VRAM pointer (A13-A0) after the call (NSETRD / NRDVRM
; pre-fetch: the address + 1).
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case x call a 32-byte record from +2:
;   +0 A after, +1 F after, +2 R#14 after, +3 / +4 the VRAM pointer after (low, high), +5 the number of port $99
;   writes during the call, +6..+12 the first seven of them, +13 $FFED after, +14 the case, +15 the call
;   (0 NSETRD .. 3 NWRVRM, 4 BIGFIL with BC 1), +16 SCRMOD ($FCAF) right after CHGMOD, +17 R#25, +18 R#0, +19 R#1, +20 MODE after,
;   +21 ACPAGE after, +22 SCRMOD after the call, +23..+31 0.
; SCREEN 10-12 are SCREEN 8 with the V9958's R#25 YJK (bit 3) / YAE (bit 4) set [A]. Case 1 shows what main CHGMOD
; does with A = 12 (SCRMOD 8, R#25 0 on the FS-A1WSX: it does not enter YJK), so the cases set R#25 (and its save cell
; $FFFA) BY HAND after CHGMOD 8; and because BASIC's SCRMOD in SCREEN 10-12 is not measured here, some cases also
; set SCRMOD to 10 / 11 / 12 by hand -- both rivals for what a SCREEN 10-12 program has in SCRMOD.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xva14.asm --row msx2p
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers and pointer read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0B00
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @timeout 120

CHGMOD  equ     $005F
LINL40  equ     $F3AE
DPPAGE  equ     $FAF5
ACPAGE  equ     $FAF6
MODE    equ     $FAFC
SV14    equ     $FFED
DONE    equ     $C000
CAP     equ     $C001
SNAPFN  equ     $E8F0                   ; a `ret`: the debugger's snapshot point (@vdpfull)
ARMFN   equ     $E8F4                   ; a `ret`: the port log's arming point (@portlog)
SNAPP   equ     $E900                   ; @vdpfull's pointer word
LOGP    equ     $E902                   ; @portlog's pointer word (0 = not logging)
ptr     equ     $E904
tp      equ     $E906
cidx    equ     $E908
call_i  equ     $E909
rAF     equ     $E90A
scrm    equ     $E90C                   ; SCRMOD right after CHGMOD
SCRMOD  equ     $FCAF
RG25SA  equ     $FFFA                   ; R#25's save cell (MSX2+)
cur     equ     $E910                   ; the case: HL (2), SCRMOD, LINL40, ACPAGE, DPPAGE, R14, SV, MODE bits, R25, SCRMOD set
SNAPB   equ     $E000                   ; 114 bytes: R#0-63, S#0-15, pointer (2), palette (32)
LOGB    equ     $E080                   ; the port log, up to 64 bytes

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $0AFF
                ld      (hl), 0
                ldir
                ld      a, $C9
                ld      (SNAPFN), a
                ld      (ARMFN), a
                ld      hl, 0
                ld      (LOGP), hl
                call    ARMFN                   ; the port watch starts here (LOGP is 0: nothing logged yet)
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, cases
                ld      (tp), hl
                xor     a
                ld      (cidx), a
c_next:
                ld      hl, (tp)
                ld      a, (hl)
                inc     hl
                and     (hl)
                dec     hl
                cp      $FF
                jp      z, finish
                ld      de, cur
                ld      bc, 11
                ldir
                ld      (tp), hl
                xor     a
                ld      (call_i), a
k_next:
                ; the mode, by CHGMOD (LINL40 first: SCREEN 0 at 80 is TEXT2)
                ld      a, (cur+3)
                ld      (LINL40), a
                ld      a, (cur+2)
                call    CHGMOD
                di
                ld      a, (SCRMOD)
                ld      (scrm), a
                ld      a, (cur+9)              ; R#25 by hand ($FF = not touched): SCREEN 10-12 = YJK on SCREEN 8
                cp      $FF
                jr      z, k_no25
                ld      (RG25SA), a
                out     ($99), a
                ld      a, $80+25
                out     ($99), a
k_no25:
                ld      a, (cur+10)             ; SCRMOD by hand ($FF = as CHGMOD left it)
                cp      $FF
                jr      z, k_nosm
                ld      (SCRMOD), a
k_nosm:
                ; the cells, by hand
                ld      a, (cur+4)
                ld      (ACPAGE), a
                ld      a, (cur+5)
                ld      (DPPAGE), a
                ld      a, (cur+7)
                ld      (SV14), a
                ld      a, (cur+8)
                cp      $FF
                jr      z, k_nomode
                ld      b, a
                ld      a, (MODE)
                and     $F9
                or      b
                ld      (MODE), a
k_nomode:
                ld      a, (cur+6)              ; the VDP's R#14
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ; arm the log, set the registers, call
                ld      hl, LOGB
                ld      (LOGP), hl
                ld      hl, (cur)
                ld      bc, $5AA5
                ld      de, $A55A
                ld      a, (call_i)
                or      a
                jr      z, k_c0
                dec     a
                jr      z, k_c1
                dec     a
                jr      z, k_c2
                dec     a
                jr      z, k_c4
                ld      a, $C7
                call    $0177                   ; NWRVRM
                jr      k_after
k_c4:
                ld      bc, 1                   ; one byte: the pointer is left at the address + 1
                ld      a, $C7
                call    $016B                   ; BIGFIL
                jr      k_after
k_c0:
                ld      a, $C7
                call    $016E                   ; NSETRD
                jr      k_after
k_c1:
                ld      a, $C7
                call    $0171                   ; NSETWR
                jr      k_after
k_c2:
                ld      a, $C7
                call    $0174                   ; NRDVRM
k_after:
                di
                push    af
                pop     hl
                ld      (rAF), hl
                ld      hl, (LOGP)              ; where the log stopped
                push    hl
                ld      hl, 0
                ld      (LOGP), hl              ; disarm
                ld      hl, SNAPB
                ld      (SNAPP), hl
                call    SNAPFN                  ; the debugger writes the VDP's state at SNAPB
                ; the record
                ld      de, (ptr)
                ld      a, (rAF+1)
                ld      (de), a                 ; A
                inc     de
                ld      a, (rAF)
                ld      (de), a                 ; F
                inc     de
                ld      a, (SNAPB+14)
                ld      (de), a                 ; R#14
                inc     de
                ld      a, (SNAPB+80)
                ld      (de), a                 ; the pointer, low
                inc     de
                ld      a, (SNAPB+81)
                ld      (de), a                 ; high
                inc     de
                pop     hl                      ; the log's end
                ld      bc, LOGB
                or      a
                sbc     hl, bc
                ld      a, l
                ld      (de), a                 ; the number of writes
                inc     de
                ld      hl, LOGB
                ld      bc, 7
                ldir                            ; the first seven
                ld      a, (SV14)
                ld      (de), a                 ; $FFED after
                inc     de
                ld      a, (cidx)
                ld      (de), a
                inc     de
                ld      a, (call_i)
                ld      (de), a
                inc     de
                ld      a, (scrm)
                ld      (de), a                 ; +16 SCRMOD after CHGMOD
                inc     de
                ld      a, (SNAPB+25)
                ld      (de), a                 ; +17 R#25
                inc     de
                ld      a, (SNAPB+0)
                ld      (de), a                 ; +18 R#0
                inc     de
                ld      a, (SNAPB+1)
                ld      (de), a                 ; +19 R#1
                inc     de
                ld      a, (MODE)
                ld      (de), a                 ; +20 MODE
                inc     de
                ld      a, (ACPAGE)
                ld      (de), a                 ; +21 ACPAGE
                inc     de
                ld      a, (SCRMOD)
                ld      (de), a                 ; +22 SCRMOD after the call
                ld      hl, 10
                add     hl, de
                ld      (ptr), hl
                ; clear the log buffer for the next call
                ld      hl, LOGB
                ld      de, LOGB+1
                ld      bc, 63
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
                xor     a
                call    CHGMOD
                ei
fin:
                jr      fin

; HL, SCRMOD (CHGMOD's A), LINL40, ACPAGE, DPPAGE, R#14, $FFED, MODE bits 2-1 ($FF = as booted), R#25 ($FF = not
; touched; $08 YJK = SCREEN 12, $18 YJK + YAE = SCREEN 10 / 11), SCRMOD by hand afterwards ($FF = not)
cases:
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $FF, $FF   ;  0 VA-7 SCREEN 8 (the in-run control)
                db      $34, $12, 12, 40, 1, 0, $03, $01, $FF, $FF, $FF  ;  1 CHGMOD with A = 12 alone
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $08, $FF   ;  2 VA-14 SCREEN 12 (R#25 YJK)
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $18, $FF   ;  3 VA-14 SCREEN 10 / 11 (YJK + YAE)
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $08, 12    ;  4 VA-14, SCRMOD 12 by hand
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $18, 11    ;  5 VA-14, SCRMOD 11 by hand
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $18, 10    ;  6 VA-14, SCRMOD 10 by hand
                db      $23, $C1, 8, 40, 0, 0, $06, $A1, $FF, $08, $FF   ;  7 S-BASE (VA-2's HL), SCREEN 12
                db      $23, $C1, 8, 40, 0, 0, $06, $A1, $FF, $18, $FF   ;  8 S-BASE, SCREEN 10 / 11
                db      $23, $C1, 8, 40, 1, 0, $00, $00, $FF, $08, $FF   ;  9 AC 1, HL $C123: 64 KB page $1C123, 32 KB $04123
                db      $23, $C1, 8, 40, 1, 0, $00, $00, $FF, $18, $FF   ; 10 the same, SCREEN 10 / 11
                db      $23, $C1, 8, 40, 1, 0, $00, $00, $FF, $08, 12    ; 11 the same, SCRMOD 12 by hand
                ; SCRMOD 10 by hand gave a 32 KB page (case 6: $09234) where 11 / 12 gave 64 KB: is it SCRMOD alone, and
                ; is it SCREEN 5's whole rule?
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $08, 10    ; 12 SCRMOD 10 with R#25 YJK only
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF, $FF, 10    ; 13 SCRMOD 10, R#25 untouched (0)
                db      $23, $C1, 8, 40, 1, 0, $00, $00, $FF, $18, 10    ; 14 SCRMOD 10, AC 1, HL $C123 (S5 rule $04123)
                db      $23, $C1, 8, 40, 3, 0, $00, $00, $FF, $18, 10    ; 15 SCRMOD 10, AC 3, HL $C123 (S5 rule $14123)
                db      $34, $12, 8, 40, 2, 0, $00, $00, $FF, $18, 10    ; 16 SCRMOD 10, AC 2, HL $1234 (S5 rule $11234)
                db      $FF, $FF

                ds      $8000 - $, $FF
