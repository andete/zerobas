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
init_ext_roms:
                xor     a
                ld      (DISKSLOT_OK),a     ; no disk-ROM slot recorded yet
    IF ROM_BASE < $4000
                ld      (SUBSLOT_OK),a      ; no zerobas-sub slot recorded yet (subrom S2b)
    ENDIF
                di                          ; slot switching must be uninterrupted
                in      a,(PSLTREG)         ; primary slot select register
                rrca
                rrca
                and     $03                 ; A = our page-1 primary slot
                inc     a                   ; begin one past ourselves (scan order)
                ld      (SCAN_PRIM),a
ier_ploop:
                ld      a,(SCAN_PRIM)
                cp      4
                jr      nc,ier_done         ; primaries (mine+1)..3 all scanned
                ; expanded primary?  EXPTBL[prim] bit 7
                ld      hl,EXPTBL
                ld      e,a
                ld      d,0
                add     hl,de
                bit     7,(hl)
                jr      z,ier_single
                ; expanded: scan secondaries 0..3
                ld      b,0                 ; B = secondary slot
ier_sloop:
                ld      a,(SCAN_PRIM)
                ld      c,a                 ; C = primary
                ld      a,b
                add     a,a
                add     a,a                 ; secondary << 2  (into bits 3-2)
                or      c                   ; | primary
                or      $80                 ; expanded-slot flag
                push    bc                  ; try_init_slot / CALSLT clobber BC
                call    try_init_slot
    IF ROM_BASE < $4000
                call    try_sub_slot        ; also record a CD sub-ROM here (3-2; subrom S2b)
    ENDIF
                pop     bc
                inc     b
                ld      a,b
                cp      4
                jr      c,ier_sloop
                jr      ier_pnext
ier_single:
                ld      a,(SCAN_PRIM)       ; slot id = primary (no expanded flag)
                call    try_init_slot
ier_pnext:
                ld      a,(SCAN_PRIM)
                inc     a
                ld      (SCAN_PRIM),a
                jr      ier_ploop
ier_done:
    IF ROM_BASE < $4000
                call    sub_int_install     ; install the page-0 EI trampoline if a
                                            ; sub-ROM was recorded (subrom trampoline)
                call    play_install        ; install the PLAY servicer H.TIMI seam
                                            ; (audio Slice 3; H.TIMI is C9-free here)
                ; interrupt-traps T1: `call trap_init` goes here once the page-1 layout
                ; bug is fixed (see docs/traps-t1-wiring-blocker.md).
    ENDIF
                ei
                ret

; try_init_slot: if slot A carries an "AB" header, CALSLT its INIT entry.
; in: A = slot id. The slot id and INIT address live in RAM (SCAN_SLOT /
; SCAN_INIT) because RDSLT destroys AF/BC/DE between reads.
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
rdslt_scan:
                ld      a,(SCAN_SLOT)
                jp      RDSLT               ; tail call: RDSLT's RET returns to caller

; NOTE (subrom S2b): the sub-ROM discovery recorder (try_sub_slot) and the
; dispatch helper/absence path (subrom_call / subrom_absent_error) live in
; basic/subromcall.asm, in the PAGE-0 low region freed by evicting the float
; formatter — NOT here. init_ext_roms is in page 1, whose tail is nearly full;
; keeping only the two tiny hooks above (the SUBSLOT_OK clear + the
; `call try_sub_slot`) in page 1 leaves the ~90 B of routine bodies in the
; freed page-0 space. See main.asm's include order and spec §WAVE-1 AMENDMENT.
