- [ ] **D-WRZERHL — WRZER WITH HL 2 AND RECORD SIZE $0180 WRITES ANOTHER SIZE, CLUSTERS AND DTA THAN THE REFERENCES**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/BLOCKS.md R-BK-ROUND4 (scratchpad/XBBLK4_run1.out, run2.out XK4 12 .. 17): WRZER
      ($28) through $F37D at RR 5 with HL 2 and +14 / +15 $0180 on a 384-byte file: the VG-8020 + NMS 1200 and the
      CF-3300 write the DTA's 128-byte record 5 (size 768, one cluster, the DTA left); zerobas makes the size 1280,
      links clusters 3 and 1 at +28 / +30 and leaves the DTA's first bytes 0. Round 2 (WRZER with HL 1 and record
      size 1) agrees on all three, so HL 2 or +15 nonzero moves it -- which one is the first thing to measure.
      disk/ (WRZER's record count / record size).
