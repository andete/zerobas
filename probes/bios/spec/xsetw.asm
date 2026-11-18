; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XSETW -- D-SETWRTEI (2026-11-18): do the VG-8020's SETWRT ($0053) / SETRD ($0050) return with interrupts enabled?
; C-BIOS's end `EI / RET`; a caller's first OUT / IN after them can then meet an interrupt. Each entered with
; interrupts OFF; LD A,I's flags read right after the return (bit 2 = IFF2), then two bytes written ($C3 $3C after
; SETWRT $1006) / read (after SETRD $1006). Also entered with interrupts ON (does the call disable them?).
; The capture (CAP = C001): +1 = $A5 when finished; +2 SETWRT-from-DI's flags, +3 SETRD-from-DI's, +4 SETWRT-from-EI's,
; +5 SETRD-from-EI's, +6 / +7 the two bytes SETRD read, +8..+23 VRAM $1000..$100F after the writes, +24 the sentinel $C3.
; Run 1 (OUTs back to back): IFF2 1 after all four calls on BOTH machines; the VG-8020 lost the first byte ($3C at
; $1006). Run 2 (two EX (SP),HL between the OUTs): both machines c33c. The loss is the emulated TMS9918's access timing in
; active display, not the interrupt: D-SETWRTEI is not a BIOS difference.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xsetw.asm --row nodisk
;
; CLEAN-ROOM: 100% own code; published BIOS entries and the VDP's published data port.
;
; @cap C000

RDVRM   equ     $004A
FILVRM  equ     $0056
SETRD   equ     $0050
SETWRT  equ     $0053

DONE    equ     $C000
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, $1000
                ld      bc, 16
                ld      a, $77
                call    FILVRM
                ; SETWRT from DI
                di
                ld      hl, $1006
                call    SETWRT
                ld      a, i
                push    af
                pop     bc
                ld      a, c
                ld      (CAP+2), a
                ld      a, $C3
                out     ($98), a
                ex      (sp), hl                ; run 2: ~45 T-states between the OUTs (a TMS9918 access slot)
                ex      (sp), hl
                ld      a, $3C
                out     ($98), a
                ; SETRD from DI
                di
                ld      hl, $1006
                call    SETRD
                ld      a, i
                push    af
                pop     bc
                ld      a, c
                ld      (CAP+3), a
                in      a, ($98)
                ld      (CAP+6), a
                in      a, ($98)
                ld      (CAP+7), a
                ; both from EI
                ei
                ld      hl, $1100
                call    SETWRT
                ld      a, i
                push    af
                pop     bc
                ld      a, c
                ld      (CAP+4), a
                ei
                ld      hl, $1100
                call    SETRD
                ld      a, i
                push    af
                pop     bc
                ld      a, c
                ld      (CAP+5), a
                di
                ld      hl, $1000
                ld      de, CAP+8
                ld      b, 16
r_lp:
                push    bc
                push    hl
                call    RDVRM
                ld      (de), a
                inc     de
                pop     hl
                pop     bc
                inc     hl
                djnz    r_lp
                ld      a, $C3
                ld      (CAP+24), a
                ld      a, $A5
                ld      (CAP+1), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp
