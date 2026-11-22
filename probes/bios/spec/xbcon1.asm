; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XBCON1 -- the BDOS's console INPUT functions through $F37D, round 1 (2026-11-22): CONST ($0B), CONIN ($01),
; DIRIO ($06) with E $FF, $07, $08 and BUFIN ($0A). Run from H.STKE (the disk ROM up, BASIC not started), as the
; XBBLK probes. Before the first case the screen is cleared (CLS). Before EACH case the probe empties the BIOS key
; buffer (GETPNT := PUTPNT := KEYBUF, work-area RAM) and puts that case's keys in it (KEYBUF, PUTPNT advanced), so no
; call ever waits. The 24-byte record: A, F, H, L, CSRY, CSRX, PUTPNT's and GETPNT's low bytes, then BUFIN's
; buffer at $A700 (12 bytes: max 10 going in, the rest $EE) -- then the screen's first row at
; columns 2 .. 5 of the current name table (NAMBAS + 2 .., read with RDVRM: the CF-3300 starts in another mode).
; Cases:
;   0: CONST, no key (C $0B)
;   1: CONST, "X" waiting (C $0B)
;   2: CONIN, "A" (C $01)
;   3: DIRIO E $FF, no key (C $06)
;   4: DIRIO E $FF, "B" (C $06)
;   5: $07, "C" (C $07)
;   6: $08, "D" (C $08)
;   7: CONIN, Return ($0D) (C $01)
;   8: CONIN, CTRL+A ($01) (C $01)
;   9: BUFIN, DE $A700, "HI" + Return (C $0A)
;   10: CONIN, "E" (after BUFIN) (C $01)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbcon1.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 110
; @timeout 60

CALSLT  equ     $001C
CLS     equ     $00C3
RDVRM   equ     $004A
NAMBAS  equ     $F922
BDOS    equ     $F37D
DRVSLT  equ     $FB22
EXPTBL  equ     $FCC1
H_STKE  equ     $FEDA
KEYBUF  equ     $FBF0
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA
CSRY    equ     $F3DC
CSRX    equ     $F3DD
BUF     equ     $A700

DONE    equ     $A000
CAP     equ     $A001
ptr     equ     $A400
tptr    equ     $A402
rsave   equ     $A410
cno     equ     $A4F1

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $10E
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
                ld      (cno), a
                ld      a, (DRVSLT)
                or      a
                jp      z, fin              ; no disk ROM: nothing to call
                xor     a
                call    CLS
nxt:
                ld      hl, (tptr)
                ld      a, (hl)
                cp      $FF
                jp      z, fin
                ld      c, a                ; C
                inc     hl
                ld      e, (hl)             ; E
                inc     hl
                ld      b, (hl)             ; the key count
                inc     hl
                push    bc
                push    de
                ld      de, KEYBUF          ; empty the key buffer, then put this case's keys in it
                ld      (GETPNT), de
                ld      a, b
                or      a
                jr      z, nokeys
kl:
                ld      a, (hl)
                ld      (de), a
                inc     hl
                inc     de
                djnz    kl
nokeys:
                ld      (PUTPNT), de
                ld      (tptr), hl
                ld      hl, BUF             ; BUFIN's buffer: max 10, the rest $EE
                ld      (hl), 10
                inc     hl
                ld      b, 11
bf:
                ld      (hl), $EE
                inc     hl
                djnz    bf
                pop     de
                pop     bc
                ld      a, c
                cp      $0A
                jr      nz, notbuf
                ld      de, BUF
notbuf:
                call    BDOS
                di
                ld      (rsave), hl
                push    af
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ex      (sp), hl            ; HL = AF
                ld      a, l
                ex      (sp), hl
                ld      (hl), a             ; F
                inc     hl
                ld      a, (rsave+1)
                ld      (hl), a
                inc     hl
                ld      a, (rsave)
                ld      (hl), a
                inc     hl
                ld      a, (CSRY)
                ld      (hl), a
                inc     hl
                ld      a, (CSRX)
                ld      (hl), a
                inc     hl
                ld      a, (PUTPNT)
                ld      (hl), a
                inc     hl
                ld      a, (GETPNT)
                ld      (hl), a
                inc     hl
                ex      de, hl
                ld      hl, BUF
                ld      bc, 12
                ldir
                ld      hl, (NAMBAS)
                inc     hl
                inc     hl
                ld      b, 4
rv:
                push    bc
                push    de
                call    RDVRM
                pop     de
                pop     bc
                ld      (de), a
                inc     de
                inc     hl
                djnz    rv
                ld      (ptr), de
                pop     af
                jp      nxt
fin:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

cases:
                db      $0B, 0, 0
                db      $0B, 0, 1, "X"
                db      $01, 0, 1, "A"
                db      $06, $FF, 0
                db      $06, $FF, 1, "B"
                db      $07, 0, 1, "C"
                db      $08, 0, 1, "D"
                db      $01, 0, 1, $0D
                db      $01, 0, 1, $01
                db      $0A, 0, 3, "HI", $0D
                db      $01, 0, 1, "E"
                db      $FF

                ds      $8000 - $, $FF
