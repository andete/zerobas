- [ ] 🐛 **`FOR I=1 TO 2 STEP 1,2`: ONE SYNTAX ERROR ON THE VG-8020, TWO ON ZEROBAS (D-FORCOMMA, found 2026-11-25 by D-KWSPEC's
      goldfish pass 1 over FOR / NEXT).**
      🎚️ TIER 6 — every error: the loop runs the same on both (2 runs, I 3); only the error COUNT differs.
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FY 16: the reference pushes the frame, then raises 2 once at the comma (RESUME NEXT goes on with the body);
      zerobas raises 2 twice (its count byte 2) -- where the second comes from is not measured yet (ERL would say).
