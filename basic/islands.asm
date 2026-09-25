; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; islands.asm -- BASIC code placed in C-BIOS's own alignment padding.
; ===========================================================================
; MAKING ROOM IN MAIN, lever B (TODO.md; Joost 2026-09-25: *"We need to come up
; with other ways to make room. Clearly reference fits everything in 32k"*, then
; *"B first, then A"*). C-BIOS pads to pinned addresses with `ds`; those runs
; are zero in OUR merged image, in the SAME slot as main, and always mapped with
; it. Each island below is one such run, confirmed in the C-BIOS source:
;   $1ACF..$1BBE  src/main.asm:3091 `ds $1bbf - $` -- pad up to the font
;   $0160..$01FF  src/main.asm:620  `ds $0200 - $` -- pad up to jump_table
; tools/split_islands.py cuts these bytes out of pasmo's image and
; tools/build_mainrom.py overlays them, REFUSING any byte outside those ranges or
; onto a non-zero C-BIOS byte.
; CLEAN-ROOM: original code (moved unchanged from basic/initext.asm). The two
; ranges come from the C-BIOS SOURCE -- a BSD-2 peer implementation this project
; already patches (cbios-repack/, docs/allowed-sources.md grade B) -- never from
; a reference ROM. No disassembly.
; ⚠️ WHAT MAY LIVE HERE: main code/data entered only by call/jp (no fallthrough
; in or out, no `jr` across the gap -- pasmo refuses those loudly), not imported
; by the sub-ROM or disk.rom ABIs, and not needed while page 0 is switched away
; from the main slot (a sub-ROM PAGE-0 tenant cannot reach it).
; ===========================================================================

; --- island 1: before the font ($1ACF..$1BBE, 240 B usable) -----------------
                org     $1ACF

; try_init_slot -- boot-time: does the slot in A carry an "AB" ROM, and if so
; CALSLT its INIT. From basic/initext.asm, unchanged. Better here than in page 1:
; the CALSLT into the cartridge's page-1 INIT runs from page 0, which the switch
; never touches.
try_init_slot:
                ld      (SCAN_SLOT),a
                ld      hl,$4000
                call    rdslt_scan
                cp      'A'
                ret     nz
                ld      hl,$4001
                call    rdslt_scan
                cp      'B'
                ret     nz
                ld      hl,$4002
                call    rdslt_scan
                ld      (SCAN_INIT),a       ; INIT entry, low byte
                ld      hl,$4003
                call    rdslt_scan
                ld      (SCAN_INIT+1),a     ; INIT entry, high byte
                ld      hl,(SCAN_INIT)
                ld      a,h
                or      l
                ret     z                   ; INIT vector $0000 -> nothing to call
                ; inter-slot call to the extension ROM's INIT (it installs its
                ; hooks / SYSTEM vector and returns).
                ld      a,(SCAN_SLOT)
                ld      (SCAN_IY+1),a       ; CALSLT reads the slot from IYh
                ld      iy,(SCAN_IY)
                ld      ix,(SCAN_INIT)
                call    CALSLT
                ; Record this external AB ROM's slot id for cross-slot BDOS calls
                ; from BLOAD (it CALSLTs the disk ROM's bdos_entry). On the
                ; combined machine the disk ROM is the only external AB ROM the
                ; scan reaches, so its slot is unambiguous; a multi-ROM setup
                ; would need per-ROM tracking (last-one-wins here — documented
                ; limitation, PROVENANCE.md §disk-ROM slot capture).
                ld      a,(SCAN_SLOT)
                ld      (DISKSLOT),a
                ld      a,1
                ld      (DISKSLOT_OK),a
                ret

; rdslt_scan: A = RDSLT(slot=(SCAN_SLOT), addr=HL). RDSLT preserves HL, so the
; caller sets HL; the slot id is reloaded from RAM each call (RDSLT clobbers it).

    IF $ > $1BBF
                db      ISLAND_BEFORE_FONT_OVERRAN_1BBF__IT_WOULD_OVERWRITE_THE_FONT
    ENDIF
