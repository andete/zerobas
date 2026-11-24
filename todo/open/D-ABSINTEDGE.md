- [ ] 🐛 **`ABS(-32768%)` IS A SINGLE ON THE VG-8020 AND A DOUBLE HERE (D-ABSINTEDGE, found 2026-11-24 by D-KWSPEC's
      maths unit).**
      🎚️ TIER 6 — one value at one edge, and only its TYPE differs: both machines give 32768.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out), which sees a result's type through the probe's own USR
      routine (VALTYP and DAC as USR receives them). Rule R-ABS-INT on [ABS.md](../../docs/keywords/ABS.md): every
      other integer gives an integer, and -32768%, whose 32768 is no integer, gives the SINGLE 32768 (45 32 76 80) on
      the reference -- here the DOUBLE 32768 (KMA MI ABS -32768; KMA FX 16, `ABS(&H8000)`). The value is the same, so
      PRINT, `/` and assignment cannot tell them apart (a scratch check of `ABS(A%)/B!` printed the same on both);
      a USR routine reading VALTYP, or the precision of a later single-only step, can.
      ➡️ When picked up: `evmc_abs` in basic/expr.asm (the -32768 path). The acceptance is R-ABS-INT and its control
      "ABS(-32768%) the DOUBLE 32768 -- zerobas's rule" in
      [`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py) (FALSE on 1 of the reference's cases).
