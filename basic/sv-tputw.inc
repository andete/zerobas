; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-tputw.inc -- tape_putword, the 16-bit LE word emitter used by the BSAVE tape header.
; ===========================================================================
; Clean-room: own design. Twelve instructions emitting a 16-bit little-endian
; word through the documented TAPOUT BIOS entry; nothing here is derived from a
; disassembly or byte-copy of any reference ROM. Basis: basic/PROVENANCE.md.
; ===========================================================================

; tape_putword — emit a 16-bit little-endian word stored at address HL via
; TAPOUT (low byte then high byte). TAPOUT clobbers every register, so the
; source address is held in TSV_PTR and reloaded for the high byte.
;   in:  HL = address of a 2-byte LE word in page-3 RAM.
;   out: CF set = error; both bytes emitted on success.
tape_putword:
                ld      (TSV_PTR),hl        ; save the word's address
                ld      a,(hl)              ; low byte
                call    TAPOUT
                ret     c
                ld      hl,(TSV_PTR)        ; reload (TAPOUT clobbered HL)
                inc     hl
                ld      a,(hl)              ; high byte
                call    TAPOUT
                ret                         ; CF from TAPOUT
