- [ ] 🐛 **ZEROBAS'S SINE IS UP TO 6.1 UNITS OF THE 14TH DIGIT OFF THE REDUCED ANGLE'S SINE, WHERE THE VG-8020 STAYS
      WITHIN 1.9 (D-SINDIGITS, found 2026-11-24 by D-KWSPEC's transcendentals unit).**
      🎚️ TIER 5 — the last printed digit of SIN / TAN differs, and zerobas's is the further from the true value
      too; Joost's 2026-07-13 ruling accepted last-digit differences on the ground that zerobas is the more accurate.
      🤖 **AUTONOMOUS** — measured by [`ktrans.py`](../../probes/basic/spec/ktrans.py) ->
      [`KTR_run1.out`](../../scratchpad/KTR_run1.out), rules R-SIN-NEAR (bound 2.5) and R-TAN-NEAR (bound 6) on
      [SIN.md](../../docs/keywords/SIN.md) / [TAN.md](../../docs/keywords/TAN.md).
      SIN(.01!) 2.6 units, SIN(3.33333!) 3.9, SIN(2.718281828459#) 5.6 (.41078129050281 here, .41078129050287 there,
      the true sine .41078129050295), SIN(3.3333333333333#) 6.1; TAN(2.718281828459#) 6.1, TAN(3.3333333333333#) 6.4
      (8 cases). The reference's worst over 431 SIN / COS results is 2.1 units; zerobas's COS stays within 1.3.
      ➡️ When picked up: the sine polynomial of `sn_kernel` (sub/fp_sin.asm) for reduced angles near a quarter turn
      or in its second half (not yet read); R-SIN-NEAR is the acceptance.
