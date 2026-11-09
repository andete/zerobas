; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; AUXINX.COM -- D-ENTRYTIERS (TODO.md): BDOS $03 AUXIN, the last function the entry
; table (tools/entry_table.py) counted NOT MEASURED. Neither target has an AUX
; device, so the question is first WHETHER it returns -- a side that never reaches
; `done` is the answer -- then with what. Captured: the outward A only (+1),
; gated in bdos-acceptance. Self-loop at `done` -- the disk_probe_diff.py capture anchor.
;
; CLEAN-ROOM: 100% own code; the published MSX-DOS 1 function list (AUXIN: A = the
; character read). No kernel byte is read.
;
; Build: pasmo --bin auxinx.asm auxinx.com auxinx.sym

                org     $0100

BDOS            equ     $0005

start:
                ld      c, $03                  ; AUXIN
                call    BDOS
                ld      (regs+1), a             ; +1 A -- the contract only (D-ENTRYTIERS
                                                ; step 3: F differs, $42 / $44, outside it)
done:
                jr      done

                ds      $0400 - $, $00
regs:           ds      8, $EE                  ; captured block $0400-$0407
