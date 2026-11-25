- [ ] 🐛 **A FAILED `NEXT J` DROPS THE OPEN FOR FRAME ON ZEROBAS; THE VG-8020 KEEPS IT (D-NEXTFRAME, found 2026-11-25 by
      D-KWSPEC's goldfish pass 1 over FOR / NEXT).**
      🎚️ TIER 6 — every error: only RESUME NEXT after a NEXT without FOR can see the frame afterwards.
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FY 24, `FOR I=1 TO 2:...:NEXT J:NEXT`: the reference raises 1 at `NEXT J`, then the bare NEXT finds I's frame
      and the loop goes on (2 runs, 2 errors, I 3); zerobas's bare NEXT is a second error 1 (1 run, I 1) -- its frame
      search pops while it looks. A miss must leave the stack as it was (R-NEXT-ERRORS).
