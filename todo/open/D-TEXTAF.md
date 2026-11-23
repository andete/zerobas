- [ ] **D-TEXTAF — THE TEXT CALLS' A / F ON RETURN DIFFER FROM THE VG-8020'S**
      🎚️ TIER 6 — every edge (a program testing A or the flags after DSPFNK / ERAFNK / FNKSB / CLS / POSIT; filed
      2026-11-17).
      🤖 **AUTONOMOUS** — docs/bios/DSPFNK.md R-K-AF and docs/bios/CLS.md R-CP-AF
      ([`XSCR_run2.out`](../../scratchpad/XSCR_run2.out)) state the VG-8020's values per case (DSPFNK 00 / 44, ERAFNK 28 / BB,
      CLS 00 / 54, POSIT 24 / 30 ...); zerobas's differ in almost every case. ERAFNK's A is LINLEN on the VG-8020
      (R-K-ERA-A, [`XSCR3_run1.out`](../../scratchpad/XSCR3_run1.out)), $20 on zerobas. Also CNVCHR's F after a conversion (A3 vs
      3B, or 2B for a $0F / $1F result: docs/bios/CNVCHR.md R-V-F, C and Z agree) and PINLIN / QINLIN / INLIN's F (18 vs 00: docs/bios/PINLIN.md R-L-F), and INIFNK's A / F (5A / E9 vs 1F / 08:
      docs/bios/INIFNK.md R-F-AF; round 2 R-F-REGS / R-F-DI / R-F-WAREA: zerobas returns other BC / HL, A not kept,
      and with interrupts ENABLED where the VG-8020's INIFNK returns them disabled).
      Not published values: match them only if cheap. CHGET's are D-CHGETEI.
      💰 **PRICED 2026-11-18: NOT CHEAP -- left unmatched under this item's own rule.** Each piece, against the low region (43 B
      free, the switch-off floor 36 B, at 13c67168):
      - ERAFNK's A = LINLEN: 3 B, but its F (BB / B3 / 9B) still differs, so R-K-AF stays red.
      - PINLIN / INLIN / QINLIN's F = $18: a constant F via push / pop past the full $3283 pin pad, ~6-8 B.
      - INIFNK: IFF kept across subrom_call's `ei`, A kept, F, and the BC / DE / HL leftovers: ~15+ B.
      - CLS / POSIT / DSPFNK: per-path literal A / F pairs (00/54, 00/44, 66/24, 24/30, 22/30, 48/18 ...), tens of B.
      - CNVCHR's F (41 OR (A AND $28), 42, A3 per path): a C-BIOS patch, ~8-10 B.
      These are the reference's register leftovers, and the low region's remaining bytes are worth more to the next
      BIOS regions. Re-open a piece only if a real program is found that reads it.
