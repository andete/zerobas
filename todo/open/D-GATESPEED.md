- [ ] ⏱ **D-GATESPEED — THE BATTERY'S WALL TIME, EVERY ITEM OF THE 2026-11-25 REVIEW (Joost: "fix all of these please,
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
      OPEN: A2 the three refcache holes (verify battery) · A5 fingerprint-skip unit-test / selftest-check on docs-only
      · A3 lnblank-say out of the excluded five; time the five · B3 shard kwsweep · B4 one host-wide slot budget
      (A/B) · B5 repack-machine as a stamp · B6 proc.wait polling · A6 programs / intarg daily (knife check first) ·
      W2 the "~20 s" / "65 serial-seconds" comments · W10 the lineerr banner · per-unit rusage · B1 step 2: split the
      own-live probes by group (the long pole is now one probe's serial cases) · check_disk_deps --selftest (30 s,
      a planter, alone) and tier_table --selftest (33 s): why so slow.
