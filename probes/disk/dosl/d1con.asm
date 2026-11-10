; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D1CON.COM -- D-DOSLADDER rung D1 (TODO.md): the console a "hello / echo" program
; uses. STROUT and CONOUT to the screen; the version, the current drive, the login
; vector; CONST and DIRIO-input with no key waiting; GETDATE. Then it WAITS on CONST
; for the capture's typed keys ("HELLO\rX", --keys at 40 s, so they land in this
; program and not in COMMAND.COM): CONST with a key, BUFIN (the line), CONIN (the X
; typed past the Enter), CONST once drained, SELDSK's drive count.
; Captured, the contract only: each call's result register(s) and BUFIN's buffer.
; Self-loop at `done` -- the capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions.
;
; Build: probes/disk/build_dosl_disk.py --prog d1con --keys 'HELLO\rX'

                org     $0100

BDOS            equ     $0005

ARMSIG          equ     $D1
                jr      start
                db      $00                     ; $0102: the arm signature, written at run
                                                ; time (D7's lesson: never a static byte)
start:
                ld      a, ARMSIG
                ld      ($0102), a
armpt:                                          ; the capture arms HERE (--arm-addr)
                ld      de, msg
                ld      c, $09                  ; STROUT
                call    BDOS
                ld      e, '!'
                ld      c, $02                  ; CONOUT
                call    BDOS
                ld      c, $0C                  ; version
                call    BDOS
                ld      (cap+0), hl
                ld      c, $19                  ; CURDRV
                call    BDOS
                ld      (cap+2), a
                ld      c, $18                  ; LOGIN vector
                call    BDOS
                ld      (cap+3), hl
                ld      c, $0B                  ; CONST, nothing typed yet
                call    BDOS
                ld      (cap+5), a
                ld      e, $FF
                ld      c, $06                  ; DIRIO input, nothing typed yet
                call    BDOS
                ld      (cap+6), a
                ld      c, $2A                  ; GETDATE
                call    BDOS
                ld      (cap+7), hl             ; the year
                ld      (cap+9), de             ; D = the month, E = the day
                ld      (cap+11), a             ; the day of the week
wait:
                ld      c, $0B                  ; CONST until the typed keys arrive
                call    BDOS
                or      a
                jr      z, wait
                ld      (cap+12), a             ; CONST with a key waiting
                ld      de, ibuf
                ld      c, $0A                  ; BUFIN
                call    BDOS
                ld      c, $01                  ; CONIN: the X typed past the Enter
                call    BDOS
                ld      (cap+13), a
                ld      c, $0B                  ; CONST, drained
                call    BDOS
                ld      (cap+14), a
                ld      e, 0
                ld      c, $0E                  ; SELDSK A: -> the number of drives
                call    BDOS
                ld      (cap+15), a
                ld      hl, ibuf+1
                ld      de, cap+16
                ld      bc, 8
                ldir                            ; BUFIN's count and its first 7 bytes
done:
                jr      done

msg:            db      "D1 CONSOLE$"
ibuf:           db      20                      ; BUFIN: the maximum, then count + line
                ds      22, $EE

; ---------------------------------------------------------------------------
; captured block $0400-$041F
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      32, $00
cap_end:
