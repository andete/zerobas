- [ ] 🐛 **A FAILING `NEXT I` (NO FOR) CREATES THE VARIABLE I ON THE VG-8020, NOT ON ZEROBAS (D-NEXTCREATE, found 2026-11-25
      by D-KWSPEC's flow region).**
      🎚️ TIER 6 — every edge: only VARPTR of I afterwards tells (error 5 here, an address there).
      🤖 **AUTONOMOUS** — [`kfor.py`](../../probes/basic/spec/kfor.py) -> [`KFR_run1.out`](../../scratchpad/KFR_run1.out)
      KFR FX 36: after `NEXT I` (error 1 on both) the reference's VARPTR(I) returns an address, zerobas's raises error 5
      (Illegal function call) -- as VARPTR of any variable that does not exist does on BOTH machines. Reading I (PRINT I)
      creates it on both, so a program only sees this through VARPTR or the variable table's size (FRE).
