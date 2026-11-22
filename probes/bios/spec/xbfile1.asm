; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBFILE1 -- the BDOS's FCB directory functions through $F37D, round 1 (2026-11-22): FMAKE ($16), FCLOSE ($10), SFIRST
; ($11), SNEXT ($12), FOPEN ($0F), FSIZE ($23), FREN ($17), FDEL ($13), on the empty 720 KB disk in drive A. XBSYS1's
; frame (probes/bios/spec/xbsys1.asm). The FCB is at $A600 (37 bytes), the DTA at $A800 (set by case 0). A case that
; names a file first clears the FCB (37 x $00) and writes drive 0 and the 11-byte name at +1 (FREN: the new name at
; +17, +16 0); "KEEP" uses the FCB as the case before left it. DE = $A600, interrupts off, then CALL $F37D. The
; 52-byte record (the frame's variables live at $A3xx: the capture reaches $A23D): A, F, the FCB's 37 bytes, the DTA's first 13 bytes ($A800 is filled with $E5 x 40 before each case).
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: FMAKE TEST.TXT (C $16)
;   2: FCLOSE (C $10)
;   3: SFIRST ????????.TXT (C $11)
;   4: SNEXT (C $12)
;   5: FOPEN TEST.TXT (C $0F)
;   6: FSIZE TEST.TXT (C $23)
;   7: FREN TEST.TXT -> NEW.TXT (C $17)
;   8: FOPEN TEST.TXT (renamed away) (C $0F)
;   9: FDEL NEW.TXT (C $13)
;   10: SFIRST ????????.??? (C $11)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbfile1.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 240
; @timeout 60

CALSLT  equ     $001C
BDOS    equ     $F37D
FCB     equ     $A600
DTAB    equ     $A800
DTA     equ     $F23D
cde     equ     $A308
chl     equ     $A30A
DRVSLT  equ     $FB22
tptr    equ     $A302
entry   equ     $A304
cb      equ     $A306
cc      equ     $A307
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA

DONE    equ     $A000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $A001
ptr     equ     $A300
rsave   equ     $A310
buf     equ     $A312

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
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      (cc), a
                inc     hl
                ld      a, (hl)             ; 0: keep the FCB, 1: name, 2: name + new name
                inc     hl
                or      a
                jr      z, fset
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
                jr      nz, fset
                ld      de, FCB + 17
                ld      bc, 11
                ldir
fset:
                ld      (tptr), hl
                ld      hl, DTAB            ; the DTA: $E5 x 40
                ld      b, 40
fd:
                ld      (hl), $E5
                inc     hl
                djnz    fd
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 52
                add     hl, de
                ld      (ptr), hl
                jr      nxt
go:
                ld      a, (cc)
                ld      c, a
                ld      de, FCB
                cp      $1A
                jr      nz, notdta
                ld      de, DTAB
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
                db      $1A, 0
                db      $16, 1, "TEST    TXT"
                db      $10, 0
                db      $11, 1, "????????TXT"
                db      $12, 0
                db      $0F, 1, "TEST    TXT"
                db      $23, 1, "TEST    TXT"
                db      $17, 2, "TEST    TXT", "NEW     TXT"
                db      $0F, 1, "TEST    TXT"
                db      $13, 1, "NEW     TXT"
                db      $11, 1, "???????????"
                db      $FF

                ds      $8000 - $, $FF
