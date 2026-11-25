- [ ] 🐛 **`FOR I%=1 TO 40000`: AN INTEGER LOOP VARIABLE WITH A LIMIT PAST 32767 IS OVERFLOW AT THE FOR ON THE VG-8020; ZEROBAS
      LOOPS (D-FORINTLIM, found 2026-11-25 by D-KWSPEC's flow region).**
      🎚️ TIER 6 — every error: a limit an integer variable cannot hold.
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FX 16: the VG-8020 raises 6 (Overflow) at the FOR, then (RESUME NEXT) runs the body once and its NEXT is
      NEXT without FOR, I% 1; zerobas raises nothing and loops (the probe's guard stops it at 21 runs, I% 21). The limit
      is converted to the variable's type at the FOR on the reference (a fractional limit 3.7 truncates to 3 on both,
      KFR FX 14). Fix after D-FORFRAME (the same statement).
