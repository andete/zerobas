; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XBCON3 -- the BDOS's console INPUT functions through $F37D, round 3 (2026-11-22), answering review pass 2 (scratchpad/
; BCON_review2.md): CONST with a key held and none waiting; $08 and DIRIO with a key held AND one waiting; console
; output (CONOUT) with the hold FULL and a key waiting; BUFIN started at column 2 (does it end at column 1, or where it
; started?). XBCON1's frame and 24-byte record (probes/bios/spec/xbcon1.asm); the hold carries over between cases.
; Cases:
;   0: CONST, "X" (C $0B)
;   1: CONST, no key (one held) (C $0B)
;   2: $08, "D" (one held) (C $08)
;   3: CONST, "X" (C $0B)
;   4: DIRIO E $FF, "B" (one held) (C $06)
;   5: CONST, "X" (C $0B)
;   6: CONOUT E "Q", "K" waiting (the hold full) (C $02)
;   7: DIRIO E $FF, no key (C $06)
;   8: DIRIO E $FF, no key (C $06)
;   9: CONIN, Return (C $01)
;   10: CONIN, "E" (C $01)
;   11: BUFIN, DE $A700, "HI" + Return, started at column 2 (C $0A)
;   12: CONIN, "F" (C $01)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbcon3.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 140
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
                ld      bc, $13E
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
                db      $0B, 0, 1, "X"
                db      $0B, 0, 0
                db      $08, 0, 1, "D"
                db      $0B, 0, 1, "X"
                db      $06, $FF, 1, "B"
                db      $0B, 0, 1, "X"
                db      $02, "Q", 1, "K"
                db      $06, $FF, 0
                db      $06, $FF, 0
                db      $01, 0, 1, $0D
                db      $01, 0, 1, "E"
                db      $0A, 0, 3, "HI", $0D
                db      $01, 0, 1, "F"
                db      $FF

                ds      $8000 - $, $FF
