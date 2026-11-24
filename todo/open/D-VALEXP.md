- [ ] 🐛 **`VAL`'S DECIMAL EXPONENT AT ITS 8-BIT EDGES: THE VG-8020 WRAPS PAST 255 DIGITS AND KEEPS THE DIGITS OF A
      ZERO; zerobas OVERFLOWS AND CLEARS THEM (D-VALEXP, found 2026-11-24 by D-KWSPEC's strings probe).**
      🎚️ TIER 6 — every edge: 200-digit strings, and bytes only `VARPTR` / `PEEK` / `MKD$` can see.
      🤖 **AUTONOMOUS** — measured by [`knum.py`](../../probes/basic/spec/knum.py) ->
      [`KNM_run1.out`](../../scratchpad/KNM_run1.out), rule R-VAL-RANGE on [VAL.md](../../docs/keywords/VAL.md). On
      the reference the exponent byte is 64 + E (the value .d1d2... x 10^E); the part of E the digits and the point
      make is counted mod 256 (64 to 191 digits give 128 to 255, error 6; a point and 70 zeros wraps below 0), and an
      `E` exponent is added to that WITHOUT wrapping (`"1E63"`, `"1E-66"`, `"1E-194"`, `"1E-200"`, `"1E300"` are all
      error 6, on both machines: KNM VL 202-204, goldfish pass 1); 0 is the value 0 with the digits left in the
      mantissa bytes; a digit count past 255 is back in range. Two shapes differ: (1) 192 ones are a zero with
      digits, 193 ones 1.1111111111111E-63, 200 ones 1.1111111111111E-57 and 255 ones .011111111111111 there,
      error 6 here (KNM VL 185, 186, 175, 148); (2) `"1E-65"`, `"5E-65"`, `"9.9E-65"` and a point
      with 64 zeros and a 1 are 0 on both, stored `00 10 00 00 ...` there and eight zero bytes here (KNM VL 103,
      178-180) -- `"1D-65"` already agrees, and `READ` shows the same split (KNM SN S 1E-65's argument).
      ➡️ When picked up: decide with Joost whether a byte image nothing but `PEEK` sees is worth matching; if so the
      edge is in `tk_float`'s exponent handling (sub/tkfloat.asm), the E path only. The controls in
      [`knum_controls.py`](../../probes/basic/spec/knum_controls.py) are zerobas's two rules (FALSE on 4 and 6).
