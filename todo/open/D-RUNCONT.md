- [ ] 🐛 **`RUN 15` TO A MISSING LINE KEEPS THE CONT POINT ON ZEROBAS; THE VG-8020 DROPS IT FIRST (D-RUNCONT, found 2026-11-25 by
      D-KWSPEC's goldfish pass 1 over RUN / CONT).**
      🎚️ TIER 6 — every error: CONT after a RUN that failed.
      🤖 **AUTONOMOUS** — [`kstop.py`](../../probes/basic/spec/kstop.py) -> [`KSP_run1.out`](../../scratchpad/KSP_run1.out)
      KST FY 13, a stopped program, then `RUN 15` (no line 15: `Undefined line number` on both), then `CONT`: the
      VG-8020 says `Can't CONTINUE` -- RUN dropped the resume point (and, by R-RUN-CLEAR, everything else) before it
      looked for the line; zerobas continues the old program (`[B]`). RUN must reset first, then check n.
