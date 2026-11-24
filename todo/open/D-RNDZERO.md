- [ ] 🐛 **WHEN RND'S STATE IS 0, ITS RESULT IS 8 ZERO BYTES ON THE VG-8020 AND A ZERO WITH LEFTOVER DIGIT BYTES HERE
      (D-RNDZERO, found 2026-11-24 by D-KWSPEC's RND unit).**
      🎚️ TIER 6 — the value is 0 on both machines (exponent byte 0); only the result's bytes (VARPTR / PEEK, a USR
      routine's DAC) differ, and only in the one state out of 10^14 that is 0.
      🤖 **AUTONOMOUS** — measured by [`krnd.py`](../../probes/basic/spec/krnd.py) (groups SQ2, FX) ->
      [`KRN_run1.out`](../../scratchpad/KRN_run1.out); rules R-RND-VALUE, R-RND-SEED, R-RND-REPEAT, R-RND-TYPE on
      [RND.md](../../docs/keywords/RND.md). `RND(-.30494897914141#)` (the reseed whose next state is 0) is 00 00 00 00
      00 00 00 00 there and 00 30 49 48 97 91 41 41 here -- the ARGUMENT's digit bytes under exponent 0; `RND(0)` and
      `USR(RND(0))` in state 0 give 00 14 43 70 00 ... / 00 14 40 30 00 ... here (other scratch), and so does
      `RND(-RND(0))`. RNDX itself agrees (00 00 ... 00 on both), and so does every later number. 6 cases (KRN SQ2
      121, FX 54, 56, 57, 58, 59). The same family as D-TRANSZERO / D-SQRZERO (a zero that keeps digit bytes).
      ➡️ When picked up: `fp_rnd` (sub/fp_rnd.asm) packs FAC from the state's digits; an all-zero state needs FAC set
      to a clean zero. The acceptance is the five rules above and the control "a zero result keeps digit bytes under
      exponent 0 -- zerobas's" in [`krnd_controls.py`](../../probes/basic/spec/krnd_controls.py).
