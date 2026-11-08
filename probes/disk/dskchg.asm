; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; DSKCHG.COM -- D-DSKCHG (TODO.md): does the CF-3300's DSKCHG ($4013) answer
; depend on how long ago the disk was last read? A drive without a disk-change
; line can only say "unchanged" (B = 1) safely shortly after an access, and
; must say "unknown" (B = 0) otherwise; a wrong "unchanged" after a swap makes
; MSX-DOS write one disk's FAT onto another. So, with NO swap:
;   record 0  DSKCHG right after a read (SFIRST touched the directory)
;   record 1  DSKCHG after ~1 s idle   (JIFFY,  50 ticks)
;   record 2  DSKCHG after ~3 s idle   (JIFFY, 150 ticks)
;   record 3  DSKCHG after ~10 s idle  (JIFFY, 500 ticks)
; Each record: A, F, B, C, D, E, H, L after the call. Called through CALSLT
; ($001C) with the slot from $FB22 (dskent.asm's way; D-DRVINT). Self-loop at
; `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published disk-ROM interface and BIOS work
; area (JIFFY $FC9E, $FB22). No ROM byte is read.
;
; Build: pasmo --bin dskchg.asm dskchg.com dskchg.sym

                org     $0100

BDOS            equ     $0005
CALSLT          equ     $001C
DSKSLT          equ     $FB22
JIFFY           equ     $FC9E

start:
                ld      de, dta                 ; a directory read just before record 0
                ld      c, $1A
                call    BDOS
                ld      de, sfcb
                ld      c, $11                  ; SFIRST
                call    BDOS
                ld      hl, regs+0*8
                call    chg
                ld      bc, 50
                call    wait
                ld      hl, regs+1*8
                call    chg
                ld      bc, 150
                call    wait
                ld      hl, regs+2*8
                call    chg
                ld      bc, 500
                call    wait
                ld      hl, regs+3*8
                call    chg
done:
                jr      done

; wait -- BC jiffies
wait:
                ei                              ; a CALSLT can return with interrupts off,
                                                ; and then JIFFY never moves (first run hung)
                ld      hl, (JIFFY)
                add     hl, bc
                ex      de, hl                  ; DE = the target
wt_lp:
                ld      hl, (JIFFY)
                or      a
                sbc     hl, de
                jr      c, wt_lp
                ret

; chg -- DSKCHG drive A (A = 0, B = 0, C = $F9, HL = the DPB buffer) through
; CALSLT; the outward registers to the record at HL.
chg:
                ld      (recp), hl
                ld      a, (DSKSLT)
                ld      iyh, a
                ld      ix, $4013
                xor     a
                ld      b, 0
                ld      c, $F9
                ld      hl, dpb
                call    CALSLT
                push    hl
                push    af
                ld      hl, (recp)
                pop     de                      ; D = A, E = F
                ld      (hl), d
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (hl), b
                inc     hl
                ld      (hl), c
                inc     hl
                ld      (hl), 0
                inc     hl
                ld      (hl), 0
                inc     hl
                pop     de                      ; the call's HL
                ld      (hl), d
                inc     hl
                ld      (hl), e
                ret

recp:           dw      0
sfcb:           db      0, "????????", "???"
                ds      37 - 12, 0

; ---------------------------------------------------------------------------
; captured block $0400-$041F: 4 records x 8 B
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
regs:           ds      4*8, $EE
dpb:            ds      32, $EE
dta:            ds      64, $00
