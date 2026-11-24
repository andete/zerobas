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
      **Second unit (2026-11-24): LEN / ASC / CHR$ / SPACE$ / STRING$ / INSTR at DRAFT 1** from
      probes/basic/spec/kstr.py (2,044 cases a machine, scratchpad/KST_run1.out; plan §6, "The second unit"), on
      the shared RAM-record harness probes/basic/spec/ramrec.py (plan §7.2, now built; kslice byte-identical
      through it). Every rule holds on the VG-8020, every output is read; kstr_controls.py shows ten rival rules
      FALSE on the reference's cases. zerobas differs in 39 cases, filed: D-INSTREMPTY (INSTR with an empty
      string to find and a start past the end), D-CLOSESPACE (a space before `)` after INSTR's / STRING$'s
      string argument). NEXT for the strings region: STR$, VAL, HEX$, OCT$, BIN$ (a number-to-string family:
      the record needs the argument's exact value, ramrec.number has it); then the review passes on all nine.
