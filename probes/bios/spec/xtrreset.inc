; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRRESET -- D-TRSPEC (2026-11-23, tr6): the frame of xtrreset0 / xtrreset1 (included; the including file sets
; F4OUT, the byte written to port $F4 before the soft reset). xf4reset.asm gave no reading on the turbo R (its chain
; lives in page 3 RAM, which read $FF at the dump). This one keeps its evidence in VRAM, which a reset may or may not
; clear -- that is measured too:
;   at INIT (DI): read the 4-byte magic "TRRS" at VRAM $1F000 (the top 64 KB of the 128 KB) and $0F000 (the bottom);
;   append an 8-byte boot record to the VRAM log at $1F010 + 8 x stage: stage, IN $F4, JIFFY (word), the $1F000 magic
;   found (1/0), the $0F000 magic found (1/0), GETCPU's A ($0183), $5A.
;   Boot 1 (no magic at $1F000): write both magics, stage := 1, OUT ($F4), F4OUT, JP $0000 (DI, page 1 = this
;   cartridge, the CPU as INIT found it).
;   A later boot (magic found): record, copy the VRAM log to the capture and set DONE. The stage byte is $1F004.
; If the cartridge is never re-entered, the @vram spans show whether the magics survived the reset and what the
; screen shows, and @dumpstate where the machine is. The capture (CAP = $C001): the VRAM log $1F010.. (32 bytes).
; CLEAN-ROOM: 100% own code; VRAM through the VDP's ports, port $F4, JIFFY, GETCPU. No ROM byte read.
;
; The including file carries the harness directives (@cap C000, @caplen 20, @vram 1F000:40 / F000:10 / 0000:800 /
; 1800:300, @dumpstate, @timeout 60).

DONE    equ     $C000
CAP     equ     $C001
JIFFY   equ     $FC9E
GETCPU  equ     $0183
buf     equ     $C100

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

; VRAM address: A = R#14 (A16-A14), HL = A13-A0
vwr:
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                or      $40
                out     ($99), a
                ret
vrd:
                out     ($99), a
                ld      a, $8E
                out     ($99), a
                ld      a, l
                out     ($99), a
                ld      a, h
                and     $3F
                out     ($99), a
                ret

; Z := the 4 bytes read from the VRAM pointer are "TRRS"
chkmagic:
                ld      hl, magic
                ld      b, 4
cm1:
                in      a, ($98)
                cp      (hl)
                ret     nz
                inc     hl
                djnz    cm1
                ret

init:
                di
                in      a, ($F4)
                ld      (buf+1), a
                ld      hl, (JIFFY)
                ld      (buf+2), hl
                call    GETCPU
                ld      (buf+6), a
                di
                ld      a, $5A
                ld      (buf+7), a
                ld      a, 7                ; $1F000
                ld      hl, $3000
                call    vrd
                call    chkmagic
                ld      a, 0
                jr      nz, nm1
                inc     a
nm1:
                ld      (buf+4), a
                ld      a, 3                ; $0F000
                ld      hl, $3000
                call    vrd
                call    chkmagic
                ld      a, 0
                jr      nz, nm2
                inc     a
nm2:
                ld      (buf+5), a
                ld      a, (buf+4)
                or      a
                jr      z, first
                ld      a, 7                ; the stage byte, $1F004
                ld      hl, $3004
                call    vrd
                in      a, ($98)
                jr      later
first:
                ld      a, 7                ; both magics, stage 0 at $1F004
                ld      hl, $3000
                call    vwr
                call    putmagic
                xor     a
                out     ($98), a
                ld      a, 3
                ld      hl, $3000
                call    vwr
                call    putmagic
                xor     a
later:
                ld      (buf), a            ; the stage of this boot
                ld      e, a                ; the record at $1F010 + 8 x stage
                add     a, a
                add     a, a
                add     a, a
                add     a, $10
                ld      l, a
                ld      h, $30
                ld      a, 7
                call    vwr
                ld      hl, buf
                ld      b, 8
wr1:
                ld      a, (hl)
                out     ($98), a
                inc     hl
                djnz    wr1
                ld      a, e
                or      a
                jr      nz, finish
                ld      a, 7                ; stage := 1
                ld      hl, $3004
                call    vwr
                ld      a, 1
                out     ($98), a
                ld      a, F4OUT
                out     ($F4), a
                jp      $0000
finish:
                ld      a, 7
                ld      hl, $3010
                call    vrd
                ld      hl, CAP
                ld      b, 32
rd1:
                in      a, ($98)
                ld      (hl), a
                inc     hl
                djnz    rd1
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

putmagic:
                ld      hl, magic
                ld      b, 4
pm1:
                ld      a, (hl)
                out     ($98), a
                inc     hl
                djnz    pm1
                ret

magic:
                db      "TRRS"

                ds      $8000 - $, $FF
