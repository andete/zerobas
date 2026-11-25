; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause
;
; CLAIMER -- a test cartridge that claims 16 bytes of RAM in its INIT, as a cartridge with its own work area does:
; HIMEM ($FC4A, published) := HIMEM - 16. Scanned before the disk ROM (an external slot), it makes the disk ROM's
; INIT see a HIMEM that is not the untouched $F380 -- the case D-DISKROMHOST step 4(d)'s guard is for.
; CLEAN-ROOM: 100% own code; only the published HIMEM cell.
HIMEM           equ     $FC4A
                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
init:
                ld      hl, (HIMEM)
                ld      de, -16
                add     hl, de
                ld      (HIMEM), hl
                ret
