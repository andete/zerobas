; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; grpdev.asm -- D-OPENGRP's main-side leaf: pchar's GRP: sink. (OPEN "GRP:"'s
; arm and its FOR-INPUT reject are sub2/filestmt.asm's since D-P0CB slice C1.)
; A FILE OF ITS OWN, included right after files.asm: inside files.asm the arms
; sat between oo_fail_* and the many `jr`s the device and cassette arms aimed at
; them, and pushed those out of range one after another. It is reached only by
; `jp` (pchar's PRDEV dispatch).
; 🔁 It was included in the LOW region at first (2026-10-12), only because page
; 1 had 49 B against the ~79 B the device costs; D-EDCARVE gave page 1 284 B
; back the same day, and D-DIMRESERVE needed the low bytes, so it moved here.
; Nothing page-0-side calls it, so its region is free to choose.
; The drawing itself is zerobas-sub2's grpprt_tenant (sub2/grpprt.asm).
; Clean-room: own design; every behaviour here is a black-box measurement of
; the VG-8020 (TODO.md D-OPENGRP, scratchpad/opengrp*_probe.out). No disassembly,
; no reference ROM bytes read. See basic/PROVENANCE.md.

; oo_dev_grp -- OPEN "GRP:"'s arm: moved to sub2/filestmt.asm (fo_dev_grp) with
; the rest of OPEN, D-P0CB slice C1 (2026-10-21). Its measured rules (one GRP:
; channel at a time, 52; no SCREEN check at the OPEN) travelled with it.

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
