; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XPCMCMP -- D-TRSPEC, docs/turbor/main/PCMPLY.md: what PCMPLY ($0186) does with a $00 byte in the data (xpcmply.asm's
; P2 table, 64 bytes with $00 runs, played 2938 samples): short patterns, each played once from RAM, with every OUT
; to $A4 / $A5 logged. Two references (--row turbor: FS-A1GT vs FS-A1ST).
; Per case (table `pats`: length, bytes): $8000-$80FF := $07 (what lies past the pattern), the pattern at $8000;
; R800 DRAM mode (CHGCPU $82), the VDP interrupt off; arm the logs; cpusnap; A = 0 (rate code 0, RAM), HL = $8000,
; BC = length, D = E = 0; CALL $0186; cpusnap; HL, BC, AF.
; Record (RECLEN = $400 from CAP+16 = $8811): +0 case, +1 length, +2..+17 the pattern, +18..+27 two cpusnaps (cpu,
; time us x4), +28 / +30 the $A4 / $A5 log counts (LE), +32 HL, +34 BC, +36 AF after, +64..+79 the $A5 log (16),
; +80..+1023 the $A4 log (944). CAP+0 = cases done. The cases most likely to play long come last.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xpcmcmp.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries, work-area RAM and I/O ports. No ROM byte read: the data played is
; this probe's own RAM.
;
; @cap 8800
; @caplen 5400
; @timeout 120
; @cpusnap 4100 E908
; @portlog A4 E90E 4118
; @portlog A5 E91E 4118

CHGCPU  equ     $0180
PCMPLY  equ     $0186
DONE    equ     $8800
CAP     equ     $8801
REC     equ     CAP+16
RECLEN  equ     $400
DATA    equ     $8000

PTR     equ     $E904
CSPTR   equ     $E908
CIDX    equ     $E90B
TP      equ     $E90C
LGA4    equ     $E90E
LGA5    equ     $E91E

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                jp      main

                ds      $4100-$, 0
snap:           ret
                ds      $4118-$, 0
armlog:         ret

main:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $53FE
                ld      (hl), 0
                ldir
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                call    armlog
                ld      a, $82
                call    CHGCPU
                di
                ld      hl, REC
                ld      (PTR), hl
                ld      hl, pats
                ld      (TP), hl
c_next:
                ld      hl, (TP)
                ld      a, (hl)
                or      a
                jp      z, finish
                ; $8000-$80FF := $07, then the pattern
                push    hl
                ld      hl, DATA
                ld      de, DATA+1
                ld      bc, 255
                ld      (hl), $07
                ldir
                pop     hl
                ld      ix, (PTR)
                ld      a, (CIDX)
                ld      (ix+0), a
                ld      c, (hl)
                ld      (ix+1), c
                ld      b, 0
                inc     hl
                push    hl
                push    bc
                ld      de, DATA
                ldir
                ld      (TP), hl
                pop     bc
                pop     hl
                push    ix
                pop     de
                inc     de
                inc     de
                ldir                            ; the pattern into the record too
                ; the VDP interrupt off
                ld      a, ($F3E0)
                and     $DF
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; snaps and logs
                push    ix
                pop     hl
                ld      de, 18
                add     hl, de
                ld      (CSPTR), hl
                push    ix
                pop     hl
                ld      de, 64
                add     hl, de
                ld      (LGA5), hl
                ld      de, 16
                add     hl, de
                ld      (LGA4), hl
                call    snap
                xor     a
                ld      hl, DATA
                ld      c, (ix+1)
                ld      b, 0
                ld      de, 0
                push    ix
                call    PCMPLY
                call    snap
                pop     ix
                di
                push    af
                ld      (ix+32), l
                ld      (ix+33), h
                ld      (ix+34), c
                ld      (ix+35), b
                pop     hl
                ld      (ix+36), l
                ld      (ix+37), h
                ld      a, ($F3E0)
                out     ($99), a
                ld      a, $81
                out     ($99), a
                ; log counts
                ld      hl, (LGA4)
                push    ix
                pop     de
                or      a
                sbc     hl, de
                ld      de, 80
                or      a
                sbc     hl, de
                ld      (ix+28), l
                ld      (ix+29), h
                ld      hl, (LGA5)
                push    ix
                pop     de
                or      a
                sbc     hl, de
                ld      de, 64
                or      a
                sbc     hl, de
                ld      (ix+30), l
                ld      (ix+31), h
                ld      hl, 0
                ld      (LGA4), hl
                ld      (LGA5), hl
                ; next
                ld      hl, (PTR)
                ld      bc, RECLEN
                add     hl, bc
                ld      (PTR), hl
                ld      hl, CIDX
                inc     (hl)
                ld      a, (hl)
                ld      (CAP), a
                jp      c_next

finish:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

; length, bytes (length 0 ends the table)
pats:
                db      4, $10, $00, $05, $20           ; 0
                db      4, $10, $00, $01, $20           ; 1
                db      4, $10, $00, $02, $20           ; 2
                db      4, $10, $00, $03, $20           ; 3
                db      4, $10, $01, $02, $20           ; 4: $01 alone
                db      3, $10, $80, $20                ; 5
                db      3, $10, $FF, $20                ; 6
                db      2, $00, $05                     ; 7: leading $00
                db      6, $10, $00, $05, $00, $03, $20 ; 8: two runs
                db      4, $10, $00, $05, $30           ; 9
                db      2, $10, $00                     ; 10: $00 as the last byte ($07 follows in RAM)
                db      1, $00                          ; 11: $00 alone
                db      4, $10, $00, $10, $20           ; 12
                db      4, $10, $00, $7F, $20           ; 13
                db      4, $10, $00, $80, $20           ; 14
                db      4, $10, $00, $81, $20           ; 15
                db      4, $10, $00, $FF, $20           ; 16
                db      4, $10, $00, $00, $20           ; 17: $00 $00
                db      0

                ds      $8000-$, $FF
