- [ ] **D-CHRGTRSKIP — CHRGTR SKIPS ONLY THE SPACE; THE VG-8020'S SKIPS TAB AND LF TOO, AND ITS END-OF-LINE F IS $44**
      🎚️ TIER 6 — every edge (a TAB or an LF inside stored program text, or a program testing F after CHRGTR at 00;
      filed 2026-11-18).
      🤖 **AUTONOMOUS** — docs/bios/CHRGTR.md R-C-SKIP / R-C-END ([`XCHRGTR_run4.out`](../../scratchpad/XCHRGTR_run4.out)): the
      VG-8020's CHRGTR steps over $20, $09 and $0A alike (HL + 2, A $31 in the probe); zerobas's (basic/islands.asm
      `chrgtr`) over $20 only, returning $09 / $0A as plain characters. At 00 the VG-8020 returns F $44 (a logical
      result's: Z, P/V), zerobas $42 (Z, N); Z agrees. zerobas's interpreter calls `rst $10` itself, so the skip would
      also change how its BASIC reads a TAB in program text -- toward the reference, whose interpreter uses the same
      entry; measure a stored TAB on both machines before picking it up. Priced when picked up (island 2).
