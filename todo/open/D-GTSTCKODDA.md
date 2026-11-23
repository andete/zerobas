- [ ] **D-GTSTCKODDA — GTSTCK'S ODD-A PORT RULE (input-calls.patch) FAILS AT A 4**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      PSG R15 after GTSTCK with A 3-6: the VG-8020 selects port 1 for A 3, 4 and 6, and A 5 flips the port; the NMS 8250
      port 1 for 3-5, and 6 leaves it. zerobas's patch selects port 1 for an odd A: wrong at 4 (and 5 / 6). Match the
      VG-8020 (Joost's split rule: the VG-8020 is the reference).
      ⚠️ CORRECTED by the C-BIOS 0.32 round-2 note (2026-11-22): the 4-6 split was a RACE -- the interrupt's trigger
      scan rewrites R15, so a reading taken after interrupts are back on can catch either. Read R15 from a stub that
      does DI right after the call: then the VG-8020 and the NMS 8250 agree for EVERY A. FIRST re-measure
      docs/bios/GTSTCK.md / GTTRIG.md's R15 cases that way (their probes read R15 later; check whether they race),
      then fix the patch to the race-free rule.
