- [ ] **WITH A FOREIGN CLAIM N > 0 THE CF-3300'S DRIVE-A DPB SITS AT $F195 - N; ZEROBAS'S STAYS AT $F195 (D-DPBMOVE --
      D-CLAIM473's option 2, split off 2026-11-27).**
      🎚️ TIER 6 — only a cartridge that both breaks the MSX convention (a top claim) and sits before the disk ROM sees it.
      🤖 **AUTONOMOUS** — black box: $F355 / IX at the boot, the $50A9 pointers, the CF-3300 the reference.
      MEASURED (scratchpad/claim_ix_probe.py, [AE_claim_dpb.out](../../scratchpad/AE_claim_dpb.out)): the CF-3300's $F355 = $F195 - N (N = 0, 300, 473) -- it
      keeps NOTHING fixed below $F1C9. zerobas (1847a8949, option 1): DPB at $F195 ($F194 at exactly N = 473), $F355
      always names it, so a program following $F355 works; only the ADDRESS differs at N > 0. The $50A9 pointers
      (W50A9_RET_DE $F1AA) likely follow N on the CF-3300 too -- unmeasured.
      COST (Joost, D-CLAIM473): the block would sweep $EFBC-$F194 as N grows, over zerobas's fixed cells there (FDC state
      $EFF7, P1_BLIT $EFFE, ...) -- a re-lay of that RAM, a FULL gate, the atlas. Joost chose "option 1 now"; this later.
      ACCEPTANCE: $F355 and the boot's IX = $F195 - N on both machines at N = 0, 300, 473 (a diskguard column).
