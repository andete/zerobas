- [ ] **D-SETRNDR36 — SETRND CLEARS THE FCB'S +36; BOTH REFERENCES LEAVE IT**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/RECORDS.md R-BR-SETRND3 (scratchpad/XBREC3_run1.out, run2.out XR3 2 / 6): over $FF
      at +34 .. +36, SETRND through $F37D writes +33 .. +35 (1, 0, 0) and leaves +36 $FF on the VG-8020 + NMS 1200 and
      the CF-3300; zerobas writes +36 0 too. disk/ (bb_setrnd).
