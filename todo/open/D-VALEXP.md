- [ ] 🐛 **`VAL`'S DECIMAL EXPONENT AT ITS 8-BIT EDGES: THE VG-8020 WRAPS PAST 255 DIGITS AND KEEPS THE DIGITS OF A
      ZERO; zerobas OVERFLOWS AND CLEARS THEM (D-VALEXP, found 2026-11-24 by D-KWSPEC's strings probe).**
      🎚️ TIER 6 — every edge: 200-digit strings, and bytes only `VARPTR` / `PEEK` / `MKD$` can see.
      🤖 **AUTONOMOUS** — measured by [`knum.py`](../../probes/basic/spec/knum.py) ->
      [`KNM_run1.out`](../../scratchpad/KNM_run1.out), rule R-VAL-RANGE on [VAL.md](../../docs/keywords/VAL.md). On
      the reference the exponent byte is 64 + E (the value .d1d2... x 10^E) taken mod 256: 128 to 255 is error 6
      (`"1E63"`, 64 to 129 digits, and `"1E-66"`, which wraps below 0); 0 is the value 0 with the digits left in the
      mantissa bytes; past 255 it is back in range. Two shapes differ: (1) 200 ones are 1.1111111111111E-57 and 255
      ones .011111111111111 there, error 6 here (KNM VL 175, 148); (2) `"1E-65"`, `"5E-65"`, `"9.9E-65"` and a point
      with 64 zeros and a 1 are 0 on both, stored `00 10 00 00 ...` there and eight zero bytes here (KNM VL 103,
      178-180) -- `"1D-65"` already agrees, and `READ` shows the same split (KNM SN S 1E-65's argument).
      ➡️ When picked up: decide with Joost whether a byte image nothing but `PEEK` sees is worth matching; if so the
      edge is in `tk_float`'s exponent handling (sub/tkfloat.asm), the E path only. The controls in
      [`knum_controls.py`](../../probes/basic/spec/knum_controls.py) are zerobas's two rules (FALSE on 2 and 5).
