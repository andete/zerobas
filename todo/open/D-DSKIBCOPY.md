- [ ] 🔴 **`COPY "A:X" TO "B:Y"` PROMPTS FOUR TIMES ON THE CF-3300 AND ONCE HERE
      (D-DSKIBCOPY, found 2026-10-27 by D-DSKIB).**
      🎚️ TIER 6 — the prompts of a copy between the two logical drives
      🤖 **AUTONOMOUS** — the CF-3300 settles it; measure a bigger file first.
      📏 [`dskib_run3.out`](scratchpad/dskib_run3.out) `copyab`: B:, A:, B:, A: for one small file
      (it swaps per buffer); zerobas names one drive per operation, so it prompts
      once. The copy is the same. Measure how the count scales with the file's size
      before modelling it.
