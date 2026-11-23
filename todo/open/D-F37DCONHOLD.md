- [ ] **D-F37DCONHOLD — CONST THROUGH $F37D LEAVES THE KEY IN THE BIOS BUFFER; THE REFERENCES MOVE IT INTO THE DOS'S ONE-KEY HOLD**
      ➕ 2026-11-22: since D-F37DCONIN, R-BC-RAW and R-BC-ECHO fail through this alone (the screen shows CONIN's
      echo of the waiting 'A' where the references echoed the held 'X'; scratchpad/AE_speclive_conin.out).
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/CONIN.md R-BC-CONST / R-BC-HOLD (scratchpad/XBCON1_run1.out, run2.out XN 1 .. 3):
      on both references CONST answers $FF and takes the waiting key out of the BIOS buffer into a hold that the next
      input call returns first; CONIN's echo takes a waiting key into it too, so DIRIO E $FF returns a key with the
      BIOS buffer empty. zerobas's CONST answers $FF and leaves the key; its DIRIO answers 0 there. A program that
      clears the BIOS buffer (KILBUF) after CONST loses the key on zerobas only. Round 2 (R-BC-HOLD2,
      scratchpad/XBCON2_run1.out, run2.out XN2 1 .. 18): the hold is one place, taken by CONST one key at a time and
      by ANY console output (CONOUT too), and served first by every input call. disk/ (the $F37D console input).
