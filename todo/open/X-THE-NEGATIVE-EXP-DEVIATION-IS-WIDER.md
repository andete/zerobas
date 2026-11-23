- [ ] 📌 **THE NEGATIVE-EXP DEVIATION IS WIDER THAN §12.9 RECORDED — and it is
      DELIBERATE, not a defect.** Re-measured 2026-08-31 by D-NGRAM14,
      [`docs/spec-basic-ngram14.md`](docs/spec-basic-ngram14.md) §5, rows in
      `scratchpad/ngram14_probe.py`.
      [`docs/spec-basic-mathpack-slice2.md`](docs/spec-basic-mathpack-slice2.md)
      §12.9 recorded ONE argument (`EXP(-200)`) as a disposition BUG in the
      reference, with zerobas correctly returning the true 0. These rows show
      the whole negative tail behaves that way — `EXP(-150)`, `-175`, `-180`,
      `-200`, `-1E30`, `-1E38` all read `ERR 6` on both references and `0` here,
      while `EXP(-100)` (still representable) reads `3.72E-44` on all three and
      `EXP(1E30)` (a real overflow) reads `ERR 6` on all three.
      🎯 **AND IT IS PRODUCED BY TWO DIFFERENT PATHS.** K-N14B moves
      `EXP(-175/-180/-200)` and NOT `EXP(-1E30)`/`EXP(-1E38)`: the extreme
      arguments raise from `evmc_exp_huge` in the main ROM before the sub-ROM is
      dispatched at all, the rest from `fexp_underflow` in `sub/fp_exp.asm`.
      Worth knowing whenever §12.9 is revisited.
      🔴 **D-EXPNEG "FIXED" THIS TO MATCH THE REFERENCES AND WAS REVERTED IN
      FULL** — `math-acceptance` encodes the §12.9 decision and went red.
      Nothing here is owed; this entry exists so the next reader finds the
      MEASUREMENT rather than repeating the mistake.
      🎚️ STANDING — a DELIBERATE §12.9 carve-out in float output, not a live defect; it would be TIER 1 only if the carve-out were re-opened
      🙋 NEEDS-JOOST — only if the §12.9 carve-out is ever to be re-opened, and
      that is your call, not a gate's.
