; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D2TYPE.COM -- D-DOSLADDER rung D2 (TODO.md): what TYPE does. FOPEN COMMAND.COM,
; SEQREAD it record by record to the end, counting the records and summing every
; byte, then FCLOSE. Captured -- the CONTRACT only, so it can be compared byte for
; byte with the National CF-3300: FOPEN's A, the record count, the 16-bit byte sum,
; the final SEQREAD's A, FCLOSE's A, and the FCB's EX (+12), size (+16..19) and
; CR (+32). Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 BDOS functions. COMMAND.COM is
; data read through them, never decoded.
;
; Build: probes/disk/build_dosl_disk.py --prog d2type

                org     $0100

BDOS            equ     $0005

start:
                ld      de, buf
                ld      c, $1A                  ; SETDTA
                call    BDOS
                ld      de, fcb
                ld      c, $0F                  ; FOPEN
                call    BDOS
                ld      (cap+0), a
                or      a
                jr      nz, fin
rd_lp:
                ld      de, fcb
                ld      c, $14                  ; SEQREAD
                call    BDOS
                ld      (cap+5), a
                or      a
                jr      nz, rd_end
                ld      hl, (cap+1)
                inc     hl
                ld      (cap+1), hl             ; records
                ld      hl, buf
                ld      de, (cap+3)
                ld      b, 128
sum_lp:
                ld      a, e
                add     a, (hl)
                ld      e, a
                jr      nc, sum_nc
                inc     d
sum_nc:
                inc     hl
                djnz    sum_lp
                ld      (cap+3), de             ; the byte sum
                jr      rd_lp
rd_end:
                ld      de, fcb
                ld      c, $10                  ; FCLOSE
                call    BDOS
                ld      (cap+6), a
fin:
                ld      a, (fcb+12)
                ld      (cap+7), a              ; EX
                ld      hl, (fcb+16)
                ld      (cap+8), hl
                ld      hl, (fcb+18)
                ld      (cap+10), hl            ; size
                ld      a, (fcb+32)
                ld      (cap+12), a             ; CR
done:
                jr      done

fcb:            db      0, "COMMAND COM"
                ds      37 - 12, 0
buf:            ds      128, 0

; ---------------------------------------------------------------------------
; captured block $0400-$040F
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
cap:            ds      16, $00
