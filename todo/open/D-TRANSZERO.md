- [ ] 🐛 **THE ZERO RESULTS OF SIN / COS / TAN / EXP / ATN CARRY OTHER DIGIT BYTES HERE THAN ON THE VG-8020
      (D-TRANSZERO, found 2026-11-24 by D-KWSPEC's transcendentals unit).**
      🎚️ TIER 6 — the value is 0 on both machines; only the result's bytes (VARPTR / PEEK, a USR routine's DAC) differ.
      🤖 **AUTONOMOUS** — measured by [`ktrans.py`](../../probes/basic/spec/ktrans.py) ->
      [`KTR_run1.out`](../../scratchpad/KTR_run1.out); rules on [SIN.md](../../docs/keywords/SIN.md),
      [COS.md](../../docs/keywords/COS.md), [TAN.md](../../docs/keywords/TAN.md), [EXP.md](../../docs/keywords/EXP.md),
      [ATN.md](../../docs/keywords/ATN.md).
      * SIN / TAN whose reduced angle is a whole or half turn (0, 1E-64, 3.1415926535897#, 1E13 up), and COS from 7E13
        up: the reference returns exponent 0 with 2 pi's digits, 00 62 83 18 53 07 17 96 (R-SIN-ZERO, R-COS-ZERO,
        R-TAN-ZERO, R-*-ODDBYTES, R-*-FORMS); zerobas's SIN gives 00 10 00 ... (00 11 14 08 46 01 64 33 at 7E13,
        00 15 91 54 94 30 91 90 from 1E14), its TAN 8 zero bytes, its COS the SIN-like bytes (72 cases).
      * EXP below 1E-129 (x from -297.04 to -65536): 8 zero bytes there, digit bytes left over here (00 10 00 ...
        for EXP(-1000!), 00 65 53 ... for -65536; R-EXP-FLUSH, 10 cases); `R=EXP(N%)` with N% = -1000 / -32768 and
        `R=EXP(&H8000)` store leftover digit bytes in R (R-EXP-ASSIGN, 3); EXP(-32768) through USR too (FX 17).
        EXP from 1E-65 to 1E-64 (R-EXP-TINY, 6 cases) is exponent 0 with e^x's digits there, 8 zero bytes here --
        inside the band the X item on negative EXP keeps deliberately different, but a byte matter of its own.
      * ATN of the single 80 10 00 00 is 00 10 00 00 00 00 00 00 there, C0 00 ... here (R-ATN-ZERO); `R=ATN(0%)` and
        `R=ATN(-0)` store leftover digit bytes in R (R-ATN-ASSIGN), the D-SQRZERO pattern.
      ➡️ When picked up: decide per function whether the reference's zero bytes are worth copying (PRINT, comparisons
      and arithmetic all read them as 0); the integer-zero leftovers are D-SQRZERO's class and may share its fix.
