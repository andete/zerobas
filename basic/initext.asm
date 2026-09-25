; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; initext.asm — initialise extension ROMs (e.g. zerobas-disk) from zerobas's
; own INIT, before entering the REPL.
;
; WHY THIS EXISTS. On the combined machine, C-BIOS's boot scan reaches
; zerobas-BASIC (slot 0, page 1) before the disk ROM (slot 3-1). zerobas's INIT
; enters the REPL and never returns, so C-BIOS never scans the remaining slots,
; and the disk ROM's INIT — which installs its DSKIO/PHYD hooks and the
; SYSTEM/BDOS vector — never runs. (Observed in openMSX: after boot the disk
; hooks + $F37D are still at C-BIOS defaults; see disk/TODO.md.) To fix this
; without modifying C-BIOS, zerobas's INIT performs the rest of that boot scan
; itself: for every primary slot *after* its own, and every expanded subslot, it
; looks for the standard "AB" cartridge header at $4000 and CALSLTs the INIT
; entry (the word at $4002) — exactly what the BIOS boot scan would have done. A
; standard extension/disk INIT installs its hooks and RETs.
;
; Scanning only primaries after our own matches the BIOS scan order: slots
; *before* us were already initialised by C-BIOS, and our own non-returning INIT
; is therefore never re-entered (which would recurse / hang). Limitation
; (own-design; see PROVENANCE.md): an extension ROM sharing zerobas's own
; (expanded) primary in a different subslot is not reached — not the case for the
; slot-3-1 disk reference, where zerobas is the slot-0 primary.
;
; SOURCES (allowed): RDSLT $000C, CALSLT $001C — MSX2 Technical Handbook / MSX
; Assembly Page BIOS call list. EXPTBL $FCC1 (expanded-slot flags) — MSX2 TH work
; area / C-BIOS. Port $A8 primary-slot-select (page-1 field = bits 3-2) and the
; slot-id byte format (bit7 expanded / bits3-2 secondary / bits1-0 primary) —
; MSX2 TH slot architecture. "AB" header + INIT word at $4002 — MSX2 TH cartridge
; ROM format (the same header zerobas itself carries).

; init_ext_roms: run the remaining boot-scan INITs. Called from `init` just
; before `repl`. Clobbers AF/BC/DE/HL/IX/IY (we are pre-REPL, nothing live).
; init_ext_roms + rdslt_scan -- MOVED to basic/islands.asm (MAKING ROOM lever B,
; 2026-09-25) beside try_init_slot: the whole boot-time extension-ROM scan now
; lives in C-BIOS's padding before the font. Still `call init_ext_roms` from
; basic/interp.asm and `call rdslt_scan` from basic/subrom-boot.asm.

; NOTE (subrom S2b): the sub-ROM discovery recorder (try_sub_slot) and the
; dispatch helper/absence path (subrom_call / subrom_absent_error) live in
; basic/subromcall.asm, in the PAGE-0 low region freed by evicting the float
; formatter — NOT here. init_ext_roms is in page 1, whose tail is nearly full;
; keeping only the two tiny hooks above (the SUBSLOT_OK clear + the
; `call try_sub_slot`) in page 1 leaves the ~90 B of routine bodies in the
; freed page-0 space. See main.asm's include order and spec §WAVE-1 AMENDMENT.
