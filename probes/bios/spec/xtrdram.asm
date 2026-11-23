; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; XTRDRAM -- D-TRSPEC, docs/turbor/main/CHGCPU.md ("the memory side of DRAM mode"): the memory mapper and the slot
; state in each CPU mode, on the two turbo R references (--row turbor: FS-A1GT vs FS-A1ST).
; Per mode, in the order R800 DRAM ($82: the boot's mode -- tested first, before anything was written), R800 ROM
; ($81), Z80 ($80) -- CHGCPU(mode), DI, then:
;  - S1990 R#6, $A8, ($FFFF) cpl (page 3's secondary slot register), IN $FC-$FF (the mapper registers read back),
;    EXPTBL $FCC1-$FCC4;
;  - for s = 0..63: OUT $FE,s then IN $FE (what the page-2 register reads back);
;  - WRITE TEST, for s = 0..63: OUT $FE,s; write $5A to $9F00 (offset $1F00 of segment s), compare; write $A5,
;    compare. Only the two equality bits are kept (3 = both writes read back = writable RAM). A segment that keeps
;    neither shows nothing of what it holds: no byte read from it is stored, reported or used beyond "equal to the
;    probe's own $5A / $A5" -- and a byte cannot equal both;
;  - TAG PASS (writable segments only -- the others are skipped, never read): for s = 0..63 write s to $9F01 of s;
;    then for s = 0..63 compare $9F01 of s with s: 1 = its own tag, 0 = another segment's (the register's upper bits
;    are not decoded: segment s and s + N are one RAM), 2 = skipped;
;  - OUT $FE back to the value read at the start.
; Offset $1F00 / $1F01 of the segment page 3 uses is $DF00 / $DF01, outside this probe's capture, stack and
; variables. The run ends in the Z80 (no CHGCPU back to DRAM mode after the writes).
; Record (RECLEN = $100 from CAP+16 = $C011): +0 mode, +1 R#6, +2 $A8, +3 ($FFFF) cpl, +4..+7 IN $FC-$FF, +8..+11
; EXPTBL, +12 $5A, +16..+79 IN $FE after OUT $FE,s, +80..+143 the write test (bit 0: $5A read back, bit 1: $A5),
; +144..+207 the tag pass (1 own tag / 0 another's / 2 skipped). CAP+0 = modes done.
; Run: python3 -u probes/bios/biosl_run.py probes/bios/spec/xtrdram.asm --row turbor
;
; CLEAN-ROOM: 100% own code; published BIOS entries (CHGCPU), work-area RAM, I/O ports, and RAM written by this probe
; and read back for equality with what it wrote. No ROM byte read, no byte of a segment it could not write.
;
; @cap C000
; @caplen 0400
; @timeout 60

CHGCPU  equ     $0180
DONE    equ     $C000
CAP     equ     $C001
REC     equ     CAP+16
RECLEN  equ     $100
TADR    equ     $9F00

PTR     equ     $E904
MIDX    equ     $E906
FESAVE  equ     $E907

                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0

init:
                di
                ld      sp, $E800
                ld      hl, CAP
                ld      de, CAP+1
                ld      bc, $03FE
                ld      (hl), 0
                ldir
                ld      hl, REC
                ld      (PTR), hl
                xor     a
                ld      (MIDX), a
m_next:
                ld      a, (MIDX)
                ld      e, a
                ld      d, 0
                ld      hl, modes
                add     hl, de
                ld      a, (hl)
                or      a
                jp      z, finish
                push    af
                call    CHGCPU
                di
                pop     af
                ld      ix, (PTR)
                ld      (ix+0), a
                ld      (ix+12), $5A
                ld      a, 6
                out     ($E4), a
                in      a, ($E5)
                ld      (ix+1), a
                in      a, ($A8)
                ld      (ix+2), a
                ld      a, ($FFFF)
                cpl
                ld      (ix+3), a
                in      a, ($FC)
                ld      (ix+4), a
                in      a, ($FD)
                ld      (ix+5), a
                in      a, ($FE)
                ld      (ix+6), a
                ld      (FESAVE), a
                in      a, ($FF)
                ld      (ix+7), a
                ld      hl, $FCC1
                push    ix
                pop     de
                ld      bc, 8
                ex      de, hl
                add     hl, bc
                ex      de, hl
                ld      bc, 4
                ldir
                ; readback of $FE
                push    ix
                pop     hl
                ld      de, 16
                add     hl, de
                ld      b, 0
rb_lp:          ld      a, b
                out     ($FE), a
                in      a, ($FE)
                ld      (hl), a
                inc     hl
                inc     b
                ld      a, b
                cp      64
                jr      nz, rb_lp
                ; write test
                push    ix
                pop     hl
                ld      de, 80
                add     hl, de
                ld      b, 0
wt_lp:          ld      a, b
                out     ($FE), a
                ld      c, 0
                ld      a, $5A
                ld      (TADR), a
                ld      a, (TADR)
                cp      $5A
                jr      nz, wt_1
                set     0, c
wt_1:           ld      a, $A5
                ld      (TADR), a
                ld      a, (TADR)
                cp      $A5
                jr      nz, wt_2
                set     1, c
wt_2:           ld      (hl), c
                inc     hl
                inc     b
                ld      a, b
                cp      64
                jr      nz, wt_lp
                ; tag pass: write
                push    ix
                pop     hl
                ld      de, 80
                add     hl, de                  ; HL = write-test results
                ld      b, 0
tw_lp:          ld      a, (hl)
                cp      3
                jr      nz, tw_skip
                ld      a, b
                out     ($FE), a
                ld      (TADR+1), a
tw_skip:        inc     hl
                inc     b
                ld      a, b
                cp      64
                jr      nz, tw_lp
                ; tag pass: compare
                push    ix
                pop     hl
                ld      de, 80
                add     hl, de
                push    ix
                pop     de
                push    hl
                ld      hl, 144
                add     hl, de
                ex      de, hl                  ; DE = tag results
                pop     hl                      ; HL = write-test results
                ld      b, 0
tc_lp:          ld      c, 2
                ld      a, (hl)
                cp      3
                jr      nz, tc_put
                ld      a, b
                out     ($FE), a
                ld      c, 0
                ld      a, (TADR+1)
                cp      b
                jr      nz, tc_put
                ld      c, 1
tc_put:         ld      a, c
                ld      (de), a
                inc     de
                inc     hl
                inc     b
                ld      a, b
                cp      64
                jr      nz, tc_lp
                ld      a, (FESAVE)
                out     ($FE), a
                ; next mode
                ld      hl, (PTR)
                ld      bc, RECLEN
                add     hl, bc
                ld      (PTR), hl
                ld      hl, MIDX
                inc     (hl)
                ld      a, (hl)
                ld      (CAP), a
                jp      m_next

finish:
                ld      a, $A5
                ld      (DONE), a
halt_lp:
                jr      halt_lp

modes:          db      $82, $81, $80, 0

                ds      $8000-$, $FF
