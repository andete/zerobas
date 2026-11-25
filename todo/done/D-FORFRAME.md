- [x] 🐛 **A FOR THAT FAILS STILL PUSHES ITS LOOP FRAME ON ZEROBAS: THE NEXT THAT `RESUME NEXT` REACHES ITERATES -- FOR
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
      ✅ FIXED 2026-11-25. The filed guess ("pushed before TO / STEP are evaluated") was WRONG: ex_for pushes last. The
      cause is D-PENDERR's DEFERRAL -- a string limit / STEP (13) or STEP with nothing (24) is recorded in FPERR and
      raised at the statement's end, which ex_for reached only after ctl_alloc had pushed the frame (traced on
      zerobas's own labels: ex_for, ef_havestep, ef_nocache, ctl_alloc, THEN raise_error). Now ex_for raises a pending
      fault before the push: `call check_expr_errors_popbc / call for_alloc` replace `ld hl,FOR_FRAME / call
      ctl_alloc` BYTE FOR BYTE (the _popbc entry discards the body pointer pushed above), and for_alloc (`ld
      hl,FOR_FRAME / jp ctl_alloc`) sits in front of the $72D4 pin (basic/field.asm; that pad 36 -> 30 B) -- in BOTH
      copies of ex_for (basic/fat.asm's ships, basic/program.asm's is the switch-off build's ELSE arm; the first edit
      went into the dead copy alone, and the ROM's bytes showed it). 🔴 WHY SAME-SIZE: the first working fix put a 3 B
      call inline, which shifted the code up to the $6CF3 pin by 3 -- and the tape corpus showed Chuckie Egg RESET
      (RUNS? before); three NOPs in its place did the same, the abort path never ran: a LAYOUT dependence, not the
      check. With the same-size fix no page-1 label moves (10 bytes differ from the unfixed ROM) and Chuckie Egg reads
      RUNS? 6293 again. Now as the VG-8020, line for line: error at the FOR's line, the body once, NEXT without FOR at
      the NEXT's line, I 1; spec-live: R-FOR-ERRORS holds on zerobas (KFR_run1.out refreshed). R-FOR-NOFRAME still
      fails only through D-FORINTLIM's case.
