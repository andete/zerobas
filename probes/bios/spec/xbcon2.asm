; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XBCON2 -- the BDOS's console INPUT functions through $F37D, round 2 (2026-11-22), answering review pass 1 (scratchpad/
; BCON_review1.md): DIRIO E $FF with no key AND no hold; the hold with CONST twice (one place, overwritten, or a
; queue?); the held key for $07, $08 and BUFIN; CONIN with TWO keys waiting (does its echo take the second?); CONST
; with two keys waiting (GETPNT to PUTPNT, or by one?); CONIN with TAB, BS, CTRL+B and LF; CONOUT with a key waiting
; (does any output take it into the hold?). XBCON1's frame and 24-byte record (probes/bios/spec/xbcon1.asm): the key
; buffer is emptied and the case's keys put in it before EACH case -- the DOS's hold is NOT touched, it carries over.
; Cases:
;   0: DIRIO E $FF, no key, nothing held (C $06)
;   1: CONST, "X" (C $0B)
;   2: CONST, "Y" (the hold full) (C $0B)
;   3: $07, "C" (C $07)
;   4: $08, "D" (C $08)
;   5: CONST, no key (C $0B)
;   6: CONST, "Z" (C $0B)
;   7: BUFIN, DE $A700, "HI" + Return (a key held) (C $0A)
;   8: CONIN, "EF" (C $01)
;   9: DIRIO E $FF, no key (C $06)
;   10: CONST, "XY" (C $0B)
;   11: DIRIO E $FF, no key (C $06)
;   12: CONIN, TAB ($09) (C $01)
;   13: CONIN, BS ($08) (C $01)
;   14: CONIN, CTRL+B ($02) (C $01)
;   15: CONIN, LF ($0A) (C $01)
;   16: DIRIO E $FF, no key (C $06)
;   17: CONOUT E "Q", "K" waiting (C $02)
;   18: DIRIO E $FF, no key (C $06)
;   19: DIRIO E $FF, no key (C $06)
;
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xbcon2.asm --row disk   (run 1; --row cf3300: run 2)
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @disk empty
; @type-at 20 \r
; @cap A000
; @caplen 1F0
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
                ld      bc, $1EE
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
                db      $06, $FF, 0
                db      $0B, 0, 1, "X"
                db      $0B, 0, 1, "Y"
                db      $07, 0, 1, "C"
                db      $08, 0, 1, "D"
                db      $0B, 0, 0
                db      $0B, 0, 1, "Z"
                db      $0A, 0, 3, "HI", $0D
                db      $01, 0, 2, "EF"
                db      $06, $FF, 0
                db      $0B, 0, 2, "XY"
                db      $06, $FF, 0
                db      $01, 0, 1, $09
                db      $01, 0, 1, $08
                db      $01, 0, 1, $02
                db      $01, 0, 1, $0A
                db      $06, $FF, 0
                db      $02, "Q", 1, "K"
                db      $06, $FF, 0
                db      $06, $FF, 0
                db      $FF

                ds      $8000 - $, $FF
