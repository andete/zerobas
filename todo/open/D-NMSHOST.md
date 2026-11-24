- [ ] 🎯 **D-NMSHOST — ZEROBAS WITHOUT ITS DISK ROM HOSTS THE NMS 1200 CARTRIDGE AND BOOTS MSX-DOS (the host half of the disk contract)**
      🎚️ TIER 1 — Joost 2026-11-24: preparing zerobas for disk ROM support in C-BIOS; "plain C-BIOS won't work, no need
      to test that yet. We still need to port any kind of disk facilities to it." The host is zerobas's no-disk build
      (C-BIOS_MSX1_EU_REPACK_NODISK = C-BIOS plus our fixes), the cartridge the Philips NMS 1200 (openMSX `-ext
      Philips_NMS_1200`, a black box: run, never read), the reference the VG-8020 with the same cartridge.
      🤖 **AUTONOMOUS** — black box: work-area RAM, hooks, slot state, VRAM, the disk image; never a ROM byte.
      First look (2026-11-24, 25 s after power-on, no disk inserted): VG-8020 + NMS 1200 -> HIMEM $DF95, DRVTBL 2 drives,
      H.PHYD patched ($F7), MSX-DOS's "Enter date" prompt; NODISK + NMS 1200 -> HIMEM $F380, DRVTBL 0, H.PHYD $C9: the
      cartridge never sets itself up. (Plain C-BIOS MSX1 EU: the same.)
      Plan: (1) a probe that traces the boot step by step on both machines -- INIT called, HIMEM lowered, DRVTBL filled,
      hooks patched, boot sector read, MSXDOS.SYS loaded, the prompt -- against a private copy of the user's DOS disk
      (never committed); the first step that differs is the first item; (2) fix each gap in zerobas's main BIOS until
      the NODISK build boots MSX-DOS from the NMS 1200 as the VG-8020 does; (3) each fix recorded on a host-contract
      page (what a disk ROM needs from the main BIOS) -- the patches for C-BIOS later. Out of scope: the NMS 1200's
      Disk BASIC side (MS-BASIC internals), plain C-BIOS (until disk facilities are ported).
      STEP 1 (2026-11-24, scratchpad/nmshost_probe.py; runs AE_nmshost_step1.out (ref, 30 s), AE_nmshost_step1_ref.out /
      AE_nmshost_step1_zb.out (8 s / 4 s, with the page@slot trace)): zerobas DOES call the cartridge's INIT -- not
      C-BIOS's scan but zerobas BASIC's own `init_ext_roms` (basic/initext.asm, islands.asm), late, from BASIC's
      start-up -- at 2.65 s (the VG-8020's BIOS scan: 4.95 s). The INIT starts the same on both: HIMEM low byte := $C1,
      $F349 := 0, DRVTBL zeroed, main-ROM calls with interrupts on. Then on zerobas the machine RESTARTS in a loop (the
      main BIOS's start-up writes repeat ~97 times in 8 s) and never reaches the reference's second HIMEM step
      ($DF97 / $DF95 at 5.74 s), the drive table, or the hooks (6.06 s). On BOTH machines the INIT makes inter-slot
      calls (cartridge -> page-3 RAM -> page 1 of SLOT 0): on the VG-8020 that is the MS-BASIC ROM page, on zerobas
      zerobas's own page-1 code. LEADING HYPOTHESIS (not yet proven): the NMS 1200's INIT calls fixed addresses in
      the main ROM's page 1 that zerobas does not keep. NEXT: pin where the restart starts (the last page@slot
      changes before the first repeated start-up write), and whether the page-1 calls go to a published BIOS entry or
      not -- black box only (page@slot and SP, never PC values or ROM bytes); then decide the remedy with Joost (a
      page-1 call table for disk ROMs, as the reference keeps, or a call-context change in init_ext_roms).
      STEP 2 (2026-11-24, AE_nmshost_step2_zb.out; zerobas's OWN addresses logged, never the reference's): the INIT waits
      in a busy loop with interrupts on (each tick: zerobas's $0038 -> H.KEYI $FD9A -> $17C8 -> back); then the cartridge
      runs RAM at $F392 (the inter-slot primitives' area, past CLPRIM $F38C) and execution enters zerobas at page-0
      $2442 -> page-1 $40C0 -> H.STKE $FEDA -> a runaway RET chain (SP climbing by 2) -> the restart. $2442 is NOT a
      published BIOS entry (the MSX1 jump table ends at $015F): THE NMS 1200 CALLS A FIXED UNPUBLISHED MAIN-ROM ADDRESS.
      ⛔ DECISION FOR JOOST before measuring further: may a probe CALL that address on the VG-8020 and observe what it does
      (registers / RAM / VRAM, black box -- as the unpublished SCANR / SCANL were measured), given that the address was
      learnt from the cartridge's behaviour on zerobas (our own ROM's PC), never from the reference? If yes: measure
      each unpublished address the NMS 1200 calls, then the remedy (zerobas answering them) is a ROM-layout decision.
      ✅ STEP 3 CORRECTS STEP 2 (2026-11-24): $2442 is zerobas's OWN RST $30 / CALLF return path (the NMS 1200 hooks
      H.TIMI -- the motor timer -- so every interrupt runs RST $30 -> CLPRIM -> the cartridge -> $F392 -> $2442 -> back);
      a call recorder on the VG-8020 never sees $2442 executed. The decision above is MOOT. THE REAL CAUSE, MEASURED:
      the cartridge's INIT is entered on zerobas with SP = $F2DA (C-BIOS's boot stack, inherited by zerobas's `init`,
      which never returns) where the VG-8020's boot scan has SP = $F08E; the INIT lowers HIMEM to $F1C1 and ZEROES its
      new work area from $F2C0 up (1,798 writes into $F2C0-$F2EF alone) -- the caller's stack (CLPRIM's saved AF, the
      scan's return addresses) -- so the return goes to junk and the machine restarts. HOST CONTRACT ITEM 1: an
      extension ROM's INIT is entered with the stack BELOW the RAM a disk ROM claims (the reference: $F08E).
      STEP 4 (experiment, isolated instance, NOT committed): `ld sp,$F0A0` before `call init_ext_roms` (basic/interp.asm)
      -> the INIT now completes phase 1, fills DRVTBL 02 01 like the reference, returns, the scan continues -- but then
      a return lands at the experimental `ld sp` itself and init_ext_roms RERUNS (SP $F09E), INIT runs again and
      registers a second, third ... drive pair every ~0.7 s. A bare `ld sp` is too crude: a stale return address from
      before the switch is still used. NEXT: a proper fix -- the scan runs on a stack of its own below the claimable RAM
      and returns to `init` on the original stack (or init_ext_roms becomes a jump, not a call, with no frame above it);
      then re-trace; then the reference's phase 2 (the 512-B buffer allocations to $DF95 at 5.74 s, with an inter-slot
      call into page 1 of slot 0 -- the MS-BASIC page) is the next comparison.
      STEP 5 (2026-11-24): PROTOTYPE A in an isolated instance (HIMEM := $DB00 and SP below it BEFORE the scan; not
      committed) -> phase 1 runs exactly as on the reference (first claim $D941 = $DB00 - $1BF, the reference's
      $F380 - $1BF); then the INIT writes $FF to zerobas's SCAN_* cells $EF42-$EF47, which it never writes on the
      reference, and zerobas's scan ends up CALSLTing zerobas's OWN INIT ($4010) -> a restart loop. Joost: "a third
      option: investigate why we still have RAM variables that diverge from reference". Measured (scratchpad/
      nmsram_probe.py, AE_nmsram_ref.out): every RAM address the NMS 1200 writes on the VG-8020 from power-on to the DOS
      boot -- its HIMEM claim, buffers, stack, the boot sector at $C000, and published system cells incl. $F672-$F675
      (MEMSIZ / STKTOP) and $F6AB / $F6B1 it evidently also READS. 22 zerobas variables below $F380 overlap it (mostly
      DISK-ONLY). ⛔ NEXT, ASKED: diff the PUBLISHED DATA cells (by name; never $F380-$F399's RAM-resident code or the
      hooks -- a full $F380-$FFFF snapshot was refused by the permission check, §8.5) at the cartridge's INIT on both
      machines -> the system variables where zerobas diverges.
      STEP 6 (Joost: yes; scratchpad/sysdata_diff.py, AE_nmshost_sysdata.out -- $F39A-$FD99 only, never the RAM code at
      $F380-$F399 or the hooks): at the INIT the VG-8020 has MS-BASIC's memory layout already in place -- MEMSIZ
      ($F672) $F168, STKTOP ($F674) $F0A0 (the boot stack: INIT's SP $F08E is just below), SAVSTK ($F6B1) $F09E, FILTAB
      ($F860) $F16A / $F177, FRETOP and the string-pool cells set -- all relative to HIMEM $F380. zerobas has $0000 /
      $F380 / $0000 / $0000 there. A disk ROM's MSX1 INIT reads these and REBUILDS BASIC's layout below the HIMEM it
      lowers (the reference's phase 2: its writes to $F672-$F675 / $F6B1, the 512-B buffers, HIMEM -> $DF95). On
      zerobas it computes from zeros and its writes land on zerobas's private RAM ($EF42 ...). HOST CONTRACT ITEM 2: at
      an extension INIT, MEMSIZ / STKTOP / SAVSTK / FILTAB / FRETOP (and the stack itself) hold MS-BASIC's layout,
      consistent with HIMEM. ⛔ DECISION FOR JOOST: zerobas keeping those published cells with the reference's
      meaning is a design change in zerobas BASIC's memory model (its string heap / control pool / TXTCEIL).
      ✅ JOOST 2026-11-24: "We go for the best option. Try to match reference" -- zerobas's memory model matches the
      reference's (published cells with MS-BASIC's meaning; no private zerobas state in RAM a disk ROM may claim).
      STEP 7-8 (prototypes in an isolated instance, NOT committed): before the scan, the reference's layout (MEMSIZ
      $F168, FRETOP $F168, FILTAB $F16A / $F177, SAVSTK $F09E, STKTOP $F0A0 and SP there) + ONE CALL TO H.RUNC ($FECB)
      after the scan -> the NMS 1200's whole INIT runs as on the reference: phase 2 HIMEM $F197 -> $EF97 -> $ED97 ->
      $EB97 -> $E596 -> $DF95, and HIMEM / DRVTBL / H.PHYD / H.DSKO / $F37D end BYTE-IDENTICAL to the VG-8020's. HOST
      CONTRACT ITEM 3: MS-BASIC calls H.RUNC (the hook the disk ROM patches in phase 1, at $FECB) in its cold start --
      zerobas never calls it (grep: no H.RUNC anywhere in basic/); phase 2 runs from there. Still NOT booted: zerobas
      then runs on in RAM the disk ROM now owns ($DF95 up: the prototype's stack, zerobas's private variables), where
      MS-BASIC moves to the layout the disk ROM rebuilt.
      PLAN (the memory model): (a) inventory every zerobas cell below $F380 (tools/ram_map.py) -> published MS-BASIC
      cell / dynamic below HIMEM / the disk ROM's own claimed area; (b) the boot layout and H.RUNC (D-HSTKE's way:
      measure when MS-BASIC calls it -- NEW / RUN / CLEAR / cold start -- and match); (c) zerobas BASIC adopts the layout
      a disk ROM rebuilt (stack from STKTOP, strings from MEMSIZ / FRETOP, files from FILTAB); (d) move the private
      cells; (e) our own disk ROM claims its RAM through HIMEM the reference's way. Each step: the NMS 1200 trace + the
      full gates; the NODISK and DISK targets both.
      ✅ ITEM 3 FIXED 2026-11-24: WHEN the VG-8020 calls H.RUNC (scratchpad/hrunc_when.py, AE_hrunc_when.out -- our own
      counting handler in the hook): NEW +1, a typed program line +1, RUN +1; CLEAR / CLEAR n / MAXFILES / a direct
      statement / a direct error 0 (unlike H.STKE: CLEAR and an error fire that one). zerobas: 0 everywhere. basic/
      files.asm `hrunc` (shares hstke's register-saving body, `hook_call`) called from new_prog, store_line, the RUN
      path and the cold start right after init_ext_roms. After: every row matches on NODISK and DISK. Unmeasured: LOAD
      (new_prog serves its ASCII path).
      ITEM 2 (2026-11-24): the rule, measured at HIMEM $F380 (INIT) and $DF95 (after phase 2) alike: MEMSIZ = HIMEM -
      $218, FRETOP = MEMSIZ (at boot), FILTAB = MEMSIZ + 2 and its next word MEMSIZ + $0F, STKTOP = MEMSIZ - 200,
      SAVSTK = STKTOP - 2; TXTTAB / VARTAB / BOTTOM do not move. basic/files.asm `layout_from_himem`; `init` calls it
      and puts SP at STKTOP BEFORE the scan, and AFTER the scan + H.RUNC rebuilds it if STKTOP is no longer below HIMEM
      (our own disk ROM lowers HIMEM without H.RUNC) and runs the rest of the start-up on that stack (repl then re-bases
      into the pool, D-SPMERGE). RESULT on NODISK + NMS 1200: the INIT byte-identical to the reference again (HIMEM
      $DF95, DRVTBL, H.PHYD, H.DSKO, $F37D), NO restart, and the cartridge loads the BOOT SECTOR to $C000 at 5.13 s
      (the reference 7.63 s; write footprint 4,218 vs 4,227 addresses) -- the DOS boot starts. NOT YET: no "Enter
      date" on screen at 30 s; pages end RAM / RAM / slot 1 / RAM. NEXT: how far MSXDOS.SYS / COMMAND.COM get.
      (Pushed: 770e102da H.RUNC, 8550f5f73 the layout -- FULL gates green.)
      STEP 9 (2026-11-24): the TARGET corrected. With drive A EMPTY the VG-8020 + NMS 1200 shows "Enter date (M-D-Y):"
      and executes neither the boot-sector entry $C01E nor $0100 (RAM breakpoints): the prompt is the DISK ROM'S OWN
      start-up dialogue (an MSX1 has no clock), not MSX-DOS. With the private DOS disk the reference loads the boot
      sector and shows a blank TEXT1 screen at 60 s -- not a usable target. zerobas NODISK + NMS 1200, empty drive, after
      items 2 + 3: "Enter date (D-M-Y):" at 6 / 10 / 25 s -- THE SAME DIALOGUE. Two differences left: (a) the date FORMAT
      (D-M-Y vs M-D-Y: the disk ROM reads it from the main ROM's published machine-ID information, which C-BIOS's EU
      build sets differently); (b) the screen is not cleared first (the reference's prompt stands alone; zerobas's lands
      under C-BIOS's start-up text, because the prompt comes from the cold start's H.RUNC, before zerobas's show_title
      clears the screen). NEXT: answer the prompt on both and compare what follows; then (b) and (a).
      STEP 10 (2026-11-24): after the date is typed the reference shows MS-BASIC's banner + "Disk BASIC version 1.0" + Ok;
      zerobas loops "in 2523" -- the NMS 1200 continues into its Disk BASIC set-up, which calls MS-BASIC internals (OUT
      OF SCOPE, as filed). The MSX-DOS target: on the VG-8020 + NMS 1200 in openMSX THREE DOS disks (the private
      test.dsk, elite.dsk 360 KB with only MSXDOS.SYS + COMMAND.COM, msxdos103-cmd111.dsk) all run the boot sector
      (RAM breakpoint $C01E hit) and NEVER reach MSX-DOS ($0100 not hit; a blank TEXT1 screen at 40-60 s), though the
      machine has 64 KB of RAM in slot 3. So the reference itself does not boot MSX-DOS from these disks here. Probe
      lesson: the RAM breakpoints first recorded a bogus hit at time 0 (reset) as the only hit -- hits in the first
      second are now ignored; the printed time was taken at definition, not at the hit.
      ⛔ FOR JOOST: is a VG-8020 + NMS 1200 known to boot MSX-DOS 1 (another disk, another setting, another MSX1 host
      with the NMS 1200)? Without a reference that boots DOS the step after the date prompt has nothing to match.
      HOST-CONTRACT PAGE: docs/concepts/disk-rom-host.md (2026-11-24) -- items 1-3 with their evidence, the disk ROM's
      write map, and the open list (date format, screen clear, DOS).
      STEP 11 (2026-11-24) -- the screen clear: both machines are in SCREEN 1 (SCRMOD 1) before the cold start's H.RUNC.
      On the VG-8020 the H.RUNC call (5.747 s) returns quickly and MS-BASIC's own cold-start screen set-up follows
      (port $99: R#1 := $A0 ... R#1 := $F0 TEXT1, by page-0 slot-0 code on the new stack $DC9B-$DCA3 under the rebuilt
      STKTOP); the disk ROM's prompt comes later, after it re-enters (it patches its other hooks at 6.06 s). On zerobas
      the disk ROM stays INSIDE H.RUNC and prompts from there ~2.4 s later (its calls into zerobas: RDSLT / CALSLT /
      WRSLT / PHYDIO / CHPUT / CHGET only, plus returns -- no screen call), before zerobas's show_title sets up the
      screen. So the disk ROM's H.RUNC handler takes another branch on zerobas -- on some state MS-BASIC has set by its
      cold start -- and MS-BASIC sets up the text screen right after H.RUNC, zerobas after its banner logic. Cosmetic;
      left open, tied to the Disk BASIC side.
