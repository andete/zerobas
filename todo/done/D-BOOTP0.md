- [x] 🔴 **AT THE BOOT CODE'S STEP-7 ENTRY ZEROBAS HAS PAGE 0 = `jp $0005` / `jp $DECD`; THE CF-3300 HAS $0000-$0007 ALL ZERO --
      CALCULUS READS $0006 AS ITS TPA TOP ($0000 = 64 KB there, $DECD here) AND REFUSES: "Not enough TPA-memory"
      (D-BOOTP0, found 2026-11-27 from D-DISKRUN's calculus.dsk lead).**
      🎚️ TIER 1 — a disk that boots and runs on the CF-3300 (calculus.dsk, ZB-ONLY in every corpus run).
      🤖 **AUTONOMOUS** — black box: page-0 RAM at the boot code's entry ($C01E, page 0 = RAM) and the program's reads.
      MEASURED (scratchpad/calc_tpa_probe.py -- no PC recorded, page 0 read only while it is RAM 3-0;
      [AE_calc_tpa2.out](../../scratchpad/AE_calc_tpa2.out), [AE_calc_tpa3.out](../../scratchpad/AE_calc_tpa3.out)): at the second $C01E entry (A8 = $FF) the CF-3300's $0000-$0007 =
      00 x 8 on calculus.dsk AND on test.dsk (an MSX-DOS disk); zerobas's = C3 05 00 FF FF C3 CD DE. CALCULUS reads
      $0006-$0007 at 11.566 s on the CF-3300 (word $0000) and at 9.9-10.0 s on zerobas (word $DECD, 12 reads).
      🔴 THIS CONTRADICTS D-BOOTREGS (0b417fb30), which laid `jp $0005` at $0000 and `jp BR_BDOS` at $0005 "as on the
      CF-3300 before MSXDOS.SYS" from scratchpad/wboot_run.out: a boot code doing `jp 0` reached $0005 on the CF-3300
      -- consistent with a NOP SLIDE through zeroed page-0 RAM, not a vector (it then wedged). The vectors also serve
      boot codes calling $0005 before MSXDOS.SYS (the D-TPAP1 / fray disks D-BOOTREGS fixed: BOTH-RUN 108 -> 118), so
      the fix must keep those running: MEASURE what those disks call first, then decide (zero $0000-$0007 at step 7 as
      the CF-3300 does and keep the bridge only where the CF-3300 has one, e.g. $F37D).
      ⚠️ scratchpad/wboot_run.out / wboot_run2.out / bootcallf_run.out / bootcallf_run2.out record SAMPLED PC VALUES
      on the reference machine -- a clean-room breach, raised with Joost 2026-11-27 (not read further).
      ACCEPTANCE: calculus.dsk BOTH-RUN; the fray disks and the rest of the collection no row worse.
      📏 THE CF-3300'S WHOLE PAGE 0 at that entry ($0000-$003F, [AE_bootp0_page0.out](../../scratchpad/AE_bootp0_page0.out)): `jp` vectors at $000C / $0014 / $001C /
      $0024 / $0030 / $0038 ONLY, every other byte 0 -- no $0000 jump, no $0005 entry. zerobas: the same RST vectors plus
      `jp $0005` at $0000 and `jp BR_BDOS` at $0005, and $FF fill between.
      ✅ FIXED 2026-11-27: install_dos_env zeroes $0000-$003F (DE kept: it runs on into WA_SEG) before lay_page0_env lays
      the RST vectors; the $0000 jump and p0_env_tab's $0005 row are gone ($F37D's stub still bridges through BR_BDOS).
      A boot code's `jp 0` now NOP-slides into the RDSLT vector at $000C, as on the CF-3300.
      calculus.dsk ZB-ONLY -> FILES-SAME; the fray disks D-BOOTREGS fixed (frayd1 / frayg1 / frayd1i / frayg1i, frayd0)
      still BOTH-RUN ([AE_bootp0_try1.out](../../scratchpad/AE_bootp0_try1.out)). Corpus ([AE_bp0_diskcorpus.out](../../scratchpad/AE_bp0_diskcorpus.out)): two rows moved -- calculus as above, and
      Seedofda.dsk UNSETTLED -> ZB-ONLY: on the old ROM zerobas sat in a page-0 loop (PC ~$01BE, SCREEN 0, blank) from
      20 s; now it is in SCREEN 1 like the CF-3300 (which is UNSETTLED itself on it, blank, PC in ROM) -- sampled 10..90 s
      on both ROMs ([AE_bp0_seedofda.out](../../scratchpad/AE_bp0_seedofda.out)); not worse. nobasic / dossession / bdos / bdos-cfhost / diskbasic / boot5e10 /
      callsystem / bdosf37d acceptance green; unit tests 101/101 (test_bdosbasic pinned $0005 -> BR_BDOS: inverted to "the
      six RST vectors, no $0005"); knife re-pinned.
