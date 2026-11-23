- [ ] **D-FMAKERS — FMAKE LEAVES THE FCB'S RECORD SIZE (+14 / +15); THE REFERENCES CLEAR +14 .. +31**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/FILES.md R-BF-MAKE2 (scratchpad/XBFILE2_run1.out, run2.out XB2 3 / 7): over an FCB
      pre-filled with $FF, FMAKE through $F37D writes +14 .. +31 on both references (record size and size 0, date,
      time, $40, the entry index) and leaves +12 / +13 and +32 .. +36; zerobas leaves +14 / +15 (the record size) at
      $FF (review pass 3 corrected an earlier "+14 .. +17": the size's bytes are written). A caller that
      reuses an FCB gets a stale record size. disk/ (bdos_create_body).
