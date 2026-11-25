- [ ] 🐛 **`GOSUB 65000` (A MISSING LINE) PUSHES A RETURN FRAME ON ZEROBAS, NONE ON THE VG-8020 (D-GOSUBFRAME, found 2026-11-25
      by D-KWSPEC's goldfish pass 1 over GOTO / GOSUB / RETURN).**
      🎚️ TIER 6 — every error: only RESUME NEXT after the Undefined line number can see it.
      🤖 **AUTONOMOUS** — [`kgosub.py`](../../probes/basic/spec/kgosub.py) -> [`KGS_run1.out`](../../scratchpad/KGS_run1.out)
      KGS FY 8, `GOSUB 65000:WN%=WN%+1:RETURN`: the reference raises 8, RESUME NEXT counts once, and the RETURN is 3
      (RETURN without GOSUB) -- WN% 1; zerobas's RETURN finds the frame the failed GOSUB left, comes back, counts again
      and only then raises 3 -- WN% 2. The frame must be pushed only after the line is found (R-GOSUB-ERRORS).
