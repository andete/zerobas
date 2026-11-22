; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBABS1 -- WRABS ($30) through $F37D, round 1 (2026-11-22): absolute sector writes on drive A, read back with RDABS
; ($2F). DE the first sector, H the count, L the drive (0 = A). XBBLK11's frame and 66-byte record
; (probes/bios/spec/xbblk11.asm: A, F, the FCB -- untouched here --, the DTA's first 13, HL, the DTA at +383 .. +1024);
; the 1040-byte DTA fill is ($40 + the case + (i AND $FF) + (i >> 8) x 16) AND $FF, so no two sectors are alike.
; Cases:
;   0: SETDTA $A800 (C $1A)
;   1: WRABS sector 20, 1 sector (C $30)
;   2: RDABS sector 20, 1 sector (case 1's bytes?) (C $2F)
;   3: WRABS sector 21, 2 sectors (C $30)
;   4: RDABS sector 22, 1 sector (case 3's second 512?) (C $2F)
;   5: RDABS sector 21, 2 sectors (C $2F)
;   6: WRABS sector 1439, 1 sector (the last of a 720 KB disk) (C $30)
;   7: RDABS sector 1439, 1 sector (C $2F)
;   (WRABS of sector 1440 -- past the end -- was case 8 of a first run: neither reference came back from it in 60 s
;   -- scratchpad/XBABS1_run0_past.out (row D); zerobas answered A $08 -- so it is not a case here.)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbabs1.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap 9000
; @caplen 260
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
                ld      bc, $25F
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
                db      $30, 4
                dw      20, $0100
                db      $2F, 4
                dw      20, $0100
                db      $30, 4
                dw      21, $0200
                db      $2F, 4
                dw      22, $0100
                db      $2F, 4
                dw      21, $0200
                db      $30, 4
                dw      1439, $0100
                db      $2F, 4
                dw      1439, $0100
                db      $FF

                ds      $8000 - $, $FF
