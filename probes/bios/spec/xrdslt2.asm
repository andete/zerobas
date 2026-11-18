; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XRDSLT2 -- docs/bios/RDSLT.md / WRSLT.md round 6 (2026-11-18): the ID's SECONDARY slot. Run on the cf3300 row only
; (the one reference with an expanded slot 3: RAM in 3-0, a ROM in 3-1). Under Joost's ruling of 2026-11-18 a probe may
; read the two cartridge-header bytes at $4000 / $4001 of a ROM sub-slot ("AB", the ID the BIOS's own slot scan reads)
; -- this probe reads 3-1 there and nowhere else. RDSLT naming 3-1 ($87) at $4000 must return 'A' where 3-0 holds $18:
; that tells "the ID's bits 2-3 go into the page's field" from "the field is cleared", and 3-1 from an alias of 3-0.
; The probe runs from RAM ($EA00, page 3 = 3-0), interrupts off.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xrdslt2.asm --row cf3300
; The capture: CAP+0 = $A5 when finished; CAP+1 the slot register at boot, +2 EXPTBL+3, +3 slot 3's secondary selection
; at boot (the register read complemented), +4 / +5 3-1's bytes at $4000 / $4001 read by hand (the header); then per
; case 8 bytes: A after, F after, the slot register after, the secondary selection after, B, C, 0, 0; then $C3.
; Cases (each starts from the boot selection; the preset is set by hand before the call, put back after):
;   0  WRSLT $83 (3-0) $4000 := $18               3  RDSLT $83 $4000
;   1  RDSLT $87 (3-1) $4000                      4  page 1's secondary preset 3-1, RDSLT $83 $4000
;   2  RDSLT $87 $4001                            5  page 1's secondary preset 3-2, RDSLT $87 $4000
;
; CLEAN-ROOM: 100% own code; published BIOS entries, the published slot registers, and 3-1's two header bytes
; ($4000 / $4001) under the ruling above -- no other byte of any ROM.
;
; @cap C000
; @caplen 0080
; @timeout 60

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $E900
a8b     equ     $E902
secb    equ     $E903
tp      equ     $E904
cop     equ     $E906                   ; the case: op (0 WRSLT, 1 RDSLT), ID, value, page-1 secondary preset ($FF none)
cid     equ     $E907
cva     equ     $E908
cps     equ     $E909
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
                ld      a, ($FCC4)
                call    RAMB + emit - blk
                ld      a, ($FFFF)
                cpl
                ld      (secb), a
                call    RAMB + emit - blk
                ; 3-1's header by hand: page 1 := slot 3, its secondary := 1, read $4000 / $4001, put both back
                ld      a, (secb)
                and     $F3
                or      $04
                ld      ($FFFF), a
                ld      a, (a8b)
                or      $0C
                out     ($A8), a
                ld      a, ($4000)
                ld      b, a
                ld      a, ($4001)
                ld      c, a
                ld      a, (a8b)
                out     ($A8), a
                ld      a, (secb)
                ld      ($FFFF), a
                ld      a, b
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                ld      hl, RAMB + cases - blk
                ld      (tp), hl
next:
                di
                ld      hl, (tp)
                ld      a, (hl)
                cp      $FF
                jp      z, RAMB + finish - blk
                ld      de, cop
                ld      bc, 4
                ldir
                ld      (tp), hl
                ld      a, (cps)                ; the preset: page 1's secondary := (cps)
                cp      $FF
                jr      z, c_nops
                add     a, a
                add     a, a
                ld      b, a
                ld      a, (secb)
                and     $F3
                or      b
                ld      ($FFFF), a
c_nops:
                ld      hl, $0014
                ld      a, (cop)
                or      a
                jr      z, c_tgt
                ld      hl, $000C
c_tgt:
                ld      (RAMB + c_jp + 1 - blk), hl
                ld      a, (cva)
                ld      e, a
                ld      hl, $4000
                ld      a, (cid)
                cp      $87
                jr      nz, c_addr
                ld      a, (cva)                ; for $87, the value byte is the address's low byte (0 / 1)
                ld      l, a
c_addr:
                ld      a, (cid)
                ld      bc, $1357
                call    RAMB + c_jp - blk
                jr      c_ret
c_jp:
                jp      0
c_ret:
                push    bc
                push    af
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
                pop     bc
                ld      a, b
                call    RAMB + emit - blk
                ld      a, c
                call    RAMB + emit - blk
                xor     a
                call    RAMB + emit - blk
                call    RAMB + emit - blk
                ld      a, (a8b)                ; boot state back
                out     ($A8), a
                ld      a, (secb)
                ld      ($FFFF), a
                jp      RAMB + next - blk

finish:
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

; ---- cases: op, ID, value (WRSLT: E; RDSLT $87: the address's low byte), page-1 secondary preset; $FF ends ----
cases:
                db      0, $83, $18, $FF        ; 0
                db      1, $87, $00, $FF        ; 1
                db      1, $87, $01, $FF        ; 2
                db      1, $83, $00, $FF        ; 3
                db      1, $83, $00, 1          ; 4
                db      1, $87, $00, 2          ; 5
                db      $FF
blk_end:
