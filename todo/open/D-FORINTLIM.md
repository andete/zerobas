- [ ] 🐛 **`FOR I%=1 TO 40000`: AN INTEGER LOOP VARIABLE WITH A LIMIT PAST 32767 IS OVERFLOW AT THE FOR ON THE VG-8020; ZEROBAS
      LOOPS (D-FORINTLIM, found 2026-11-25 by D-KWSPEC's flow region).**
      🎚️ TIER 6 — every error: a limit an integer variable cannot hold.
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FX 16: the VG-8020 raises 6 (Overflow) at the FOR, then (RESUME NEXT) runs the body once and its NEXT is
      NEXT without FOR, I% 1; zerobas raises nothing and loops (the probe's guard stops it at 21 runs, I% 21). The limit
      is converted to the variable's type at the FOR on the reference (a fractional limit 3.7 truncates to 3 on both,
      KFR FX 14). Fix after D-FORFRAME (the same statement).
      **Widened 2026-11-25 (goldfish pass 1's KFR FY cases): the whole class is "an integer loop variable's start,
      limit and STEP are converted at the FOR".** The reference: a start, a limit or a STEP outside -32768..32767 is
      6 at the FOR (FY 8 limit -40000, FY 9 start 40000 -- I% stays 0, FY 10 step 40000); a fractional STEP is cut
      towards zero at the FOR (FY 6 STEP 1.5: 5 runs, I% 6; FY 7 STEP -.5 is 0 and never ends). zerobas: FY 8 / FY 9
      loop (21 runs), FY 10 is 6 only at the NEXT, FY 6 runs 4 times (I% 5) and FY 7 3 times (I% 0) -- it keeps the
      fraction and cuts the sum. One fix: convert start / limit / STEP to the variable's type, range-checked, at FOR.
