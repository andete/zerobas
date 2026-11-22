; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBBLK10 -- the BDOS's block functions through $F37D, round 10 (2026-11-22), answering review pass 8 (scratchpad/
; BBLK_review8.md): WRZER's zero fill into NEWLY allocated clusters whose disk bytes are not zero (a deleted file's:
; zeros, or the disk's?); +28 / +30 after a growing WRZER at a cluster boundary below 64 KB, with and without a gap
; (the cluster holding RR, or the one before?). XBBLK9's frame (probes/bios/spec/xbblk9.asm) and 66-byte record
; unchanged; the 1040-byte DTA fill differs in every sector.
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: FMAKE Q.TXT (C $16)
;   2: WRBLK 1024 x 1 at RR 0 (C $26)
;   3: WRBLK 1024 x 1 at RR 1024 (C $26)
;   4: WRBLK 1024 x 1 at RR 2048 (C $26)
;   5: WRBLK 1024 x 1 at RR 3072 (Q.TXT: 4096 bytes, clusters 2 .. 5) (C $26)
;   6: FCLOSE (C $10)
;   7: FDEL Q.TXT (C $13)
;   8: FMAKE R.TXT (C $16)
;   9: WRZER RS 128, RR 31 (32 records over Q's freed clusters) (C $28)
;   10: FCLOSE (C $10)
;   11: FOPEN R.TXT (C $0F)
;   12: RDBLK 8 x 128 from RR 0 (C $27)
;   13: RDBLK 8 x 128 from RR 16 (C $27)
;   14: FMAKE S.TXT (C $16)
;   15: WRZER RS 128, RR 8 on the empty file (a gap; record 8 starts cluster index 1) (C $28)
;   16: FMAKE T.TXT (C $16)
;   17: WRZER RS 128, RR 7 (8 records: one full cluster) (C $28)
;   18: WRZER RS 128, RR 8 (no gap; record 8 starts cluster index 1) (C $28)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbblk10.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap 9000
; @caplen 4F0
; @timeout 300

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

DONE    equ     $9000           ; the capture (below HIMEM: the disk ROM's work area is live once H.STKE runs)
CAP     equ     $9001
FCB2    equ     $A640
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
                ld      bc, $4EF
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
                cp      8
                jp      z, m8               ; 8: FSIZE through FCB2, reset from the template
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
m8:
                push    hl
                ld      hl, fcb2t
                ld      de, FCB2
                ld      bc, 37
                ldir
                pop     hl
fset:
                ld      (tptr), hl
                ld      a, (cno)            ; the DTA: 1040 bytes, ($40 + the case + (i AND $FF) + (i >> 8) x 16)
                add     a, $40
                ld      (cb), a
                ld      hl, DTAB
                ld      de, 0
fd:
                ld      a, d
                add     a, a
                add     a, a
                add     a, a
                add     a, a
                add     a, e
                push    hl
                ld      hl, cb
                add     a, (hl)
                pop     hl
                ld      (hl), a
                inc     hl
                inc     de
                ld      a, d
                cp      4
                jr      nz, fd
                ld      a, e
                cp      $10
                jr      nz, fd
fde:
                ld      hl, cno
                inc     (hl)
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)
                ld      de, 66
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
                cp      8
                jr      nz, notf2
                ld      de, FCB2
notf2:
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
                ld      a, (cmode)
                ld      hl, FCB
                cp      8
                jr      nz, capf
                ld      hl, FCB2
capf:
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
                ld      a, (DTAB + 383)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 384)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 476)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 511)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 512)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 639)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 640)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 767)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 768)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 776)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 1023)
                ld      (de), a
                inc     de
                ld      a, (DTAB + 1024)
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

fcb2t:
                db      0, "F       TXT", 0, 0, $80, $FF
                ds      21, 0
cases:
                db      $1A, 4
                dw      $A800, $0000
                db      $16, 1, "Q       TXT"
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $00, 35, $00, 36, $00
                dw      1024
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $04, 35, $00, 36, $00
                dw      1024
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $08, 35, $00, 36, $00
                dw      1024
                db      $26, 7, 6, 14, $01, 15, $00, 33, $00, 34, $0C, 35, $00, 36, $00
                dw      1024
                db      $10, 0
                db      $13, 1, "Q       TXT"
                db      $16, 1, "R       TXT"
                db      $28, 7, 6, 14, $80, 15, $00, 33, $1F, 34, $00, 35, $00, 36, $00
                dw      1
                db      $10, 0
                db      $0F, 1, "R       TXT"
                db      $27, 7, 5, 14, $80, 15, $00, 33, $00, 34, $00, 35, $00
                dw      8
                db      $27, 7, 5, 14, $80, 15, $00, 33, $10, 34, $00, 35, $00
                dw      8
                db      $16, 1, "S       TXT"
                db      $28, 7, 6, 14, $80, 15, $00, 33, $08, 34, $00, 35, $00, 36, $00
                dw      1
                db      $16, 1, "T       TXT"
                db      $28, 7, 6, 14, $80, 15, $00, 33, $07, 34, $00, 35, $00, 36, $00
                dw      1
                db      $28, 7, 5, 14, $80, 15, $00, 33, $08, 34, $00, 35, $00
                dw      1
                db      $FF

                ds      $8000 - $, $FF
