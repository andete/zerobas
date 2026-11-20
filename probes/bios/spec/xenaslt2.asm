; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XENASLT2 -- docs/bios/ENASLT.md round 5 (2026-11-18): ENASLT ($0024) and the SECONDARY slot. Run on the cf3300 row
; only (the one reference with an expanded slot 3: RAM in 3-0, a ROM in 3-1). Under Joost's ruling of 2026-11-18 the
; probe reads 3-1 only at $4000 / $4001 (its "AB" header). The probe runs from RAM ($EA00, page 3 = 3-0), writes $5A /
; $A5 into 3-0 at $4000 / $4001 by hand, then per case: the boot state by hand (slot register, slot 3's secondary
; register, SLTTBL), the case's preset (slot 3's secondary selection AND SLTTBL+3's pages 0-2 fields := the case's
; byte, page 3's kept; round 3 sets pages 0 and 2 to other sub-slots too, so "the other fields kept" is seen), ENASLT
; with H = $40, then reads $4000 / $4001 directly -- 3-0's markers or 3-1's header.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xenaslt2.asm --row cf3300
; The capture: CAP+0 = $A5 when finished; CAP+1 the slot register at boot, +2 slot 3's secondary selection at boot,
; +3 SLTTBL+3 at boot; then per case 12 bytes: A, F, the slot register, slot 3's secondary selection, SLTTBL+3, the
; two bytes at $4000 / $4001, B, C, D, E, IFF; then $C3.
; Cases: ID, the secondary register's preset, SLTTBL+3's preset ($FF none; else pages 0-2's fields), ei:
; 0 $83 / page 1 3-1 (both)   1 $87 / none   2 $87 / page 1 3-2   3 $87 / page 1 3-1   4 $83 / $25 (pages 0, 1, 2 :=
; 3-1, 3-1, 3-2)   5 $87 / $29; round 4: 6 $83 / register $25, SLTTBL+3 $1A (different: which one the other fields
; come from)   7 $87 / register $19, SLTTBL+3 $26   8 $87 / none, interrupts on.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry, the published slot registers and work-area cells, and 3-1's two
; header bytes under the ruling above -- no other byte of any ROM.
;
; @cap C000
; @caplen 0080
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
a8b     equ     $E902
secb    equ     $E903
sltb    equ     $E904
tp      equ     $E906
cid     equ     $E908
cps     equ     $E909
cpt     equ     $E90A                   ; SLTTBL+3's preset
cei     equ     $E90B
RAMB    equ     $EA00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $007F
                ld      (hl), 0
                ldir
                ld      hl, blk
                ld      de, RAMB
                ld      bc, blk_end - blk
                ldir
                jp      RAMB

blk:
                di
                ld      hl, CAP+1
                ld      (ptr), hl
                in      a, ($A8)
                ld      (a8b), a
                call    RAMB + emit - blk
                ld      a, ($FFFF)
                cpl
                ld      (secb), a
                call    RAMB + emit - blk
                ld      a, ($FCC8)
                ld      (sltb), a
                call    RAMB + emit - blk
                ; 3-0's markers by hand: page 1 := slot 3, its secondary 0
                ld      a, (secb)
                and     $F3
                ld      ($FFFF), a
                ld      a, (a8b)
                or      $0C
                out     ($A8), a
                ld      a, $5A
                ld      ($4000), a
                ld      a, $A5
                ld      ($4001), a
                call    RAMB + boot - blk
                ld      hl, RAMB + cases - blk
                ld      (tp), hl
next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, RAMB + finish - blk
                ld      (cid), a
                inc     hl
                ld      a, (hl)
                ld      (cps), a
                inc     hl
                ld      a, (hl)
                ld      (cpt), a
                inc     hl
                ld      a, (hl)
                ld      (cei), a
                inc     hl
                ld      (tp), hl
                call    RAMB + boot - blk
                ld      a, (cps)
                cp      $FF
                jr      z, c_nops
                and     $3F
                ld      b, a
                ld      a, (secb)
                and     $C0
                or      b
                ld      ($FFFF), a
                ld      a, (cpt)
                and     $3F
                ld      b, a
                ld      a, (sltb)
                and     $C0
                or      b
                ld      ($FCC8), a
c_nops:
                ld      a, (cei)
                or      a
                jr      z, c_di
                ei
c_di:
                ld      bc, $1357               ; round 5: markers, so B-E after are ENASLT's, not the last case's
                ld      de, $9BDF
                ld      a, (cid)
                ld      h, $40
                call    $0024                   ; ENASLT (the presets may have switched page 2 to 3-1 / 3-2: safe,
                                                ; as the code, the capture and the stack are all in page 3)
                push    de
                push    bc
                push    af
                ld      a, i
                jp      pe, $+5                 ; off? read again: an interrupt accepted DURING `ld a,i` reads
                ld      a, i                    ; P/V 0 (the NMOS erratum, D-IFFREAD1)
                di
                push    af
                pop     hl
                ld      a, l
                rrca
                rrca
                and     1
                ld      c, a                    ; C = IFF
                pop     hl                      ; H = A, L = F
                ld      a, h
                call    RAMB + emit - blk
                ld      a, l
                call    RAMB + emit - blk
                in      a, ($A8)
                call    RAMB + emit - blk
                ld      a, ($FFFF)
                cpl
                call    RAMB + emit - blk
                ld      a, ($FCC8)
                call    RAMB + emit - blk
                ld      a, ($4000)
                call    RAMB + emit - blk
                ld      a, ($4001)
                call    RAMB + emit - blk
                ld      e, c
                pop     bc
                ld      a, b
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      c, e
                pop     de
                ld      a, d
                call    RAMB + emit - blk
                ld      a, e
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                jp      RAMB + next - blk

boot:
                ld      a, (secb)
                ld      ($FFFF), a
                ld      a, (a8b)
                out     ($A8), a
                ld      a, (sltb)
                ld      ($FCC8), a
                ret

finish:
                call    RAMB + boot - blk
                ld      a, $C3
                call    RAMB + emit - blk
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret

; ---- cases: ID, page-1 preset ($FF none); $FF ends ----
cases:
                db      $83, $04, $04, 0
                db      $87, $FF, $FF, 0
                db      $87, $08, $08, 0
                db      $87, $04, $04, 0
                db      $83, $25, $25, 0
                db      $87, $29, $29, 0
                db      $83, $25, $1A, 0
                db      $87, $19, $26, 0
                db      $87, $FF, $FF, 1
                db      $FF
blk_end:
