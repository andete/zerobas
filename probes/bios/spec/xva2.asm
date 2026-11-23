; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XVA2 -- D-MSX2SPEC, docs/msx2/sub/NRDVRM.md / NWRVRM.md: the SUB-ROM's NRDVRM ($010D) and NWRVRM ($0109), through
; EXTROM, over xva.asm's cases (the shared VRAM address matrix), with main NSETRD / NSETWR as the in-run baseline:
; does the sub-ROM's "64 KB address" pair follow the main ROM's 17-bit rule? Record and decoding as xva.asm
; (call 0 main NSETRD, 1 main NSETWR, 2 sub NRDVRM, 3 sub NWRVRM).
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
; Goldfish pass 1 (2026-11-23), appended at the END (cases 0-24 and their records unchanged): cases 25-35 extend the
; page rule's matrix (SCREEN 3 / 6, SCREEN 0 at 80 and with ACPAGE 2 / 3, SCREEN 7 / 8 with ACPAGE >= 2, SCREEN 5
; ACPAGE 1, SCREEN 0 HL $D123 / $F123 -- HL + ACPAGE x $1000 vs HL OR $1000 --, SCREEN 5 HL $FFFE), same record.
; Then the DATA section (table `dcases`: HL, SCRMOD, LINL40, ACPAGE): per case CHGMOD, ACPAGE / DPPAGE 0 / R#14 0 by
; hand, ALL 128 KB of VRAM := the pattern ((o low) XOR (o high) XOR key[bank]) AND $7F at bank x $4000 + o; then
; four calls -- 0 main NRDVRM $0174, 1 main NWRVRM $0177, 2 sub NRDVRM $010D, 3 sub NWRVRM $0109 (EXTROM) -- each
; with A $C7 (never in the pattern), BC $5AA5, DE $A55A, IX $1357 (the sub calls: the entry), IY $2468, AF' $7788,
; BC' $1122, DE' $3344, HL' $5566; after each, every register, then the whole VRAM compared with the pattern and
; the first differing byte put back. A 32-byte record per case x call after the matrix's records: +0 the case, +1
; the call, +2 A, +3 F, +4 BC, +6 DE, +8 HL, +10 IX, +12 IY, +14 BC', +16 DE', +18 HL', +20 AF' (F, A), +22..+24
; the number of VRAM bytes that differ (24-bit), +25..+27 the first such address (17-bit, low first), +28 its
; byte, +29 0, +30 $DA $DA. Decoder: scratchpad/xva2_decode.py.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xva2.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports, the VDP's
; registers and pointer read by the debugger (hardware state, not a ROM byte).
;
; @cap C000
; @caplen 0C00
; @vdpfull E8F0 E900
; @portlog 99 E902 E8F4
; @timeout 400

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
                ld      bc, $0BFF
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
                ld      ix, $0109               ; sub-ROM NWRVRM, through EXTROM
                ld      a, $C7
                call    $015F
                jr      k_after
k_c0:
                ld      a, $C7
                call    $016E                   ; main NSETRD (the baseline, as in xva)
                jr      k_after
k_c1:
                ld      a, $C7
                call    $0171                   ; main NSETWR (the baseline)
                jr      k_after
k_c2:
                ld      ix, $010D               ; sub-ROM NRDVRM, through EXTROM
                ld      a, $C7
                call    $015F
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
                call    dsect
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
                ; goldfish pass 1 (2026-11-23)
                db      $23, $C1, 3, 40, 1, 0, $00, $00, $FF  ; 25 S3 ACPAGE 1
                db      $23, $C1, 0, 80, 1, 0, $00, $00, $FF  ; 26 S0 width 80 ACPAGE 1
                db      $23, $C1, 0, 40, 2, 0, $00, $00, $FF  ; 27 S0 ACPAGE 2
                db      $23, $C1, 0, 40, 3, 0, $00, $00, $FF  ; 28 S0 ACPAGE 3
                db      $23, $C1, 6, 40, 1, 0, $00, $00, $FF  ; 29 S6 ACPAGE 1
                db      $34, $12, 7, 40, 2, 0, $00, $00, $FF  ; 30 S7 ACPAGE 2
                db      $34, $12, 8, 40, 3, 0, $00, $00, $FF  ; 31 S8 ACPAGE 3
                db      $34, $12, 5, 40, 1, 0, $00, $00, $FF  ; 32 S5 ACPAGE 1 HL $1234 (NR-03)
                db      $23, $D1, 0, 40, 1, 0, $00, $00, $FF  ; 33 S0 ACPAGE 1 HL $D123
                db      $23, $F1, 0, 40, 1, 0, $00, $00, $FF  ; 34 S0 ACPAGE 1 HL $F123
                db      $FE, $FF, 5, 40, 1, 0, $00, $00, $FF  ; 35 S5 ACPAGE 1 HL $FFFE
                db      $FF, $FF

; ---- the DATA section (goldfish pass 1) ----
dcur    equ     $E930                   ; HL (2), SCRMOD, LINL40, ACPAGE
dtp     equ     $E936
dci     equ     $E938
dk      equ     $E939
sv      equ     $E940                   ; AF, BC, DE, HL, IX, IY, BC', DE', HL', AF' (20)
cnt     equ     $E960                   ; 3
first   equ     $E963                   ; 3
fval    equ     $E966

