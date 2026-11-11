; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D-INITSLOT cartridge B (slot 2): INIT writes $A5 to $E000 (and returns).
; CLEAN-ROOM: 100% own code.
;
                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
init:           ld      a, $A5
                ld      ($E000), a
                ret
                ds      $8000 - $, $FF
