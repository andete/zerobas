; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXB.COM -- D-DISKCONTRACT gap 8 (2026-11-17): DRIVE B on a one-drive machine -- the
; phantom drive. Every BDOS gate used drive A only (BX9 / D1: SELDSK E = 0, CURDRV 0).
;
; The program clears the screen, selects drive B (SELDSK E = 1 -> the drive count in A),
; asks CURDRV, then SFIRSTs *.* on the default drive -- now B, the same physical drive:
; the disk system asks for drive B's diskette and waits for a key, which the harness
; types (--keys2). The program records each A, then reads its own screen back through the
; VDP's ports (the prompt's text and where it stands) and loops.
;
; CLEAN-ROOM: 100% own code; the published BDOS / work-area interface. Nothing of the
; reference read.
;
; Build: pasmo --bin bdosxb.asm bdosxb.com bdosxb.sym

                org     $0100

BDOS            equ     $0005
NAMBAS          equ     $F922

start:
                jr      begin                   ; $0102 = $5D: a distinctive arm signature
                db      $5D
begin:
                ld      e, 12                   ; clear the screen
                ld      c, $02
                call    BDOS
                ld      de, dta
                ld      c, $1A                  ; SETDTA
                call    BDOS
                ld      e, 1
                ld      c, $0E                  ; SELDSK B
                call    BDOS
                ld      (cells+1), a            ; the drive count
                ld      a, ($F247)
                ld      (cells+4), a            ; the current-drive cell CURDRV reads, after SELDSK
                ld      c, $19                  ; CURDRV
                call    BDOS
                ld      (cells+2), a
                ld      de, afcb
                ld      c, $11                  ; SFIRST *.* on B: the swap prompt, a key
                call    BDOS
                ld      (cells+3), a
                ; the screen into RAM through the VDP's own ports
                di
                ld      hl, (NAMBAS)
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ld      hl, screen
                ld      bc, 960
vread:
                in      a, ($98)
                ld      (hl), a
                inc     hl
                dec     bc
                ld      a, b
                or      c
                jr      nz, vread
                ei
                ld      a, $A5
                ld      (cells+0), a            ; the run finished
                jp      done

afcb:           db      0, "????????", "???"
                ds      37 - 12, 0

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
cells:          ds      8, $EE                  ; $A5, SELDSK's A, CURDRV's A, SFIRST's A, ($F247)
dta:            ds      36
screen:         ds      960
