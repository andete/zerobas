; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XFSW -- docs/bios/DSPFNK.md / D-KEYLINESHIFT (2026-11-18): does the VG-8020's DSPFNK ($00CF) pick the label set
; (keys 1-5 or 6-10) from FNKSWI ($FBCD), or from the SHIFT key at call time? zerobas's key-line tenant reads
; FNKSWI (1: keys 1-5, 0: keys 6-10) -- and leaves it 0 at cartridge INIT. Four cases, no key pressed: FNKSWI := 0, 1,
; $5A, $FF, then DSPFNK (40 columns, CRTCNT 24, FNKSTR "key0".."key9").
; The capture (CAP = C001): +1 = $A5 when finished; per case 41 bytes from +2: FNKSWI after the call, row 24's first
; 40 cells; then the sentinel $C3.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xfsw.asm --row nodisk
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM.
;
; @cap C000

RDVRM   equ     $004A
INITXT  equ     $006C
DSPFNK  equ     $00CF
LINL40  equ     $F3AE
CRTCNT  equ     $F3B1
CNSDFG  equ     $F3DE
FNKSTR  equ     $F87F
FNKSWI  equ     $FBCD

DONE    equ     $C000
CAP     equ     $C001
ptr     equ     $EF00
cidx    equ     $EF02

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
                ld      hl, CAP+2
                ld      (ptr), hl
                ld      hl, keys
                ld      de, FNKSTR
                ld      bc, 160
                ldir
                xor     a
                ld      (cidx), a
c_lp:
                ld      a, 40
                ld      (LINL40), a
                ld      a, 24
                ld      (CRTCNT), a
                xor     a
                ld      (CNSDFG), a
                call    INITXT
                ld      a, (cidx)
                ld      e, a
                ld      d, 0
                ld      hl, vals
                add     hl, de
                ld      a, (hl)
                ld      (FNKSWI), a
                call    DSPFNK
                ld      a, (FNKSWI)
                call    emit
                ld      hl, 920
                ld      b, 40
r_lp:
                push    bc
                push    hl
                call    RDVRM
                call    emit
                pop     hl
                pop     bc
                inc     hl
                djnz    r_lp
                ld      a, (cidx)
                inc     a
                ld      (cidx), a
                cp      4
                jr      nz, c_lp
                ld      a, $C3
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

vals:           db      0, 1, $5A, $FF
keys:
                db      "key0", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key1", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key2", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key3", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key4", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key5", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key6", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key7", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key8", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                db      "key9", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
