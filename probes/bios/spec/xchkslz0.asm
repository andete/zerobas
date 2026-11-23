; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCHKSLZ0 -- D-MSX2SPEC, docs/msx2/main/CHKSLZ.md (goldfish pass 1, 2026-11-23): xchkslzd.asm with EXBRSA preset
; $00 (the "no sub-ROM" value) instead of $A5 -- does CHKSLZ write EXBRSA when it holds 0? Otherwise identical.
; The original's description: does CHKSLZ ($0162) return, and in which slot state?
; Progress goes to VRAM (which no slot switch hides): $3F00 'B' before the call; after it 'R', port $A8, ($FFFF) cpl,
; A, F, C, B, E, D, L, H, I/IFF F, SP low, SP high; then 'P' once page 3 is put back (port $A8, then ($FFFF)) by hand.
; then EXBRSA, JIFFY before (2) and after (2). Our INIT called again (a magic in page 2 says so) logs 'I', its SP and
; port $A8 at VRAM $3F20 + 4 x n and RETurns at once. Stack in page 2 RAM ($B800). DI; the VDP's interrupt left enabled (the
; NMS 8250 never returned with it disabled). EXBRSA ($FAF8) := $00 first (here).
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchkslz0.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells, the VDP's published ports. No ROM byte read.
;
; @vram 3F00:40
; @caplen 01
; @timeout 30

CHKSLZ  equ     $0162
EXBRSA  equ     $FAF8
DONE    equ     $E000
SVSP    equ     $B900
INISL   equ     $B902
REGS    equ     $B910
JIF0    equ     $B920
MAGIC   equ     $B9F0
NRE     equ     $B9F2
RESP    equ     $B9F4
JIFFY   equ     $FC9E

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      (RESP), sp
                push    af
                push    hl
                ld      hl, (MAGIC)
                ld      a, l
                cp      $5A
                jr      nz, first
                ld      a, h
                cp      $42
                jr      nz, first
                ; re-entry: VRAM $3F20 + 4 x n := 'I', SP lo, SP hi, port $A8; n kept at $B9F2; then RET
                ld      a, (NRE)
                cp      8
                jr      nc, re_ret
                add     a, a
                add     a, a
                add     a, $20
                out     ($99), a
                ld      a, $3F+$40
                out     ($99), a
                ld      a, 'I'
                out     ($98), a
                ld      a, (RESP)
                out     ($98), a
                ld      a, (RESP+1)
                out     ($98), a
                in      a, ($A8)
                out     ($98), a
                ld      hl, NRE
                inc     (hl)
re_ret:
                pop     hl
                pop     af
                ret
first:
                di
                ld      sp, $B800
                ld      hl, $425A
                ld      (MAGIC), hl
                xor     a
                ld      (NRE), a
                xor     a
                out     ($99), a
                ld      a, $8E
                out     ($99), a                ; R#14 := 0
                in      a, ($A8)
                ld      (INISL), a
                ld      a, ($FFFF)
                cpl
                ld      (INISL+1), a
                xor     a
                ld      (EXBRSA), a
                ld      hl, (JIFFY)
                ld      (JIF0), hl
                ld      hl, $3F00
                call    vwr
                ld      a, 'B'
                out     ($98), a
                ld      a, $A7
                ld      bc, $B1C2
                ld      de, $4E5F
                ld      hl, $9876
                call    CHKSLZ
                ld      (SVSP), sp
                ld      sp, REGS+8
                push    hl
                push    de
                push    bc
                push    af
                ld      sp, (SVSP)
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (REGS+8), a
                in      a, ($A8)
                ld      d, a
                ld      a, ($FFFF)
                cpl
                ld      e, a
                ld      hl, $3F01
                call    vwr
                ld      a, 'R'
                out     ($98), a
                ld      a, d
                out     ($98), a
                ld      a, e
                out     ($98), a
                ld      hl, REGS
                ld      a, (hl)                 ; F
                inc     hl
                ld      b, (hl)                 ; A
                inc     hl
                push    af
                ld      a, b
                out     ($98), a
                pop     af
                out     ($98), a
                ld      b, 7
d_lp:
                ld      a, (hl)
                out     ($98), a
                inc     hl
                djnz    d_lp
                ld      a, (SVSP)
                out     ($98), a
                ld      a, (SVSP+1)
                out     ($98), a
                ld      a, (INISL)
                out     ($A8), a
                ld      a, (INISL+1)
                ld      ($FFFF), a
                ld      a, 'P'
                out     ($98), a
                ld      a, (EXBRSA)
                out     ($98), a
                ld      a, (JIF0)
                out     ($98), a
                ld      a, (JIF0+1)
                out     ($98), a
                ld      a, (JIFFY)
                out     ($98), a
                ld      a, (JIFFY+1)
                out     ($98), a
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

vwr:
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      $40
                out     ($99), a
                ret

                ds      $8000 - $, $FF
