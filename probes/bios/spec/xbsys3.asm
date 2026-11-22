; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBSYS3 -- the BDOS system functions through $F37D, round 3 (2026-11-22), answering review pass 2 (scratchpad/
; BSYS_review2.md): GDATE's A for a Tuesday (the weekday, or (day - 1) mod 7); does a refused SDATE write any field (month
; 13 with another year; day 32; day 31 of November -- each followed by GDATE); the acceptance edges (12-31, 01-01,
; 23:59:59); DSKRST with E 1 after SELDSK 1 (drive A, or drive E). XBSYS1's frame and 15-byte record
; (probes/bios/spec/xbsys1.asm).
; Cases (the function; DE, HL):
;   0: SDATE 2026-12-01 (a Tuesday): C $2B, DE $0C01, HL $07EA
;   1: GDATE: C $2A, DE $0000, HL $0000
;   2: SDATE 1999, month 13: C $2B, DE $0D01, HL $07CF
;   3: GDATE: C $2A, DE $0000, HL $0000
;   4: SDATE 2026-01-32: C $2B, DE $0120, HL $07EA
;   5: GDATE: C $2A, DE $0000, HL $0000
;   6: SDATE 2026-11-31: C $2B, DE $0B1F, HL $07EA
;   7: GDATE: C $2A, DE $0000, HL $0000
;   8: SDATE 2026-12-31: C $2B, DE $0C1F, HL $07EA
;   9: SDATE 2026-01-01: C $2B, DE $0101, HL $07EA
;   10: GDATE: C $2A, DE $0000, HL $0000
;   11: STIME 23:59:59: C $2D, DE $3B00, HL $173B
;   12: SELDSK, E 1: C $0E, DE $0001, HL $0000
;   13: DSKRST, E 1: C $0D, DE $0001, HL $0000
;   14: CURDRV: C $19, DE $0000, HL $0000
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbsys3.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
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
                ld      bc, $FE
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
                ld      de, 15
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
                ld      (ptr), hl
                pop     af
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

cases:
                db      $2B
                dw      $0C01, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0D01, $07CF
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0120, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0B1F, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0C1F, $07EA
                db      $2B
                dw      $0101, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2D
                dw      $3B00, $173B
                db      $0E
                dw      $0001, $0000
                db      $0D
                dw      $0001, $0000
                db      $19
                dw      $0000, $0000
                db      $FF

                ds      $8000 - $, $FF
