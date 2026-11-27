- [ ] **A FOREIGN TOP CLAIM OF 440-473 B: THE CF-3300 INSTALLS, ZEROBAS DECLINES -- BRING THE LIMIT AND THE BEHAVIOUR AT IT IN
      LINE WITH THE REFERENCE (D-CLAIM473, Joost 2026-11-27).**
      🎚️ TIER 4 — RAM usage: what a disk machine does with RAM a cartridge took before the disk ROM (a convention-breaking
      cartridge -- MSX2 TH ch.5 sec.7 says BOTTOM -- but one the CF-3300 tolerates).
      🤖 **AUTONOMOUS** — black box: RAM writes, HIMEM / SLTWRK / DRVTBL / $0006, the boot; never a PC, never a ROM byte.
      JOOST 2026-11-27, on "move HOOK_SLOT, CLAIM_D and VERIFY_F so they move with the claim": "yes. But the solution
      should be more in line with reference" -- so MEASURE the CF-3300 first and copy its rule, not just ours relocated.
      TODAY: zerobas's own cells HOOK_SLOT $F1C8, CLAIM_D $F1C6-$F1C7, VERIFY_F $F1C5 sit FIXED just below the fixed
      area $F1C9-$F37F; a claim N > 439 would reach them, so INIT declines (as SHIFT). The CF-3300 installs up to N = 473
      (scratchpad/AE_wasize_threshold*.out); why 473 is unknown. diskguard-acceptance pins N = 440 as KNOWN.
      PLAN: (1) on the CF-3300, a claim cartridge (probes/disk/claimonce.asm) that FILLS its claimed bytes with a pattern,
      N = 0, 439, 456, 473, 474, 480, 491: which bytes below $F1C9 the CF-3300 writes at INIT and at H.RUNC (a RAM diff
      against the pattern) -- does its own state sit at fixed addresses or at claim-relative ones, and what does it
      overwrite of the claim; (2) past 473: does it decline (and how does that show), install broken, or crash;
      (3) then zerobas: its cells placed by the same rule, the same threshold and the same behaviour past it.
      COST: disk-ROM bytes (323 B free 2026-11-27) and RAM addresses move -> FULL gate, RAM atlas, ram-map.
      ACCEPTANCE: diskguard-acceptance SAME at every N the CF-3300 installs at (the 440 row KNOWN -> SAME), and at the
      first N it does not, both machines do the same thing.
