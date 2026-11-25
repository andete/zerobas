- [ ] 🐛 **`ON ERROR GOTO A` IS `ON ERROR GOTO 0` ON THE VG-8020; ZEROBAS SAYS SYNTAX ERROR (D-ONERRVAR, found 2026-11-25 by
      D-KWSPEC's errors region, the ERROR / RESUME unit).**
      🎚️ TIER 6 — every error: a variable where ON ERROR GOTO's line belongs.
      🤖 **AUTONOMOUS** — [`kerr.py`](../../probes/basic/spec/kerr.py) -> [`KER_run1.out`](../../scratchpad/KER_run1.out)
      KER FX 34, a handler whose line is `100 ON ERROR GOTO A`: the reference reads no number, so it is GOTO 0 -- inside
      the handler that re-raises the original error, `Division by zero in 20`; zerobas raises `Syntax error in 100`.
      RESUME.md said "a Syntax error that the current handler does not catch" -- zerobas's behaviour, not the reference's;
      the page is corrected (rule R-RESUME-ONERROR).