dsect:
                ld      hl, dcases
                ld      (dtp), hl
                xor     a
                ld      (dci), a
d_next:
                ld      hl, (dtp)
                ld      a, (hl)
                inc     hl
                and     (hl)
                dec     hl
                cp      $FF
                ret     z
                ld      de, dcur
                ld      bc, 5
                ldir
                ld      (dtp), hl
                ld      a, (dcur+3)
                ld      (LINL40), a
                ld      a, (dcur+2)
                call    CHGMOD
                di
                ld      a, (dcur+4)
                ld      (ACPAGE), a
                xor     a
                ld      (DPPAGE), a
                call    vfill
                xor     a
                ld      (dk), a
d_call:
                xor     a                       ; R#14 := 0
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      hl, $7788
                push    hl
                pop     af
                ex      af, af'
                exx
                ld      bc, $1122
                ld      de, $3344
                ld      hl, $5566
                exx
                ld      iy, $2468
                ld      ix, $1357
                ld      bc, $5AA5
                ld      de, $A55A
                ld      hl, (dcur)
                ld      a, (dk)
                or      a
                jr      z, d_c0
                dec     a
                jr      z, d_c1
                dec     a
                jr      z, d_c2
                ld      ix, $0109
                ld      a, $C7
                call    $015F
                jr      d_after
d_c0:
                ld      a, $C7
                call    $0174
                jr      d_after
d_c1:
                ld      a, $C7
                call    $0177
                jr      d_after
d_c2:
                ld      ix, $010D
                ld      a, $C7
                call    $015F
d_after:
                di
                ld      (sv+6), hl
                push    af
                pop     hl
                ld      (sv), hl
                ld      (sv+2), bc
                ld      (sv+4), de
                ld      (sv+8), ix
                ld      (sv+10), iy
                exx
                ld      (sv+12), bc
                ld      (sv+14), de
                ld      (sv+16), hl
                exx
                ex      af, af'
                push    af
                pop     hl
                ld      (sv+18), hl
                ex      af, af'
                call    vscan
                ld      de, (ptr)
                ld      a, (dci)
                ld      (de), a
                inc     de
                ld      a, (dk)
                ld      (de), a
                inc     de
                ld      a, (sv+1)
                ld      (de), a                 ; A
                inc     de
                ld      a, (sv)
                ld      (de), a                 ; F
                inc     de
                ld      hl, sv+2
                ld      bc, 18
                ldir                            ; BC .. AF'
                ld      hl, cnt
                ld      bc, 7
                ldir                            ; count, first, its byte
                xor     a
                ld      (de), a
                inc     de
                ld      a, $DA
                ld      (de), a
                inc     de
                ld      (de), a
                inc     de
                ld      (ptr), de
                ; put the first differing byte back
                ld      a, (cnt)
                ld      hl, cnt+1
                or      (hl)
                inc     hl
                or      (hl)
                jr      z, d_nofix
                call    vfix
d_nofix:
                ld      a, (dk)
                inc     a
                ld      (dk), a
                cp      4
                jp      nz, d_call
                ld      a, (dci)
                inc     a
                ld      (dci), a
                jp      d_next

; C := the key of bank B
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
keys:           db      $5A, $7F, $14, $31, $46, $63, $08, $2D

; R#14 := B, the address 0 for writing (A = $40) or reading (A = $00)
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
                and     $7F
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

vscan:
                ld      hl, cnt
                ld      de, cnt+1
                ld      bc, 6
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
                ld      e, a
                ld      a, l
                xor     h
                xor     c
                and     $7F
                cp      e
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
                ret
vs_bad:
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
                ld      a, b
                and     3
                rrca
                rrca
                or      h
                ld      (first+1), a
                ld      a, b
                srl     a
                srl     a
                ld      (first+2), a
                ld      a, e
                ld      (fval), a
vs_nf:
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
                jr      vs_nx

; the pattern byte back at `first`
vfix:
                ld      a, (first+2)            ; the bank: A16 x 4 + A15-A14
                add     a, a
                add     a, a
                ld      b, a
                ld      a, (first+1)
                rlca
                rlca
                and     3
                or      b
                ld      b, a
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, (first)
                ld      l, a
                out     ($99), a
                ld      a, (first+1)
                and     $3F
                ld      h, a
                or      $40
                out     ($99), a
                call    bkey
                ld      a, l
                xor     h
                xor     c
                and     $7F
                out     ($98), a
                ret

; HL, SCRMOD, LINL40, ACPAGE
dcases:
                db      $34, $12, 5, 40, 0      ; D0 S5 ACPAGE 0 $1234
                db      $34, $12, 5, 40, 1      ; D1 S5 ACPAGE 1 $1234
                db      $23, $C1, 1, 40, 1      ; D2 S1 ACPAGE 1 $C123
                db      $23, $D1, 0, 40, 1      ; D3 S0 ACPAGE 1 $D123
                db      $34, $12, 8, 40, 1      ; D4 S8 ACPAGE 1 $1234
                db      $FF, $FF

                ds      $8000 - $, $FF
