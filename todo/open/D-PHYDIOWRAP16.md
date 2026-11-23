- [ ] **D-PHYDIOWRAP16 — PHYDIO PAST SECTOR $FFFF GOES ON AT SECTOR 0; THE REFERENCE REFUSES THE CALL UP FRONT**
      🎚️ TIER 6 — every error (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md R-PD-PAST (scratchpad/XDSK6_run1.out D73): a 2-sector read from $FFFF.
      The VG-8020 + NMS 1200 refuses it before any sector (A 2, F $41, B 2, the buffer untouched) -- the last sector
      DE + B - 1 must fit 16 bits; a 1-sector read of $FFFF works. zerobas's DSKIO reads $FFFF and then sector 0 (the
      boot sector). The fix is DSKIO's (disk/), with D-PHYDIOMEDIA's and D-PHYDIOGEOM's.
