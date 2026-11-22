; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XBSYS1 -- the BDOS's system functions through $F37D (the disk ROM's BDOS entry, the one Disk BASIC and a ROM use),
; round 1 (2026-11-22): VERSION ($0C), CURDRV ($19), SELDSK ($0E), LOGIN ($18), SETDTA ($1A), ALLOC ($1B), GDATE /
; SDATE ($2A / $2B), GTIME / STIME ($2C / $2D), DSKRST ($0D). XDENT1's frame (probes/bios/spec/xdent1.asm: an H.STKE
; cartridge, so the cases run once the disk interface is initialised; drive A the generated empty 720 KB disk). Each
; case sets C = the function, DE and HL as listed, IX $1111, IY $2222, interrupts off, and calls $F37D. The 15-byte
; record: A, F, B, C, D, E, H, L, the interrupt state after, IX (2), IY (2), then the DTA cell ($F23D, 2). The NODISK
; row has no disk ROM ($FB22 0): its records are skipped (0).
; Cases (the function; DE, HL):
;   0: VERSION: C $0C, DE $0000, HL $0000
;   1: CURDRV: C $19, DE $0000, HL $0000
;   2: SELDSK, E 0: C $0E, DE $0000, HL $0000
;   3: LOGIN: C $18, DE $0000, HL $0000
;   4: SETDTA, DE $A800: C $1A, DE $A800, HL $0000
;   5: ALLOC, E 0: C $1B, DE $0000, HL $0000
;   6: GDATE: C $2A, DE $0000, HL $0000
;   7: SDATE 2026-11-22: C $2B, DE $0B16, HL $07EA
;   8: GDATE: C $2A, DE $0000, HL $0000
;   9: GTIME: C $2C, DE $0000, HL $0000
;   10: STIME 12:34:56.00: C $2D, DE $3800, HL $0C22
;   11: GTIME: C $2C, DE $0000, HL $0000
;   12: DSKRST: C $0D, DE $0000, HL $0000
;   13: SDATE, month 13: C $2B, DE $0D01, HL $07EA
;   14: STIME, hour 25: C $2D, DE $0000, HL $1900
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbsys1.asm --row both   (and --row cf3300)
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
                db      $0C
                dw      $0000, $0000
                db      $19
                dw      $0000, $0000
                db      $0E
                dw      $0000, $0000
                db      $18
                dw      $0000, $0000
                db      $1A
                dw      $A800, $0000
                db      $1B
                dw      $0000, $0000
                db      $2A
                dw      $0000, $0000
                db      $2B
                dw      $0B16, $07EA
                db      $2A
                dw      $0000, $0000
                db      $2C
                dw      $0000, $0000
                db      $2D
                dw      $3800, $0C22
                db      $2C
                dw      $0000, $0000
                db      $0D
                dw      $0000, $0000
                db      $2B
                dw      $0D01, $07EA
                db      $2D
                dw      $0000, $1900
                db      $FF

                ds      $8000 - $, $FF
