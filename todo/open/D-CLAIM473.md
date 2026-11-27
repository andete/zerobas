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
      📏 **STEP 1 MEASURED 2026-11-27** (scratchpad/claim473_probe.py, probes/disk/claimfill.asm -- a claim cartridge that
      fills $A5 over its claim and over $D000-$EF7F; RAM diffs at the boot code's entry and at 25 s; no PC, no ROM byte;
      [AE_claim473_1.out](../../scratchpad/AE_claim473_1.out)). The CF-3300:
        N = 0:   installs, HIMEM $DF93, SLTWRK 3-1 $F1BF
        N = 439: installs, HIMEM $DDDC, SLTWRK $F008 -- in the claim it writes ONLY $F1C9-$F37F (the fixed area)
        N = 473: installs, HIMEM $DDBA, SLTWRK $EFE6 -- the same: nothing in [$F1A7, $F1C9)
        N = 474: DECLINES -- DRVTBL 0, no boot code -- yet HIMEM and SLTWRK = $EFE5 ($F1BF - N), the fixed area written
      Below $F1C9 it keeps NO fixed cell: its writes there shift by exactly the difference in N (34 B from 439 to 473).
      (The cartridge's fill breaks zerobas's boot even at N = 0 -- it runs later there, from BASIC's scan, over BASIC's
      state -- so zerobas is measured by diskguard, not by this cartridge.)
      🧭 JOOST 2026-11-27: past 473, "Copy the CF-3300 exactly" -- decline at 474 WITH HIMEM / SLTWRK := $F1BF - N.
      STEP 2 (build): HOOK_SLOT / CLAIM_D / VERIFY_F out of $F1C5-$F1C8 into the claim-relative block; install up to
      N = 473; at N >= 474 decline as the CF-3300 (the fixed area written, HIMEM = SLTWRK = $F1BF - N, DRVTBL 0).
      diskguard: rows 456, 473 SAME, 474 SAME (the 440 KNOWN row goes).
      🔴 CORRECTION (same day): "N = 474: DECLINES -- yet HIMEM and SLTWRK = $EFE5" was a TRANSIENT, read from ONE sample at
      25 s. diskguard reads more moments ([AE_claim473_guard1.out](../../scratchpad/AE_claim473_guard1.out)): at H.RUNC HIMEM $F1A6 (the cartridge's claim
      only), at 20 s HIMEM $EFE5 with $0006 garbage ($9898), and at the BASIC prompt HIMEM $F1A6 again, SLTWRK EMPTY,
      no drive -- a CLEAN decline. Joost's "Copy the CF-3300 exactly" was asked on the misreading; copying it exactly
      is the clean decline (what zerobas already did with SHIFT): ig_out, HIMEM and SLTWRK untouched. Told Joost.
      ✅ BUILT (option 1, Joost 2026-11-27): HOOK_SLOT = DRVTBL+0 ($F348), CLAIM_D = DRVTBL+3 ($F34B, held across the
      $FF-gated DRVTBL LDIR), VERIFY_F $F23C (a fixed-area byte nothing else writes -- watched through an MSX-DOS
      session); CLAIM_NMAX 473; past it the clean decline; DPBLIST $F355 published ($F195, $F194 only at N = 473,
      where $F1A7 is the claim's), IX and GETDPB's base read from it. diskguard rows 0 16 300 439 456 473 474, the 474
      rows compare the end state (the CF-3300's 20 s readings are its mid-decline transient).
      LEFT for option 2 (filed later): the DPB and the $50A9 pointers moving with N as on the CF-3300.
