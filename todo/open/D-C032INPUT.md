- [ ] **D-C032INPUT — INPUT FACTS TO CHECK: BREAKX ON CTRL+STOP, ISCNTC / CKCNTC IDLE, OUTDO WITH PRTFLG**
      🎚️ TIER 6 — every edge (filed 2026-11-21).
      🤖 **AUTONOMOUS** — From the C-BIOS 0.32 port's measurements (Joost, 2026-11-21; headless openMSX, BIOS calls made directly, VG-8020 = NMS 8250 unless noted). Check zerobas against them first.
      (1) BREAKX on CTRL+STOP also empties the key buffer and marks STOP down in OLDKEY row 7 ($EF). (2) ISCNTC / CKCNTC
      with no break pending: A 0, F Z+H+P/V, interrupts on (D-ISCNTCEI covered ISCNTC). (3) OUTDO with PRTFLG 1, $FF or 2
      goes to the printer through OUTDLP; H.OUTD stays $C9 x5 after boot.
