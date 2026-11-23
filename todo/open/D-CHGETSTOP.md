- [ ] **D-CHGETSTOP — CHGET WITH INTFLG 4 (STOP'S PAUSE) CLEARS IT AND RETURNS THE NEXT KEY**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      With INTFLG = 4, CHGET sets INTFLG to 0 and returns the next key from the buffer as usual, already there or typed
      while waiting (an earlier note said a key was dropped: corrected by measurement). Other INTFLG values stay; CHSNS
      leaves INTFLG alone. Check docs/bios/CHGET.md and zerobas's CHGET.
