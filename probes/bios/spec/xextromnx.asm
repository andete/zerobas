; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XEXTROMNX -- D-MSX2SPEC, docs/msx2/main/EXTROM.md (goldfish pass 1, 2026-11-23): EXTROM ($015F) with EXBRSA ($FAF8)
; := a NON-EXPANDED slot (bit 7 clear). xextrom.asm's RAM slots are all expanded; this one is our own cartridge's
; slot. openMSX mirrors a 16 KB cartridge into page 0 when its mapper is guessed as mirrored -- the probe first reads
; its own slot's $0000 / $0001 with RDSLT (our own bytes) and calls only if they are "AB".
; The routine is ours, in the cartridge at `stub` ($4xxx), called at its page-0 mirror (IX = stub - $4000); it is
; position-independent (RAM addresses only) and records BC, DE, HL, IX, AF, port $A8, ($FFFF) cpl (page 3's
; secondary register), SP, then returns A $24, HL $1357.
; The capture (CAP = C001): +0 $01 when the call returned ($EE: cartridge slot expanded, $ED: no page-0 mirror),
; +1 the cartridge's primary slot, +2 EXPTBL of it, +3/+4 RDSLT ($0000) / ($0001), +5 port $A8 before, +6 ($FFFF)
; cpl before, +7 the stub's mark ($5A = it ran), +8 its port $A8, +9 its ($FFFF) cpl, +10/11 its BC, +12/13 DE,
; +14/15 HL, +16/17 IX, +18/19 AF (F, A), +20/21 its SP, +22 A after, +23/24 HL after, +25 port $A8 after,
; +26 ($FFFF) cpl after, +27 EXBRSA after, +28 IFF after (ld a,i flags, bit 2), +29 $5A.
; Entry: A $A7, F $00, BC $B1C2, DE $4E5F, HL $9876, DI. SP $E800 at the CALL.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xextromnx.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; published BIOS entries and work-area cells; RDSLT reads only our own cartridge.
;
; @cap C000
; @caplen 0040
; @timeout 60

RDSLT   equ     $000C
EXTROM  equ     $015F
EXBRSA  equ     $FAF8
EXPTBL  equ     $FCC1
DONE    equ     $C000
CAP     equ     $C001
SVEX    equ     $E902

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $003E
                ld      (hl), 0
                ldir
                ld      a, $5A
                ld      (CAP+29), a
                in      a, ($A8)
                rrca
                rrca
                and     3
                ld      (CAP+1), a
                ld      e, a
                ld      d, 0
                ld      hl, EXPTBL
                add     hl, de
                ld      a, (hl)
                ld      (CAP+2), a
                and     $80
                jr      z, nx_ok
                ld      a, $EE
                ld      (CAP), a
                jp      finish
nx_ok:
                ld      a, (CAP+1)
                ld      hl, $0000
                call    RDSLT
                di
                ld      (CAP+3), a
                ld      a, (CAP+1)
                ld      hl, $0001
                call    RDSLT
                di
                ld      (CAP+4), a
                ld      hl, (CAP+3)
                ld      de, $4241               ; "AB"
                or      a
                sbc     hl, de
                jr      z, mir_ok
                ld      a, $ED
                ld      (CAP), a
                jp      finish
mir_ok:
                in      a, ($A8)
                ld      (CAP+5), a
                ld      a, ($FFFF)
                cpl
                ld      (CAP+6), a
                ld      a, (EXBRSA)
                ld      (SVEX), a
                ld      a, (CAP+1)
                ld      (EXBRSA), a
                ld      ix, stub - $4000
                ld      bc, $B1C2
                ld      de, $4E5F
                ld      hl, $A700
                push    hl
                pop     af
                ld      hl, $9876
                call    EXTROM
                ld      (CAP+22), a
                ld      (CAP+23), hl
                ld      a, i
                push    af
                pop     hl
                ld      a, l
                ld      (CAP+28), a
                di
                in      a, ($A8)
                ld      (CAP+25), a
                ld      a, ($FFFF)
                cpl
                ld      (CAP+26), a
                ld      a, (EXBRSA)
                ld      (CAP+27), a
                ld      a, (SVEX)
                ld      (EXBRSA), a
                ld      a, 1
                ld      (CAP), a
finish:
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

; runs at its page-0 mirror: RAM addresses only, no jump inside
stub:
                ld      (CAP+10), bc
                ld      (CAP+12), de
                ld      (CAP+14), hl
                ld      (CAP+16), ix
                push    af
                pop     hl
                ld      (CAP+18), hl
                ld      (CAP+20), sp
                in      a, ($A8)
                ld      (CAP+8), a
                ld      a, ($FFFF)
                cpl
                ld      (CAP+9), a
                ld      a, $5A
                ld      (CAP+7), a
                ld      hl, $1357
                ld      a, $24
                ret

                ds      $8000 - $, $FF
