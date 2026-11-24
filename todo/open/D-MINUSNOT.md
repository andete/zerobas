- [ ] 🐛 **`-NOT 0` IS A SYNTAX ERROR ON ZEROBAS; THE VG-8020 EVALUATES IT AS -(NOT 0) = 1 (D-MINUSNOT, found 2026-11-24
      by D-KWSPEC's operators unit).**
      🎚️ TIER 1 — a valid expression refused (happy path), though rare in programs: re-tier if Joost prefers.
      🤖 **AUTONOMOUS** — measured by [`kops.py`](../../probes/basic/spec/kops.py) group FX ->
      [`KOP_run1.out`](../../scratchpad/KOP_run1.out); rule R-NOT-PREC on [NOT.md](../../docs/keywords/NOT.md): KOP FX
      53 (`R=-NOT 0`: 1, an integer, on the reference; error 2 here, from `R=` and from `USR(...)`). NOT after other
      operators (`1+NOT 0` ...) is not measured yet.
      ➡️ When picked up: the unary-minus operand parser must accept NOT (and so a NOT-level expression) as its
      operand. The acceptance is R-NOT-PREC and the control "a minus before NOT a Syntax error -- zerobas's" in
      [`kops_controls.py`](../../probes/basic/spec/kops_controls.py).
      Goldfish pass 1 (2026-11-24): WIDER -- NOT after ANY operator is refused here: `2*NOT 0` (-2 there), `2+NOT 0=0`
      (2 there), `-NOT 0=1` (1 there) are all error 2 here (KOP FY 17-19). On the reference NOT, wherever it stands,
      takes in a whole comparison-level expression. The acceptance grows to those rows.
