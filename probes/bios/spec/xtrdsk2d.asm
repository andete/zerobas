; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDSK2D -- D-TRSPEC (2026-11-23, tr6): xbsys2.asm UNCHANGED except two additions: the interrupt flag is ALSO
; sampled as the first instruction after the BDOS call returns (after a PUSH AF; LD A,I's P/V, 1 = enabled) into the
; byte array at $A300 + case number -- beside xbsys2's own sample, taken ~25 instructions later (the record's +8);
; and @caplen 310 to read that array. Does the FS-A1GT's DI after DSKRST (case 14) exist at the return, or arise
; after it?
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdsk2d.asm --row turbor
;
; (xbsys2's header follows.)
; XBSYS2 -- the BDOS system functions through $F37D, round 2 (2026-11-22), answering review pass 1 (scratchpad/
; BSYS_review1.md): SDATE / GDATE of a non-Sunday (is GDATE's A the day of the week; is SDATE's A 0 "accepted"); what a
; refused SDATE leaves; SDATE / STIME edges; what ALLOC's IX / IY point AT; ALLOC with E 1; what DSKRST resets (the
; current drive, after SELDSK 1). XBSYS1's frame (probes/bios/spec/xbsys1.asm); the record grows to 23 bytes: XBSYS1's
; 15, then -- after ALLOC only -- the 4 bytes at IX and the 4 at IY (both point into RAM, the disk work area; after the
; other functions IX holds an address in the disk ROM and is NOT read: 8 x $00 there).
; Cases (the function; DE, HL):
;   0: SDATE 2026-11-23 (a Monday): C $2B, DE $0B17, HL $07EA
;   1: GDATE: C $2A, DE $0000, HL $0000
;   2: SDATE, month 13: C $2B, DE $0D01, HL $07EA
;   3: GDATE: C $2A, DE $0000, HL $0000
;   4: SDATE, month 0: C $2B, DE $0001, HL $07EA
;   5: SDATE, day 0: C $2B, DE $0100, HL $07EA
;   6: SDATE, day 32: C $2B, DE $0120, HL $07EA
;   7: STIME, hour 24: C $2D, DE $0000, HL $1800
;   8: STIME, minute 60: C $2D, DE $0000, HL $003C
;   9: STIME, second 60: C $2D, DE $3C00, HL $0000
;   10: ALLOC, E 0: C $1B, DE $0000, HL $0000
;   11: ALLOC, E 1: C $1B, DE $0001, HL $0000
;   12: SELDSK, E 1: C $0E, DE $0001, HL $0000
;   13: CURDRV: C $19, DE $0000, HL $0000
;   14: DSKRST: C $0D, DE $0000, HL $0000
;   15: CURDRV: C $19, DE $0000, HL $0000
;   16: LOGIN: C $18, DE $0000, HL $0000
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbsys2.asm --row disk   (and --row cf3300)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 310
; @timeout 60

CALSLT  equ     $001C
BDOS    equ     $F37D
DTA     equ     $F23D
cde     equ     $A208
chl     equ     $A20A
DRVSLT  equ     $FB22
tptr    equ     $A202
entry   equ     $A204
cb      equ     $A206
cc      equ     $A207
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $A001
ptr     equ     $A200
rsave   equ     $A210
buf     equ     $A212

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $18F
                ld      (hl), 0
                ldir
                in      a, ($A8)            ; our slot ID (page 1), for the RST 30h call in H.STKE
                rrca
                rrca
                and     3
                ld      c, a
                ld      hl, EXPTBL
                add     a, l
                ld      l, a
                ld      a, (hl)
                and     $80
                jr      z, plain
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ld      a, (hl)
                rrca
                rrca
                and     3
                rlca
                rlca
                or      c
                or      $80
                ld      c, a
plain:
                ld      a, $F7              ; RST 30h, slot, address, RET
                ld      (H_STKE), a
                ld      a, c
                ld      (H_STKE+1), a
                ld      hl, stke
                ld      (H_STKE+2), hl
                ld      a, $C9
                ld      (H_STKE+4), a
                ret

stke:
                ld      a, $C9
                ld      (H_STKE), a         ; once
                ld      hl, CAP
                ld      (ptr), hl
                ld      hl, cases
                ld      (tptr), hl
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      (cc), a
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (cde), de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
                ld      (tptr), hl
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 23
                add     hl, de
                ld      (ptr), hl
                jr      nxt
go:
                ld      ix, $1111
                ld      iy, $2222
                ld      a, (cc)
                ld      c, a
                ld      de, (cde)
                ld      hl, (chl)
                di
                call    BDOS
                push    af
                ld      a, i                ; at once: P/V := IFF2
                ld      a, 0
                jp      po, eoff
                inc     a
eoff:
                ld      ($A3F0), a
                push    hl
                push    de
                ld      hl, (tptr)          ; the case number = (tptr - (cases + 5)) / 5
                ld      de, cases+5
                or      a
                sbc     hl, de
                ld      e, 0
ediv:
                ld      a, h
                or      l
                jr      z, edone
                ld      a, l
                sub     5
                ld      l, a
                ld      a, h
                sbc     a, 0
                ld      h, a
                inc     e
                jr      ediv
edone:
                ld      d, $A3
                ld      a, ($A3F0)
                ld      (de), a
                pop     de
                pop     hl
                pop     af
                ld      (rsave), hl
                push    af
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                push    hl
                push    af
                pop     hl
                ld      a, l
                pop     hl
                ld      (hl), a
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                ld      a, (rsave+1)
                ld      (hl), a
                inc     hl
                ld      a, (rsave)
                ld      (hl), a
                inc     hl
                ld      a, i
                jp      pe, ion
                ld      a, i
ion:
                ld      a, 0
                jp      po, ioff
                ld      a, 1
ioff:
                ld      (hl), a
                inc     hl
                di
                push    ix
                pop     de
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                push    iy
                pop     de
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                ld      a, (DTA+1)
                ld      (hl), a
                inc     hl
                ld      a, (DTA)
                ld      (hl), a
                inc     hl
                ex      de, hl              ; DE -> the record
                ld      a, (cc)
                cp      $1B                 ; ALLOC: the 4 bytes at IX, the 4 at IY
                jr      nz, nodump
                push    ix
                pop     hl
                ld      bc, 4
                ldir
                push    iy
                pop     hl
                ld      bc, 4
                ldir
                jr      dumped
nodump:
                ld      b, 8
nd1:
                xor     a
                ld      (de), a
                inc     de
                djnz    nd1
dumped:
                ld      (ptr), de
                pop     af
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

cases:
                db      $2B
                dw      $0B17, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0D01, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0001, $07EA
                db      $2B
                dw      $0100, $07EA
                db      $2B
                dw      $0120, $07EA
                db      $2D
                dw      $0000, $1800
                db      $2D
                dw      $0000, $003C
                db      $2D
                dw      $3C00, $0000
                db      $1B
                dw      $0000, $0000
                db      $1B
                dw      $0001, $0000
                db      $0E
                dw      $0001, $0000
                db      $19
                dw      $0000, $0000
                db      $0D
                dw      $0000, $0000
                db      $19
                dw      $0000, $0000
                db      $18
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
