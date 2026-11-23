; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XVA -- D-MSX2SPEC, docs/msx2/main/README.md "The shared VRAM address matrix": where NSETRD ($016E), NSETWR ($0171),
; NRDVRM ($0174) and NWRVRM ($0177) put the 17-bit VRAM address, on the MSX2 / MSX2+ references.
; Per case (the table `cases`: HL, SCRMOD, LINL40, ACPAGE, DPPAGE, R#14, $FFED, MODE's bits 2-1 or $FF) and per call,
; the probe sets, BY HAND after CHGMOD (main $005F, interrupts then off): ACPAGE ($FAF6), DPPAGE ($FAF5), $FFED, MODE
; ($FAFC) bits 2-1 where given, the VDP's R#14 through port $99; then A $C7 (NWRVRM's byte), BC $5AA5, DE $A55A, the
; call, and right after it the VDP's whole state through the debugger (@vdpfull).
; Instead of marking VRAM (the README's S-MARK), the address is READ from the VDP: R#14 (A16-A14) and the VRAM
; pointer (A13-A0) as the debugger holds them after the call -- a read setting pre-fetches, so NSETRD / NRDVRM leave
; it at the address + 1; NSETWR / NWRVRM at the address / + 1.
; The capture (CAP = C001): +0 $A5 when finished, +1 the case count; per case x call a 16-byte record from +2:
;   +0 A after, +1 F after, +2 R#14 after, +3 / +4 the VRAM pointer after (low, high), +5 the number of port $99
;   writes during the call, +6..+12 the first seven of them, +13 $FFED after, +14 the case, +15 the call
;   (0 NSETRD .. 3 NWRVRM).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xva.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers and pointer read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0680
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
cur     equ     $E910                   ; the case: HL (2), SCRMOD, LINL40, ACPAGE, DPPAGE, R14, SV, MODE bits
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
                ld      bc, $067F
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
                ld      bc, 9
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
                ld      a, $C7
                call    $0177                   ; NWRVRM
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
                ld      (ptr), de
                ; clear the log buffer for the next call
                ld      hl, LOGB
                ld      de, LOGB+1
                ld      bc, 63
                ld      (hl), 0
                ldir
                ld      a, (call_i)
                inc     a
                ld      (call_i), a
                cp      4
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

; HL, SCRMOD, LINL40, ACPAGE, DPPAGE, R#14, $FFED, MODE bits 2-1 ($FF = as booted)
cases:
                db      $34, $12, 5, 40, 0, 0, $06, $A1, $FF  ;  0 VA-1  S-BASE
                db      $23, $C1, 5, 40, 0, 0, $06, $A1, $FF  ;  1 VA-2
                db      $23, $C1, 5, 40, 2, 0, $02, $05, $FF  ;  2 VA-3
                db      $23, $C1, 5, 40, 2, 0, $05, $02, $FF  ;  3 VA-4
                db      $23, $C1, 5, 40, 3, 0, $00, $00, $FF  ;  4 VA-5
                db      $23, $C1, 5, 40, 0, 2, $02, $01, $FF  ;  5 VA-6
                db      $34, $12, 8, 40, 1, 0, $03, $01, $FF  ;  6 VA-7  SCREEN 8
                db      $34, $12, 7, 40, 1, 0, $03, $01, $FF  ;  7 VA-7  SCREEN 7
                db      $23, $C1, 1, 40, 0, 0, $00, $00, $FF  ;  8 VA-8
                db      $23, $C1, 1, 40, 0, 0, $05, $02, $FF  ;  9 VA-9
                db      $23, $C1, 0, 40, 0, 0, $05, $02, $FF  ; 10 VA-10 SCREEN 0 width 40
                db      $23, $C1, 0, 80, 0, 0, $05, $02, $FF  ; 11 VA-10 SCREEN 0 width 80
                db      $23, $C1, 2, 40, 0, 0, $05, $02, $FF  ; 12 VA-10 SCREEN 2
                db      $23, $C1, 3, 40, 0, 0, $05, $02, $FF  ; 13 VA-10 SCREEN 3
                db      $23, $C1, 4, 40, 0, 0, $05, $02, $FF  ; 14 VA-10 SCREEN 4
                db      $23, $C1, 1, 40, 1, 0, $00, $00, $FF  ; 15 VA-11
                db      $34, $12, 5, 40, 2, 0, $00, $00, $02  ; 16 VA-12 MODE bits 2-1 := 01 (64 KB)
                db      $23, $C1, 5, 40, 2, 0, $06, $A1, $FF  ; 17 VA-15
                ; VA-11's follow-up (SCREEN 1 with ACPAGE 1 put HL $C123 at $0015A on all three references)
                db      $23, $C1, 1, 40, 2, 0, $00, $00, $FF  ; 18 VA-11b SCREEN 1 ACPAGE 2
                db      $23, $C1, 1, 40, 3, 0, $00, $00, $FF  ; 19 VA-11c SCREEN 1 ACPAGE 3
                db      $34, $12, 1, 40, 1, 0, $00, $00, $FF  ; 20 VA-11d SCREEN 1 ACPAGE 1 HL $1234
                db      $00, $00, 1, 40, 1, 0, $00, $00, $FF  ; 21 VA-11e SCREEN 1 ACPAGE 1 HL $0000
                db      $23, $C1, 0, 40, 1, 0, $00, $00, $FF  ; 22 VA-11f SCREEN 0 ACPAGE 1
                db      $23, $C1, 2, 40, 1, 0, $00, $00, $FF  ; 23 VA-11g SCREEN 2 ACPAGE 1
                db      $23, $C1, 4, 40, 1, 0, $00, $00, $FF  ; 24 VA-11h SCREEN 4 ACPAGE 1
                db      $FF, $FF

                ds      $8000 - $, $FF
