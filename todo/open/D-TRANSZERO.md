- [ ] 🐛 **THE ZERO RESULTS OF SIN / COS / TAN / EXP / ATN CARRY OTHER DIGIT BYTES HERE THAN ON THE VG-8020
      (D-TRANSZERO, found 2026-11-24 by D-KWSPEC's transcendentals unit).**
      🎚️ TIER 6 — the value is 0 on both machines; only the result's bytes (VARPTR / PEEK, a USR routine's DAC) differ.
      One case is VISIBLE (goldfish pass 1, below): ATN of a POKEd signed zero PRINTs "-." here -- reachable only
      through POKEd bytes, so the tier is left for the lead to judge.
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
      * Goldfish pass 1 (2026-11-24, KTR TS3 / TD3 / FY): the same zeros where p has 13 integer digits (SIN / TAN of
        1.5E13 and 3E13, COS of 7E12, 1.2E13, 1.7E13, 6.3E13) and where p flushes below 1E-64 (SIN / TAN of 5E-64,
        6E-64, 6.28318E-64), and for the singles 00 12 34 56 / 80 12 34 56; EXP's tiny zeros up to its new entry
        edge (-147.3655#, -147.36544596#, -147.366#), its flushed ones down to -75453, and its zero where the
        reference raises Overflow (-75460 down) all carry digit bytes here. IN USE (rules R-*-USE): STR$ (PRINT's
        format) gives " 0", `=0` is true, `<0` false and `+1` exactly 1 on both machines -- EXCEPT ATN's signed zero
        (80 10 00 00), whose C0 00 ... here STR$s as "-." (KTR FY 32); and on the reference `*1E10`, negation and a
        single variable keep the zero's digit bytes (a single: rounded to 6, 00 62 83 19 / 00 96 60 36 / 00 10 00 00)
        where zerobas gives zeros of its own (KTR FY 4-6, 12-14, 20-22, 28-30, 36-38). ATN of 80 12 34 56 is
        00 10 00 00 00 00 00 00 there, C0 00 ... here (FY 52).
      ➡️ When picked up: decide per function whether the reference's zero bytes are worth copying (PRINT, comparisons
      and arithmetic all read them as 0); the integer-zero leftovers are D-SQRZERO's class and may share its fix.
