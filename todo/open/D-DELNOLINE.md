- [ ] 🐛 **DELETING A LINE THAT DOES NOT EXIST AFTER A STOP: ZEROBAS SAYS `Undefined line number in 10`, AND THE NEXT CONT RUNS THE
      STOP AGAIN (D-DELNOLINE, found 2026-11-25 by D-KWSPEC's goldfish pass 1 over CONT).**
      🎚️ TIER 6 — every error: a typed line number alone, for a line that is not there, while a program is stopped.
      🤖 **AUTONOMOUS** — [`kstop.py`](../../probes/basic/spec/kstop.py) -> [`KSP_run1.out`](../../scratchpad/KSP_run1.out)
      KST FY 8, `10 PRINT "[A]":STOP:PRINT "[B]"` / `RUN` / `20` / `CONT`: the VG-8020 prints `Undefined line number`
      (a direct-mode error: no "in"), and CONT then goes on (`[B]`); zerobas prints `Undefined line number in 10` -- the
      current line is still the stopped program's -- and CONT prints `Break in 10` again (it resumes AT the STOP).
      Two symptoms, likely one cause: the edit path's error leaves CURLIN / the resume point as the STOP set them.
