; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; islands.asm -- BASIC code placed in C-BIOS's own alignment padding.
; ===========================================================================
; MAKING ROOM IN MAIN, lever B (TODO.md; Joost 2026-09-25: *"We need to come up
; with other ways to make room. Clearly reference fits everything in 32k"*, then
; *"B first, then A"*). C-BIOS pads to pinned addresses with `ds`; those runs
; are zero in OUR merged image, in the SAME slot as main, and always mapped with
; it. Each island below is one such run, confirmed in the C-BIOS source:
;   $1AF5..$1BBE  src/main.asm:3091 `ds $1bbf - $` -- pad up to the font
;                 (was $1AF2 until cbios-repack patch #7, D-LINTTBWRAP, 2026-10-06)
;                 (was $1ADB until cbios-repack patch #6, D-CTRLKEYS, 2026-10-05)
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

; --- island 1: before the font ($1AF5..$1BBE, 202 B usable) -----------------
; D-LINTTBWRAP (2026-10-06): cbios-repack/linttb-scroll.patch adds 3 bytes to
; chput_esc_m, before the font pad: this island starts 3 B later than $1AF2.
; D-CTRLKEYS (2026-10-05): cbios-repack/ctrl-keys.patch puts 23 bytes in
; key_ascii, BEFORE the font pad, so the pad -- and this island -- start 23 B
; later than D-HOMEKEY's $1ADB. rn_undefined moved to island 2 to make room.
                org     $1AF5

; try_init_slot -- boot-time: does the slot in A carry an "AB" ROM, and if so
; CALSLT its INIT. From basic/initext.asm, unchanged. Better here than in page 1:
; the CALSLT into the cartridge's page-1 INIT runs from page 0, which the switch
; never touches.
try_init_slot:
                call    try_text_slot       ; D-BASICROM: a page-2 TEXT cartridge? (keeps A)
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
                ; D-BOOTKEYS (2026-10-10): `inc`, not `ld 1` -- the scan zeroed the
                ; cell, so a normal INIT makes it 1; a disk ROM that SHIFT told to
                ; stay out (as the CF-3300's does: no Disk BASIC, HIMEM $F380 --
                ; scratchpad/bootkeys_run.out) left $FF, which wraps to 0: no disk.
                ; 🔴 D-DRVCOUNT (2026-11-13): the cell is DRVINF, and since D-DRVINT our
                ; disk ROM's INIT writes the drive count there (2, as the CF-3300 holds):
                ; a plain `inc` made it 3, and facdemo3.di2's drive loop ran on where the
                ; CF-3300's ends (scratchpad/facusr_run7.out / run8.out). 0 -> 1 and $FF
                ; -> 0 as before; a count the disk ROM wrote stays.
                ld      hl,DISKSLOT_OK
                ld      a,(hl)
                inc     a
                cp      2
                ret     nc                  ; the disk ROM set the drive count: keep it
                ld      (hl),a
                ret


; init_ext_roms -- the boot-time extension-ROM scan (from basic/initext.asm,
; unchanged): every primary/secondary slot after ours, CALSLT each "AB" ROM's
; INIT via try_init_slot above. Runs once, with interrupts off, at power-on.
init_ext_roms:
                xor     a
                ld      (DISKSLOT_OK),a     ; no disk-ROM slot recorded yet
                ; (SUBSLOT_OK is NOT cleared here since D-BIOSLADDER B5, 2026-11-10: the
                ; cold start clears it (interp.asm) and the caller records the sub-ROM
                ; just before this scan.)
                ; (SUBSLOT2 was cleared here for zerobas-sub2 until D-SUB2RETIRE
                ; step 2f, 2026-11-04 retired that ROM; the cell is unused.)
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

; --- D-ISLDATA2 (2026-10-03): pure-DATA blocks into the font island ---------------
; (five blocks, 58 B, when it landed; space plan B-7 took fmt_menu_text out to
; disk.rom on 2026-10-04 -- four blocks, 41 B, now.)
; Same rules as the $0160 block: absolute `ld` readers only. `rn_in` became an
; equ alias of in_msg in basic/program.asm (both were " in ",0); since D-P0CB
; (2026-10-24) it is sub2/pgmedit.asm's import p0_rn_in = in_msg.
; rn_undefined -- MOVED to island 2 (D-CTRLKEYS, 2026-10-05): island 1 lost
; 23 B to the CTRL arm in C-BIOS's key_ascii. Same readers, same rules.
; fmt_menu_text WAS here (D-ISLDATA2) until space plan B-7 (C6-FORMAT,
; 2026-10-04) moved CALL FORMAT's menu into disk.rom's hk_format, text and all.
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
; synchr -- RST 08h, the PUBLISHED MSX BIOS SYNCHR (D-SYNCHR, 2026-11-07): (HL) must
; equal the byte AFTER the RST, else Syntax error; on a match the return address
; steps past that byte and it continues AS CHRGTR (no space skip BEFORE the compare,
; spaces skipped after). Measured on the VG-8020 and the CF-3300, both alike
; (scratchpad/synchr_probe.py -> synchr_run.out): ",5" -> HL+1, A = '5', F = $23;
; ";" expected -> ERR 2; " ," -> ERR 2; ", 5" -> HL+2. C-BIOS's $0008 was its debug
; stub (it printed "SYNCHR" and returned). Falls into chrgtr.
synchr:
                ld      a,(hl)
                ex      (sp),hl             ; HL = the RST's return address
                cp      (hl)                ; = the expected byte?
                inc     hl                  ; return PAST it
                ex      (sp),hl
                jp      nz,stmt_error       ; no: Syntax error
chrgtr:
                call    H_CHRG              ; the published hook (a RET by default)
                ; D-SYNCHR: the CLASSIC order, so the flags are the reference's to the
                ; bit (a digit '5' leaves F = $23 on both references -- `inc a / dec a`'s
                ; S/Z/H/P/N over the carry `ccf` made); was cp ' ' / cp ':' / or a /
                ; cp '0' / cp '9'+1, the same Z / C contract with other undocumented
                ; bits, and 4 B longer.
cgt_lp:
                inc     hl
                ld      a,(hl)
                cp      ':'                 ; ':' and above: NC (Z only on ':')
                ret     nc
                cp      ' '
                jr      z,cgt_lp
                cp      '0'                 ; below '0': CF -> ccf -> NC; a digit: NC -> CF
                ccf
                inc     a
                dec     a                   ; Z on end of line (0), flags as the reference
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
; `ld a,(CSRX)` at $1162 with a call to this, and C-BIOS's own store that
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
; cl_lvtab: the evaluator's precedence CODE of each binary operator, indexed by
; token - GT_TOKEN ($EE..$FC). D-EVALSLOPE (2026-10-20): the one climber in
; basic/expr.asm reads it once per operand with an absolute `ld hl,cl_lvtab`; it
; took the slot of logtab, the logical layer's own table, which that climber
; replaced. The codes (CL_*) and what they mean are at expr.asm's climber.
cl_lvtab:
                db      CL_REL              ; $EE >
                db      CL_REL              ; $EF =
                db      CL_REL              ; $F0 <
                db      CL_ADD              ; $F1 +
                db      CL_ADD              ; $F2 -
                db      CL_MUL              ; $F3 *
                db      CL_MUL              ; $F4 /
                db      CL_POW              ; $F5 ^
                db      CL_AND              ; $F6 AND
                db      CL_OR               ; $F7 OR
                db      CL_XOR              ; $F8 XOR
                db      CL_EQV              ; $F9 EQV
                db      CL_IMP              ; $FA IMP
                db      CL_MOD              ; $FB MOD
                db      CL_IDIV             ; $FC integer division
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
; (autoexec_name, the 11-byte "AUTOEXECBAS", left this island 2026-10-19: the
; AUTOEXEC.BAS probe is disk.rom's hk_auto now, which stages its own copy.)
fmt_name:       db      "FORMAT"
prompt_text:
                db      "ZB",13,10,0
; rn_undefined -- from island 1 (D-CTRLKEYS, 2026-10-05): pure data, absolute
; `ld` readers only, exactly as in its D-ISLDATA2 home. Its one reader is RENUM's
; report in sub2/pgmedit.asm since D-P0CB (2026-10-24): an `ld hl,p0_rn_undefined`
; handed to main's print_string through p0cb, which maps this page back in.
rn_undefined:   db      "Undefined line ",0

; --- D-KEYSHIFT (Joost, 2026-10-11): the key line follows SHIFT ---------------
; Measured on the VG-8020 (scratchpad/keyidle_probe.out, keyshift_wait.out):
; while SHIFT is held the bottom row shows F6..F10 and FNKSWI reads 0, back on
; release -- at the prompt and in INPUT, LINE INPUT, INPUT$ AND an INKEY$
; loop, but NOT in a loop that never asks the keyboard; with KEY OFF nothing is
; drawn and FNKSWI stays 1. So it rides the BIOS key calls: zerobas's own call
; sites reach CHSNS / CHGET through these two wrappers (C-BIOS's own chget
; waits on a HALT and is left untouched). The paint is the keystr tenant's,
; which picks the set from FNKSWI; its register saves run in zks_paint (here)
; and zks_p2 (the low region, basic/subromcall.asm) -- CALSLT clobbers all but
; IY, which sr_slot keeps (D-PLAYIY).
zb_chget:
                call    zb_chsns
                jp      nz,CHGET            ; a key is waiting: CHGET takes it
                halt                        ; (CHSNS enabled interrupts)
                jr      zb_chget
zb_chsns:
                ld      a,(CNSDFG)
                inc     a                   ; $FF (shown) -> 0
                jr      nz,zks_go
                ld      a,(SCRMOD)
                cp      2
                jr      nc,zks_go           ; no key line in a graphics mode
                ld      a,(NEWKEY+6)
                and     1                   ; SHIFT, active low: 0 = held
                ld      hl,FNKSWI           ; ... = the FNKSWI value for it. HL is
                cp      (hl)                ; NOT preserved: all four call sites
                ld      (hl),a              ; guard it (read_line has none live)
                call    nz,zks_paint        ; it changed: repaint
zks_go:
                jp      CHSNS
zks_paint:
                push    bc
                push    de
                push    hl
                push    ix
                jp      zks_p2

; st_go -- STRTMS's start (bios_strtms, basic/biosfnk.asm; D-BIOSRUNG / STRTMS): PLYCNT -
; 1, MUSICF := 7. Also PLAY's start (the parser tenant through the resident ABI) and the
; servicer's sync (through bios_strtms). Here because page 0 had no other 10 B.
st_go:
                ld      hl,PLYCNT
                dec     (hl)
                ld      a,7
                ld      (MUSICF),a
                ret

    IF $ > $0200
                db      ISLAND_BEFORE_JUMPTABLE_OVERRAN_0200__IT_WOULD_OVERWRITE_CBIOS
    ENDIF

; --- islands 3 and 4: C-BIOS gap 1 around the tape bodies (space plan A3) ------
; C-BIOS src/main.asm:631 pads `ds $0D01 - $` from the end of debug.asm up to its
; pinned compat ISR-exit tail at $0D01 ("Hacker" jumps to $0D02, Star Force calls
; $0D0E). zerobas's tape bodies take $09EE..tape_end of that run; what is left is
; $09E0..$09ED (14 B, island 3; $09D9 until D-BIOSRUNG's SCREEN 3 arms grew C-BIOS,
; 2026-11-12). Island 4 ($0CC9.., the error-message table) is
; RETIRED (2026-10-15): TAPION's cycle verify (D-TAPLEAD's residual) needed the tape
; bodies to run to C-BIOS's compat tail at $0D01, the cap every other variant's
; tape patch already has, and err_msgtab went back to main page 1 (interp.asm).
; ⚠️ That pad is C-BIOS's deliberate "wrong jumper" slide (src/main.asm:631-633,
; "put RET instruction there"): a stray jump into $0CC9..$0D00 used to slide to
; the RET at $0D01. With island 4 filled, only the bytes after the table still
; slide. No published contract names those addresses; recorded here, not hidden.
; Both islands hold DATA only (read by an absolute `ld hl,<label>` in main page 1,
; never by a page-0 tenant), and tools/build_mainrom.py now REFUSES a tape image
; ending past island 4's start -- the non-zero-overlap check alone would let a
; growing tape silently replace a table's $00 bytes.
; (Space plan A3, docs/plan-main-rom-space-2026-10.md: C2-GAP1's islands, DT-2's
; tables -- DT-2 no longer fit islands 1/2 once A2/DT-3 had filled them.)
; 📦 D-SCALXYF (2026-11-13): island 3 is EMPTY now. SCALXY's flag answer (cbios-repack/
; scalxy-flags.patch) grew C-BIOS's graphics span by 3 B, to $09E2, into the table that
; sat here; fperr_to_err moved to main page 1 (basic/catalias.asm), its one reader an
; absolute `ld hl,fperr_to_err`. $09E3..$09ED (11 B) stays a declared island
; (tools/build_mainrom.py ISLAND_RANGES) for the next tenant.

                org     $0008
                jp      synchr              ; D-SYNCHR (was C-BIOS's `jp $10ED` debug stub)

                org     $0010
                jp      chrgtr

; --- the RST 18h vector: $0018 `jp outdo` (was C-BIOS's `jp $111B`) ---------
                org     $0018
                jp      outdo

                org     $0028
                jp      getypr              ; D-SYNCHR follow-up (was C-BIOS's `jp $1127`)

; --- ERAFNK / DSPFNK: C-BIOS's are print_debug stubs (D-BIOSCONTRACT, 2026-11-09) --
; The jump-table slots point at basic/biosfnk.asm instead; PATCH_RANGES refuses
; unless they still read C-BIOS's `jp erafnk` / `jp dspfnk`.
                org     $003E
                jp      bios_inifnk         ; INIFNK: C-BIOS's was a stub too
                org     $00AE
                jp      bios_inlin          ; PINLIN: C-BIOS's INLIN never returned
                jp      bios_inlin          ; INLIN
                jp      bios_qinlin         ; QINLIN
                org     $00B7
                jp      bios_breakx         ; BREAKX: a press it sees is consumed (D-BRKLATCH)
                jp      bios_iscntc         ; ISCNTC: C-BIOS's was a stub (D-BIOSRUNG)
                jp      bios_iscntc         ; CKCNTC: the same entry on the VG-8020
                org     $00C0
                jp      bios_beep           ; BEEP: C-BIOS's was a stub too
                org     $00C9
                jp      bios_fnksb          ; FNKSB: C-BIOS's was a stub (D-BIOSRUNG)
                org     $014D
                jp      bios_outdlp         ; OUTDLP: C-BIOS's was a stub (D-BIOSRUNG)
                org     $0159
                jp      bios_calbas         ; CALBAS: C-BIOS's printed an error (D-BIOSRUNG)
                org     $0099
                jp      bios_strtms         ; STRTMS: C-BIOS's was a stub (D-BIOSRUNG)
                org     $00F9
                jp      bios_putq           ; PUTQ: pre-incrementing, as the VG-8020 (D-BIOSRUNG)
                org     $008D
                jp      bios_grpprt         ; GRPPRT: C-BIOS's drew in SCREEN 2 only (D-BIOSRUNG)
                org     $0129
                jp      bios_pntini         ; PNTINI / SCANR / SCANL: C-BIOS's were bare
                jp      bios_scanr          ;   `ret`s (D-BIOSRUNG; the sub-ROM's paint
                jp      bios_scanl          ;   tenant, sub/paintbios.asm)
                org     $00CC
                jp      bios_erafnk
                jp      bios_dspfnk

; --- C-BIOS's CHPUT stores CSRX-1 into TTYPOS, not CSRX -----------------------
; $116E is C-BIOS's `ld a,(CSRX)` just before `ld (TTYPOS),a` (src/chput.asm,
; "CSRX -> TTYPOS"; $1162 on 0.30, $11CF before; D-CBIOS030 / D-CBIOS031). PATCH_RANGES refuses
; unless it reads 3A DD F3.
                org     $116E
cbios_chput_ttypos:                         ; a root: C-BIOS enters it (PATCH_ROOTS)
                call    ttypos_col

; --- C-BIOS's boot leaves H.OUTD a RET, not `jp chput` -----------------------
; $0FD6 is C-BIOS's `ld a,$c3` before `ld (H_OUTD),a` (src/main.asm, "set up
; hook"; $0FCA on 0.30, $1037 before; D-CBIOS030 / D-CBIOS031); only its operand byte changes.
; PATCH_RANGES refuses unless it is $C3.
                org     $0FD7
                db      $C9
