; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; XTAP5 -- the tape region's BIOS calls round 5 (2026-11-19): every tape call entered with the CARRY SET (does it
; clear it, or keep it?). STMOTR at port C $B0 / $F0 / $48; then the round trip with interrupts off: TAPOON (A $FF,
; F $FF, port C $4A: the low nibble := 7, or OR 7?), TAPOUT x 4 (SCF before each), TAPOOF -- the harness rewinds and
; plays the recording (@tape) -- TAPION (F $FF, port C $F8: := $47, or bits 6-7 kept?), TAPIN x 4 (SCF before each),
; TAPIOF. The TAPOUT / TAPIN calls in tight loops recording A and F (2 bytes each), then port C once.
; Each other step: port C ($AA) preset as listed (bit 4 the motor relay, 0 = running), BC $1357, DE $9BDF (TAPOON
; $1234, TAPION $4321), HL $2468, A and F and the interrupt state as listed, the call, then a 10-byte record: A, F,
; B, C, D, E, H, L, the interrupt state after (1 on, read twice), port C after.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtap5.asm --row both
; CLEAN-ROOM: 100% own code; published BIOS entries, the PPI's port C.
;
; @tape
; @timeout 120

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
                ld      a, $B0
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
                ; STMOTR ($00F3)
                ld      a, $F0
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
                ld      a, $48
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
                ; TAPOON ($00EA)
                ld      a, $4A
                out     ($AA), a
                ld      bc, $FFFF
                push    bc
                ld      bc, $1357
                ld      de, $1234
                ld      hl, $2468
                pop     af
                di
                call    $00EA
                call    rec
                ; TAPOUT x 4 in a tight loop (the reference's reader needs the bytes back to back): A, F after
                ; each, then port C once
                ld      hl, odata
                ld      b, 4
ol:
                ld      a, (hl)
                push    hl
                push    bc
                scf
                call    $00ED
                push    af
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                pop     de
                ld      (hl), e
                inc     hl
                ld      (ptr), hl
                pop     bc
                pop     hl
                inc     hl
                djnz    ol
                call    pcrec
                ; TAPOOF ($00F0)
                ld      bc, $A700
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00F0
                call    rec
                ld      a, 1                    ; the recording is written: rewind and play it
                ld      (TREADY), a
wack:
                ld      a, (TACK)
                or      a
                jr      z, wack
                ; TAPION ($00E1)
                ld      a, $F8
                out     ($AA), a
                ld      bc, $A7FF
                push    bc
                ld      bc, $1357
                ld      de, $4321
                ld      hl, $2468
                pop     af
                di
                call    $00E1
                call    rec
                ; TAPIN x 4 in a tight loop: A, F after each, then port C once
                ld      b, 4
il:
                push    bc
                scf
                call    $00E4
                push    af
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                pop     de
                ld      (hl), e
                inc     hl
                ld      (ptr), hl
                pop     bc
                djnz    il
                call    pcrec
                ; TAPIOF ($00E7)
                ld      bc, $A700
                push    bc
                ld      bc, $1357
                ld      de, $9BDF
                ld      hl, $2468
                pop     af
                di
                call    $00E7
                call    rec
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

odata:          db      $00, $55, $AA, $FF

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
