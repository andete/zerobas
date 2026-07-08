; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX8.COM -- Item 5 (spec-diskbasic-option-closure.md): the WRSEQ ($15)
; FCB POSITION WRITE-BACK differential. M33 taught the sequential-read branch
; to advance the caller-visible FCB position (+32 CR / +12 EX / +28,29 cluster
; / +30) after each delivered record, but wired it to the READ branch only;
; the WRSEQ write branch was a bare `jp bdos_seqwrite` with no advance. Stock
; MSX-DOS-1 advances the FCB on sequential WRITES too -- our file bytes were
; already correct (the internal write-iterator tracks position), but the
; caller-visible FCB position field went stale. This exerciser drives exactly
; that path and captures it byte-for-byte vs the stock oracle.
;
; Lifecycle: FMAKE a fresh scratch file -> set DTA -> WRSEQ the same 128-byte
; pattern 12 times (12 records = 1536 B; on a 1024-byte-cluster fixture that is
; recPerClus=8 records per cluster, so it CROSSES one cluster boundary into the
; 2nd data cluster and exercises +28/29 cluster and +30, not just CR/EX). 12 is
; a multiple of RECPERSEC (=4), so every record is FLUSHED at capture time (no
; partial buffer) and the write iterator's BDOS_WRCLUS equals the logical
; current cluster -- the clean, unambiguous point for the differential (a
; mid-buffer stop just before a not-yet-allocated next cluster is a documented
; boundary, out of this gate's scope). Then snapshot the post-WRSEQ FCB into
; `fcbsnap` (frozen before FCLOSE can mutate it) -> FCLOSE. The differential
; compares the frozen post-WRSEQ FCB position AND the post-FCLOSE live FCB to
; stock.
;
; NOTE (deliberately NOT exercised here): $24 SETRND. Ours INTENTIONALLY
; diverges from stock on SETRND's +33..35 output (stock writes the constant
; rr=1; ours computes the true random position -- documented divergence,
; setrnd_body). Including SETRND would inject that known/allowlisted delta and
; muddy the WRSEQ-write-back signal, so this exerciser stops at FCLOSE. The
; post-WRSEQ FCB position (fcbsnap) IS the clean gate for the write-back.
;
; Every call's outward registers land in `regs`; the frozen post-WRSEQ FCB in
; `fcbsnap`; then the program self-loops at `done` -- the anchor for
; disk_probe_diff.py's `capture --at <done> --mem ...`. Same skeleton as
; bdosx4.asm (WRSEQ loop) + bdosx6.asm (frozen-FCB snapshot).
;
; CLEAN-ROOM: 100% own code. BDOS function contracts = published
; map.grauw.nl MSX-DOS function reference (DOS-1 subset) + CP/M 2.2 FCB layout
; (CR +32, EX +12, cluster +28..29, record-in-cluster +30), cited in
; disk/PROVENANCE.md; no stock/kernel bytes decoded.
;
; Build: pasmo --bin bdosx8.asm bdosx8.com bdosx8.sym

                org     $0100

BDOS            equ     $0005

start:
                call    build_wrpat

                ; --- record 0: $16 FMAKE (fresh FCB "WSEQPOS DAT") ---
                ld      hl, name_wseqpos_dat
                call    fillfcb_named
                ld      c, $16
                ld      de, fcb
                call    BDOS
                ld      ix, regs+0*8
                ld      (ix+0), $16
                call    snap

                ; --- set DTA -> wrpat (once for the whole WRSEQ run) ---
                ld      de, wrpat
                ld      c, $1A
                call    BDOS

                ; --- records 1..12: $15 WRSEQ; crosses a cluster boundary ---
                ; IX walks regs+1*8..; after 12 iterations it points at
                ; regs+13*8 -- we reuse that slot for FCLOSE.
                ld      ix, regs+1*8
wr_loop:
                ld      c, $15
                ld      de, fcb
                push    ix                      ; kernel returns FCB calls with IX clobbered
                call    BDOS                    ; (to $F195); preserve our record-walk across it
                pop     ix
                ld      (ix+0), $15
                call    snap                    ; snap sees the true BDOS return regs
                ld      de, 8
                add     ix, de                  ; next 8-byte record slot
                ld      hl, wr_count
                dec     (hl)
                jr      nz, wr_loop

                ; --- freeze the post-WRSEQ FCB (position fields live here) ------
                ; Copy the whole 37-byte FCB into fcbsnap BEFORE FCLOSE can touch
                ; it. This snapshot is the clean write-back gate: +12 EX / +28,29
                ; cluster / +30 rec-in-cluster / +32 CR after 10 written records.
                ld      hl, fcb
                ld      de, fcbsnap
                ld      bc, 37
                ldir

                ; --- record 13: $10 FCLOSE (IX already at regs+13*8) -----------
                ld      c, $10
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      (ix+0), $10
                call    snap

done:
                jr      done                    ; self-loop; capture --at <done>

; ---------------------------------------------------------------------------
; build_wrpat -- fill `wrpat` with byte[i] = (i*3 + 1) & $FF, i=0..127. Same
; deterministic pattern as bdosx3.asm/bdosx4.asm. Clobbers AF/B/HL.
; ---------------------------------------------------------------------------
build_wrpat:
                ld      hl, wrpat
                ld      b, 128
                ld      a, 1
bw_loop:
                ld      (hl), a
                inc     hl
                add     a, 3
                djnz    bw_loop
                ret

; ---------------------------------------------------------------------------
; fillfcb_named -- zero the 37-byte FCB, set drive=0 (implicit via the zero
; fill), copy the 11-byte 8.3 name at HL into +1. Clobbers AF/BC/DE/HL.
; ---------------------------------------------------------------------------
fillfcb_named:
                push    hl
                ld      hl, fcb
                ld      b, 37
                xor     a
ffn_zero:
                ld      (hl), a
                inc     hl
                djnz    ffn_zero
                pop     hl
                ld      de, fcb+1
                ld      bc, 11
                ldir
                ret

; ---------------------------------------------------------------------------
; snap -- store A, B, C, D, E, H, L into (ix+1)..(ix+7). (ix+0) is pre-filled
; by the caller with the literal BDOS function number.
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
; data
; ---------------------------------------------------------------------------
wr_count:        db     12                      ; WRSEQ attempts (loaded once per run)
name_wseqpos_dat: db    "WSEQPOS DAT"           ; fresh scratch file, written 10 records

; Addresses are NOT hand-pinned (build_bdosx8_disk.py reads them from the .sym).
; fcb, regs, fcbsnap are laid out CONTIGUOUSLY so one --mem region
; (fcb..fcbsnap+37) covers the live post-FCLOSE FCB, every return code, AND the
; frozen post-WRSEQ FCB position snapshot.
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      16*8                    ; 16 records x 8 B (12 used)
fcbsnap:        ds      37                      ; frozen post-WRSEQ FCB (position fields)
wrpat:          ds      128                     ; deterministic write pattern
