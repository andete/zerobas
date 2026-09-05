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
                ; 💰 D-PEEPINC (2026-09-05): `ld hl,nn / dec (hl)` is 4 B where
                ; `ld a,(nn) / dec a / ld (nn),a` is 7 -- and this is the ONLY
                ; site of that shape in the whole tree where HL is free AND the
                ; bytes land in MAIN PAGE 1. The other four main-tree sites
                ; (basic/screen.asm, basic/traps.asm x3) each already carry a
                ; comment saying HL is live there; the other twelve are in
                ; sub-only bodies, where a byte is not a carve.
                ; ⚠️ HL IS DEAD HERE and that is READ, not assumed: `ld (TSV_PTR),hl`
                ; two instructions up has already stored it, and the loop top
                ; reloads it with `ld hl,(TSV_PTR)`.
                ; ⚠️ A AND Zf ON RETURN CHANGE, AND ALL THREE CALLERS WERE CHECKED.
                ; The old form left A = 0 on the fall-through; this one leaves
                ; whatever the last TAPOUT byte was. basic/save.asm:354,
                ; basic/sv-tsb.inc:37 and basic/sv-bsvcas.inc:43 each test CF
                ; alone (`ret c` / `jp c,sv_load_error`) and go straight into
                ; `call TAPOOF`. `or a` below still clears CF, which is the
                ; documented half of the contract.
                ld      hl,TSV_CNT
                dec     (hl)
                jr      nz,tne_loop
                or      a                   ; CF = 0 (success)
                ret
