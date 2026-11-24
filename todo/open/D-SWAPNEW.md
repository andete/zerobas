- [ ] 🐛 **`A=1:SWAP A,B` WITH NO `B` IS ERROR 5 ON BOTH MACHINES, BUT ZEROBAS HAS CREATED `B` HOLDING A'S VALUE (1);
      ON THE VG-8020 `B` IS NOT CREATED -- IT READS 0 (D-SWAPNEW, found 2026-11-24 by D-KWSPEC's operators unit).**
      🎚️ TIER 6 — after an error; a program that resumes (ON ERROR ... RESUME NEXT) then sees B = A.
      🤖 **AUTONOMOUS** — measured by [`klet.py`](../../probes/basic/spec/klet.py) ->
      [`KLT_run1.out`](../../scratchpad/KLT_run1.out); rule R-SWAP-NEW on [SWAP.md](../../docs/keywords/SWAP.md):
      KLT FX 38 (`A=1:SWAP A,B`) and FX 50 (`A=1:SWAP A,B,C`): ERR 5 and A 1 on both, B 0 there, 1 here.
      ➡️ When picked up: SWAP must find the second variable WITHOUT creating it, and raise 5 before writing
      anything. The acceptance is R-SWAP-NEW and the control "the missing second created holding the first's value
      -- zerobas's" in [`klet_controls.py`](../../probes/basic/spec/klet_controls.py).
