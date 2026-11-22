; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XCHGW -- docs/bios/CHGET.md (2026-11-17): CHGET ($009F) WAITING on an empty key buffer, on the VG-8020 against
; zerobas. XCHG found zerobas's CHGET returning with interrupts disabled when entered so; does it then wait with them
; disabled -- so the key scan never runs and it never returns?
;   case 1: interrupts ON, KILBUF, CSRSW 1, cursor at (7, 5) on $5A garbage; 'Q' typed (@keys, at KEYREADY).
;   case 2: interrupts OFF, the same; 'R' typed at 15 emulated seconds (@type-at).
; Case 1 runs first, so a hang in case 2 leaves case 1's record (and STAGE) readable.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xchgw.asm --row nodisk
; The capture (CAP = C001): +0 STAGE (1 = case 1 entered CHGET, 2 = case 1 returned, 3 = case 2 entered, 4 = case 2
; returned), then per case 8 bytes from +1 / +9: A, F, LD A,I's flags (bit 2 = IFF2), GETPNT low, PUTPNT low, CSRSW,
; the cursor cell (row 5 column 7) after the call, and the cell right of it.
;
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells; VRAM through RDVRM / FILVRM.
;
; @cap C000
; @keys Q
; @type-at 15 R
; @timeout 40

RDVRM   equ     $004A
FILVRM  equ     $0056
CHGET   equ     $009F
INITXT  equ     $006C
KILBUF  equ     $0156
CNSDFG  equ     $F3DE
CSRY    equ     $F3DC
CSRX    equ     $F3DD
CSRSW   equ     $FCA9
PUTPNT  equ     $F3F8
GETPNT  equ     $F3FA

DONE    equ     $C000
CAP     equ     $C001
STAGE   equ     CAP
KEYREADY equ    $C100
ptr     equ     $EF00

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $FE
                ld      (hl), 0
                ldir
                xor     a
                ld      (CNSDFG), a
                call    INITXT
                ld      hl, CAP+1
                ld      (ptr), hl
                ; case 1: interrupts on
                call    setup
                ld      a, 1
                ld      (STAGE), a
                ld      (KEYREADY), a           ; the harness types 'Q' now
                ei
                call    CHGET
                call    record
                ld      a, 2
                ld      (STAGE), a
                ; case 2: interrupts off; 'R' arrives at 15 s
                call    setup
                ld      a, 3
                ld      (STAGE), a
                di
                call    CHGET
                call    record
                ld      a, 4
                ld      (STAGE), a
                ld      a, $A5
                ld      (DONE), a
                ei
halt_lp:
                jr      halt_lp

setup:
                call    KILBUF
                ld      a, 1
                ld      (CSRSW), a
                ld      hl, 0
                ld      bc, 960
                ld      a, $5A
                call    FILVRM
                ld      a, 7
                ld      (CSRX), a
                ld      a, 5
                ld      (CSRY), a
                ret

; record -- A and F as CHGET returned them, then the rest
record:
                push    af
                ld      a, i                    ; P/V := IFF2
                jp      pe, $+5                 ; off? read again: an interrupt accepted DURING `ld a,i` reads
                ld      a, i                    ; P/V 0 (the NMOS erratum, D-IFFREAD1)
                push    af
                di
                pop     bc                      ; c = LD A,I's flags
                pop     hl                      ; h = A, l = F
                ld      a, h
                call    emit
                ld      a, l
                call    emit
                ld      a, c
                call    emit
                ld      a, (GETPNT)
                call    emit
                ld      a, (PUTPNT)
                call    emit
                ld      a, (CSRSW)
                call    emit
                ld      hl, 166                 ; (5 - 1) x 40 + (7 - 1)
                call    RDVRM
                call    emit
                ld      hl, 167
                call    RDVRM
                call    emit
                ret

emit:
                push    hl
                ld      hl, (ptr)
                ld      (hl), a
                inc     hl
                ld      (ptr), hl
                pop     hl
                ret
