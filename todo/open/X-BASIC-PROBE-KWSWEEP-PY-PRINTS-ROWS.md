- [ ] 📌 **`basic_probe_kwsweep.py` PRINTS ROWS NO RUNNER CAN PARSE, AND ITS
      EXIT-2 PATH PRINTS A DIFFERENT TABLE ENTIRELY.** Found 2026-08-07 by
      D-ROWSHAPE's walk ([`docs/spec-probe-rowshape.md`](docs/spec-probe-rowshape.md)
      §2.4) — the hand-list in the residual above did not have it, and the walk
      did. `kwsweep`'s scored rows print `{state:5}  {key:9} {body}` with the
      body **undelimited**: no `repr()`, so a value containing a space cannot be
      recovered from the line by any parser, whatever the layout. It is
      therefore **out of the row-grammar contract by definition, not by
      exemption**, and `make rowshape-check` does not watch it.
      Its `return 2` block prints `    {k:9} {n} chars` — a *probe-defect* table
      (keywords whose direct-mode exec line exceeds one screen row), not its
      readings — so a runner holding a `kwsweep` baseline sees **zero** rows
      under that knife.
      ⚠️ **That abort is CORRECT** (the probe genuinely measured nothing) and the
      landed §Knives rule *"enumerate the probe's exit codes and parse all of
      them"* already covers it, which is why this is filed rather than fixed.
      **Priced:** de-tabulating the defect list is one line; giving the scored
      rows a parseable encoding is a format change to a **162-word** sweep whose
      re-run is the real cost, bought to prevent a fault the runner rule already
      prevents. **No byte count is implied.**
      ✅ **THE CHEAP HALF SHIPPED 2026-09-06 (D-KWFOOT), AND IT IS THE I3 HALF
      RATHER THAN THE DE-TABULATING ONE.** `probe_report`'s own invariant is
      *"every exit path that prints rows ends with `footer()`: a POSITIVE
      statement"* — and `basic_probe_kwsweep.py` had **FIVE exit paths and not
      one footer**, including the success path. So a runner could not tell *"the
      probe measured nothing"* from *"I failed to parse it"*, which is exactly
      the complaint in this entry's second paragraph. All five now say which:
      • `return 2` (defect table) — *"probe defect, nothing measured: the listed
        words' direct-mode exec lines exceed one screen row"*
      • `return 2` (`--only` typo) — *"nothing measured"*
      • `return 3` (ROMs changed mid-run) — *"DISCARDED … taken from more than
        one machine"*
      • `return 4` (control group failed) — *"NOT SCORED … the apparatus is not
        measuring what it claims"*
      • `return 0` — `ROWS: 55 printed, 37 scored — 18 crunch-only word(s) carry
        no support reading and are printed but not scored`
      ⚠️ **THE UNDELIMITED-BODY HALF IS UNCHANGED AND STILL OUT OF CONTRACT.**
      A footer says what happened; it does not make `{state:5}  {key:9} {body}`
      recoverable when the body contains a space. That is still the 162-word
      re-run this entry prices, and it is still not bought.
      🎚️ APPARATUS — kwsweep output
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
