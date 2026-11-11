; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
;
; D-INITSLOT cartridge A (slot 1): INIT writes $5A to $E001 and RETURNS, so the BIOS's
; cartridge search must go on to slot 2 -- with the slot ID it kept across the call.
; CLEAN-ROOM: 100% own code.
;
                org     $4000
                db      "AB"
                dw      init, 0, 0, 0
                ds      6, 0
init:           ld      a, $5A
                ld      ($E001), a
                ret                     ; INIT returns: the search must go on
                ds      $8000 - $, $FF
