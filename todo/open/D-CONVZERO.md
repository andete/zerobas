- [ ] 🐛 **CSNG AND CDBL OF A SINGLE WHOSE EXPONENT BYTE IS 0 OR &H80 (DIGIT BYTES LEFT IN IT) KEEP ITS BYTES ON THE
      VG-8020; ZEROBAS MAKES A CLEAN ZERO, AND ITS CSNG OF 80 10 00 00 IS A DOUBLE (D-CONVZERO, found 2026-11-24 by
      D-KWSPEC's conversion unit).**
      🎚️ TIER 6 — only a POKEd single reaches it; the value is 0 on both.
      🤖 **AUTONOMOUS** — measured by [`kconv.py`](../../probes/basic/spec/kconv.py) group FX ->
      [`KCV_run1.out`](../../scratchpad/KCV_run1.out); rules R-CSNG-ODD, R-CDBL-ODD on
      [CSNG.md](../../docs/keywords/CSNG.md) / [CDBL.md](../../docs/keywords/CDBL.md): `CSNG` of 00 10 00 00 / 80 10
      00 00 is that single unchanged there, 4 zero bytes here -- and for 80 10 00 00 zerobas's result is of TYPE 8 (a
      double, 8 zero bytes); `CDBL` of them is 00 10 00 00 00 00 00 00 / 80 10 00 00 00 00 00 00 there, 8 zero bytes
      here (KCV FX 48, 49, 73, 74). The same family as D-ZEROLET / D-TRANSZERO (a zero that keeps digit bytes).
      ➡️ When picked up: CSNG of a single must return it as it is; CDBL of a single must append four zero bytes
      without normalising. The acceptance is the two ODD rules and the controls "an exponent-0 single made a clean
      zero -- zerobas's" in [`kconv_controls.py`](../../probes/basic/spec/kconv_controls.py).
