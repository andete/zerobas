; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; SETRND.COM — clean single-shot BDOS $24 SETRND characterisation exerciser
; (disk/docs/tier2-m32-setrnd-char.md). Runs identically on OURS (C-BIOS +
; zerobas-disk) and STOCK (National CF-3300) via the real BDOS at $0005, then
; self-loops at `done`.
;
; Purpose (BLACK-BOX): $24 SETRND is supposed to write the FCB random-record
; field (FCB+33..35) from the CURRENT sequential position. We do NOT know stock's
; exact formula (the earlier "FCB+33 = 1 constant" note was a single data point),
; so this exerciser drives the sequential position to a known place — FOPEN, then
; K sequential reads (each advances the current-record) — calls $24, and snapshots
; the FCB position fields so the runner can dump the stock RESULT and derive the
; formula empirically. Stock ROM code is never read/disassembled; only the RAM
; result (the FCB bytes stock's SETRND wrote) is compared.
;
; A param block at the FIXED offset $0102 is patched by the Python runner per case:
;   $0102        magic   = $5A  (constant arm signature: "program loaded")
;   $0103        nreads  = number of RDSEQ ($14) calls before $24 (0..255)
;   $0104..$0105 rs      = record size to store in FCB+14..15 before $24
;                         (0 => leave FCB+14 as FOPEN set it)
;
; CLEAN-ROOM: our own program; calls the published BDOS $0F/$1A/$14/$24 contract
; entries only; the CF-3300 is a black box we run + whose RAM RESULT we read
; (never its ROM code).

BDOS    equ     $0005

        org     $0100
start:
        jr      main                    ; $0100..$0101 -> param block at $0102
magic:  db      $5A                     ; $0102  constant arm signature
nreads: db      3                       ; $0103
rs:     dw      0                       ; $0104..$0105
dosr:   db      1                       ; $0106  1 => call $24 SETRND, 0 => skip (isolate)

main:
        ; --- fill the FCB: zero 37 bytes (drive=0 => default drive), copy the
        ; 11-byte 8.3 name into FCB+1 (without this FOPEN fails -> no position). ---
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

        ; --- FOPEN ($0F) ---
        ld      de, fcb
        ld      c, $0F
        call    BDOS

        ; --- SETDTA ($1A) -> scratch sink (the read bytes are discarded; only the
        ; FCB position side effect matters) ---
        ld      de, scratch
        ld      c, $1A
        call    BDOS

        ; --- K x RDSEQ ($14): advance the current sequential position ---
        ld      a, (nreads)
        or      a
        jr      z, afterreads
        ld      b, a
rdloop:
        push    bc
        ld      de, fcb
        ld      c, $14
        call    BDOS
        pop     bc
        djnz    rdloop
afterreads:

        ; --- optionally set record size FCB+14..15 := rs (0 => leave as-is) ---
        ld      hl, (rs)
        ld      a, h
        or      l
        jr      z, dosetrnd
        ld      (fcb+14), hl
dosetrnd:

        ; --- $24 SETRND: writes FCB+33..35 from the current position (skippable
        ; via dosr=0 to isolate whether $24 or FOPEN/RDSEQ wrote the value) ---
        ld      a, (dosr)
        or      a
        jr      z, snapshot
        ld      de, fcb
        ld      c, $24
        call    BDOS
snapshot:

        ; --- snapshot the FCB position fields into fixed cells (stable capture
        ; window regardless of assemble). We ALSO capture the raw FCB directly,
        ; but these give a clean labelled readout. ---
        ld      a, (fcb+12)             ; EX  (extent low)
        ld      (res_ex), a
        ld      a, (fcb+14)             ; S2  (extent high / record-size low)
        ld      (res_s2), a
        ld      a, (fcb+32)             ; CR  (current record)
        ld      (res_cr), a
        ld      hl, fcb+33              ; RR  (random record r0/r1/r2)
        ld      de, res_rr
        ld      bc, 3
        ldir

done:
        jr      done                    ; self-loop; capture --at done --arm-check-val 0x5A

; ---------------------------------------------------------------------------
; fixed absolute layout so the runner's `capture --mem` window is stable.
; ---------------------------------------------------------------------------
fcb_name:       db      "RDTEST  BIN"           ; 8.3, space-padded (11 bytes)

                ds      $0300 - $, $00
fcb:            ds      37                      ; $0300-$0324 (EX=+12 S2=+14 CR=+32 RR=+33..35)

                ds      $0340 - $, $00
res_ex:         ds      1                       ; $0340  FCB+12 EX  after $24
res_s2:         ds      1                       ; $0341  FCB+14 S2  after $24
res_cr:         ds      1                       ; $0342  FCB+32 CR  after $24
res_rr:         ds      3                       ; $0343-$0345  FCB+33..35 RR after $24

                ds      $0380 - $, $00
scratch:        ds      128                     ; $0380-$03FF: RDSEQ sink (discarded)
