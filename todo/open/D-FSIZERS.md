- [ ] **D-FSIZERS — FSIZE LEAVES THE FCB'S +14; BOTH REFERENCES CLEAR IT (AND KEEP +15)**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/BLOCKS.md R-BK-FSIZE (XK 9, 11): FSIZE over a record size 1 / 128 answers the
      records of 128 on all three machines; the references then read +14 0, zerobas keeps the record size.
      Round 4 (R-BK-ROUND4, scratchpad/XBBLK4_run1.out, run2.out XK4 3 / 5 / 7 / 15): with $0180 going in the
      references leave $0100 -- they clear +14 only, +15 stays; zerobas leaves $0180. WRZER does the same on the
      references (XK4 12: $0180 -> $0100).
