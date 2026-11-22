; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCNV -- docs/bios/CNVCHR.md round 1 (2026-11-17): CNVCHR ($00AB) on the VG-8020 against zerobas, exhaustively:
; every A (0..255) x GRPHED ($FCA6) in {0, 1, $5A} x the flags on entry in {$00, $FF} (A / F loaded by POP AF).
; Order: for ef in ($00, $FF): for g in (0, 1, $5A): for a in 0..255 -- 1536 cases, 3 bytes each: A, F, GRPHED after
; the call. probes/bios/spec/xcnv_rules.py decodes the same order.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xcnv.asm --row nodisk
; The capture: CAP+1 = $A5 when finished; records from CAP+2, then the sentinel $C3 after the last.
;
; CLEAN-ROOM: 100% own code; one published BIOS entry and one work-area cell.
;
; @cap C000
; @caplen 1203
; @timeout 120

CNVCHR  equ     $00AB
GRPHED  equ     $FCA6

DONE    equ     $C000
CAP     equ     $C001
CAPLEN  equ     4611                    ; 2 + 1536 x 3 + 1
ptr     equ     $EF00
cef     equ     $EF02
cg      equ     $EF03
ca      equ     $EF04
gidx    equ     $EF05

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, CAPLEN - 1
                ld      (hl), 0
                ldir
                ld      hl, CAP+2
                ld      (ptr), hl
                xor     a
                ld      (cef), a
ef_lp:
                xor     a
                ld      (gidx), a
g_lp:
                ld      a, (gidx)
                ld      e, a
                ld      d, 0
                ld      hl, gvals
                add     hl, de
                ld      a, (hl)
                ld      (cg), a
                xor     a
                ld      (ca), a
a_lp:
                ld      a, (cg)
                ld      (GRPHED), a
                ld      a, (ca)
                ld      d, a
                ld      a, (cef)
                ld      e, a
                push    de
                pop     af
                call    CNVCHR
                push    af
                pop     de
                ld      a, d
                call    emit
                ld      a, e
                call    emit
                ld      a, (GRPHED)
                call    emit
                ld      a, (ca)
                inc     a
                ld      (ca), a
                jr      nz, a_lp
                ld      a, (gidx)
                inc     a
                ld      (gidx), a
                cp      3
                jr      nz, g_lp
                ld      a, (cef)
                cpl
                ld      (cef), a
                or      a
                jr      nz, ef_lp               ; $00 then $FF, then back to $00: done
                ld      a, $C3                  ; the sentinel
                call    emit
                ld      a, $A5
                ld      (CAP+1), a
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

gvals:          db      0, 1, $5A
