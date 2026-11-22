; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTAP3 -- the tape region's BIOS calls round 3 without a tape (2026-11-19): STMOTR with A $80 / $FE / $81 from a running
; motor (toggle or start?), A $02 / $03 / $28 from a stopped one, port C's low nibble set ($5A, $4A, $45); TAPOON with
; interrupts off, the motor already running (port C $40, $45), A $00 (short leader) and $FF, each followed by TAPOOF.
; Each step: port C ($AA) preset as listed (bit 4 the motor relay, 0 = running), BC $1357, DE $9BDF (TAPOON $1234 /
; $5678), HL $2468, A and F and the interrupt state as listed, the call, then a 10-byte record: A, F, B, C, D, E, H, L,
; the interrupt state after (1 on, read twice), port C after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtap3.asm --row both
; CLEAN-ROOM: 100% own code; published BIOS entries, the PPI's port C.

DONE    equ     $E000
CAP     equ     $E001
TREADY  equ     $E101
TACK    equ     $E102
ptr     equ     $E200
rsave   equ     $E210

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                xor     a
                ld      (TACK), a
                ld      (TREADY), a
                ld      hl, CAP
                ld      (ptr), hl

                ; STMOTR ($00F3)
                ld      a, $40
                out     ($AA), a
                ld      bc, $8000
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $40
                out     ($AA), a
                ld      bc, $FE00
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $40
                out     ($AA), a
                ld      bc, $8100
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $50
                out     ($AA), a
                ld      bc, $0200
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $50
                out     ($AA), a
                ld      bc, $0300
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $50
                out     ($AA), a
                ld      bc, $2800
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $5A
                out     ($AA), a
                ld      bc, $0100
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $4A
                out     ($AA), a
                ld      bc, $0000
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; STMOTR ($00F3)
                ld      a, $45
                out     ($AA), a
                ld      bc, $FF00
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F3
                call    rec
                ; TAPOON ($00EA)
                ld      a, $40
                out     ($AA), a
                ld      bc, $0000
                push    bc
                ld      bc, $1357
                ld      de, $1234
                ld      hl, $2468
                pop     af
                di
                call    $00EA
                call    rec
                ; TAPOOF ($00F0)
                ld      a, $40
                out     ($AA), a
                ld      bc, $A700
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F0
                call    rec
                ; TAPOON ($00EA)
                ld      a, $45
                out     ($AA), a
                ld      bc, $FF00
                push    bc
                ld      bc, $1357
                ld      de, $5678
                ld      hl, $2468
                pop     af
                di
                call    $00EA
                call    rec
                ; TAPOOF ($00F0)
                ld      a, $40
                out     ($AA), a
                ld      bc, $A700
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F0
                call    rec
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

odata:          db      $00

; rec -- the 10-byte record: A F B C D E H L, the interrupt state, port C
rec:
                ld      (rsave), hl
                push    af
                push    af
                ld      hl, (ptr)
                pop     af
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
                ld      a, i                    ; P/V := IFF2, read twice
                jp      pe, ion
                ld      a, i
ion:
                ld      a, 0
                jp      po, ioff
                ld      a, 1
ioff:
                ld      (hl), a
                inc     hl
                in      a, ($AA)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     af
                ld      hl, (rsave)
                ret

; pcrec -- port C, one byte
pcrec:
                in      a, ($AA)
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                ret
