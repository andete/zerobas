- [x] ⏱ **D-GATESPEED — THE BATTERY'S WALL TIME, EVERY ITEM OF THE 2026-11-25 REVIEW (Joost: "fix all of these please,
      this is the biggest issue with zerobas development").**
      🎚️ APPARATUS — every commit pays for the batteries; Joost ranks it first (2026-11-25).
      🤖 **AUTONOMOUS** — the review is [docs/gate-time-review-2026-11-25.md](../../docs/gate-time-review-2026-11-25.md);
      each item carries its own verify step. Ranked FIRST, ahead of the disk ROM queue (Joost, 2026-11-25).
      ✅ W1: the printed wall is measured from the battery's start (t_start); the mutator phase and the refresh time
      themselves with _t0. Every earlier wall figure was ~105 s low.
      ✅ B1: spec-live's own-live screen probes join its pool, longest first. Measured alone, REFS mode, 83 zerobas
      readings both ways, ALL PAGES AGREE both ways: 280 s -> 161 s (scratchpad/AE_speed_spec_live_before.out,
      AE_speed_spec_live.out).
      ✅ W7: zerobas's reading of one .asm on one machine is measured once and shared by the disk / cf3300 / nms8250
      rows. SPEC_LIVE_DEDUPE_CHECK=1 proved it: 38 of 38 shared readings byte-equal (AE_speed_dedupecheck.out);
      161 s -> 133 s.
      ✅ A1: below FULL, spec-live runs only the pages a change can move (pick_gates.spec_live_scope: a module's
      footprint = its import closure + the run files evaluate() records it opening + its page; an unclaimed input,
      a spec tool or a ROM change runs every page). Selftest arms P-SLSCOPE, negatives included.
      ✅ A4 + B2 (part): selftest-check runs the 2 planters (PLANTERS, measured by `--classify`) alone, the other 88
      on 8 workers, with a guard that turns it RED if a selftest outside PLANTERS moves a tracked file; inside a
      battery it skips the 20 selftests a unit of the same run already runs. 88-110 s -> 65 s (AE_speed_cs.out).
      run_gates gives a mutator's restored files their old mtime back (index blob / saved bytes compared), so the
      post-mutator refresh has nothing to rebuild (a no-op WARM is 0 s). pick_gates's selftest 23 s -> 6 s
      (footprints memoised).
      ✅ A2, the three refcache holes (batch 2): (1) a temp path in a key is keyed by its BYTES (a printer log as
      <OUT>: openMSX truncates it on plug), (2) run_case goes through run_cases' wrapper, (3) run_programs,
      run_sessions and the lof / badfnum launcher go through cached_run (+ `optional=` outputs: a session that prints
      nothing). Each suite run twice, REFS mode, output identical: lptverb 48 -> 11 s, intarg 36 -> 14, programs
      104 -> 74, sessions 33 -> 21, lof 17 -> 10, badfnum 29 -> 11, editverb 38 -> 12, outdlp 20 -> 9, abort 31 -> 19
      (scratchpad/AE_speed_*.out). 🔴 THE CATCH THE REVIEW PREDICTED ("a key that is too coarse"): cassave and
      tapebios went RED on the replay run -- their reading includes a TAPE the machine records (`cassetteplayer
      new`), which a hit cannot recreate; they had missed by accident before (the fresh path was in the key).
      side_output() now runs any call that records a tape, writes a savestate or reads a printer log from the file
      LIVE (selftest KM7, negatives included); both green on two runs. omsx_session.py left alone: its users
      (diskbasic-acceptance) run zerobas only, which is never cached.
      ✅ B6: the watchdog loops wait on proc.wait(timeout) instead of a fixed sleep (omsx_repl + the launchers).
      ✅ A3: lnblank-say-acceptance is a daily suite beside its twin, out of the excluded five (pick_gates, gate_wt).
      ✅ B5: repack-machine is a stamp in build/ (a no-op make 0.06 s); W9's docstring corrected.
      ✅ W2 / W10: the stale timing comments, and the banner names lineerr's shards only when they run.
      ✅ per-unit CPU: run_gates' sh() records each unit's CPU (os.wait4) and prints the top ten + build/_cpu.json.
      ✅ A5 (batch 3), unit-test ONLY: an audit hook on every Python process of a unit-test run saw 1125 tracked
      files opened and none under docs/ / todo/ / TODO.md, so a STATIC / SCOPED run (--skip-proven, from the planner)
      skips unit-test when every other tracked file is byte-identical to a green unit-test's (run_gates ut_input,
      S-UTSKIP arms). selftest-check does NOT qualify -- the same audit saw it open ~650 docs/ and todo/ files.
      ✅ B1 step 2: run_cases' boot-per-case path may run its boots on a small pool (BOOT_PER_CASE_JOBS, default 1);
      spec-live uses 2: 133 -> 122 s, ALL PAGES AGREE (AE_speed_speclive3.out).
      ✅ B3, as an inner pool rather than shards: kwsweep's (machine, rig) groups run 4 at a time (serial when a
      hardware rig board drives a group). The verdict pin is byte-identical to a serial run's but for its
      `written` stamp; 125 -> 92 s warm (AE_speed_kw_j1.out, AE_speed_kw_j4.out).
      ⚠️ FULL 2 of batch 2 still missed 435 references (badfnum, programs, lof, sessions, the trap suites) though
      every one of them hits on a second run alone; FULL 1's entries did not match FULL 2's keys for a reason the
      overwritten logs no longer show. The next pair of FULL runs re-tests it.
      ✅ THE 435 (batch 3's pair): FULL 1 re-measured (2474 misses), FULL 2 replayed with 11 misses left (9 of them
      refcache-check's own selftest) -- the batch-2 figure was that pair's mismatch, not a standing hole.
      FULL 2: 287/287, wall 849 s, CPU 4928 s (AE_speed3_full2.out) -- against 1387 s / 8106 s re-measuring.
      ❌ B4, MEASURED AND REJECTED (2026-11-26): a host-wide emulator budget (probes/lib/emu_slot.py: flock + exec
      under ZEROBAS_EMU_SLOTS, from omsx_preflight.guarded()), A/B after a warm-up battery, 3 pairs: OFF (J 8, no
      slots) 847 / 855 / 837 s, ON (10 slots, J 12) 904 / 914 / 903 s -- ON is ~60 s SLOWER every time, and uses
      more CPU (scratchpad/AE_speed_b4_ab.out). The wrapper stays, opt-in and off; nothing runs it by default.
      ✅ A6, NO CHANGE, by the rule: intarg is no longer >= 60 s (46 s wall, 16 s CPU since its references
      replay), and programs is no longer never-red (4 reds in 187 gate runs in the 2026-11-26 census). Neither
      qualifies, so both stay in the battery -- no catch traded.
      ✅ W11: the excluded-five are timed. ✅ A red MUTATOR's log is now kept (gate_flakes): it is never retried, and
      selftest-check's one red in the A/B (OFF3) had been eaten by the next battery. ✅ check_selftests re-runs a
      pooled selftest that fails ALONE once and prints it as a FLAKE when it then passes (red alone stays red).
      LEFT (small, not the review's): spec-live's long pole is one own-live probe's serial groups; check_disk_deps
      --selftest (30 s, a planter, alone) and tier_table --selftest (33 s) are slow for unknown reasons; the store
      holds 1.8 GB of entries the 14-day expiry will prune now that temp paths no longer mint new keys (W4).
