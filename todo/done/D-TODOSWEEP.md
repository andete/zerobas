- [x] 🔴 **D-TODOSWEEP'S OWN ELEVEN PROBES RE-IMPLEMENT THE `[...]` READER, WHICH
      IS THE TRAP THE ITEM BELOW DESCRIBES.** Filed 2026-08-26 by D-TODOSWEEP
      tranche 55, against itself. `probes/lib/omsx_repl.py` ships
      `result_span_after_echo` (:1765) specifically so *"an aborted case's echoed
      `[` is not misread as printed output"* — and
      `scratchpad/sweep_tranche{1,11,12,16,17}.py`,
      `scratchpad/{citepaths,patchfresh}_falsify.py` and
      `scratchpad/editscout_{layout,reentry,reentry2}.py` each carry their own
      `spans()` instead — **ELEVEN, not nine: the filed count was written from
      memory and corrected by counting 2026-08-26 (tranche 58)**, and **0 of the
      eleven import the shared reader**. 🎯 **THE ITEM WAS READ AFTER THE NINE PROBES WERE
      WRITTEN**, which is the item's own thesis demonstrated. ⚠️ None of the nine
      is a GATE — they are one-shot sweep instruments — so the exposure is to
      wrong readings in this sweep's own record, not to a green battery. The
      cheap fix is to import the shared reader; the durable one is whatever stops
      the next scratch probe copying the last scratch probe.
      🔴 **COUNTED A THIRD TIME 2026-08-26, AND 11 IS WRONG IN BOTH DIRECTIONS.**
      The real membership is **8**, and the list above names **ten** files for a
      count of eleven — it does not even agree with itself:
      * **NOT MEMBERS:** `citepaths_falsify.py` and `patchfresh_falsify.py`
        **never import `omsx_repl` and never read a screen** — they falsify the
        two citation gates. They were swept in by name, not by property.
      * **NOT MEMBERS (weaker sense):** `editscout_{layout,reentry,reentry2}`
        slice rows, but only to **print the whole screen** for inspection; they
        extract no `[...]` value, so they cannot misread one.
      * **MISSED:** `sweep_tranche2`, `sweep_tranche3` and `sweep_paintflood`
        each carry their own `spans()` and were not listed.
      🎯 **AND THE EXPOSURE IS VISIBLE, NOT SILENT — MEASURED, NOT ARGUED.**
      [`scratchpad/spanreader_diff.py`](../../scratchpad/spanreader_diff.py) separates
      the two readers on **4 of 4** cases: the hand-rolled one returns a LIST
      whose **first element is always the echo's bracket fragment**
      (`'";1+1;"'`), where `result_span_after_echo` returns the value. But
      **all 8 print the whole list** (`spans={...}`) and none picks an element in
      code — so the echo fragment was on the page for a human to see, and **no
      verdict rests on a code-chosen element**. The sweep's record is not
      corrupted by this.
      🔴 **ONE REAL HAZARD SURVIVES THAT MEASUREMENT.** On an **aborted** case
      the hand-rolled reader returns a **non-empty** list — the echo fragment
      alone — where the shared reader returns `None`. *"No output"* can therefore
      read as *"a value"*, which is this tree's oldest trap
      [[an-unnamed-outcome-reads-as-no-outcome]].
      ⚠️ **THE 8 WERE DELIBERATELY NOT REWRITTEN.** They are one-shot
      instruments whose printed output IS the sweep's evidence; changing the code
      changes what that record is reproducible from. The open half is the durable
      fix — whatever stops the next scratch probe copying the last — and
      today's `sweep_tranche65.py` is evidence it is still needed: it imports the
      shared reader now, but **its first cut hand-rolled a finder and read its
      own echo**, at rc 0.
      ✅ **THE DURABLE FIX SHIPPED 2026-08-26 as rule READER of
      `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](../../docs/spec-chokepoint-gate.md)). The 8 are
      PINNED with that reason in `tools/chokepoint-allow.txt`; a NEW unfenced
      reader is RED. Pins may shrink, never grow, and a stale pin is itself RED.
      🔴 **THIS ITEM'S SCOPE CLAIM IS FALSIFIED.** *"None of the nine is a
      GATE — so the exposure is … not to a green battery"* is wrong: **two gate
      probes define an unfenced reader**, `basic_probe_direct_ctrl.py` and
      `basic_probe_time.py`. On reading, both are SAFE — they use `#…#` markers,
      so `result_span`'s `[` never applies, and both handle the echo explicitly
      and say so — but the reason for not worrying was wrong even though the
      conclusion held [[a-justification-parenthesis-is-an-unrun-claim]].
      🔴 **THE RULE IS "REACHES A FENCE", NOT "DEFINES A `bracket()`"** — the
      first cut tested the name and reddened **24 correct gate probes** that wrap
      `screen_tail` and add sentinels. Wrapping a chokepoint is the goal; only
      bypassing it is the finding.
      ✅ **DONE** — counted, measured, and gated.
