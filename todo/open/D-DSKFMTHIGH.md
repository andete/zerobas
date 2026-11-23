- [ ] **D-DSKFMTHIGH — DSKFMT TAKES CHOICE $81 AS A SUCCESS AND FORMATS NOTHING; THE REFERENCE REFUSES IT**
      🎚️ TIER 6 — every error (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/DSKFMT.md R-DF-BAD (scratchpad/XDFMT3_run1.out XF3 0): DSKFMT ($401C) with A = $81
      on the CF-3300 returns A 12, carry set, E $80, the disk untouched (as 0, 5-8, $80, $FF); zerobas returns A 0
      with the carry clear and formats nothing -- a caller is told the disk is formatted. Its range test lets a high
      bit through; fix in disk/ (the choice check).
