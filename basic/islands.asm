; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; islands.asm -- BASIC code placed in C-BIOS's own alignment padding.
; ===========================================================================
; MAKING ROOM IN MAIN, lever B (TODO.md; Joost 2026-09-25: *"We need to come up
; with other ways to make room. Clearly reference fits everything in 32k"*, then
; *"B first, then A"*). C-BIOS pads to pinned addresses with `ds`; those runs
; are zero in OUR merged image, in the SAME slot as main, and always mapped with
; it. Each island below is one such run, confirmed in the C-BIOS source:
;   $1ADB..$1BBE  src/main.asm:3091 `ds $1bbf - $` -- pad up to the font
;                 ($1ACF until cbios-repack patch #4, D-HOMEKEY, added 12 bytes
;                 to C-BIOS's key_ascii before it: the pad now starts 12 later)
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

; --- island 1: before the font ($1ADB..$1BBE, 228 B usable) -----------------
                org     $1ADB

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

; --- D-ISLDATA2 (2026-10-03): five pure-DATA blocks, 58 B, into the font island --
; Same rules as the $0160 block: absolute `ld` readers only. `rn_in` became an
; equ alias of in_msg in basic/program.asm (both were " in ",0).
rn_undefined:   db      "Undefined line ",0
fmt_menu_text:  db      "1=360k 2=720k? ",0
tkf_ref32767:
                db      3,2,7,6,7           ; signed 16-bit ceiling
tkf_ref65535:
                db      6,5,5,3,5           ; unsigned 16-bit ceiling
tkf_ref32768:
                db      3,2,7,6,8           ; negative magnitude ceiling (-32768)
in_msg:         db      " in ",0
brk_msg:        db      "Break",0           ; repack: " in " moved into print_in_lineno

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

; --- D-ISLDATA2 (2026-10-03): six more pure-DATA blocks, 61 B, to the brim --
; Each is read by exactly the absolute `ld hl/de,<label>` sites its source file
; still carries; none is a `jr` target, none is fallen into, nothing in sub/ or
; disk/ names any of them, and no test decodes them by image offset. Order here
; is free. The `IF $ > $0200` guard below is what refuses an overrun.
; The precedence table: LOOSEST first, `db token, dw leaf`, $00-terminated.
; EQV sits looser than XOR only because something had to; the two are measurably
; indistinguishable (see the header), so this is a free choice, not a claim.
logtab:
                db      IMP_TOKEN
                dw      lg_imp
                db      EQV_TOKEN
                dw      lg_eqv
                db      XOR_TOKEN
                dw      lg_xor
                db      OR_TOKEN
                dw      lg_or
                db      AND_TOKEN
                dw      lg_and
                db      0                   ; terminator -> drop to ev_not
; The single-numeric-argument $FF selectors, for the cpir set test above. Order is
; free. Repack-only, like the scan that reads it.
ev_ff_argtab:
                db      PEEK_TOKEN          ; $97
                db      VPEEK_TOKEN         ; $98
                db      INP_TOKEN           ; $90
                db      EOF_TOKEN           ; $AB
                db      LOF_TOKEN           ; $AD
                db      LOC_TOKEN           ; $AC  (D-LOC)
                db      DSKF_TOKEN          ; $A6
                db      POS_TOKEN           ; $91  (cursor cluster; arg DISCARDED)
                db      LPOS_TOKEN          ; $9C  (D-LPTVERB; arg DISCARDED too)
    IF I1_RESIDENT
                db      STICK_TOKEN         ; $A2  (input devices, slice I1)
                db      STRIG_TOKEN         ; $A3
    ENDIF
    IF I2_RESIDENT
                db      PDL_TOKEN           ; $A4  (input devices, slice I2)
                db      PAD_TOKEN           ; $A5
    ENDIF
ev_ff_argtab_len equ    $ - ev_ff_argtab
; --- evmc_total_tab: <selector token>, <low byte of the sub-ROM entry> ------
; The five rows carry what used to be five stub headers. All are COMPUTE-ONLY
; tenants (they leave FAC correct but touch neither FACTYP nor DE), so
; evmc_dispatch does the shared FACTYP:=8 + flt_to_int16 refresh for all of them.
evmc_total_tab:
                db      ATN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ATN) & $FF
                db      SIN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SIN) & $FF
                db      COS_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_COS) & $FF
                db      TAN_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_TAN) & $FF
                ; RND's argument VALUE is read by fp_rnd itself (ignored when
                ; positive, consumed as mant14 when negative) -- nothing here
                ; interprets it, so RND collapses with the other four.
                db      RND_TOKEN, (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_RND) & $FF
; --- autoexec_name: the upcased 11-byte 8.3 name we probe for on cold start ---
; "AUTOEXEC" (8) + "BAS" (3) = exactly 11 non-space characters -- no padding
; needed (see disk/docs/autoexec-bas-spec.md §3 point 2).
autoexec_name:  db      "AUTOEXECBAS"
fmt_name:       db      "FORMAT"
prompt_text:
                db      "ZB",13,10,0

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
