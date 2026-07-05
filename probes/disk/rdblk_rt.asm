; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; RDBLK.COM — clean single-shot BDOS $27 RDBLK exerciser for the M31
; random-record round-trip (disk/docs/tier2-m31-rdblk-randrecord-spec.md §6.2).
; Runs identically on OURS (C-BIOS + zerobas-disk) and STOCK (National CF-3300)
; via the real BDOS at $0005, then self-loops at `done` — the anchor for
; disk_probe_diff.py's `capture --at <done> --mem ...` differential. The runner
; captures the DTA + the return snapshot on BOTH machines and diffs them: if
; M31's faithful $27 positions to the SAME record as stock (and returns the same
; A/HL + advances FCB+33..35 the same way), the two are byte-identical.
;
; The random-record field FCB+33..35 is set DIRECTLY here (NOT via $24 SETRND):
; ours' $24 is still a no-op (the deferred gate-green piece), so driving it that
; way would leave RR=0 and defeat the test. Setting the FCB field directly is
; the exact method the M31 investigation exerciser used, and it is what any
; program that computes its own random-record position would do.
;
; A 6-byte param block at the FIXED offset $0102 is patched by the Python runner
; per case (so one assemble covers every case):
;   $0102..$0104  recnum  24-bit random record (LE) -> FCB+33..35
;   $0105..$0106  rs      record size word          -> FCB+14..15
;   $0107..$0108  cnt     RDBLK record count (HL)
;
; CLEAN-ROOM: our own program; calls the published BDOS $0F/$1A/$27/$00 contract
; entries only; the CF-3300 is a black box we run + whose RAM RESULT we read
; (never its ROM code).

BDOS    equ     $0005
SENT    equ     $EE                     ; DTA prefill sentinel (unwritten bytes stay this)

        org     $0100
start:
        jr      main                    ; $0100..$0101 (2 bytes) -> params at $0102
recnum: db      1, 0, 0                 ; $0102..$0104  (arm signature = recnum[0])
rs:     dw      128                     ; $0105..$0106
cnt:    dw      1                       ; $0107..$0108

main:
        ; --- prefill the DTA buffer with the sentinel so any byte $27 does NOT
        ; write stays SENT on both machines (only genuinely-transferred bytes can
        ; differ) ---
        ld      hl, data
        ld      de, data+1
        ld      bc, DATALEN-1
        ld      (hl), SENT
        ldir

        ; --- fill the FCB: zero 37 bytes (drive=0 => default drive), then copy
        ; the 11-byte 8.3 name into FCB+1. (Without this the FCB is uninitialised
        ; and FOPEN fails -> reads return zeros/EOF on BOTH machines.) ---
        ld      hl, fcb
        ld      b, 37
        xor     a
fillz:  ld      (hl), a
        inc     hl
        djnz    fillz
        ld      hl, fcb_name
        ld      de, fcb+1
        ld      bc, 11
        ldir

        ; --- FOPEN ($0F) the target file ---
        ld      de, fcb
        ld      c, $0F
        call    BDOS

        ; --- RDSEQ ($14) x2 into a scratch buffer ---------------------------
        ; BDOSX.COM's PROVEN preamble (its $27 reads real file data in the
        ; acceptance gate): two sequential reads establish the FCB extent/size
        ; state stock's random block read needs. A bare FOPEN -> $27 (even with
        ; $24) leaves stock reading past-EOF. The bytes read here are discarded
        ; (scratch DTA); only the side effect on FCB state matters. $27 re-seeks
        ; from the file start (k_47B2 fat_open + skip-RR), so this preamble does
        ; not affect WHERE $27 lands.
        ld      de, scratch
        ld      c, $1A
        call    BDOS
        ld      de, fcb
        ld      c, $14
        call    BDOS
        ld      de, fcb
        ld      c, $14
        call    BDOS

        ; --- $24 SETRND (captures current position into FCB+33..35; we override
        ; it next) ---
        ld      de, fcb
        ld      c, $24
        call    BDOS

        ; --- record size := rs (FCB+14..15) — set AFTER $24, right before the
        ; block op: FCB+14..15 overlaps the sequential/position state the earlier
        ; calls rely on (bdosx.asm §; investigation recipe), so setting it earlier
        ; corrupts stock's file-size view. ---
        ld      hl, (rs)
        ld      (fcb+14), hl

        ; --- random record := recnum (FCB+33..35), set DIRECTLY (override $24's
        ; value): our $24 leaves it 0; a program computing its own position writes
        ; the field itself. This is what makes RR>0 actually exercised. ---
        ld      a, (recnum+0)
        ld      (fcb+33), a
        ld      a, (recnum+1)
        ld      (fcb+34), a
        ld      a, (recnum+2)
        ld      (fcb+35), a

        ; --- SETDTA ($1A) -> our capture buffer ---
        ld      de, data
        ld      c, $1A
        call    BDOS

        ; --- $27 RDBLK, cnt records ---
        ld      de, fcb
        ld      hl, (cnt)
        ld      c, $27
        call    BDOS

        ; --- snapshot the outward result (A/HL/BC) into fixed cells ---
        ld      (res_a), a              ; A = 0 all-read / 1 EOF-first
        ld      (res_hl), hl            ; HL = records actually read
        ld      (res_bc), bc            ; BC = HL at the boundary (kernel wrapper may clobber at API)

        ; --- copy FCB+33..35 AFTER the call (RR write-back := RR + HL) ---
        ld      a, (fcb+33)
        ld      (res_rr+0), a
        ld      a, (fcb+34)
        ld      (res_rr+1), a
        ld      a, (fcb+35)
        ld      (res_rr+2), a

done:
        jr      done                    ; self-loop; capture --at done --arm-check-val recnum[0]

; ---------------------------------------------------------------------------
; data (FCB name + result cells + DTA capture buffer), fixed absolute layout so
; the runner's `capture --mem` window is stable across assembles.
; ---------------------------------------------------------------------------
fcb_name:       db      "RDTEST  BIN"           ; 8.3, space-padded (11 bytes)

                ds      $0300 - $, $00
fcb:            ds      37                      ; $0300-$0324

                ds      $0340 - $, $00
res_a:          ds      1                       ; $0340  A (0/1)
res_hl:         ds      2                       ; $0341-$0342  HL (records read)
res_bc:         ds      2                       ; $0343-$0344  BC
res_rr:         ds      3                       ; $0345-$0347  FCB+33..35 after ($27 write-back)

                ds      $0380 - $, $00
scratch:        ds      128                     ; $0380-$03FF: RDSEQ x2 preamble sink (discarded)

                ds      $0400 - $, $00
data:           ds      3*128                   ; $0400-$057F: RDBLK DTA capture buffer
DATALEN         equ     3*128
