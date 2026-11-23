- [ ] **D-DSKCHGTIME — DSKCHG'S "UNCHANGED" WINDOW IS ~3 S IN ZEROBAS, LESS THAN 2 S (96 INTERRUPTS) ON THE REFERENCE**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/DSKCHG.md R-DC-RECENT / R-DC-READ (scratchpad/XDENT3_run1.out XE3 3-5): the
      reference reads again 96 timer interrupts after its last read (B 1 at 48), zerobas answers B 1 at 96 and reads
      only later (XE3 4, 144 interrupts after its last read -- its GETDPB at XE3 1 -- so its bound is 97-144). Both count from a READ (a B 1 answer restarts neither); but a FAILED read restarts zerobas's count, not the reference's (XDENT6_run1.out: with drive A empty the reference fails twice, zerobas answers B 1 twice). Measure zerobas's limit, then
      match the reference's (between 48 and 96: one more probe narrows it).
