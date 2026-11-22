; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; BDOSXK.COM -- D-DISKCONTRACT gap 5 (2026-11-17): what CONIN's and BUFIN's ECHO put on the
; screen. BX2 / D1 / bufinx compare their returned registers and buffer, never the screen.
;
; Typed by the harness (--keys2 `xHelz\blo\r`): CONIN ($01) takes the 'x' and echoes it;
; then BUFIN ($0A) reads "Helz", a BACKSPACE, "lo", RETURN -- line editing: the buffer
; ends "Hello". The program then copies the screen (the name table, read through the VDP
; ports by our own code, as BDOSXC), and loops. Captured: a flag, CONIN's A, the BUFIN
; buffer, the screen.
;
; CLEAN-ROOM: 100% own code; the published BDOS / work-area interface. Nothing of the
; reference read.
;
; Build: pasmo --bin bdosxk.asm bdosxk.com bdosxk.sym

                org     $0100

BDOS            equ     $0005
NAMBAS          equ     $F922

start:
                jr      begin                   ; $0102 = $5B: a distinctive arm signature
                db      $5B
begin:
                ld      e, 12                   ; clear the screen
                call    conout
                ld      e, 13
                call    conout
                ld      e, 10
                call    conout
                ld      c, $01                  ; CONIN: the 'x', echoed
                call    BDOS
                ld      (cells+1), a
                ld      e, 13
                call    conout
                ld      e, 10
                call    conout
                ld      de, buf                 ; BUFIN: "Helz" BS "lo" CR
                ld      c, $0A
                call    BDOS
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

conout:
                ld      c, $02
                jp      BDOS

                ds      $0330 - $, $00
done:
                jr      done                    ; the capture anchor, pinned at $0330
                ds      $0340 - $, $00
cells:          ds      2                       ; $A5 when finished, CONIN's A
buf:            db      20                      ; BUFIN: max length, count, the bytes
                ds      21
screen:         ds      960
