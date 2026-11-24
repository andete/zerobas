- [ ] 🐛 **RND OF A SIGN-BIT ZERO (A SINGLE 80 00 00 00) RESEEDS FROM m = 0 ON THE VG-8020; ZEROBAS TREATS IT AS A
      ZERO AND REPEATS THE LAST NUMBER (D-RNDNEGZERO, found 2026-11-24 by the goldfish review of RND.md).**
      🎚️ TIER 6 — only a number whose bytes were POKEd reaches it (typed `-0`, `-0!`, `-0#` are stored as zero
      bytes, KRN SQ1); but from there every later number differs.
      🤖 **AUTONOMOUS** — measured by [`krnd.py`](../../probes/basic/spec/krnd.py) group EDIT ->
      [`KRN_run1.out`](../../scratchpad/KRN_run1.out); rule R-RND-SIGN on [RND.md](../../docs/keywords/RND.md):
      `Z!=0:V=VARPTR(Z!):POKE V,128:R#=RND(Z!)` in state 66740297881811 gives RNDX 00 14 38 98 20 42 08 21 (C: the
      reseed of m = 0) and R .14389820420821 there; RNDX unchanged and R the old number here (KRN EDIT 15), and the
      next RND(1) differs too (EDIT 16). The sign bit decides, as R-RND-SIGN says for 80 10 00 00 -- zerobas already
      reseeds that one; it is the all-zero digits with the sign bit that it takes for a zero.
      ➡️ When picked up: RND's argument classification (zero / positive / negative) must read the sign bit before
      the zero test. The acceptance is R-RND-SIGN, -SEED, -ASSIGN and -CHAIN on EDIT 15-16 and the control "an
      exponent-0 number is a zero even with the sign bit set" (krnd_controls.py).
