- [ ] 🐛 **`ABS("A"` (NO `)`) AND `ABS("A",2)` ARE A SYNTAX ERROR (2) ON THE VG-8020 AND A TYPE MISMATCH (13) HERE --
      THE REFERENCE REQUIRES THE `)` BEFORE IT REFUSES A STRING ARGUMENT (D-ARGTYPEORDER, found 2026-11-24 by
      D-KWSPEC's goldfish pass 1 over the maths unit).**
      🎚️ TIER 6 — a malformed call that is also wrongly typed; only the error code differs.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) (group FY) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out). Rule R-*-ORDER on [ABS.md](../../docs/keywords/ABS.md),
      [SGN.md](../../docs/keywords/SGN.md), [INT.md](../../docs/keywords/INT.md), [FIX.md](../../docs/keywords/FIX.md),
      [SQR.md](../../docs/keywords/SQR.md): on the reference the argument is evaluated first (`F(1/0` and
      `F(1/0,2)` raise its own error 11, on both machines), then the `)` is required, then the type is checked:
      `F("A"` and `F("A",2)` are error 2 there. zerobas raises 13 for both, for all five functions (10 cases: KMA FY
      1, 3, 8, 10, 15, 17, 22, 24, 29, 31). `F("A")` (closed) is 13 on both (KMA FX 0 ...).
      Not measured for the other functions that share the argument reader (EXP ... ATN, CINT ...). Related, not the
      same: D-TMORDER (where an operator's type mismatch is raised), D-CLOSESPACE.
      ➡️ When picked up: `ev_mc_arg` in basic/expr.asm (the shared math-function argument reader) -- the type test
      seems to come before the `)` test (not yet read). The acceptance is R-ABS-ORDER ... R-SQR-ORDER and the control
      "the argument's type checked before the `)` (13) -- zerobas's rule" in
      [`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py).
