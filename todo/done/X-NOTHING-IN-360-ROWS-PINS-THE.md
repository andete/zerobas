- [x] ⚠️ **NOTHING IN 360 ROWS PINS THE TENANT'S `GRPACX` STORE.** Filed
      ✅ **CLOSED 2026-09-05.** The verdict is delivered — KEEP THE WRITE, on
      TWO independent knives that each move 0 of 360 rows, with the code's own
      justification corrected rather than deleted. The text below the verdict
      is the ORIGINAL FILING, kept for the record; nothing in it is open.
      🔴 **AND IT WAS INVISIBLE TO `closesweep.py` UNTIL TODAY**: its `DONE`
      vocabulary had no `ANSWERED`, so this block was never even shortlisted.
      A false NEGATIVE there is worse than a false positive, because nothing
      prints it [[readout-blind-to-its-own-subject]].
      2026-08-17 by D-GATEBLIND round 5 (§21.2). ✅ **READ AND ANSWERED
      2026-09-05 (D-GRPACDUP) — the residual asked for exactly this and the
      answer inverts the code's own justification.**
      🔴 **THE CIRCLE-SPOKES WORRY IS FALSE.** `gco_done` writes GRPACX/GRPACY
      **unconditionally, AFTER** calling `gco_spoke_s`/`gco_spoke_e`, so a
      spoke's own work-area write is always superseded — `gfx_line_op`'s own
      header says so in as many words ("a spoke's endpoint never survives as the
      last-referenced point"). The comment at `basic/graphics.asm` that keeps the
      duplicate *because* "the CIRCLE spokes ... rely on it" is therefore wrong
      about its reason; corrected in place, not deleted.
      🔴 **AND ON THE LINE PATH THE RESIDENT ALREADY WROTE p2**: `elg_second`
      parses p2 and then `call gfx_point_gate` → `gfx_work_area`, BEFORE the
      tenant runs. That is why the store is unobservable, and it is a mechanism
      the residual could not see from the gate's silence.
      🔬 **TWO INDEPENDENT KNIVES AGREE**: `K-GR4` (divert the store) and
      `M-GRPAC2` (feed it the Y value) each move **0 of 360 rows**. M-GRPAC2's
      own PREDICT named 8–9 rows and **had never been run**; corrected in the
      sweep, with the wrong prediction kept beside it.
      ✅ **VERDICT: KEEP THE WRITE, and the residual's "before removing ~3 B"
      is answered "do not".** The bytes are sub page 0, which `make basic-reloc`
      printed at **1348 B free** on 2026-09-05 — there is no budget pressure, so
      removing a redundant write buys nothing and risks a path no row watches.
      The conclusion the code reached stands; only its reason was wrong.
      --- the original filing ---
      `K-GR4` diverts
      `gfx_line_op`'s `ld (GRPACX),hl` and **not one row of 360 moves** — the
      resident's write covers the drawn path and the tenant never runs on the
      error path. 💰 It may still be load-bearing for **CIRCLE's spokes**, which
      call `gfx_line_op` internally (`gco_done` writes the circle's own work-area
      values AFTER the spokes, so the ordering matters); before removing ~3 B of
      sub p0, READ that path rather than trusting the gate's silence — the gate
      having no row for it is exactly what this residual says. ⚠️ The claim is
      narrow: only the `GRPACX` store was diverted, not `GXPOS`/`GYPOS`/`GRPACY`.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
