; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; RNDFCB.COM -- D-RNDFCB (TODO.md): what does RDRND ($21) leave in the FCB?
; BDOSX3 and wrzer.asm disagreed on +15 after RDRND (a 3-record file: $03; a
; 21-record file: $00), so +12..15 and the cluster cache +28..31 are
; characterised over file sizes before any code changes.
;
; For N in 1, 3, 21, 128, 200 (records of 128 bytes): FMAKE "R<n>.DAT", RS := 128,
; WRBLK of N records from the DTA, FCLOSE; then FOPEN, RDRND record N-1 (the
; last) -> snapshot, RDRND record 0 -> snapshot. A snapshot is the RDRND's A then
; FCB bytes +12..+15 and +28..+35 (13 bytes); five files x two snapshots. The
; record size is NOT re-set after FOPEN, so what RDRND finds is FOPEN's.
; Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 function list. No kernel
; byte is read.
;
; Build: pasmo --bin rndfcb.asm rndfcb.com rndfcb.sym

                org     $0100

BDOS            equ     $0005

start:
                ld      hl, sizes
                ld      (sizep), hl
                ld      hl, snaps
                ld      (snapp), hl
file_loop:
                ld      hl, (sizep)
                ld      a, (hl)
                or      a
                jr      z, done
                ld      (nrec), a
                inc     hl
                ld      a, (hl)                 ; the name's digit character
                inc     hl
                ld      (sizep), hl
                ld      (fcb+2), a
                call    clear_fcb
                ld      de, dta
                ld      c, $1A                  ; SETDTA
                call    BDOS
                ld      de, fcb
                ld      c, $16                  ; FMAKE
                call    BDOS
                ld      hl, 128
                ld      (fcb+14), hl
                ld      a, (nrec)
                ld      l, a
                ld      h, 0
                ld      de, fcb
                ld      c, $26                  ; WRBLK, N records
                call    BDOS
                ld      de, fcb
                ld      c, $10                  ; FCLOSE
                call    BDOS
                call    clear_fcb
                ld      de, fcb
                ld      c, $0F                  ; FOPEN
                call    BDOS
                ld      a, (nrec)
                dec     a
                call    rdrnd_snap              ; the last record
                xor     a
                call    rdrnd_snap              ; record 0
                jr      file_loop
done:
                jr      done

; rdrnd_snap -- RR := A (r1..r3 = 0), RDRND, then append A and FCB +12..15,
; +28..35 to the snapshot table.
rdrnd_snap:
                ld      (fcb+33), a
                xor     a
                ld      (fcb+34), a
                ld      (fcb+35), a
                ld      (fcb+36), a
                ld      de, fcb
                ld      c, $21                  ; RDRND
                call    BDOS
                ld      de, (snapp)
                ld      (de), a
                inc     de
                ld      hl, fcb+12
                ld      bc, 4
                ldir
                ld      hl, fcb+28
                ld      bc, 8
                ldir
                ld      (snapp), de
                ret

; clear_fcb -- drive 0, keep the name (+1..11), zero +12..36
clear_fcb:
                xor     a
                ld      (fcb), a
                ld      hl, fcb+12
                ld      b, 25
cf_lp:
                ld      (hl), a
                inc     hl
                djnz    cf_lp
                ret

sizes:          db      1, '1', 3, '3', 21, '2', 128, '4', 200, '5', 0
nrec:           db      0
sizep:          dw      0
snapp:          dw      0
fcb:            db      0, "R0      ", "DAT"
                ds      37 - 12, 0

; ---------------------------------------------------------------------------
; captured block $0400-$0481: 10 snapshots x 13 bytes
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
snaps:          ds      10*13, $EE
                ds      $0500 - $, $00
dta:            ds      200*128, $3C            ; WRBLK's data ($0500-$6CFF)
