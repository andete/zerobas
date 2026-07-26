; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sv-tne.inc -- tape_name_emit, the 6-byte cassette filename emitter.
; ===========================================================================
; Shared, byte-identically, between the RESIDENT main ROM (basic/save.asm, where
; it is included at its ORIGINAL POSITION in BOTH builds, so no emitted byte
; moves) and the sub-ROM PAGE-1 SAVE tenant (sub/save.asm), which needs its own
; SUB-LOCAL copy because the resident one is switched out while a page-1 tenant
; runs. A duplicate in the sub-ROM costs no main page-1 bytes.
;
; This is a COPY, not an eviction: every routine here keeps a resident caller
; (do_save's ASCII path for disk_write_begin/disk_write_end; cas_write_ea_header,
; which files.asm's OPEN"CAS:" calls, for tape_name_emit).
;
; CLEAN-ROOM: our own code, moved. See basic/PROVENANCE.md.
; ===========================================================================

; tape_name_emit — emit the 6 bytes of TSV_NAME via TAPOUT.
; in:  TSV_NAME[0..5] = the name to emit.
; out: CF = set if TAPOUT reported an error; else CF = clear.
; TAPOUT clobbers every register; the loop counter is kept in TSV_CNT.
tape_name_emit:
                ld      a,6
                ld      (TSV_CNT),a
                ld      hl,TSV_NAME
                ld      (TSV_PTR),hl        ; reuse TSV_PTR as walk pointer
tne_loop:
                ld      hl,(TSV_PTR)
                ld      a,(hl)
                call    TAPOUT
                ret     c                   ; propagate error
                ld      hl,(TSV_PTR)
                inc     hl
                ld      (TSV_PTR),hl
                ld      a,(TSV_CNT)
                dec     a
                ld      (TSV_CNT),a
                jr      nz,tne_loop
                or      a                   ; CF = 0 (success)
                ret
