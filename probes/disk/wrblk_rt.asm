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
;
; CLEAN-ROOM: our own program; calls the published BDOS $0F/$1A/$26/$10/$00
; contract entries only; the CF-3300 is a black box we run + whose OUTPUT DISK we
; read (never its ROM code).

BDOS    equ     $0005

        org     $0100
start:
        jr      main                    ; $0100..$0101 (2 bytes) -> params at $0102
recnum: db      0, 0, 0                 ; $0102..$0104
rs:     dw      128                     ; $0105..$0106
cnt:    dw      1                       ; $0107..$0108
fillb:  db      $A5                     ; $0109

main:
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

        ; --- fill 128-byte DTA with the sentinel byte ---
        ld      a, (fillb)
        ld      hl, dta
        ld      b, 128
fill:
        ld      (hl), a
        inc     hl
        djnz    fill

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

dta:
        ds      128, 0
