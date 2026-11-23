- [ ] 🧹 **122 HARDCODED `/tmp/...` LITERALS ARE OUTSIDE THE TEMP ROOT** — pinned,
      not fixed. `probes/lib/probe_tmp.py` owns `/tmp/zerobas` and sets
      `tempfile.tempdir`, which relocated **140** bare `tempfile.*` call sites at
      a stroke; string literals cannot be relocated that way. **67 files, 10 of
      them reached by a gate.** 🔴 **THEY ARE NOT UNIFORMLY WRONG — 11 are
      `argparse` defaults**, a documented output location someone may rely on,
      which is exactly why they were not moved in bulk: that would be a silent
      behaviour change in probes no gate runs. The rest are one-shot capture
      files; each is a small safe conversion for whoever next touches that probe.
      🟢 `tools/temp-root-allow.txt` pins the set and `make temp-root-check`
      makes it **shrink-only** — a new literal is RED, and a pin that stops
      matching is STALE, so the file cannot drift from what it claims.
      Filed 2026-08-26 by the temp-root work, which chose containment + a gate
      over a 122-site edit it could not verify.
      📏 **RE-MEASURED 2026-08-26. IT IS 124 LITERALS IN 69 FILES**, not 122 in
      67 — it drifted **+2 within the day**, which is the gate doing its job
      rather than a problem: a new literal is RED, so the pin file cannot lie.
      🔴 **AND "10 OF THEM REACHED BY A GATE" DOES NOT REPRODUCE UNDER ANY
      DEFINITION I CAN CONSTRUCT.** Taking the **real** `GATES` list out of
      `run_gates.py` (41 targets), resolving each target's recipe to its scripts
      (48 seeds) and closing over imports (58 files), exactly **2** pinned files
      are on a battery path — and **both ARE the temp-root machinery itself**:
      `probes/lib/probe_tmp.py`, whose literals *define* the root, and
      `tools/check_temp_root.py`, whose two are its own matching regex and its
      docstring. **Zero of the 124 is a stray write on a battery path.**
      🔴 **MY OWN FIRST MEASUREMENT WAS WRONG THE SAME WAY THE FILING WAS.** It
      reported a different pair, including `probes/disk/disk_probe_dskio.py`
      (which really does write `/tmp/disk_probe_ours.txt`) — because I selected
      battery targets by *"the target name appears somewhere in `run_gates.py`"*,
      and **`probe` matched the substring `probes/lib`**. `make probe` is a
      SMOKE target, explicitly not a gate. A substring is not a membership test.
      ✅ **SO THE CONTAINMENT DECISION IS VINDICATED AND THIS DE-ESCALATES.** No
      bulk edit: today's lesson is that a mechanical sweep whose blast radius
      cannot be verified breaks invariants its own rule cannot see
      [[a-mechanical-fix-can-break-a-different-invariant]]. Convert
      opportunistically, when touching a probe for another reason.
      🎚️ APPARATUS — temp-root literals
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (re-measured 2026-08-26: 0 stray writes on a battery path; DE-ESCALATED).
