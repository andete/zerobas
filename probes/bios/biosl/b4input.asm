; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; B4INPUT -- D-BIOSLADDER rung B4 (TODO.md): the input entries a game polls.
; A 16 KB "AB" cartridge; INIT runs it.
;   1. idle: GTSTCK 0 / 1 / 2, GTTRIG 0..4, SNSMAT rows 0..10, CHSNS (CAP+0..);
;   2. KILBUF, KEYREADY := 1 -- the harness then holds the cursor-RIGHT key and
;      SPACE down (a raw key-matrix press, row 8, mask $81) for 0.3 s; the program
;      polls for up to 100 frames and, on the first frame row 8 shows the press,
;      reads GTSTCK 0, GTTRIG 0 and SNSMAT 8 (CAP+$20..);
;   3. 30 frames after the release: GTSTCK 0, GTTRIG 0, SNSMAT 8, CHSNS and what
;      CHGET then returns if a key is waiting (CAP+$28..);
;   4. KILBUF: CHSNS after it (CAP+$2E).
; GTPAD / GTPDL are the PAD rung's (no device here). Joysticks 1 / 2 read idle: no
; device is plugged on either machine.
; CLEAN-ROOM: 100% own code; only published BIOS entries and work-area cells.
;
; @matrix 8 81
; @timeout 40

CHSNS   equ     $009C
CHGET   equ     $009F
GTSTCK  equ     $00D5
GTTRIG  equ     $00D8
SNSMAT  equ     $0141
KILBUF  equ     $0156

DONE    equ     $E000
CAP     equ     $E001
KEYRDY  equ     $E100

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
                ei
                halt
                ; --- 1: idle ---------------------------------------------------------
                ld      ix, CAP
                xor     a
                call    GTSTCK
                ld      (ix+0), a
                ld      a, 1
                call    GTSTCK
                ld      (ix+1), a
                ld      a, 2
                call    GTSTCK
                ld      (ix+2), a
                ld      b, 0
trig_lp:
                push    bc
                ld      a, b
                call    GTTRIG
                pop     bc
                ld      (ix+3), a
                inc     ix
                inc     b
                ld      a, b
                cp      5
                jr      nz, trig_lp
                ld      ix, CAP+8
                ld      b, 0
mat_lp:
                push    bc
                ld      a, b
                call    SNSMAT
                pop     bc
                ld      (ix+0), a
                inc     ix
                inc     b
                ld      a, b
                cp      11
                jr      nz, mat_lp
                call    CHSNS
                push    af
                pop     hl
                ld      a, l
                and     $40                 ; Z flag: 1 = nothing waiting
                ld      (CAP+19), a
                ; --- 2: the press ------------------------------------------------------
                call    KILBUF
                ld      a, 1
                ld      (KEYRDY), a
                ld      b, 100
wait_press:
                halt
                push    bc
                ld      a, 8
                call    SNSMAT
                pop     bc
                cp      $FF
                jr      nz, pressed
                djnz    wait_press
                jr      released            ; never seen: CAP+$20.. stay 0
pressed:
                ld      (CAP+$22), a        ; SNSMAT 8 while held
                xor     a
                call    GTSTCK
                ld      (CAP+$20), a        ; 3 = right
                xor     a
                call    GTTRIG
                ld      (CAP+$21), a        ; $FF = space down (the frame it was seen
                                            ; on is timing, so it is not kept)
released:
                ; --- 3: after the release ---------------------------------------------
                ld      b, 30
rel_lp:
                halt
                djnz    rel_lp
                xor     a
                call    GTSTCK
                ld      (CAP+$28), a
                xor     a
                call    GTTRIG
                ld      (CAP+$29), a
                ld      a, 8
                call    SNSMAT
                ld      (CAP+$2A), a
                call    CHSNS
                push    af
                pop     hl
                ld      a, l
                and     $40
                ld      (CAP+$2B), a
                jr      nz, no_key          ; Z: nothing waiting
                call    CHGET
                ld      (CAP+$2C), a        ; the space ($20) the press queued
                call    CHSNS
                push    af
                pop     hl
                ld      a, l
                and     $40
                ld      (CAP+$2D), a
no_key:
                ; --- 4 -------------------------------------------------------------------
                call    KILBUF
                call    CHSNS
                push    af
                pop     hl
                ld      a, l
                and     $40
                ld      (CAP+$2E), a
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp
