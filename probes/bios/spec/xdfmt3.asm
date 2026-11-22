; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XDFMT3 -- DSKFMT ($401C) round 3 (2026-11-22), answering review pass 2 (scratchpad/DFMT_review2.md): choice $81 (a
; range test that masks the high bit would format $FC); a format with HL $8400 and BC $2000, and with HL $8010 (does
; HL -- and E -- follow HL or BC). XDFMT2's frame and record (probes/bios/spec/xdfmt2.asm).
; Cases (the choice, BC, HL):
;   0: choice $81, BC $2000, HL $8000
;   1: choice $01, BC $2000, HL $8400
;   2: choice $01, BC $2000, HL $8010
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xdfmt3.asm --row cf3300   (the CF-3300's interface:
;      zerobas's disk target; run 1, --row both, showed the VG-8020 + NMS 1200 offers other choices)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 160
; @timeout 400

CALSLT  equ     $001C
PHYDIO  equ     $0144
cbc     equ     $A208
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
                ld      bc, $15F
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
                ld      hl, choices
                ld      (tptr), hl
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $EE                 ; the table's end marker ($FF is a case)
                jp      z, fin
                ld      (cb), a
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (cbc), de
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      (chl), de
                ld      (tptr), hl
                ld      a, (DRVSLT)
                or      a
                jr      nz, go
                ld      hl, (ptr)           ; no disk interface (the NODISK row): an empty record
                ld      de, 38
                add     hl, de
                ld      (ptr), hl
                jr      nxt
go:
                ld      iyh, a
                ld      ix, $401C
                ld      a, (cb)
                ld      d, 0
                ld      e, 0
                ld      hl, (chl)
                ld      bc, (cbc)
                di
                call    CALSLT
                ld      (rsave), hl         ; the record's registers
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
                ld      (ptr), hl
                pop     af
                ; read sectors 0 and 1 back
                ld      a, 0
                ld      b, 2
                ld      c, $F9
                ld      de, 0
                ld      hl, $A400
                or      a                   ; carry clear: read
                di
                call    PHYDIO
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
                ld      hl, $A400 + 11      ; the BPB fields
                ld      bc, 19
                ldir
                ld      hl, $A400 + 512     ; the FAT's first 4 bytes
                ld      bc, 4
                ldir
                xor     a                   ; pad the record to 38 with $00
                ld      (de), a
                inc     de
                ld      (de), a
                inc     de
                ld      (de), a
                inc     de
                ld      (de), a
                inc     de
                ld      (ptr), de
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

choices:
                db      $81
                dw      $2000, $8000
                db      $01
                dw      $2000, $8400
                db      $01
                dw      $2000, $8010
                db      $EE

                ds      $8000 - $, $FF
