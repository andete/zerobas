- [x] 🟢 **A DEAD REFERENCE MACHINE WAS CACHED AS A READING — FIXED 2026-09-02
      (D-SCRAPEMODE), AND THE HARNESS HAD DIAGNOSED IT THREE TIMES ALREADY.**
      Filed and closed the same day,
      [`docs/spec-scrapemode.md`](../../docs/spec-scrapemode.md).
      🔴 **THE DIAGNOSIS EXISTED AND WAS DISCARDED.** Re-running the exact call
      that wrote seven ghost entries prints
      `verdicts: ['BLIND/mode', 'BLIND/mode', 'BLIND/mode']`,
      `mis_echoed() == []`, `storable() == True`. `BLIND/mode` is emitted when
      the echo oracle reads **SCRMOD out of the machine's own RAM** and finds it
      non-zero — *"this scrape is not looking at the text plane"*. The harness
      concluded that three times out of three and dropped all three, because
      `mis_echoed()` counts only `MANGLED`.
      🎯 **THAT RULE IS RIGHT AND IS NOT THE BUG.** A blind SLOT really is a
      refusal to judge. But `BLIND/mode` is not a blind spot — it is a POSITIVE
      reading, from the machine, that the instrument is aimed wrong. Nothing
      downstream asked for it.
      ✅ **FIXED**: `scrape_invalid()` at the single `run_cases` chokepoint —
      every judged slot `BLIND/mode` ⇒ **do not store**, and say why on stderr.
      ⚠️ The predicate is `BLIND/mode` SPECIFICALLY, not "all blind": a probe
      that CLSes early legitimately produces `BLIND/rewrote` throughout, and
      refusing on that would redden correct runs.
      🎯 **IT REFUSES TO CACHE, NOT TO RUN** — readings still returned and
      printed, so an early refusal cannot bury a divergence the way 08-31's did.
      🟢 **RED AND GREEN ON THE SAME APPARATUS**, same machine and probe, only
      `reset` differing, scored by COUNTING CACHE ENTRIES ON DISK rather than by
      reading the guard's own message: off-plane 0 → 0 (refused, guard spoke),
      on-plane 0 → 1 (stored, guard silent).
      ➡️ **STILL OPEN, named:** the scrape is still SCREEN-0-only (this does not
      teach it `$1800`/32 columns — a stock MSX1 side must still inject
      `SCREEN 0` in its `reset`), and `storable()` still tests the wrong layer
      for every OTHER way a capture can be junk.
