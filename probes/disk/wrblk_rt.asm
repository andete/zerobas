; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; WRBLK.COM — clean single-shot BDOS $26 WRBLK exerciser for the disk-artifact
; round-trip (M28 verification). Runs identically on OURS (C-BIOS + zerobas-disk)
; and STOCK (National CF-3300) via the real BDOS at $0005, then terminates to
; DOS. Nothing is captured to RAM: the runner reads the MUTATED /tmp .dsk image
; afterwards and diffs the two on-disk artifacts.
;
; A 9-byte param block at the FIXED offset $0102 is patched by the Python
; injector per case (so one assemble covers every case):
;   $0102..$0104  recnum  24-bit random record (LE) -> FCB+33..35
;   $0105..$0106  rs      record size word          -> FCB+14..15
;   $0107..$0108  cnt     WRBLK record count (HL)
;   $0109         fillb   DTA sentinel fill byte
;   $010A         delflag M30 del_realloc case: nonzero -> BDOS $13 DELETE
;                         "DELFILE BIN" (a pre-seeded low-cluster file) BEFORE
;                         the FOPEN/WRBLK below, so the subsequent allocation
;                         must reuse the clusters just freed. 0 (the default)
;                         reproduces every pre-M30 case byte-for-byte (no
;                         extra BDOS call at all).
;
; CLEAN-ROOM: our own program; calls the published BDOS $0F/$13/$1A/$26/$10/
; $00 contract entries only; the CF-3300 is a black box we run + whose OUTPUT
; DISK we read (never its ROM code).

BDOS    equ     $0005

        org     $0100
start:
        jr      main                    ; $0100..$0101 (2 bytes) -> params at $0102
recnum: db      0, 0, 0                 ; $0102..$0104
rs:     dw      128                     ; $0105..$0106
cnt:    dw      1                       ; $0107..$0108
fillb:  db      $A5                     ; $0109
delflag: db     0                       ; $010A (M30 del_realloc; 0 = skip, pre-M30 shape)

main:
        ; --- M30 del_realloc: optionally DELETE ($13) a pre-seeded low-cluster
        ; file FIRST, freeing its chain, before the normal FOPEN/WRBLK below
        ; allocates. Skipped entirely (delflag=0) for every other case. ---
        ld      a, (delflag)
        or      a
        jr      z, main_open
        ld      de, delfcb
        ld      c, $13
        call    BDOS
main_open:
        ; --- FOPEN ($0F) the target file ---
        ld      de, fcb
        ld      c, $0F
        call    BDOS

        ; --- record size := rs (FCB+14..15) ---
        ld      hl, (rs)
        ld      (fcb + 14), hl

        ; --- SETDTA ($1A) -> our DTA buffer ---
        ld      de, dta
        ld      c, $1A
        call    BDOS

        ; --- fill the whole DTA span with the sentinel byte ---
        ; A multi-record WRBLK (cnt>1) reads cnt*RS consecutive bytes from DTA, so
        ; the source for records 1..cnt-1 must be deterministic too (not leftover
        ; RAM) or an ours-vs-stock byte compare would spuriously differ. A constant
        ; fill makes every 128-byte record identical, so any record's bytes are a
        ; valid differential regardless of start record. Covers up to 16 records.
        ld      a, (fillb)
        ld      hl, dta
        ld      bc, dta_len
fill:
        ld      (hl), a
        inc     hl
        dec     bc
        ld      d, a
        ld      a, b
        or      c
        ld      a, d
        jr      nz, fill

        ; --- random record RR := recnum (FCB+33..35) ---
        ld      a, (recnum)
        ld      (fcb + 33), a
        ld      a, (recnum + 1)
        ld      (fcb + 34), a
        ld      a, (recnum + 2)
        ld      (fcb + 35), a

        ; --- WRBLK ($26), HL = cnt ---
        ld      de, fcb
        ld      hl, (cnt)
        ld      c, $26
        call    BDOS

        ; --- FCLOSE ($10) : flush size/first-cluster + persist ---
        ld      de, fcb
        ld      c, $10
        call    BDOS

        ; --- terminate to DOS (system reset $00) ---
        ld      c, $00
        call    BDOS
        ret

; unopened FCB for "WRTEST  BIN"
fcb:
        db      0                       ; drive = default
        db      "WRTEST  "              ; 8-char name
        db      "BIN"                   ; 3-char ext
        ds      40 - 12, 0              ; EX..r2 (BDOS fills on FOPEN; RR set above)

; unopened FCB for "DELFILE BIN" (M30 del_realloc case only; harmless unused
; bytes when delflag=0)
delfcb:
        db      0                       ; drive = default
        db      "DELFILE "              ; 8-char name
        db      "BIN"                   ; 3-char ext
        ds      40 - 12, 0

dta_len equ     2048                    ; 16 records * 128 B (covers every case)
dta:
        ds      dta_len, 0
