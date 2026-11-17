; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XFNK -- docs/bios/INIFNK.md / INITXT.md (2026-11-17): the function-key strings FNKSTR ($F87F, 160 B:
; 10 keys x 16) as a cartridge finds them at INIT, and after INIFNK ($003E). XINIT showed the VG-8020's key
; line drawn with labels after INITXT and zerobas's blank: is FNKSTR empty at INIT on zerobas?
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xfnk.asm --row nodisk
; The capture: CAP+0 = $A5 when finished; CAP+1..160 FNKSTR at INIT; CAP+161..320 FNKSTR after INIFNK.
;
; CLEAN-ROOM: 100% own code; a published BIOS entry and work-area cells only.
;
; @cap C000
; @caplen 0141

INIFNK  equ     $003E
FNKSTR  equ     $F87F

DONE    equ     $C000
CAP     equ     $C001

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, FNKSTR
                ld      de, CAP+1
                ld      bc, 160
                ldir
                call    INIFNK
                ld      hl, FNKSTR
                ld      de, CAP+161
                ld      bc, 160
                ldir
                ld      a, $A5
                ld      (CAP), a
                ld      (DONE), a
halt_lp:
                jr      halt_lp
