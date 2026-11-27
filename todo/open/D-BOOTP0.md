- [ ] 🔴 **AT THE BOOT CODE'S STEP-7 ENTRY ZEROBAS HAS PAGE 0 = `jp $0005` / `jp $DECD`; THE CF-3300 HAS $0000-$0007 ALL ZERO --
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
