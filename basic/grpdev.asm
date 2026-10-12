; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; grpdev.asm -- D-OPENGRP's main-side leaves: OPEN "GRP:"'s arm and pchar's
; GRP: sink (oodv_notout, its FOR-INPUT reject, is in files.asm). A FILE OF
; ITS OWN, included right after files.asm: inside files.asm the arms sat
; between oo_fail_* and the many `jr`s the device and cassette arms aim at
; them, and pushed those out of range one after another. They are reached
; only by `jp` (pchar's PRDEV dispatch, do_open's device dispatch).
; 🔁 It was included in the LOW region at first (2026-10-12), only because page
; 1 had 49 B against the ~79 B the device costs; D-EDCARVE gave page 1 284 B
; back the same day, and D-DIMRESERVE needed the low bytes, so it moved here.
; Nothing page-0-side calls it, so its region is free to choose.
; The drawing itself is zerobas-sub2's grpprt_tenant (sub2/grpprt.asm).
; Clean-room: own design; every behaviour here is a black-box measurement of
; the VG-8020 (TODO.md D-OPENGRP, scratchpad/opengrp*_probe.out). No disassembly,
; no reference ROM bytes read. See basic/PROVENANCE.md.

; oo_dev_grp -- OPEN "GRP:" (D-OPENGRP). A device channel like CRT:, whose
; PRINT # draws on the graphics screen (pchar's PRDEV 4 -> zerobas-sub2's
; grpprt_tenant). ONE AT A TIME: a second OPEN "GRP:" while one is open is
; `Bad file number`, 52, at that OPEN -- measured on the VG-8020 (round 5,
; `two`). The SCREEN mode is NOT checked here: the VG-8020 accepts the OPEN in
; SCREEN 0 and refuses at PRINT # (round 1). Clears GRP_HDR (RAM is garbage
; at power-on, and a header left armed would bend the first glyph).
oo_dev_grp:
                push    hl
                ld      hl,FCH_MODES
                ld      bc,16
                ld      a,GRP_MODE
                cpir                        ; Z: a GRP: channel is already open
                pop     hl
                jp      z,oo_fail_bfn
                ld      a,b                 ; B = 0 after a cpir that ran out
                ld      (GRP_HDR),a
                ld      a,GRP_MODE
                jp      oo_dev_open

; pch_grp -- D-OPENGRP: one byte to the GRP: channel. SCREEN 0 / 1 is `Illegal
; function call` HERE, at PRINT #, not at the OPEN -- measured on the VG-8020
; (rounds 1 and 5: SCREEN 0, SCREEN 1, and a SCREEN 2 -> SCREEN 0 switch after
; the OPEN). The drawing is zerobas-sub2's grpprt_tenant (sub2/grpprt.asm),
; byte in E. IX is guarded as pch_disk guards it (a CALSLT clobbers it, and
; pchar's contract is every register). Without sub2 (CF=1) nothing is drawn:
; both shipped machines carry it, and 3 B of `jp c` buys only a third-party
; machine config an error message.
pch_grp:
                ld      a,(SCRMOD)
                cp      2
                jp      c,gfx_err5          ; SCREEN 0/1 -> ERR 5
                ld      e,c
                push    ix
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUB2_IDX_GRPPRT
                call    subrom2_call
                pop     ix
                jp      pch_done
