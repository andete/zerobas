; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBFILE5 -- the BDOS's FCB directory functions through $F37D, round 5 (2026-11-25, D-COPYDATE): WHICH DATE FCLOSE
; WRITES. docs/bdos/FILES.md had "whether FCLOSE re-stamps the date" unmeasured; D-DOSSESSION found COMMAND.COM's
; COPY keeps the source's date on the CF-3300 and gets the current one on zerobas. The FCB's date word is +20, its
; time +22 (R-BF-MAKE). The poked values: 1990-05-05 12:34:56 = date $14A5, time $645C; 1999-12-31 23:59:58 = date
; $279F, time $BF7D. XBFILE4's frame, record and modes (probes/bios/spec/xbfile4.asm).
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: FMAKE EEE.TXT (C $16)
;   2: WRSEQ (C $15) -- the FCB's date after a write
;   3: FCLOSE, +20..23 := 1990-05-05 12:34:56 poked after the write (C $10)
;   4: FOPEN EEE.TXT (C $0F) -- the entry's date / time: case A
;   5: FMAKE FFF.TXT (C $16)
;   6: WRSEQ, +20..23 := 1990-05-05 12:34:56 poked BEFORE the write (C $15) -- does the write overwrite it
;   7: FCLOSE (C $10)
;   8: FOPEN FFF.TXT (C $0F) -- case B
;   9: FCLOSE, +20..23 := 1999-12-31 23:59:58, nothing written since FOPEN (C $10)
;   10: FOPEN FFF.TXT (C $0F) -- case C
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbfile5.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 2B0
; @timeout 60

CALSLT  equ     $001C
BDOS    equ     $F37D
cmode   equ     $A4F0
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
                db      $16, 1, "EEE     TXT"
                db      $15, 0
                db      $10, 5, 4, 20, $A5, 21, $14, 22, $5C, 23, $64
                db      $0F, 1, "EEE     TXT"
                db      $16, 1, "FFF     TXT"
                db      $15, 5, 4, 20, $A5, 21, $14, 22, $5C, 23, $64
                db      $10, 0
                db      $0F, 1, "FFF     TXT"
                db      $10, 5, 4, 20, $9F, 21, $27, 22, $7D, 23, $BF
                db      $0F, 1, "FFF     TXT"
                db      $FF

                ds      $8000 - $, $FF
