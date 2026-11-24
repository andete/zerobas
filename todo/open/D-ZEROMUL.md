- [ ] 🐛 **AN EXPONENT-0 ZERO TIMES 3 (`FIX(.5!)*3`) IS A DOUBLE ZERO WITH DIGIT BYTES 30 00 ... ON THE VG-8020, EIGHT
      ZERO BYTES HERE (D-ZEROMUL, found 2026-11-24 by D-KWSPEC's goldfish pass 1 over the maths unit).**
      🎚️ TIER 6 — the value is 0 on both machines; only the result's bytes (USR / VARPTR) differ.
      🤖 **AUTONOMOUS** — measured by [`kmath.py`](../../probes/basic/spec/kmath.py) (group FY) ->
      [`KMA_run1.out`](../../scratchpad/KMA_run1.out). Rules R-FIX-ZEROUSE / R-INT-ZEROUSE on
      [FIX.md](../../docs/keywords/FIX.md), [INT.md](../../docs/keywords/INT.md): `R=FIX(.5!)*3` and `R=INT(.5!)*3`
      (the zero 00 50 00 00 times the integer 3) give, through USR, the double 00 30 00 00 00 00 00 00 on the
      reference -- exponent 0, the digit bytes those of 3, the other operand -- and 00 00 00 00 00 00 00 00 here
      (KMA FY 36, 44). One multiplier measured: whether the reference always leaves the other operand's digits, and
      what a canonical zero times a number gives, is not. Everything else these zeros were used in agrees (`+1`,
      `=`, `<`, `>`, SGN, STR$: KMA FY 35-50). Same family as D-ZEROLET / D-SQRZERO / D-TRANSZERO (a zero's digit
      bytes), but the multiply's, not an assignment's or a function's.
      ➡️ When picked up: measure the operators region's multiply on zeros first (a canonical zero and an exponent-0
      one, times integers / singles / doubles, both orders) -- this is an operator's behaviour, not FIX's or INT's.
