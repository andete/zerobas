- [ ] 🐛 **`VAL("-32768%")` IS `Overflow` HERE AND -32768 ON THE VG-8020: zerobas TESTS `%`'S RANGE ON THE MAGNITUDE
      (D-VALPCT, found 2026-11-24 by D-KWSPEC's goldfish pass 1 on VAL).**
      🎚️ TIER 6 — one value at one edge: a `%`-marked string at exactly -32768 (or -32768.x), an error where the
      reference returns a number.
      🤖 **AUTONOMOUS** — measured by [`knum.py`](../../probes/basic/spec/knum.py) ->
      [`KNM_run1.out`](../../scratchpad/KNM_run1.out), rule R-VAL-SUFFIX on [VAL.md](../../docs/keywords/VAL.md). On
      the reference `%` cuts the value toward zero and THEN tests -32768..32767: `"-32768%"` and `"-32768.5%"` are
      -32768, `"-32769%"` and `"32768%"` error 6, `"32767.9%"` 32767, `"-1.5%"` -1 (KNM VL 187-193). zerobas agrees on
      all of them except the two at -32768, which are error 6 here (KNM VL 189, 192): it overflows from a MAGNITUDE
      of 32768, as if the sign were applied after the test.
      ➡️ When picked up: the `%` path of `tk_float` (sub/tkfloat.asm), which `VAL` calls; `READ` of a `DATA` item
      `-32768%` goes through the same scanner -- a row for it against the reference before changing anything (a
      typed `-32768%` in a program line is a unary minus on 32768%, a different path). The acceptance is rule
      R-VAL-SUFFIX and its control "% an overflow from a magnitude of 32768 -- zerobas's rule" in
      [`knum_controls.py`](../../probes/basic/spec/knum_controls.py) (FALSE on 2 of the reference's cases).
