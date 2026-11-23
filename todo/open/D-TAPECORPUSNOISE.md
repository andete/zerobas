- [ ] **D-TAPECORPUSNOISE — THE TAPE CORPUS'S PER-TITLE DIFFERENCE COUNTS SWING WITH TIMING, NOT ONLY WITH CORRECTNESS**
      🎚️ TIER 6 — apparatus (filed 2026-11-20).
      🤖 **AUTONOMOUS** — scratchpad/tapecorpus_run.py compares screens captured at fixed times after a load. Five runs
      on 2026-11-19 were byte-identical; then two commits that only shifted timing moved titles: the VDP batch
      (FILVRM / LDIRMV / LDIRVM a few cycles longer) took Ballblazer RUNS? 279 -> SAME and Elite RUNS? 254 -> NEAR 18,
      and D-OUTDOINIT (BASIC's screen output a few cycles shorter) took them back, Elite to RUNS? 3004. So a count,
      and a category near its boundary, can move with any speed change: read a corpus change as a TIMING signal
      first. Worth a capture taken at a game-synchronised moment (a known screen state) rather than a fixed time,
      or a per-title tolerance. Not a regression in either commit (no title lost a category against the run before
      the pair).
