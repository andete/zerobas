- [ ] **D-GATEKNIFESKIP — A DOCS / PROBE-ONLY GATE RE-PINS THE KNIVES AND RUNS THE WHOLE UNIT SUITE: ~15-20 MIN FOR A STATIC**
      🎚️ TIER 2 — reasonable time (the gate's own wall time; filed 2026-11-17 at Joost's request).
      🤖 **AUTONOMOUS** — measured on the STATIC gate of 9152f845, a commit whose only delta from a FULL-green tree was
      the generated docs/tier-status.md:
      - tools/gate_wt.py re-ran the keyword knives (128 s + 78 s) and the tape corpus: it runs them whenever the range
        since the last push touches basic/ sub/ disk/. Here the range still held the unpushed ROM commits, whose EXACT
        bytes the previous FULL gate had knifed minutes before (corrected 2026-11-17: first filed as "every tier");
      - the unit suite (97 files, ~10 min) and selftest-check (~3.5 min) run inside STATIC.
      (1) **NEXT: skip the knives** when the built ROMs are byte-identical to the ones the last green knife pin was
      measured on (the knife ROM guard already records the hashes). A docs or probe commit then saves ~3.5 min, and a ROM
      change still re-pins.
      ✅ **(1) LANDED 2026-11-17:** `knife_key` in tools/gate_wt.py, a sha256 over the built ROMs, their .sym files and
      the knife / corpus harness (kwknife.py, knife_guard.py, tier_table.py, basic_probe_kwsweep.py,
      tapecorpus_run.py). A PASSING knife + corpus run writes it to the gate output folder (knife_inputs.json, runtime state, never committed); a later
      gate whose build hashes the same skips both and says so. tests/test_gate_wt_knife_key.py pins the key: it
      moves for one ROM byte, a .sym change and a harness edit, and refuses an empty build.
      (2) **LATER: a tier for generated-docs-only commits**: only the checks that read the changed files (tiers-md-check,
      citations, bios-spec-index-check, the TODO checks). It needs care: which files may go through it, and how
      gates-plan proves the delta is docs-only. Joost: "file it and do the knife skip after CHPUT".
