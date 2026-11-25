- [ ] 🐛 **`FOR I=3 TO 1 STEP 0`: THE VG-8020 LOOPS FOR EVER, ZEROBAS RUNS THE BODY ONCE (D-FORSTEP0, found 2026-11-25 by
      D-KWSPEC's flow region).**
      🎚️ TIER 6 — every edge: STEP 0 with the start already past the limit.
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FX 6 (the guard counts 21 there, 1 here); `FOR I=1 TO 3 STEP 0` loops for ever on both (FX 5). So the
      reference's end test with step 0 is not "past the limit in the step's direction" -- measure STEP 0 with start =
      limit and start below to pin its rule before changing NEXT's test.
