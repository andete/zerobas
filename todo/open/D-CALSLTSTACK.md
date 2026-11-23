- [ ] **D-CALSLTSTACK — A CALSLT / CALLF TARGET RUNS 10 BYTES BELOW THE CALLER'S SP ON ZEROBAS; 6 ON THE VG-8020 AND CF-3300 (14 FOR THE CF-3300'S EXPANDED RAM)**
      🎚️ TIER 6 — every edge (a target, or an interrupt in it, that runs within a few bytes of the stack's bottom;
      filed 2026-11-18).
      🤖 **AUTONOMOUS** — docs/bios/CALSLT.md R-CS-SP, docs/bios/CALLF.md R-CF-SP ([`XCALSLT_run4.out`](scratchpad/XCALSLT_run4.out),
      [`XCALSLT_run4c.out`](scratchpad/XCALSLT_run4c.out)): the references' inter-slot call pushes 6 bytes before
      the target runs for a slot that is not expanded, 14 for the CF-3300's expanded 3-0; zerobas's pushes 10 for
      both. The stack is not a published part of the contract. Priced when picked up.      💰 **PRICED 2026-11-20: left unmatched.** Matching the 6-byte stack (14 for an expanded slot) means rewriting
      CALSLT's slot-switch core (C-BIOS slot.asm), which every inter-slot call and interrupt goes through, for a
      value the contract does not publish. Re-open only if a program is found that runs out of stack there.
