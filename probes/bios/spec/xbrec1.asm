; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XBREC1 -- the BDOS's record functions through $F37D, round 1 (2026-11-22): WRSEQ ($15), RDSEQ ($14), SETRND ($24),
; RDRND ($21), WRRND ($22), with FMAKE / FCLOSE / FOPEN / FSIZE around them, on the empty 720 KB disk. XBFILE4's frame,
; 52-byte record and modes (probes/bios/spec/xbfile4.asm), with ONE change: before each case the DTA's 128 bytes are
; filled with $40 + the case number, so a record written carries its case's mark and a record read shows whose it is.
; The record's DTA bytes are the DTA's first 13 after the call.
; Cases:
;   0: SETDTA $A800 (C $1A; the DTA $40)
;   1: FMAKE R.TXT (C $16; the DTA $41)
;   2: WRSEQ (record 0) (C $15; the DTA $42)
;   3: WRSEQ (record 1) (C $15; the DTA $43)
;   4: FCLOSE (C $10; the DTA $44)
;   5: FOPEN R.TXT (C $0F; the DTA $45)
;   6: RDSEQ (C $14; the DTA $46)
;   7: RDSEQ (C $14; the DTA $47)
;   8: RDSEQ (past the end) (C $14; the DTA $48)
;   9: SETRND (C $24; the DTA $49)
;   10: RDRND, RR := 0 (C $21; the DTA $4A)
;   11: WRRND, RR := 5 (C $22; the DTA $4B)
;   12: RDRND, RR := 5 (C $21; the DTA $4C)
;   13: RDRND, RR := 3 (never written) (C $21; the DTA $4D)
;   14: FCLOSE (C $10; the DTA $4E)
;   15: FSIZE R.TXT (C $23; the DTA $4F)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbrec1.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 350
; @timeout 60

CALSLT  equ     $001C
BDOS    equ     $F37D
cmode   equ     $A4F0
cno     equ     $A4F1
FCB     equ     $A600
DTAB    equ     $A800
DTA     equ     $F23D
cde     equ     $A408
chl     equ     $A40A
DRVSLT  equ     $FB22
tptr    equ     $A402
entry   equ     $A404
cb      equ     $A406
cc      equ     $A407
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $A001
ptr     equ     $A400
rsave   equ     $A410
buf     equ     $A412

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $23F
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
                xor     a
                ld      (cno), a            ; the case counter (outside the cleared capture)
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      (cc), a
                inc     hl
                ld      a, (hl)             ; 0 keep, 1 name, 2 name + new, 3 name + $FF fill, 4 DE / HL
                inc     hl
                ld      (cmode), a
                cp      4
                jr      nz, notregs
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
                jp      fset
notregs:
                cp      5
                jr      z, pokes            ; 5: poke into the FCB as it is
                or      a
                jp      z, fset
                push    af
                push    hl
                ld      hl, FCB             ; clear the FCB
                ld      b, 37
fc:
                ld      (hl), 0
                inc     hl
                djnz    fc
                pop     hl
                ld      de, FCB + 1
                ld      bc, 11
                ldir
                pop     af
                cp      2
                jr      nz, not2
                ld      de, FCB + 17
                ld      bc, 11
                ldir
not2:
                cp      3
                jp      nz, chk6
                push    hl
                ld      hl, FCB + 12        ; $FF at +12 .. +36
                ld      b, 25
ff1:
                ld      (hl), $FF
                inc     hl
                djnz    ff1
                pop     hl
chk6:
                ld      a, (cmode)
                cp      6
                jp      nz, fset
pokes:
                ld      b, (hl)             ; the pair count, then (offset, value) pairs
                inc     hl
pk1:
                ld      e, (hl)
                inc     hl
                ld      d, 0
                ld      a, (hl)
                inc     hl
                push    hl
                ld      hl, FCB
                add     hl, de
                ld      (hl), a
                pop     hl
                djnz    pk1
fset:
                ld      (tptr), hl
                ld      a, (cno)            ; the DTA: 128 x ($40 + the case number)
                add     a, $40
                ld      hl, DTAB
                ld      b, 128
fd:
                ld      (hl), a
                inc     hl
                djnz    fd
                ld      hl, cno
                inc     (hl)
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 52
                add     hl, de
                ld      (ptr), hl
                jp      nxt
go:
                ld      a, (cc)
                ld      c, a
                ld      de, FCB
                ld      a, (cmode)
                cp      4
                jr      nz, notdta
                ld      de, (cde)
                ld      hl, (chl)
notdta:
                di
                call    BDOS
                di
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
                ex      de, hl
                ld      hl, FCB
                ld      bc, 37
                ldir
                ld      hl, DTAB
                ld      bc, 13
                ldir
                ld      (ptr), de
                pop     af
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

cases:
                db      $1A, 4
                dw      $A800, $0000
                db      $16, 1, "R       TXT"
                db      $15, 0
                db      $15, 0
                db      $10, 0
                db      $0F, 1, "R       TXT"
                db      $14, 0
                db      $14, 0
                db      $14, 0
                db      $24, 0
                db      $21, 5, 3, 33, $00, 34, $00, 35, $00
                db      $22, 5, 3, 33, $05, 34, $00, 35, $00
                db      $21, 5, 1, 33, $05
                db      $21, 5, 1, 33, $03
                db      $10, 0
                db      $23, 1, "R       TXT"
                db      $FF

                ds      $8000 - $, $FF
