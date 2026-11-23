- [ ] 🔴 **`RUN`'S T5 RATIO FLIPS BETWEEN RUNS — 1.1×, 1.5× AND 1.7× ON 2026-09-28 —
      SO `tiers-md-check` GOES RED AFTER ANY BATTERY THAT RE-RUNS `kwtime` (D-RUNT5NOISE).**
      🎚️ APPARATUS — a red that carries no information about the ROM.
      🤖 **AUTONOMOUS** — find why RUN's keyword-alone reading is unstable (its row
      re-runs a program, so the twin subtraction may be timing the reboot of the run
      rather than RUN itself) and either stabilise it or report it as `~`.
      📏 Three readings in one day, one ROM: 1.1× (07:40), 1.5× (15:30), 1.7× (the
      batch-10 FULL run, `scratchpad/b10_scoped.out`). Twice today the only red in a
      battery was this cell, and each time the fix was regenerating the doc.
      📏 **2026-09-29 — NOT RUN ALONE, AND THE NOISE IS THE REFERENCE'S:** FIELD's T5
      went 1.94× → 8.66× between two runs with zerobas's `fieldkw` identical to
      0.01 ms (2128.9) and the CF-3300's row moving 4012 → 3821 ms, because the second
      run re-measured the reference instead of replaying its cache
      ([`noasto_kwtime.out`](../../scratchpad/noasto_kwtime.out) against
      [`copywild_kwtime.out`](../../scratchpad/copywild_kwtime.out)). The twin subtraction
      makes a ~5% reference wobble a 4.5× swing in the cell. Four other disk keywords
      moved the same run (BLOAD, DSKO$, KILL, LSET). So the fix is not RUN-specific:
      a T5 cell whose REFERENCE side is a disk row needs either several reference
      samples or a stability rule before it is shown as a number.
