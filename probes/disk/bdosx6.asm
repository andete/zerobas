; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BDOSX6.COM -- Tier-C case 4: PAST-EOF random-record I/O ($21 RDRND / $22
; WRRND). See disk/docs/tier2-tierC-spec.md "Candidate cases" #4. The
; happy-path RDRND/WRRND round trip is already proven byte-identical to stock
; elsewhere (BDOSX3 records 18-20); this exerciser drives the ADVERSARIAL
; corner: positioning the FCB's random-record field PAST the file's current
; end and issuing RDRND (must report some EOF/unwritten-record code, deliver
; no valid data) then WRRND at that SAME past-EOF position (must extend the
; file -- record 5 of a 128-byte-record file is byte offset 640, still inside
; the fixture's single 1024-byte cluster, so this exercises in-cluster
; extension without forcing a second cluster allocation).
;
; Fixture: a 256-byte "SHORT   .DAT" (2 records of 128 B, one data cluster).
; Lifecycle: FOPEN -> set record size 128 -> set random record 5 (past EOF:
; file only has records 0,1) -> RDRND -> set random record 5 again -> WRRND
; (deterministic pattern) -> FCLOSE (captures how each side finalises the
; extended file). Every call's outward registers land in a fixed RAM buffer
; (`regs`), then the program self-loops at `done` -- the anchor for
; disk_probe_diff.py's `capture --at <done> --mem ...` differential. Same
; skeleton as bdosx4.asm/bdosx3.asm (fillfcb-style setup, IX-indexed `snap`,
; 8-byte records).
;
; CLEAN-ROOM: 100% own code; BDOS function contracts = published
; map.grauw.nl MSX-DOS function reference (DOS-1 subset) + CP/M 2.2 FCB
; layout (random-record field +33..35, record-size field +14..15), cited in
; disk/PROVENANCE.md; no stock/kernel bytes decoded.
;
; Build: pasmo --bin bdosx6.asm bdosx6.com bdosx6.sym

                org     $0100

BDOS            equ     $0005

start:
                call    build_wrpat

                ; --- record 0: $0F FOPEN "SHORT   DAT" ---
                ld      hl, name_short_dat
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                push    ix                      ; the kernel returns FCB calls with IX clobbered
                call    BDOS                    ; (to $F195); preserve our record-walk across it,
                pop     ix                      ; else `ld (ix+0)` stamps system RAM (killed stock)
                ld      ix, regs+0*8
                ld      (ix+0), $0F
                call    snap

                ; --- set FCB+14..15 = 128 (record size, word), AFTER open ---
                ld      hl, 128
                ld      (fcb+14), hl

                ; --- record 1: $21 RDRND, r0=5,r1=0,r2=0 (past EOF; file has 0,1) -> rdbuf ---
                xor     a
                ld      (fcb+33), a             ; r0
                ld      (fcb+34), a             ; r1
                ld      (fcb+35), a             ; r2
                ld      a, 5
                ld      (fcb+33), a             ; r0 = 5
                ld      de, rdbuf
                ld      c, $1A
                call    BDOS
                ld      c, $21
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+1*8
                ld      (ix+0), $21
                call    snap

                ; --- record 2: $22 WRRND, r0=5 again -> wrpat (extends the file) ---
                xor     a
                ld      (fcb+33), a
                ld      (fcb+34), a
                ld      (fcb+35), a
                ld      a, 5
                ld      (fcb+33), a             ; r0 = 5
                ld      de, wrpat
                ld      c, $1A
                call    BDOS
                ld      c, $22
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+2*8
                ld      (ix+0), $22
                call    snap

                ; --- record 3: $10 FCLOSE (extended-file finalisation) ---
                ld      c, $10
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+3*8
                ld      (ix+0), $10
                call    snap

                ; --- save the post-WRRND FCB size (fcb+16..19) into wrsize -------
                ; (proves the IN-MEMORY FCB held the extended size right after the
                ; WRRND/FCLOSE sequence, before the re-FOPEN below reloads from disk)
                ld      hl, fcb+16
                ld      de, wrsize
                ld      bc, 4
                ldir

                ; --- record 4: $0F re-FOPEN "SHORT   DAT" ------------------------
                ; A fresh FOPEN reloads FCB+16..19 from the ON-DISK DIRENT (fat.asm
                ; fopen_fill_body's own LDIR from FAT_FILESIZE) -- so if M36 truly
                ; persisted the extension to the directory (not just the in-memory
                ; FCB from the WRRND above), this reopen's size must ALSO read back
                ; 768. This is the non-vacuous check: a RAM-only fix would show
                ; wrsize=768 here but the reopened fcb+16..19 back at 256.
                ld      hl, name_short_dat
                call    fillfcb_named
                ld      c, $0F
                ld      de, fcb
                push    ix
                call    BDOS
                pop     ix
                ld      ix, regs+4*8
                ld      (ix+0), $0F
                call    snap

done:
                jr      done                    ; self-loop; capture --at <done>

; ---------------------------------------------------------------------------
; build_wrpat -- fill `wrpat` with byte[i] = (i*3 + 1) & $FF, i=0..127. Same
; deterministic-pattern idiom as bdosx3.asm/bdosx4.asm.  Clobbers AF/B/HL.
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
name_short_dat: db      "SHORT   DAT"           ; fixture file: 256 B, 2 records, 1 cluster

; Addresses are NOT hand-pinned (build_bdosx6_disk.py reads them from the .sym).
; fcb, regs, wrsize are laid out CONTIGUOUSLY so a single --mem capture region
; (fcb..wrsize+4) covers the reopened FCB size (fcb+16..19, record 4's result),
; every return code (regs, records 0-4), and the saved post-WRRND size (wrsize).
fcb:            ds      37                      ; 37-byte FCB
regs:           ds      8*8                     ; 8 records x 8 B (5 used)
wrsize:         ds      4                       ; post-WRRND fcb+16..19 snapshot (LE)
rdbuf:          ds      128                     ; RDRND (past-EOF) read buffer
wrpat:          ds      128                     ; deterministic write pattern (WRRND)
