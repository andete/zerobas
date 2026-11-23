- [x] ⚠️ **THE `tools/` SEED ARM IS AN INTERSECTION, NOT AN ASSERTION** (filed
      2026-08-22 by D-SEEDHOLE2, §11.5). `init`, the sub entry-table tenants and
      the resident-ABI import each fail loudly if they stop resolving; the
      `tools/` arm is `set(m.nodes) & external_names(['tools'])`, so a main
      routine renamed out from under a `tools/` by-name `.sym` lookup drops out
      of the seed set **silently**. It over-seeds by construction, so the failure
      direction is a MISSED finding rather than a false one — which is why it is
      filed rather than fixed. 🔴 **`docs/spec-deadcode-gate.md` §2.2 claimed
      *"every seed name is asserted to resolve to a real label"* for the whole
      set; that sentence was never true of this arm.** Corrected in place, not
      deleted. The real fix is a per-tool lookup model, not a stricter regex.
      ✅ **MEASURED AND GUARDED 2026-09-05 (D-SEEDARM) — the hole is real and
      its EXPOSURE IS ZERO, so the coarse arm is safe to leave coarse.**
      The arm contributes **37 seeds of 1650 main nodes, 23 of them seeded no
      other way** — and **removing it entirely changes no finding**: dead-with =
      dead-without = **0**. Every name it seeds is already reachable from `init`
      + the resident ABI + the prologue seeds, so BOTH failure directions are
      empty today: nothing is over-seeded into invisibility, and a rename can
      drop a seed without costing anything.
      🎯 **THE GUARD IS NOT "every tools/ name resolves"** — that IS the per-tool
      lookup model, and this does not substitute for it. It is **"this arm still
      carries no weight"**: `deadcode` now computes `dead(seeds)` with and
      without the arm and REFUSES if they differ, naming the routines that have
      become dependent on it. The moment the arm starts carrying weight is
      exactly the moment its silence begins to matter, and that is when the real
      model is owed — for the specific names the failure prints.
      🔬 **ARMED**: forcing the arm to matter (dropping `init`+abi from the
      comparison baseline) makes it refuse with rc 2 and name 1569 routines;
      restored byte-identically, `deadcode` green again.
      ⚠️ So this closes the *"filed rather than fixed"* status honestly: the
      hole is not fixed, it is **measured empty and instrumented to say when it
      stops being empty**.
      ☑️ **BOX TICKED 2026-09-06 — the work landed on 09-05 and the checkbox did
      not follow it, which is the failure the very next item in this section
      describes.** Nothing was owed but the tick: `make deadcode` is green today
      (main 0 dead, sub 0 dead + 2 allowlisted, both still verified dead), the
      weight-comparison guard is live in
      [`tools/check_dead_code.py:622`](../../tools/check_dead_code.py:622), and the
      only remaining scope is CONDITIONAL — the per-tool lookup model is owed
      *when the arm starts carrying weight*, and that gate is precisely what
      announces the moment. A residual whose trigger is gated is not an open
      item; it is a gate.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
