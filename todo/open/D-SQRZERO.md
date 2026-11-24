- [ ] 🐛 **`SQR(0%)` RETURNS A ZERO WITH LEFTOVER DIGIT BYTES HERE; THE VG-8020 RETURNS 8 ZERO BYTES (D-SQRZERO,
      found 2026-11-24 by D-KWSPEC's maths unit).**
      🎚️ TIER 6 — the value is 0 on both machines; only the result's bytes (VARPTR / PEEK) differ.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out), rule R-SQR-ASSIGN on
      [SQR.md](../../docs/keywords/SQR.md) (what `R=SQR(x)` stores).
      After `R=-12345`, `R=SQR(N%)` with N% = 0 stores 00 12 34 50 00 00 00 00 here (KMA MI SQR 0) and `R=SQR(-0)`
      00 13 40 50 ... (KMA FX 110): exponent byte 0, the digit bytes whatever the number accumulator held before.
      The reference stores 8 zero bytes. After `R=0` the leftovers are zeros and the two agree (KMA FX 117); a
      single or double zero argument agrees (`SQR(0!)`, KMA FX 118; KMA MS / MD SQR 0).
      ➡️ When picked up: `evmc_sqr` (basic/expr.asm) / `fp_sqrt` (sub/fp_sqrt.asm), the path an INTEGER zero takes
      to a double: it seems to set the exponent byte without clearing the digit bytes (not yet read). The
      acceptance is R-SQR-ASSIGN (2 zerobas cases); through USR the result is a clean zero on both (the leftovers
      there happened to be zeros), so R-SQR-ZERO agrees.
