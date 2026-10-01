; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; dosdate.asm -- D-CLOSESTAMP and D-DOSDATE (TODO), measured on both machines.
; Joost 2026-10-01 "Stamp as 3300": files are dated as the CF-3300 dates them.
; Two questions that ruling left open:
;   (1) D-CLOSESTAMP: FOPEN FIXD.TXT (dated 0 on the disk), WRRND record 0 --
;       INSIDE its size, so nothing grows -- FCLOSE. Is the entry re-dated?
;   (2) D-DOSDATE: GDATE, SDATE 1999-12-31, GDATE again (registers kept), then
;       FMAKE NEWD.TXT, WRBLK 16 B, FCLOSE. Which date does NEWD.TXT carry?
; Results: PHASE ($C000) 1 running, 2 done; RESULT ($C010..) the register record
; below; the disk image for the two entries. Clean-room: published BDOS FCB
; calls only (MSX2 TH / map.grauw.nl), our own data.

BDOS    equ     $0005
PHASE   equ     $C000
RESULT  equ     $C010   ; +0 GDATE#1 HL,DE,A (5 B) +5 SDATE A (1 B) +6 GDATE#2 HL,DE,A (5 B)
        org     $0100
        ld      a, 1
        ld      (PHASE), a
        ; --- (1) D-CLOSESTAMP --------------------------------------------------
        ld      de, dta
        ld      c, $1A                  ; SETDTA
        call    BDOS
        ld      hl, dta
        ld      b, 128
fillw:  ld      (hl), 'W'
        inc     hl
        djnz    fillw
        ld      de, fcbd
        ld      c, $0F                  ; FOPEN FIXD.TXT
        call    BDOS
        ld      hl, 128
        ld      (fcbd + 14), hl         ; RS = 128
        ld      hl, 0
        ld      (fcbd + 33), hl         ; record 0, inside the 256-byte file
        ld      (fcbd + 35), hl
        ld      de, fcbd
        ld      c, $22                  ; WRRND
        push    ix
        call    BDOS
        pop     ix
        ld      de, fcbd
        ld      c, $10                  ; FCLOSE
        call    BDOS
        ; --- (2) D-DOSDATE -----------------------------------------------------
        ld      c, $2A                  ; GDATE
        call    BDOS
        ld      (RESULT + 0), hl
        ld      (RESULT + 2), de
        ld      (RESULT + 4), a
        ld      hl, 1999
        ld      d, 12
        ld      e, 31
        ld      c, $2B                  ; SDATE 1999-12-31
        call    BDOS
        ld      (RESULT + 5), a
        ld      c, $2A                  ; GDATE again
        call    BDOS
        ld      (RESULT + 6), hl
        ld      (RESULT + 8), de
        ld      (RESULT + 10), a
        ld      de, fcbn
        ld      c, $16                  ; FMAKE NEWD.TXT
        call    BDOS
        ld      hl, 1
        ld      (fcbn + 14), hl         ; RS = 1
        ld      hl, 0
        ld      (fcbn + 33), hl
        ld      (fcbn + 35), hl
        ld      de, fcbn
        ld      hl, 16
        ld      c, $26                  ; WRBLK 16 bytes of 'W'
        push    ix
        call    BDOS
        pop     ix
        ld      de, fcbn
        ld      c, $10                  ; FCLOSE
        call    BDOS
        ld      a, 2
        ld      (PHASE), a
        ld      c, $00                  ; terminate
        call    BDOS
        ret

fcbd:   db      0
        db      "FIXD    TXT"
        ds      40 - 12, 0
fcbn:   db      0
        db      "NEWD    TXT"
        ds      40 - 12, 0
dta:    ds      128
