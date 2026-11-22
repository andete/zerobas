; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XFNK2 -- docs/bios/INIFNK.md round 1 (2026-11-17): INIFNK ($003E) from GARBAGE. XFNK (xfnk.asm) called INIFNK on
; the VG-8020's boot-time FNKSTR, which already held the defaults, so "INIFNK writes them" could not be told from
; "INIFNK does nothing". Here FNKSTR ($F87F, 160 B) is filled with $5A first, and the bytes either side of it with
; $A5 (does INIFNK write outside FNKSTR?); A / F := $5A / $FF on entry.
; The capture (CAP = C001): +1 = $A5 when finished; +2..+161 FNKSTR after INIFNK; +162 the byte before it, +163 the
; byte after it; +164 A, +165 F on return; +166 the sentinel $C3.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xfnk2.asm --row nodisk
;
; CLEAN-ROOM: 100% own code; one published BIOS entry and work-area cells.
;
; @cap C000

INIFNK  equ     $003E
FNKSTR  equ     $F87F

DONE    equ     $C000
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                ld      hl, FNKSTR
                ld      b, 160
g_lp:
                ld      (hl), $5A
                inc     hl
                djnz    g_lp
                ld      a, $A5
                ld      (FNKSTR-1), a
                ld      (FNKSTR+160), a
                ld      de, $5AFF
                push    de
                pop     af
                call    INIFNK
                push    af
                ld      hl, FNKSTR
                ld      de, CAP+2
                ld      bc, 160
                ldir
                ld      a, (FNKSTR-1)
                ld      (CAP+162), a
                ld      a, (FNKSTR+160)
                ld      (CAP+163), a
                pop     de
                ld      a, d
                ld      (CAP+164), a
                ld      a, e
                ld      (CAP+165), a
                ld      a, $C3
                ld      (CAP+166), a
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp
