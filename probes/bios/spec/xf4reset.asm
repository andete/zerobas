; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XF4RESET -- D-MSX2SPEC, docs/msx2/main/RDRES.md RR-7 / WRRES.md WR-3: port $F4 across a soft reset (JP $0000), set
; BY HAND (no BIOS call; WRRES's effect on the port is xrdres.asm's). A chain of three boots, kept in page 3 RAM by a
; magic at $C800 ("F4RS") and a stage byte:
;   boot 1 (no magic): record IN $F4 and JIFFY at INIT; OUT ($F4), $00; JP $0000
;   boot 2: record the same; OUT ($F4), $80; JP $0000
;   boot 3: record the same; finish.
; JIFFY at INIT measures how long the boot took to reach the cartridge (a start-up screen shows as a longer boot).
; If the boot clears the magic the chain never ends (no reading) -- that would itself be the finding.
; The capture (CAP = C001): +0 stages done, then per boot: IN $F4, JIFFY lo, JIFFY hi; +10 $5A.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xf4reset.asm --row msx2all
;
; CLEAN-ROOM: 100% own code; an I/O port and a work-area cell. No ROM byte read, no BIOS call.
;
; @cap C000
; @caplen 0020
; @timeout 120

DONE    equ     $C000
CAP     equ     $C001
MAGIC   equ     $C800
STAGE   equ     $C804
SAVE    equ     $C810
JIFFY   equ     $FC9E

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                in      a, ($F4)
                ld      b, a
                ld      hl, (JIFFY)
                push    hl
                ld      hl, (MAGIC)
                ld      de, $3446               ; "F4"
                or      a
                sbc     hl, de
                jr      nz, boot1
                ld      hl, (MAGIC+2)
                ld      de, $5352               ; "RS"
                or      a
                sbc     hl, de
                jr      nz, boot1
                jr      rec
boot1:
                ld      hl, $3446
                ld      (MAGIC), hl
                ld      hl, $5352
                ld      (MAGIC+2), hl
                xor     a
                ld      (STAGE), a
rec:
                ld      a, (STAGE)
                ld      e, a
                add     a, a
                add     a, e                    ; 3 x stage
                ld      e, a
                ld      d, 0
                ld      hl, SAVE
                add     hl, de
                ld      (hl), b
                inc     hl
                pop     de
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ld      a, (STAGE)
                inc     a
                ld      (STAGE), a
                cp      1
                jr      nz, st2
                xor     a
                out     ($F4), a
                jp      $0000
st2:
                cp      2
                jr      nz, st3
                ld      a, $80
                out     ($F4), a
                jp      $0000
st3:
                ld      (CAP), a
                ld      hl, SAVE
                ld      de, CAP+1
                ld      bc, 9
                ldir
                ld      a, $5A
                ld      (CAP+10), a
                xor     a
                ld      (MAGIC), a
                ld      a, $A5
                ld      (DONE), a
fin:
                jr      fin

                ds      $8000 - $, $FF
