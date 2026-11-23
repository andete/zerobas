- [ ] **D-KWSPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE BASIC KEYWORDS**
      🎚️ TIER 1 — Joost 2026-11-23, third of "3, 2, 1".
      🤖 **AUTONOMOUS** — docs/keywords/*.md exist as user pages; make them specs with executable rules, region by
      region (as the BIOS), the VG-8020 the reference. BASIC graduates to C-BIOS eventually: these pages are what a
      port is checked against.
      **First unit (2026-11-23, scaffold + pilot):** the plan is docs/keywords/spec-plan.md (14 regions, strings
      first; harnesses; the spec page = the user page + the contract sections), the queue docs/keywords/spec-index.md
      (generated, tools/kw_spec_index.py). Pilot: LEFT$ / RIGHT$ / MID$ (function) at DRAFT 1 from
      probes/basic/spec/kslice.py (1,224 cases a machine, scratchpad/KSL_run1.out), rules modules
      probes/basic/spec/{left_s,right_s,mid_s}_rules.py -- every rule holds on the VG-8020, zerobas agrees in every
      case. NEXT: the review passes on the three pages (spec-method §6); a keyword probe in spec_live (plan §7.1);
      then the rest of the strings region. Joost to rule: "What we found" on a FINAL page, and the cassette
      statements (plan §2, §4).
