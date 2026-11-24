- [ ] 🐛 **`INT` OF A NEGATIVE NON-WHOLE SINGLE OR DOUBLE CHANGES TYPE ON THE VG-8020 -- THE INTEGER -1 ABOVE -1, A
      DOUBLE BELOW -- AND KEEPS THE ARGUMENT'S TYPE HERE (D-INTNEGTYPE, found 2026-11-24 by D-KWSPEC's maths unit).**
      🎚️ TIER 6 — the values agree in every case; only the result's TYPE differs, which no PRINT tried shows.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out) (the result's type through the probe's own USR routine). Rule
      R-INT-NEGFRAC on [INT.md](../../docs/keywords/INT.md): on the reference `INT(-.5!)`, `INT(-1E-64!)`,
      `INT(-.9#)` are the INTEGER -1 (FF FF); `INT(-1.5!)`, `INT(-32768.5!)`, `INT(-12345.6!)` are DOUBLES (-2,
      -32769, -12346: c1 20 00 ... 8 bytes); a single stays a single only when it is zero, positive or whole. zerobas
      returns the argument's own type in all 26 cases (KMA MS INT -.5 ... -32768.5, KMA MD INT -.5 / -.9 / -1D-10 /
      -1D-14 / -1D-64 / -.99999999999999, KMA FX 55 `INT(-2.5)`, KMA FX 68 a single 80 10 00 00). The values agree;
      `/`, PRINT and assignment to a double could not tell them apart in a scratch check (`INT(-1.5)/B!` printed
      -.66666666666667 on both).
      Goldfish pass 1 (2026-11-24, group FZ): nested 16 and 32 deep, `INT(INT(...(-2.5)...))` is the double -3 on
      the reference and the single -3 here (KMA FZ 4, 5; rule R-INT-NEST) -- the same difference, carried through.
      Stored in a variable it is invisible: `T%=INT(-.5)` is -1 and `T!=INT(-1.5)` -2 on both (KMA FY 56, 60).
      ➡️ When picked up: `evmc_int` in basic/expr.asm (its "subtract 1 when a negative number lost a fraction" step, spec-basic-math-pack.md §9). The acceptance is
      R-INT-NEGFRAC and its control "the argument's own type -- zerobas's rule" in
      [`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py) (FALSE on 24 of the reference's cases).
