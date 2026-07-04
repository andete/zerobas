; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX.COM -- Tier-2 BDOS exerciser, Phase 1 (FCB cluster). See
; disk/docs/tier2-bdos-exerciser-spec.md for the full design. Calls a fixed,
; deterministic sequence of FCB BDOS functions ($23/$0F/$14/$24/$27/$26/$10)
; against BDOSX.BIN and records every call's outward registers (+ delivered
; data) into a fixed RAM buffer, then self-loops at `done` -- the anchor for
; disk_probe_diff.py's `capture --at <done> --mem ...` differential.
;
; CLEAN-ROOM: 100% own code. BDOS function contracts are the published
; map.grauw.nl MSX-DOS 2 function spec (documents this DOS-1-compatible FCB
; subset verbatim); FCB layout is the published CP/M/MSX2-TH standard already
; cited in disk/PROVENANCE.md SS FCB layout. No stock/kernel bytes decoded.
;
; Build: pasmo -s bdosx.sym --bin bdosx.asm bdosx.com

                org     $0100

BDOS            equ     $0005

; ---------------------------------------------------------------------------
; entry: FSIZE -> FOPEN -> RDSEQ x2 -> SETRND -> RDBLK -> WRBLK -> FCLOSE
;
; Each call is immediately followed by a snapshot of A/B/C/D/E/H/L into the
; matching `regs` record via IX (IX is not one of the snapshotted registers,
; so indexing through it never clobbers the value being saved -- notably HL,
; which is itself an outward result register for $27 RDBLK; see spec SS7 for
; why a shared HL-pointer snapshot routine was rejected).
; ---------------------------------------------------------------------------
start:
                ; --- record 0: $23 FSIZE (unopened FCB) ---
                call    fillfcb
                ld      c, $23
                ld      de, fcb
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $23
                call    snap

                ; --- record 1: $0F FOPEN (fresh FCB) ---
                call    fillfcb
                ld      c, $0F
                ld      de, fcb
                call    BDOS
                ld      ix, regs+1*8
                ld      (ix+0), $0F
                call    snap

                ; --- record 2: $14 RDSEQ #1 (DTA -> data+0) ---
                ld      de, data+0*128
                ld      c, $1A
                call    BDOS
                ld      c, $14
                ld      de, fcb
                call    BDOS
                ld      ix, regs+2*8
                ld      (ix+0), $14
                call    snap

                ; --- record 3: $14 RDSEQ #2 (DTA -> data+128) ---
                ld      de, data+1*128
                ld      c, $1A
                call    BDOS
                ld      c, $14
                ld      de, fcb
                call    BDOS
                ld      ix, regs+3*8
                ld      (ix+0), $14
                call    snap

                ; --- record 4: $24 SETRND ---
                ld      c, $24
                ld      de, fcb
                call    BDOS
                ld      ix, regs+4*8
                ld      (ix+0), $24
                call    snap

                ; --- set FCB record size = 128 (FCB+14..15, word) for the block ops ---
                ; The random block ops $27 RDBLK / $26 WRBLK take their per-record
                ; transfer size from FCB+14..15; the published contract makes the
                ; application responsible for setting it (an unset 0 is an
                ; implementation-defaulted value -> out of contract, and ours vs
                ; stock disagree on the default). Set it to the standard 128-byte
                ; record so the block-op differential compares a well-defined
                ; transfer size. Deliberately set here -- AFTER the RDSEQ calls,
                ; immediately before the first block op -- because FCB+14..15
                ; overlaps position state the sequential path relies on; setting it
                ; earlier disturbs RDSEQ (records 2/3). 128 matches the 128-B DTA
                ; spacing below.
                ld      hl, 128
                ld      (fcb+14), hl

                ; --- record 5: $27 RDBLK, 1 record (DTA -> data+256) ---
                ld      de, data+2*128
                ld      c, $1A
                call    BDOS
                ld      c, $27
                ld      de, fcb
                ld      hl, 1
                call    BDOS
                ld      ix, regs+5*8
                ld      (ix+0), $27
                call    snap

                ; --- record 6: $26 WRBLK, 1 record (from data+256) ---
                ld      c, $26
                ld      de, fcb
                ld      hl, 1
                call    BDOS
                ld      ix, regs+6*8
                ld      (ix+0), $26
                call    snap

                ; --- record 7: $10 FCLOSE ---
                ld      c, $10
                ld      de, fcb
                call    BDOS
                ld      ix, regs+7*8
                ld      (ix+0), $10
                call    snap

done:
                jr      done                    ; self-loop; the disk_probe_diff.py `capture --at
                                                ; <done> --arm-check-val 0x01` anchor (arm-gated on
                                                ; $0102 == BDOSX.COM's own 3rd byte, so the count
                                                ; only starts once BDOSX.COM -- not COMMAND.COM's
                                                ; own busy-poll loop, which happened to collide with
                                                ; a bare mid-program address -- is the resident
                                                ; program; see spec SS7 + disk_probe_diff.py capture
                                                ; mode's --arm-check-* option).

; ---------------------------------------------------------------------------
; fillfcb -- zero the 37-byte FCB, set drive=0, copy the 11-byte 8.3 name.
; Clobbers AF/BC/DE/HL.
; ---------------------------------------------------------------------------
fillfcb:
                ld      hl, fcb
                ld      b, 37
                xor     a
fillfcb_zero:
                ld      (hl), a
                inc     hl
                djnz    fillfcb_zero
                ld      hl, fcb_name
                ld      de, fcb+1
                ld      bc, 11
                ldir
                ret

; ---------------------------------------------------------------------------
; snap -- store A, B, C, D, E, H, L into (ix+1)..(ix+7). (ix+0) is pre-filled
; by the caller with the literal BDOS function number. Clobbers nothing
; live (the values it stores are the last thing each call site needs).
; ---------------------------------------------------------------------------
snap:
                ld      (ix+1), a
                ld      (ix+2), b
                ld      (ix+3), c
                ld      (ix+4), d
                ld      (ix+5), e
                ld      (ix+6), h
                ld      (ix+7), l
                ret

; ---------------------------------------------------------------------------
; data (37-byte FCB name table + result buffers)
; ---------------------------------------------------------------------------
fcb_name:       db      "BDOSX   BIN"           ; 8.3, space-padded (11 bytes)

                ds      $0300 - $, $00
fcb:            ds      37                      ; $0300-$0324

                ds      $0340 - $, $00
regs:           ds      8*8                     ; $0340-$037F: 8 records x 8 B

                ds      $0400 - $, $00
data:           ds      3*128                   ; $0400-$057F: RDSEQ x2 + RDBLK snapshots
