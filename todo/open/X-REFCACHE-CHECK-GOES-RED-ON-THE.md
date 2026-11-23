- [ ] 🔴 **`refcache-check` GOES RED ON THE CALENDAR, AND THE RETRY ARM CALLS IT
      "REAL".**
      🎚️ APPARATUS — a time-dependent red is indistinguishable from a
      regression at the moment you have to decide whether to commit.
      🤖 **AUTONOMOUS** — no ruling needed.
      Observed 2026-09-19: a full `make gates` reported `rc=2 refcache-check`,
      retried it, printed **`retry refcache-check: rc 2->2  REAL (still red)`**
      and failed the battery. The suite then passed STANDALONE, and passed again
      under the battery's own `ZEROBAS_REFCACHE=0`, so the environment was not
      the cause.
      🔴 **THE CAUSE IS THE CLOCK.** `probes/lib/probe_refcache.py --maintain`
      reported `oldest 14.0d, cap 14d; pruned 27` on the first standalone run
      and `pruned 0` on the next: the store had aged PAST its 14-day cap during
      the battery, and the run that diagnosed it also REPAIRED it. A second full
      battery was then 42/42 green with `refcache-check rc=0`.
      ⚠️ **THE RETRY ARM IS THE PART THAT MISLEADS.** It exists to separate flakes
      from regressions, and it reported this one as REAL because a second run
      inside the same battery is a second run at the same instant — a boundary
      condition is not a race. A retry that cannot move the clock cannot classify
      a clock-driven red.
      ⚠️ **AND A GREEN RE-RUN WAS GREEN FOR THE WRONG REASON** — the prune had
      already fixed it [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      🟢 **PARTIAL 2026-09-19 (D-REFRACE) — ONE PROVEN MECHANISM REMOVED, AND
      THE ORIGINAL RED STILL NOT EXPLAINED.** `maintain()` walked the store
      TWICE, pruning against one `time.time()` and then measuring ages against a
      later one, so its own post-condition (*"after a prune no entry may be past
      the cap"*) could fail an entry that the prune had legitimately kept. One
      clock reading is now threaded through `_age`/`expired`/`prune`/
      `store_stats`, so the two walks cannot disagree about what time it is.
      🔴 **BUT THAT IS ALMOST CERTAINLY NOT WHAT WAS OBSERVED, AND SAYING SO IS
      THE POINT.** The gap between the two walks is MICROSECONDS; for it to
      matter an entry must sit within microseconds of the cap. The filed red had
      27 entries pruned and `oldest 14.0d` — plausible for a store aging out,
      not for a microsecond window. So this removes a mechanism that is provably
      red-capable, and does NOT close the item.
      ⚠️ **AND THE FIRST ARM I WROTE FOR IT WAS VACUOUS.** KA11 planted an entry
      half a second under the cap and asserted `maintain()` green — it passes
      with or without the fix, which a mutation reverting `prune(now=now)`
      DEMONSTRATED by leaving it passing. It is relabelled as a green control.
      KA12 is the arm with content: measure the post-condition a second later
      than the prune — the shape the code had — and the same store goes RED.
      🟢 **CANDIDATES TESTED 2026-09-19 (D-REFDIAG) — ONE REPRODUCES, ONE IS
      REFUTED, AND THE FILED INCIDENT IS STILL UNEXPLAINED.**
      🔴 **Candidate 1 REPRODUCES ON DEMAND:** an over-cap entry whose unlink
      fails (read-only parent directory) is counted by `except OSError: kept +=
      1` and is then INDISTINGUISHABLE from a legitimately young entry —
      `maintain()` goes red saying only *"an entry survived the prune"*, with no
      path, no age for the offender, and no hint that a delete failed.
      🟢 **Candidate 2 is REFUTED BY CONSTRUCTION, not by a test:** a concurrent
      writer cannot produce this symptom at all. `store()` writes through
      `mkstemp` + `os.replace`, so every entry it creates has a FRESH mtime and
      an age of ~0. A parallel suite can race the walk but cannot manufacture an
      over-cap entry.
      ⚠️ **NEITHER EXPLAINS THE FILED RED**, whose survivor sat at `oldest 14.0d`
      and pruned cleanly on the next run. So the item stays OPEN — but the next
      occurrence will name its own cause instead of needing reconstruction: the
      red now prints WHICH entry survived, its age to four decimals, its margin
      over the cap in seconds, and whether its unlink FAILED (`PRUNE_FAILED`,
      with the errno). The run that investigates it will no longer be the run
      that destroys the evidence.
      🔴 **AND A LARGER FINDING ABOUT MY OWN METHOD, WHICH COST A WRONG CLAIM.**
      D-REFRACE reported "KA11 is vacuous — a mutation reverting `prune(now=now)`
      left it PASSING". That conclusion was right and the EVIDENCE WAS NOT: the
      mutation was applied to a COPY of the file, and this module's selftest does
      `import probe_refcache as RC` (line ~617, deliberately — it tests the
      instance `omsx_repl` will use), so the copy's own code was never under
      test. **`assert the source changed` is necessary and NOT sufficient; the
      mutated code must BE the code under test.** Mutating IN PLACE and restoring
      afterwards shows the truth: reverting the one-clock fix made NO arm fail —
      KA12 passes `stats_now` by hand, so it exercises the shape without ever
      checking that `maintain` threads its clock into `prune`. **D-REFRACE's fix
      shipped UNCOVERED.**
      🟢 **KA15 covers it now**, and a mutation confirms it bites: plant a
      20-day-old entry, run `maintain` against a clock 30 days in the PAST, and
      the entry must SURVIVE (its age is negative at that clock). Revert
      `prune(now=now)` and it is deleted. Its negative control runs the same
      entry at the real clock and requires it to be pruned, so the arm is about
      the clock and not about expiry being broken.
      🟢 **✅ THE MISLEADING-VERDICT HALF IS FIXED 2026-09-21 (D-RETRYSUBJ) —
      AND BOTH VERDICTS WERE WRONG, NOT ONE.** The item said *"a retry that
      cannot move the clock cannot classify a clock-driven red"*; the deeper rule
      is that **a retry is only evidence when the first run did not change the
      subject**. `refcache-check`'s recipe ends `probe_refcache.py --maintain`,
      and maintain PRUNES — so the red run is also a REPAIRING run.
      * **Still red → not REAL**: a second run inside the same battery is a
        second run at the same instant.
      * **Green on retry → not FLAKE**: the first run fixed it, and counting that
        as a recovered flake launders a real repair
        [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. A fix that caught
        only the red half would have left this one standing.
      `tools/run_gates.py` gained `SELF_REPAIRING` + `retry_verdict()`: such a
      target reads **INCONCLUSIVE** in BOTH directions and is never added to the
      recovered-flakes list. ⚠️ **The battery's pass/fail is UNCHANGED** — rc is
      still rc; only the CLAIM about what the rc means is corrected.
      🔴 **MEMBERSHIP IS EARNED BY THE RECIPE, NOT ASSERTED:** arm S18 runs
      `make -n` on every member and requires a mutating flag in its own recipe,
      so the set cannot rot into a list of targets someone wanted to stop
      failing. Six arms (S13–S18); S15/S16/S17 verified to go RED with
      `SELF_REPAIRING` emptied **in the module under test**, which is the
      mutation discipline this item's own D-REFRACE entry had to learn.
      ⚠️ **THE ROOT CAUSE OF THE FILED RED IS STILL OPEN** — this fixes what the
      battery SAYS about it, not why the store aged out. The item stays open.
