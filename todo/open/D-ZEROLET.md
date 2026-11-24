- [ ] 🐛 **A SINGLE WHOSE EXPONENT BYTE IS 0 BUT WHOSE DIGIT BYTES ARE NOT (WHAT `FIX(.5!)` RETURNS) IS STORED AS ALL
      ZERO BYTES HERE; THE VG-8020 STORES ITS BYTES AS THEY ARE (D-ZEROLET, found 2026-11-24 by D-KWSPEC's maths
      unit).**
      🎚️ TIER 6 — the value is 0 on both machines; only the variable's bytes (VARPTR / PEEK) differ.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out). On both machines `FIX` / `INT` of a single below 1 in size
      returns exponent byte 0 with the argument's digit bytes (`FIX(.5!)` is 00 50 00 00, rules R-FIX-SMALL /
      R-INT-DOWN, agreeing). Assigned to a double (`R=FIX(N!)`), the reference stores 00 50 00 00 00 00 00 00 and
      zerobas 8 zero bytes (rules R-FIX-ASSIGN, R-INT-ASSIGN, R-ABS-ASSIGN on [FIX.md](../../docs/keywords/FIX.md),
      [INT.md](../../docs/keywords/INT.md), [ABS.md](../../docs/keywords/ABS.md); 24 FIX cases, 13 INT, 2 ABS). It is
      LET's, not the functions': a POKEd single 00 10 00 00 assigned with `R=N!` (KMA FX 115) and `N!=FIX(.5!)`
      stored back into a SINGLE (KMA FX 116) differ the same way. A double result with exponent 0 (`FIX(.5#)`) is
      stored as it is on both.
      Goldfish pass 1 (2026-11-24, group FY): stored in a SINGLE variable the same -- `T!=FIX(.5!)`,
      `T!=INT(.5!)` and `T!=ABS(N!)` (N! the POKEd 00 10 00 00) keep the digit bytes in T! on the reference and are
      00 00 00 00 here (KMA FY 62, 59, 53; rules R-FIX-TARGET, R-INT-TARGET, R-ABS-TARGET). The two LET rows are now
      a rule of their own, R-FIX-LET (KMA FX 115, 116). Stored in an INTEGER (`T%=FIX(.5!)`) both give 0.
      ➡️ When picked up: the store path of LET (and the single -> double conversion), which on zerobas normalises an
      exponent-0 number to a clean zero. The acceptance: the three ASSIGN rules and the control "a single exponent-0
      zero stored in R as 8 zero bytes -- zerobas's LET" in
      [`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py) (FALSE on 24 of FIX's reference cases).
