- [ ] 🎯 **D-DISKROMHOST — ZEROBAS'S OWN DISK ROM AS A CONTRACT-FOLLOWING CARTRIDGE: ITS MSX-DOS HALF STANDS ON ITS OWN
      (Joost 2026-11-24: "this is exactly what I had in mind").**
      🎚️ TIER 1 — preparing disk support for C-BIOS (a host without BASIC): the DOS half must need nothing from zerobas
      BASIC, and must follow the host contract (docs/concepts/disk-rom-host.md) as a stock disk ROM does.
      🤖 **AUTONOMOUS** — step 1 done; step 2 (it changes the disk ROM's structure and RAM map) approved by Joost
      2026-11-24.
      STEP 1 (2026-11-24, zerobas's own source; scripts inline in the session): of disk/basic-resident-abi.inc's 104
      imports, 10 are unused; of the rest, 32 are BASIC CODE (interp / expr / float-arith / vars / strvar / field /
      files / str-engine / traps / pdfcb-body) and 62 are RAM CELLS (sysvars.inc). EVERY code import is called from a
      Disk BASIC statement handler -- in disk/kernel.asm hk_dsk (DSKI$ / DSKO$), hkc_body (COPY), hk_mkfloat (MKS$ /
      MKD$), hk_lrset (LSET / RSET), hk_system (CALL SYSTEM), hk_cv (CVI / CVS / CVD), hk_name (NAME), the RANDOM
      record helpers; in disk/fat.asm / driver.asm / runtime.asm / pageenv.asm only the BASIC file paths (OPEN,
      INPUT#, GET / PUT / FIELD, FILES, LOAD) import cells. The MSX-DOS path -- the DSKIO / DSKCHG / GETDPB / DSKFMT
      driver, the BDOS / FCB layer, the page-0 environment, INIT and the DOS boot bridge -- calls NO BASIC code; its
      only ties are four layout constants in disk/disk.asm: the sector buffers FSECTOR_BUF / FWBUF, FLD_END and
      TXTMAX_NODISK -- fixed addresses from zerobas's RAM map, not RAM the disk ROM claims.
      STEP 2 (⛔ Joost): the disk ROM claims its RAM by lowering HIMEM in INIT and keeps ALL its state inside the claim
      (the sector buffers, the DOS-path bridge block -- today $DDAE..$DF92, straddling DISK_HIMEM $DE77 --, the disk-only
      cells of scratchpad/ram_inventory_f380.md class C); patches H.RUNC and does its phase-2 set-up and the DOS boot
      from there, as a stock disk ROM does. ACCEPTANCE: zerobas's disk ROM, inserted as a cartridge into a VG-8020
      (real MS-BASIC host) in openMSX, boots MSX-DOS -- host-independent, so a C-BIOS host can take it.
      STEP 3: memory parity on the DISK build vs the CF-3300 (plain boot: FRE, the layout cells), after D-BOOTCELLS.
      ✅ STEP 2 APPROVED (Joost 2026-11-24: "excellent news. Go ahead"). SEQUENCED after D-BOOTCELLS's swap (both touch
      basic/interp.asm init's HIMEM / layout path), as an isolated-instance unit with its own FULL gate.
      STEP 2a DONE (2026-11-24, isolated instance): INIT is phase 1 only (slot byte, the HIMEM claim, the hooks -- HPHYD
      and H.RUNC are rows of install_basic_hooks' table now); the first H.RUNC call runs `init_p2` (the rest of the
      set-up) and the DOS boot, and the handler leaves the hook five RETs, as the CF-3300 and the VG-8020 + HBD-F1 do.
      ACCEPTANCE MET: zerobas's disk ROM as a cartridge in the VG-8020 boots MSX-DOS 1.03 from inside the cold start's
      H.RUNC (before: from INIT) -- scratchpad/AE_diskhost_vg8020.out; the DISK machine's HIMEM / FRE(0) / FRE("") /
      MEMSIZ / STKTOP / FILTAB still equal the CF-3300's (scratchpad/AE_diskhost_fre.out). Bytes: hrunc_h took
      fat_bufinit's (inline in init_p2 now) and rh_init's (moved to the $4EDE pad).
      STEP 2b ⛔ (a ruling): the RAM. Every BASIC-phase cell the disk ROM keeps is already inside [$DE77, $F380); what
      lies below DISK_HIMEM is the DOS-phase block -- GETWRK_AREA $DD0E (128 B, the $4030 work area MSXDOS.SYS places
      its kernel under) and the slot bridges INT_H_HIRAM $DDAE..$DF92 -- written only at DOS entry (install_dos_env),
      when BASIC is gone, and at the CF-3300's own addresses ($DD0E is its DRVTBL+3 value, $DDAE its $0038 target;
      its own H.RUNC claim stops at $DF93, above both). Options: (a) keep them (reference-faithful); (b) move both into
      the claim (e.g. over the engine-table rows, dead under DOS) -- changes the DOS kernel's placement, the TPA top
      at $0006 and $0039 against the CF-3300. Also open: the reference's TWO-STEP claim ($F195 in INIT, $DF93 in
      H.RUNC, with the layout rebuilt under each -- docs/concepts/disk-rom-host.md, Open) against zerobas's one-step
      $DE77 with no rebuild, which leaves an MS-BASIC host's layout inside the claim when no DOS disk boots.
      ⛔ OPEN (Joost still deciding, 2026-11-24): the DOS-phase block below DISK_HIMEM -- GETWRK_AREA $DD0E and the
      slot bridges from INT_H_HIRAM $DDAE -- options (a) / (b) above. Placement unchanged for now (the CF-3300's
      addresses); measured at MSX-DOS's entry for the decision (scratchpad/AE_diskhost2_ref.out, DOS lines): the
      word at $0006 ends $D606 on all four set-ups; $0038 jumps to $DDAE on the CF-3300 and on ours (both hosts),
      to $DDA8 on the VG-8020 + HBD-F1; DRVTBL 02 87 (CF-3300, the DISK machine) / 02 01 (the VG-8020 with either
      cartridge); SLTWRK holds the work-area base for the interface's page 1 on both references ($F1BF CF-3300 slot
      3-1, $F1C0 HBD-F1 slot 1-0) and nothing on ours; HIMEM at DOS's entry $DF93 / $DF94 on the references, $DE77
      on ours (the references' last step, to $DE77 / $DE78, comes only when Disk BASIC starts).
      STEP 2b DONE (2026-11-24, isolated instance; Joost: "do the two-step claim NOW, matching the reference
      cartridges" + call the $7D2F routine): MEASURED FIRST (scratchpad/diskhost2_ref.py -> AE_diskhost2_ref.out):
      the CF-3300's INIT lowers HIMEM $F380 -> $F1BF -> $F195 (VG-8020 + HBD-F1: $F1C0 -> $F196), its H.RUNC handler
      in five steps to $DF93 ($DF94), and every step rewrites MEMSIZ / STKTOP / SAVSTK / FILTAB + its two table words /
      NULBUF by MS-BASIC's rule (MEMSIZ = HIMEM - $218, FILTAB = MEMSIZ + 2 -> [FCB #0 = HIMEM - $212, FCB #1 =
      HIMEM - $109], NULBUF = FCB #0 + 9, STKTOP = MEMSIZ - 200, SAVSTK = STKTOP - 2); FRETOP is left for BASIC's
      next CLEAR. WHO MOVES SP: the cartridge -- SP is below the new STKTOP inside the INIT and inside each H.RUNC
      step, and the host calls H.RUNC on whatever stack the scan returned with (with our cartridge, which moves no
      stack, the VG-8020 calls it at SP $F09A, STKTOP $EEB5) -- so zerobas's main ROM needs no change.
      DONE: INIT claims INIT_HIMEM $F195 (the CF-3300's) and rebuilds the layout (disk/kernel.asm layout_rebuild);
      hrunc_h calls the routine named by the HOST main ROM's word at $7D2F (RDSLT x2 + CALSLT, EXPTBL's slot), then
      claims $DE77 (CTRL: $E48D, the SNSMAT test moved here from INIT) and rebuilds again, then phase 2.
      RESULT: VG-8020 + our cartridge, no disk: HIMEM $DE77, MEMSIZ $DC5F, STKTOP $DB97, FILTAB $DC61 [DC65 DD6E],
      NULBUF $DC6E, FRE(0) 23430 / FRE("") 200 -- the CF-3300's figures (was: the HIMEM-$F380 layout inside the
      claim, FRE(0) 28815); with a DOS disk MSX-DOS starts on SCREEN 0, LINLEN 37, VDP R#0-R#7 00 F0 00 00 01 00 00
      F4 -- the VG-8020 + HBD-F1's (was SCREEN 1 / 29). The DISK machine still equals the CF-3300 at BASIC's Ok
      (scratchpad/AE_diskhost_fre.out, AFTER step 2b) and now starts MSX-DOS in TEXT1 37 columns (zerobas EU's
      STARTUP_SCREEN; the CF-3300 is a Japanese machine, SCREEN 1 / 29, as expected).
      BYTES: the new code took ~89 B in the $607B-$75A5 region; found by pre-entries (rs_dbuf / rs_mbuf in front of
      read_sector, 15 sites; ff_name, fwfe_zero, fws_mbuf, nc_ptr), shared runs (fat_wclus_x15, dta_put_cnt,
      hl_cmp_eoc, op_lfiles, ldir_11, dta_from_dos, toupper_cmp, dirrem_z) and wrblk_mul16 inline. disk.rom pads,
      2026-11-24 (FDC window excluded): 80 B in 36 runs before, 115 B in 40 after (`make basic-reloc` for today's).
      NOT DONE: the stock cartridges move their stack below each new STKTOP and set SLTWRK; ours does neither
      (unchanged from before); HOOK_SLOT ($ED6A) lies below INIT's claim between INIT and H.RUNC.
      GATES (isolated instance, 2026-11-24): 74 of 76 green; the 2 red ones RESOLVED on merge (main ROM and sub ROM
      byte-identical before / after, only disk.rom changed): both compared the DISK machine's MSX-DOS start screen
      with the CF-3300's JP SCREEN 1 / 29, and the DISK machine now starts DOS in zerobas EU's TEXT1 / 37 because the
      disk ROM calls $7D2F -- a presentational JP / EU split, which the standing rule gives to the VG-8020 (Joost
      2026-09-04). (a) dosmode-acceptance: the boot / date rows are now compared against a MEASURED VG-8020 + Sony
      HBD-F1 booting the same disk -- every cell and line equal, the date compared as a date (the locale's order is
      kept, D-NMSHOST step 9); the old LINL40 39->37 excusal is gone (scratchpad/AE_dh2_dosmode3.out). (b)
      bdos-acceptance BDOSXC / BDOSXK / BDOSXB: their subject is the BDOS console, so each AUTOEXEC.BAT now runs MODE
      32 first and the exerciser no longer inherits the start-up screen; all three 0-byte-diff against the CF-3300
      again (scratchpad/AE_dh2_BDOSXC.out, AE_dh2_BDOSXK.out, AE_dh2_BDOSXB.out).

      🏗️ STEP 4 RULED (Joost 2026-11-25, after a zoom-in on the four moments -- INIT, H.RUNC, MSX-DOS start, Disk BASIC
      start -- measured in scratchpad/AE_diskhost2_ref.out): MATCH THE REFERENCES EXACTLY ON THE OUTSIDE, DO BETTER
      INSIDE. Outside = what a program sees: HIMEM at each moment, FRE, the layout cells (the CF-3300's: INIT $F380 ->
      $F1BF -> $F195 with its base in SLTWRK; H.RUNC -> $DF93; MSX-DOS runs with $DF93; Disk BASIC's start takes the
      last piece, $DF93 -> $DE77). Inside = how zerobas arranges its own state in the RAM it claims. Joost's question
      ("might something expect certain internal memory data structure shapes?") sorts every structure in three
      classes, decided by measuring both references: (1) PUBLISHED -- shape and contents kept (DRVTBL, the MSX-DOS 1
      system cells: RAMAD / MASTERS, the DPB list, the sector / directory buffer pointers; the FCB; FILTAB and the
      265-byte file blocks that VARPTR(#n) hands a BASIC program -- D-BOOTCELLS step 4; the entries MSXDOS.SYS calls);
      (2) NOT published but IDENTICAL on the CF-3300 and the HBD-F1 -- kept, to be safe ($0006 = $D606 under DOS);
      (3) DIFFERENT between the two references -- ours to arrange (the driver's private work area: 1 B apart; the DOS
      interrupt entry $DDAE / $DDA8; zerobas's own cells). THE PLAN: (a) measure, per moment, what zerobas's disk code
      uses (tools/ram_map.py's disk cells in the claim) against the reference's claim, and classify the structures;
      (b) HOOK_SLOT ($ED6A, class 3) into the INIT claim -- today a cartridge scanned after ours could overwrite it
      before H.RUNC, on a real machine too; (c) H.RUNC claims to $DF93 and Disk BASIC's start takes the rest, the DOS
      block and Disk BASIC's data on separate addresses (today they share $DE77-$DF92: the DOS block is written over
      the top of what H.RUNC claimed for Disk BASIC -- unmeasured: BASIC typed at A>); (d) the work area addressed
      from the base recorded in SLTWRK, not fixed addresses (host independence: a cartridge that claimed RAM before
      ours); (e) the real-disk corpus (scratchpad/diskcorpus_run.py, D-DISKRUN) after each move. If zerobas needs MORE than
      a reference at some moment, exact matching is impossible -- ask Joost with the numbers. Settled with it: the DOS
      block below the claim at MSX-DOS start is what the CF-3300 does (closed: matches); the 1-byte CF-3300 / HBD-F1
      difference is the drivers' own work-area sizes, and the CF-3300 (the DISK build's reference) is matched.
      ✅ STEP 4 (a), FIRST PART + (b) DONE (2026-11-25): scratchpad/claimuse_probe.py -- every write to the INIT claim
      $F195-$F37F through an MSX-DOS session + BASIC at A> + a file write, and Disk BASIC from a data disk + a file
      write. zerobas's DISK machine (AE_claimuse_zb.out): its disk ROM writes 47 B there, all named cells; 293 B are
      written by nothing -- among them the whole of DRVA_DPB ($F195, 18 B: IX points there for MSXDOS.SYS, but nothing
      writes it in these runs; to explain in (a)'s next part). The references (AE_claimuse_cf.out / AE_claimuse_hbd.out;
      clean room: the address, the time and the writer's page@slot only, writes after 1.0 s): the WHOLE range is
      written by the disk ROM side (the cartridge's slot, and the main ROM's page 1 on its behalf) -- the disk ROM's own
      work area, cleared and filled. 🔴 So inside $F195-$F37F the classes CANNOT be decided by comparing the
      references' values: that range holds their RAM-resident code, which the clean room never reads; only the
      published MSX-DOS cells and the fixed addresses MSXDOS.SYS calls (already at the reference addresses) are class 1
      there, the rest is class 3. (b): HOOK_SLOT $ED6A -> $F1C8, a byte nothing wrote before (disk/equates.inc): now
      written only by our INIT (AE_claimuse_zb2.out); the DOS session 20 / 20 (AE_hs_dossession.out); the VG-8020 +
      zerobas's disk cartridge boots MSX-DOS 1.03 (AE_hs_vg8020.out).
      ➡️ NEXT: (a) second part -- the claim at each moment against what zerobas uses there (H.RUNC's $DE77-$F194:
      the buffers, the layout rebuild's cells, the DOS block), then (c).
      STEP 4 (a) SECOND PART, from the high RAM atlas (docs/ram-atlas.md, D-RAMATLAS, 2026-11-25): in the H.RUNC claim
      zerobas writes the slot-switching code ($DDAE-$DF85) at H.RUNC in both scenarios and keeps Disk BASIC's data
      from $E8AD up, so the DOS block and Disk BASIC's data are ALREADY on separate addresses -- (c)'s overlap does
      not exist; what is left of (c) is only HIMEM under MSX-DOS ($DE77 here, $DF93 on the CF-3300). $DF86-$E8AC is
      claimed and never written. GETWRK_AREA ($DD0E) is never written, where the references write that band -- (a)
      continues there.
      GETWRK_AREA EXPLAINED (2026-11-25, the atlas): $DD0E is the address the $4030 entry and DRVTBL+3 hand MSXDOS.SYS,
      which places its kernel $067A below it ($0006 = $D606 on all three machines). On the references the band
      after it is written by their disk ROM and main ROM (the driver's own work area; class 3, the CF-3300 and the
      HBD-F1 differ there), never by MSX-DOS itself; zerobas's driver keeps its variables from $E8AD, so nothing
      writes the band here -- correct, not a gap. disk/init.asm's comment ("the 128-byte work area DOS fills") was
      wrong and is corrected (no byte changed). So on zerobas $DCB5-$DDAD and $DF86-$E8AC are claimed and unused:
      room for (d) -- the work area addressed from a base -- without moving anything visible.
      ✅ STEP 4 (c) DONE (2026-11-25): disk/kernel.asm hrunc_h claims to DOS_RESV_TOP ($DF93) and rebuilds the layout,
      CALLS init_p2, and only when it returns -- Disk BASIC starts: no disk, a data disk, the date prompt, a BASENT
      restart -- takes the last piece (DISK_HIMEM $DE77, or CTRL's $E48D read before init_p2 while the key is down)
      and rebuilds again; MSX-DOS never returns. MSX-DOS now runs with HIMEM $DF93 as on the CF-3300
      (scratchpad/AE_c_dosstart.out); a plain boot still equals the CF-3300 (AE_c_fre.out); `BASIC` at A> gives
      $DE77 / 23430 / 200 on both. Bytes: +8 in the $75A5 region, from hl_cmp_eoc (7 B) moved into the pad before the
      $77B8 pin and 1 of the 2 B before $75A5. The atlas gate caught the change ($DD7D-$DD80, the $DF93 layout's
      FILTAB table, now written at H.RUNC -- as the CF-3300 writes that band) and was re-measured. Not measured: MSX-DOS
      with CTRL held on the CF-3300 (its DOS-time HIMEM). Side note: openMSX's get_screen reads nothing on zerobas
      after BASIC at A> (the VRAM text is there: the banner, "ZB", the output) -- a probe artefact, not a defect.
      LEFT of step 4: (d) the work area addressed from a base recorded in SLTWRK (host independence); (e) the disk corpus.
      🧭 JOOST 2026-11-25 on (d): "guard first" -- a few bytes in INIT that check the claim landed where the fixed
      work-area addresses assume, and decline to install (rather than corrupt another cartridge's RAM) when it did
      not. The full base-addressed rewrite (~2.5 KB, estimated) stays filed for later.
      📋 The readiness map for the C-BIOS port: [docs/disk/port-readiness.md](../../docs/disk/port-readiness.md) (2026-11-25):
      the disk ROM has 0 B usable, so the guard needs room carved first.
      ✅ STEP 4 (d), THE GUARD (2026-11-25). disk/kernel.asm init_gate: after the SHIFT test, HIMEM is compared with
      $F380; any other value means a cartridge scanned before us claimed RAM, and INIT declines exactly as SHIFT held
      does (no hooks, no claim, DISKSLOT_OK 0). Room: carved the same day (D-DISKROOM, below). 🔴 THE FIRST FULL GATE
      WAS RED in 4 disk units (scratchpad/AE_room_full.out): A>BASIC reruns the ROM INITs with MSX-DOS's HIMEM $DF93
      still in the cell, the guard declined, and BASIC came up with no disk (scratchpad/AE_room_dosbasic.out). Fixed:
      basent_tramp's bt_keep (both restart paths) puts HIMEM back to $F380 before re-entering the main INIT, as at
      power-on -- the hooks were already reset there. MEASURED (probes/disk/disk_probe_guard.py + the test cartridge
      probes/disk/claimer.asm, which lowers HIMEM by 16; scratchpad/AE_room_guard.out): zerobas with no cartridge 2
      drives / $DE77 / DSKF 706 as the CF-3300; with the claimer, 0 drives and DSKF "Illegal function call" -- declined.
      The CF-3300 installs either way ($DE57 with the claimer: its work area follows its claim) -- that is what (d)'s
      base-addressed rewrite would give zerobas. 🔮 scored: "zerobas + claimer reads HIMEM $F370" MISSED -- it reads
      $F380: zerobas BASIC's boot drops a small claim ([D-CARTCLAIM](D-CARTCLAIM.md), filed). Disk collection on the
      new ROM (scratchpad/AE_room_diskcorpus.out): every class the same as AE_s4_diskcorpus.out but f1sp3d-2.dsk
      BOTH-RUN -> UNSETTLED; sampled again at 10..90 s it is BOTH-RUN (at 45 s the PC sat in a BIOS RAM routine, $F38C,
      which the classifier rightly refuses as a reading) -- not worse (🔮 "none worse": HIT on re-reading).
      D-DISKROOM, the carve that paid for it: five tails shared (hkg_st, hk_claim_status -> hka_st; frp_full ->
      fac_full; fdel_ioerr -> fren_ioerr), two `jp` -> `jr` (fname_ev, hrh_him), the pinned $5E10 entry falls into
      basent_body instead of jumping to the next byte, and write_sector shortened (10 -> 8 B) and moved in front of the
      $7F7C pin to make room for bt_keep's reset. What is left is under the wall tool's 16-byte floor.
      LEFT of step 4: (d)'s base-addressed work area (host independence, ~2.5 KB estimated -- no room for it).
      🧭 JOOST 2026-11-26: the base-addressed work area (compatible with other devices claiming RAM) ranks AFTER the
      disk-ROM re-read and D-BUFINCTL, and BEFORE the other filed disk fixes. The ~2.5 KB was never counted: first
      SIZE it (every work-area reference and how it is reached; schemes: a base register for hot paths, a base kept
      in SLTWRK as the references do, relocating only what can overlap a foreign claim), then build.
      ✅ STEP 4 (e) for (b) + (c) (2026-11-25): the disk collection (scratchpad/diskcorpus_run.py, 143 images) on
      0f5e72f1f against the last recorded run (scratchpad/diskcorpus_iffread.out): NO image worse (🔮 "none worse":
      HIT); BOTH-RUN 98 -> 99, UNSETTLED 19 -> 17; YOUMAKOR, xak2eng3 / 4 / 5 UNSETTLED -> BOTH-RUN, and TestameB
      UNSETTLED -> ZB-ONLY -- the CF-3300 crashes on it (D-DISKRUN, 2026-10-23), so zerobas alone running it is the
      expected reading (scratchpad/AE_s4_diskcorpus.out).
      📏 STEP 4 (d) SIZED (2026-11-26, [AE_wasize.md](../../scratchpad/AE_wasize.md)): the full base-addressed rewrite is 789 code sites
      naming zerobas's own cells below $F1C9 -- +2.3 to +3.6 KB by scheme (a base in SLTWRK through a helper: ~90 cycles
      a reach instead of 14-17), 4-6x the room; the ~2.5 KB estimate was right for THAT. But the references do not do
      that rewrite: with a foreign claim of N bytes everything they keep BELOW $F1C9 (SLTWRK's base, the DPB, the
      sector buffers, the $4030 pointer and MSX-DOS's $0006, HIMEM at every moment, FRE) moves down by exactly N, and
      $F1C9-$F37F stays at its addresses -- written over the foreign claim, 439 of 439 bytes
      ([AE_wasize_claimN.out](../../scratchpad/AE_wasize_claimN.out), [AE_wasize_threshold.out](../../scratchpad/AE_wasize_threshold.out)). Both references fail to reach Disk BASIC at N = 474
      ([AE_wasize_threshold2.out](../../scratchpad/AE_wasize_threshold2.out), [AE_wasize_threshold_hbd.out](../../scratchpad/AE_wasize_threshold_hbd.out)). So the outside can be matched with every
      cell left where it is and only the NUMBERS shifted: scheme D, ~41 B (CLAIM_D = -N in INIT; init_gate declines
      only N > 439, or 472 with HOOK_SLOT moved into a free fixed-area byte; layout_rebuild, the $4030 entry and
      DRVTBL +1 / +3 add it), +~25 B to publish SLTWRK as the references do. NEXT: build D.
      🔴 probes/disk/claimer.asm claims 32 B on the references, not 16: its 16 KB image is mirrored into page 2 and its
      INIT runs twice there (once on zerobas's C-BIOS machine) -- the "$DE57 with the claimer" above is that. A
      comparison needs a claim-once cartridge.
