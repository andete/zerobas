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


; init_ext_roms -- the boot-time extension-ROM scan (from basic/initext.asm,
; unchanged): every primary/secondary slot after ours, CALSLT each "AB" ROM's
; INIT via try_init_slot above. Runs once, with interrupts off, at power-on.
init_ext_roms:
                xor     a
                ld      (DISKSLOT_OK),a     ; no disk-ROM slot recorded yet
                ld      (SUBSLOT_OK),a      ; no zerobas-sub slot recorded yet (subrom S2b)
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
                call    try_sub_slot        ; also record a CD sub-ROM here (3-2; subrom S2b)
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
                ld      hl,SCAN_PRIM
                inc     (hl)                ; D-PEEPHOLE: -3 B (7 B -> 4 B)
                jr      ier_ploop
ier_done:
                call    sub_int_install     ; install the page-0 EI trampoline if a
                                            ; sub-ROM was recorded (subrom trampoline)
                call    play_install        ; install the PLAY servicer H.TIMI seam
                                            ; (audio Slice 3; H.TIMI is C9-free here)
    IF TRAPS_T3
                call    zkey_install        ; install the KEY-trap fn-key hook (traps T3;
                                            ; H_ZKEY is C9-filled by C-BIOS's hook init)
    ENDIF
                call    trap_init           ; interrupt-traps T1: zero the ZTRAP table so
                                            ; garbage boot RAM can't look like an armed
                                            ; trap. Under the boot DI (below); the H.TIMI
                                            ; poll installed just above fast-outs anyway
                                            ; until TRAPENA is set. (traps.asm)
                ei
                ret

; try_init_slot: if slot A carries an "AB" header, CALSLT its INIT entry.
; in: A = slot id. The slot id and INIT address live in RAM (SCAN_SLOT /
; SCAN_INIT) because RDSLT destroys AF/BC/DE between reads.
; try_init_slot -- MOVED to basic/islands.asm (MAKING ROOM lever B, 2026-09-25):
; it now lives in C-BIOS's own padding before the font, in page 0, and is still
; reached by the two `call try_init_slot` sites above.

; rdslt_scan: A = RDSLT(slot=(SCAN_SLOT), addr=HL). RDSLT preserves HL, so the
; caller sets HL; the slot id is reloaded from RAM each call (RDSLT clobbers it).
rdslt_scan:
                ld      a,(SCAN_SLOT)
                jp      RDSLT               ; tail call: RDSLT's RET returns to caller

    IF $ > $1BBF
                db      ISLAND_BEFORE_FONT_OVERRAN_1BBF__IT_WOULD_OVERWRITE_THE_FONT
    ENDIF

; --- island 2: before C-BIOS's internal jump table ($0160..$01FF, 160 B) -----
                org     $0160

; chrgtr -- RST 10h, the PUBLISHED MSX BIOS CHRGTR (MAKING ROOM lever A, Joost
; 2026-09-25 "B first, then A"; docs: the MSX2 Technical Handbook's BIOS table).
; Contract: calls H.CHRG, then INC HL and skips spaces; A = the character at HL;
; Z set at end of statement (00 or ':'); CF set on a digit '0'..'9'; else NZ/NC.
; 🔴 C-BIOS's own routine behind $0010 is NOT this contract: it reads (HL) and
; THEN increments, returning HL PAST the character. Ours is the published one,
; and it is also exactly zerobas's `inc_skip` plus the flags -- so the 50 internal
; `call inc_skip` sites (none reads Z/C before setting them; scratchpad/
; rst_scout.py) become 1-byte `rst $10`, and USR machine code gets a real CHRGTR.
chrgtr:
                call    H_CHRG              ; the published hook (a RET by default)
cgt_lp:
                inc     hl
                ld      a,(hl)
                cp      ' '
                jr      z,cgt_lp
                cp      ':'                 ; end of statement -> Z
                ret     z
                or      a                   ; end of line -> Z (and NC)
                ret     z
                cp      '0'
                jr      c,cgt_nd
                cp      '9'+1               ; a digit -> CF
                ret     c
cgt_nd:
                or      a                   ; anything else: NZ, NC
                ret

; outdo -- RST 18h, the PUBLISHED MSX BIOS OUTDO (MAKING ROOM lever A, step 3).
; Contract: calls H.OUTD, then outputs A to the CURRENT output channel; every
; register preserved. zerobas's `pchar` already IS that (screen, file, LPT:,
; CRT: or CAS: by PRDEST/PRDEV, all four pairs and the flags kept), so the 13
; `call pchar` sites become 1-byte `rst $18`.
; 🔴 C-BIOS's own $0018 only calls H.OUTD, and its boot points H.OUTD at
; `chput` -- the hook IS its output. Calling the hook AND pchar would print every
; character twice, so the merge also patches C-BIOS's boot to leave H.OUTD a
; RET (`ld a,$c3` -> `ld a,$c9` at $1037, below), as on the published machine.
; A is saved around the hook as C-BIOS saves it: a hook may clobber it.
outdo:
                push    af
                call    H_OUTD              ; the published hook (a RET by default)
                pop     af
                jp      pchar

; ttypos_col -- TTYPOS as the reference keeps it (D-ADDR29 N set, 2026-09-25).
; C-BIOS's CHPUT ends `ld a,(CSRX) / ld (TTYPOS),a`, a 1-BASED cursor mirror;
; the VG-8020's TTYPOS is BASIC's 0-BASED print column (scratchpad/
; nset_probe.py: PRINT"ABC"; -> 3 there, 4 here). The merge replaces only the
; `ld a,(CSRX)` at $11CF with a call to this, and C-BIOS's own store that
; follows it writes the corrected A. chput_exit pops AF, so flags are free.
ttypos_col:
                ld      a,(CSRX)
                dec     a
                ret

    IF $ > $0200
                db      ISLAND_BEFORE_JUMPTABLE_OVERRAN_0200__IT_WOULD_OVERWRITE_CBIOS
    ENDIF

; --- the RST 10h vector: $0010 `jp chrgtr` (was C-BIOS's `jp $10FF`) ---------
; tools/build_mainrom.py PATCH_RANGES allows exactly these 3 bytes, and only
; while the base still holds C-BIOS's `C3 FF 10`.
                org     $0010
                jp      chrgtr

; --- the RST 18h vector: $0018 `jp outdo` (was C-BIOS's `jp $111B`) ---------
                org     $0018
                jp      outdo

; --- C-BIOS's CHPUT stores CSRX-1 into TTYPOS, not CSRX -----------------------
; $11CF is C-BIOS's `ld a,(CSRX)` just before `ld (TTYPOS),a` (src/chput.asm,
; "CSRX -> TTYPOS"). PATCH_RANGES refuses unless it reads 3A DD F3.
                org     $11CF
cbios_chput_ttypos:                         ; a root: C-BIOS enters it (PATCH_ROOTS)
                call    ttypos_col

; --- C-BIOS's boot leaves H.OUTD a RET, not `jp chput` -----------------------
; $1037 is C-BIOS's `ld a,$c3` before `ld (H_OUTD),a` (src/main.asm, "set up
; hook"); only its operand byte changes. PATCH_RANGES refuses unless it is $C3.
                org     $1038
                db      $C9
