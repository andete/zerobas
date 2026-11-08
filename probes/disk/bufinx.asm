; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; BUFINX.COM -- D-ENTRYTIERS (TODO.md): BDOS $0A BUFIN, the last console function
; the entry table (tools/entry_table.py) counted NOT MEASURED. One call with a
; 10-character buffer; the harness types "AB" + Return after this program has
; loaded (disk_probe_diff.py --keys2 / --keys2-at, bdosx2.asm's way). Captured:
; the call's outward A / F / B / C / D / E / H / L and the buffer itself (+0 the
; max, +1 the count, +2.. the characters, the rest pre-filled $EE so an untouched
; byte shows). Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 function list (BUFIN: DE =
; the buffer, +0 = the max length; on return +1 = the count). No kernel byte is read.
;
; Build: pasmo --bin bufinx.asm bufinx.com bufinx.sym

                org     $0100

BDOS            equ     $0005

start:
                ld      de, buf
                ld      c, $0A                  ; BUFIN
                call    BDOS
                ld      (regs+6), hl
                ld      (regs+4), de
                ld      (regs+2), bc
                push    af
                pop     hl
                ld      (regs+0), hl            ; +0 F, +1 A (little-endian AF)
done:
                jr      done

; ---------------------------------------------------------------------------
; captured block $0400-$041F: the registers (8 B), then the buffer (24 B)
; ---------------------------------------------------------------------------
                ds      $0400 - $, $00
regs:           ds      8, $EE
buf:            db      10                      ; +0 the max length
                ds      23, $EE                 ; +1 the count, +2.. the characters
