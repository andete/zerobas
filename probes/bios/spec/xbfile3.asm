; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBFILE3 -- the BDOS's FCB directory functions through $F37D, round 3 (2026-11-22), answering review pass 2
; (scratchpad/BFILE_review2.md): WHICH pre-filled byte made round 2's WRSEQ / FOPEN fail -- the extent (+12) or the
; current record (+32), each set alone; whether WRSEQ writes +24 / +32 or clears bits ($41 / $85 entered); FOPEN with
; +12 $FF and the rest 0, and with +12 1; FOPEN / FSIZE of a file holding a record (FSIZE over $FF at +33 .. +36); the
; not-found answers of FDEL, FREN and FSIZE. XBFILE2's frame and 52-byte record (probes/bios/spec/xbfile2.asm); two
; new modes: 5 = POKE the listed (offset, value) pairs into the FCB as the case before left it, 6 = clear + name, then
; poke. The frame's variables live at $A4xx (the capture reaches $A341).
; Cases:
;   0: FMAKE TEST.TXT (C $16)
;   1: WRSEQ, extent +12 := $FF only (C $15)
;   2: FCLOSE (C $10)
;   3: FMAKE TWO.TXT (C $16)
;   4: WRSEQ, current record +32 := $FF only (C $15)
;   5: FCLOSE (C $10)
;   6: FMAKE THREE.TXT (C $16)
;   7: WRSEQ, +24 := $41, +32 := $85 (C $15)
;   8: FCLOSE (C $10)
;   9: FOPEN TEST.TXT, +12 := $FF (the rest 0) (C $0F)
;   10: FOPEN TEST.TXT, +12 := 1 (C $0F)
;   11: FOPEN THREE.TXT (C $0F)
;   12: FSIZE THREE.TXT, +33 .. +36 := $FF (C $23)
;   13: FDEL MISSING.TXT (C $13)
;   14: FREN MISSING.TXT -> NEW.TXT (C $17)
;   15: FSIZE MISSING.TXT (C $23)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbfile3.asm --row disk   (run 1; --row cf3300: run 2)
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
                db      $16, 1, "TEST    TXT"
                db      $15, 5, 1, 12, $FF
                db      $10, 0
                db      $16, 1, "TWO     TXT"
                db      $15, 5, 1, 32, $FF
                db      $10, 0
                db      $16, 1, "THREE   TXT"
                db      $15, 5, 2, 24, $41, 32, $85
                db      $10, 0
                db      $0F, 6, "TEST    TXT", 1, 12, $FF
                db      $0F, 6, "TEST    TXT", 1, 12, $01
                db      $0F, 1, "THREE   TXT"
                db      $23, 6, "THREE   TXT", 4, 33, $FF, 34, $FF, 35, $FF, 36, $FF
                db      $13, 1, "MISSING TXT"
                db      $17, 2, "MISSING TXT", "NEW     TXT"
                db      $23, 1, "MISSING TXT"
                db      $FF

                ds      $8000 - $, $FF
