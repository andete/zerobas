- [x] 🔴 **`castail-acceptance` VOIDS THE WHOLE BATTERY WHEN A CONTROL FAILS ON
      THE **ZEROBAS** SIDE, SO IT CANNOT SCORE ITS OWN KNIVES.** Filed
      2026-08-21 by D-FNRUN, found by running K-FR3 against it.
      K-FR3 (`dr_cas_close`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)`) cut exactly
      what it aimed at — `cas-run-hit` went `ZQ9` → `<load-failed>` and
      `cas-run-hit-res` with it. But `cas-run-hit` is a POSITIVE CONTROL, so the
      probe printed **`33 printed, 0 scored — NOT MEASURED (a positive control
      failed)`** and exited 2. A knife is *supposed* to break things; a battery
      that treats any control failure as a broken instrument cannot measure one.
      🎯 **`basic_probe_namspc.py` ALREADY HAS THE RIGHT RULE AND IS THE
      PRECEDENT**: *"ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control
      that fails on `zb` is a finding and is scored below like any other row."*
      That is [[classify-a-control-failure-by-which-side-failed-it]], applied in
      one probe and not the other.
      ⚠️ **THE READING SURVIVED ONLY BECAUSE THE RUNNER READS ROWS, NOT `rc`.**
      Scoring on the exit code would have recorded rc 2 (instrument fault) as
      "the knife did nothing" — 8 of 11 knives were mis-scored exactly that way
      once already [[injjudge-slice]].
      💰 0 ROM bytes; a probe change. Shape: split the control check by side, as
      namspc does — a reference miss is exit 2, a zerobas miss is an ordinary
      scored divergence. ⚠️ Re-run the battery after: some rows may then SCORE
      that were previously only printed, and a row that starts being scored is a
      claim about it.
      ✅ **FIXED AND PROVEN WITH THE FOUNDING KNIFE 2026-08-28 (D-CASTAILCTL),**
      [`docs/spec-castail-control.md`](docs/spec-castail-control.md). 0 ROM bytes.
      `control_faults()` skips `zb`, exactly namspc's rule.
      **Falsified twice.** `--selftest` plants readings and checks WHICH SIDE
      decides (zb-only miss → 0 faults; reference miss → 1; both → 1, only the
      reference listed) with no machine booted. Then K-FR3 itself — **not tracked
      anywhere, so re-created** as
      [`scratchpad/castail_knife.py`](scratchpad/castail_knife.py) — with the cut
      in: `32 printed, 31 scored — 29 agree, 2 diverge`, exit **1**, naming
      `cas-run-hit` and `cas-run-hit-res`. Was `33 printed, 0 scored — NOT
      MEASURED`. Clean tree 31/31, unchanged, so no row starts being scored today.
      🔴 **THE KNIFE TAUGHT TWO THINGS.** The instruction alone was NOT the site:
      `ld hl,(FN_RESUME) ; D-FNRUN: …` occurs TWICE in `basic/cload.asm` (the disk
      path at :231, whose comment continues `--`), so the bare line matched both as
      a PREFIX and the uniqueness guard refused to cut — anchored on the LABEL
      instead. And ⚠️ **`make`'s exit code is not the probe's**: `make` exits 2 on
      any failed target, and the first reading nearly recorded "still voided" when
      the probe had in fact exited 1.
