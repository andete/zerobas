; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBBLK2 -- the BDOS's block functions through $F37D, round 2 (2026-11-22), answering review pass 1 (scratchpad/
; BBLK_review1.md): RDBLK straight after FOPEN (the record size FOPEN leaves); RDBLK at the end (nothing to read); the
; DTA past a partial record; WRBLK with HL 0; WRZER with record size 1 on the OPENED file; a 4-record read-back; RDABS's
; whole sector. XBBLK1's frame and modes (probes/bios/spec/xbblk1.asm) with two changes: the DTA fill covers 512 bytes
; (byte i = $40 + the case + i, AND $FF), so every transfer reads and writes defined bytes; and the record is 58 bytes:
; XBBLK1's 54, then the DTA's bytes +72, +128, +511 and +512.
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: FMAKE B.TXT (C $16)
;   2: WRBLK 200 x 1 (RS 1, RR 0) (C $26)
;   3: FCLOSE (C $10)
;   4: FOPEN B.TXT (C $0F)
;   5: RDBLK HL 1 right after FOPEN (no pokes) (C $27)
;   6: RDBLK 5 x 1 from RR 200 (at the end) (C $27)
;   7: RDBLK 1 x 128 from RR 1 (the partial record) (C $27)
;   8: WRBLK HL 0, RS 128, RR 1 (C $26)
;   9: FCLOSE (C $10)
;   10: FOPEN B.TXT (C $0F)
;   11: WRZER, RS 1, RR 3, HL 1 (opened FCB) (C $28)
;   12: FCLOSE (C $10)
;   13: FOPEN B.TXT (C $0F)
;   14: RDBLK 4 x 128 from RR 0 (C $27)
;   15: RDABS sector 0, 1 sector, drive A (C $2F)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbblk2.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 3B0
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
                cp      7
                jp      z, pokes            ; 7: pokes, then HL from the table
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
                ld      a, (cmode)
                cp      7
                jr      nz, fset
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
fset:
                ld      (tptr), hl
                ld      a, (cno)            ; the DTA: 128 x ($40 + the case number)
                add     a, $40
                ld      hl, DTAB            ; 512 bytes: $40 + the case + i
                ld      bc, 512
fd:
                ld      (hl), a
                inc     a
                inc     hl
                dec     bc
                ex      af, af'
                ld      a, b
                or      c
                jr      z, fde
                ex      af, af'
                jr      fd
fde:
                ld      hl, cno
                inc     (hl)
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 58
                add     hl, de
                ld      (ptr), hl
                jp      nxt
go:
                ld      a, (cc)
                ld      c, a
                ld      de, FCB
                ld      hl, (chl)           ; HL from the table (modes 4 and 7)
                ld      a, (cmode)
                cp      4
                jr      nz, notdta
                ld      de, (cde)
notdta:
                di
                call    BDOS
                di
                ld      (rsave), hl         ; HL after the call, for the record's end
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
                ld      a, (rsave+1)
                ld      (de), a
                inc     de
                ld      a, (rsave)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 72)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 128)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 511)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 512)
                ld      (de), a
                inc     de
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
                db      $16, 1, "B       TXT"
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $00, 35, $00, 36, $00
                dw      200
                db      $10, 0
                db      $0F, 1, "B       TXT"
                db      $27, 7, 1, 33, $00
                dw      1
                db      $27, 7, 5, 14, $01, 15, $00, 33, $C8, 34, $00, 35, $00
                dw      5
                db      $27, 7, 5, 14, $80, 15, $00, 33, $01, 34, $00, 35, $00
                dw      1
                db      $26, 7, 5, 14, $80, 15, $00, 33, $01, 34, $00, 35, $00
                dw      0
                db      $10, 0
                db      $0F, 1, "B       TXT"
                db      $28, 7, 5, 14, $01, 15, $00, 33, $03, 34, $00, 35, $00
                dw      1
                db      $10, 0
                db      $0F, 1, "B       TXT"
                db      $27, 7, 5, 14, $80, 15, $00, 33, $00, 34, $00, 35, $00
                dw      4
                db      $2F, 4
                dw      $0000, $0100
                db      $FF

                ds      $8000 - $, $FF
