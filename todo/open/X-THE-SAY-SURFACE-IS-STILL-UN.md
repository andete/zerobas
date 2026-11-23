- [ ] ⚠️ **THE `--say` SURFACE IS STILL UN-GATED OUTSIDE `ONLY=lnrd-`.** Split
      out 2026-08-09 from the `dir-name` item above, whose *payload* is now green
      (D-NAMSPC) but whose *apparatus* half never was. `--say` rows are filtered
      out of `lnblank-acceptance` entirely; `make lnblank-say-acceptance` exists
      but is scoped to `lnrd-` because THIS surface is where `dir-name` was
      hiding, and a whole-surface default would have shipped a red target.
      ✅ **That reason is now spent** — the row that made the default narrow
      reads ` 7 ` on all three sides — so widening the default is unblocked, and
      it is the fix. ⚠️ **A payload that now agrees says nothing about the rows
      nobody looks at** [[echo-guard-never-saw-say-rows]]: ask what else the say
      pass says BEFORE widening, because the answer decides whether widening is
      a one-line Makefile change or a slice.
      ✅ **ASKED AND ANSWERED 2026-09-06 (D-SAYWIDE): THE WHOLE SURFACE IS GREEN,
      AND WIDENING IS A COST DECISION RATHER THAN A RISK ONE.** Run unscoped,
      `basic_probe_lnblank.py --gate --say` over all three sides reads
      **771/771 gating rows agreeing**, with the same **2** rows allowlisted as
      `KNOWN_DIVERGE` and pinned to their exact values that the scoped target
      already carries. So the fear the narrow default was built around — *"a
      whole-surface default would have shipped a red target"* — is measured
      false.
      ⚠️ **AND THE ENTRY'S OWN DESCRIPTION OF THE SCOPING IS STALE**: it says the
      target is *"scoped to `lnrd-`"*, and the Makefile has listed **thirteen**
      prefixes for some time (`lnrd- kwgd- lnrt- dlt- lst- lse- cln- cle- clp-
      cld- csv- dsk- crf-`).
      💰 **THE PRICE IS WHY IT IS NOT A ONE-LINE CHANGE.** Measured today:
      scoped is **208 rows in 317 s**; unscoped is **771 rows**, ~3.7× — and
      `lnblank-say-acceptance` is already one of the battery's longer units, so
      widening it lands squarely on the critical path of a battery that has its
      own open item about wall time. The entry asked whether the answer makes
      this a one-liner or a slice: **it is a slice, and the slice is about
      battery time, not about correctness.**
      🎚️ APPARATUS — --say gating
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
