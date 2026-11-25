- [ ] 🐛 **A FOR THAT FAILS STILL PUSHES ITS LOOP FRAME ON ZEROBAS: THE NEXT THAT `RESUME NEXT` REACHES ITERATES -- FOR
      EVER WHEN THE STEP IS MISSING OR A STRING; THE VG-8020 SAYS NEXT WITHOUT FOR (D-FORFRAME, found 2026-11-25 by
      D-KWSPEC's flow region).**
      🎚️ TIER 3 — common errors: a program with `ON ERROR ... RESUME NEXT` around a faulty FOR HANGS on zerobas.
      🤖 **AUTONOMOUS** — measured by [`kfor.py`](../../probes/basic/spec/kfor.py) ->
      [`KFR_run1.out`](../../scratchpad/KFR_run1.out), KFR FX 26, 32, 42 (first error / last error / body runs / I):
      `FOR I=1 TO "A":WN%=WN%+1:NEXT` -- VG-8020 13 / 1 / 1 / I=1, zerobas 13 / 13 / 1 / I=2 (its NEXT stepped I);
      `FOR I=1 TO 3 STEP:...:NEXT` -- 24 / 1 / 1 there, 24 / 24 / 21 here (the probe's guard ended a loop that does not
      stop: the step was 0); `FOR I=1 TO 2 STEP "A":...` -- 13 / 1 / 1 there, 13 / 13 / 21 here. Without the guard the
      first run never got past the STEP case. In isolation (`FOR I=1 TO 3 STEP:PRINT ...`) both say Missing operand
      -- it is the NEXT after RESUME NEXT that differs: the reference has no frame for a FOR that failed.
      ➡️ When picked up: find where zerobas's FOR pushes the frame (before TO / STEP are evaluated) and push it only after
      the whole statement parsed and evaluated, or pop it on the error path.
