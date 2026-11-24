- [ ] 🐛 **NEAR A HALF OR WHOLE TURN, ZEROBAS'S SIN / COS / TAN KEEP MORE OF THE ANGLE THAN THE VG-8020'S 14-DIGIT
      REDUCTION: `SIN(3.1415926535898#)` IS -1.5707963267949E-13 HERE, -1.2566370614359E-13 THERE (D-TRIGHALF, found
      2026-11-24 by D-KWSPEC's transcendentals unit).**
      🎚️ TIER 1 — a printed number differs in a plain calculation, in its leading digits (as D-COSHALFPI).
      🤖 **AUTONOMOUS** — measured by [`ktrans.py`](../../probes/basic/spec/ktrans.py) ->
      [`KTR_run1.out`](../../scratchpad/KTR_run1.out), rules R-SIN-NEAR / R-COS-NEAR / R-TAN-NEAR on
      [SIN.md](../../docs/keywords/SIN.md), [COS.md](../../docs/keywords/COS.md), [TAN.md](../../docs/keywords/TAN.md).
      The reference turns x into p = x * 0.15915494309190 rounded to 14 digits and works on its fraction f (SIN) or on
      the fraction of r14(1/4 - p) (COS) -- one black-box rule that fits all 431 measured nonzero SIN / COS results within 2.1
      units of the 14th digit (D-TANBIG adopted it for large angles). Where the reduced angle lands near a half or a
      whole turn, the result is small and its leading digits ARE the reduction's last digits, and zerobas's differ:
      SIN(3.14159!) 2.6535897459098E-06 here, 2.6535897144938E-06 there; SIN(3.1416!), SIN(6.28318!), SIN(+-3.1415926535898#);
      COS(4.71239!) 1.0196155196152E-06 vs 1.0196154567834E-06, COS(4.7123889803847#) 1.5707963267949E-13 vs
      1.2566370614359E-13; TAN at the same angles, TAN(4.7123889803847#) -6366197723675.8 vs -7957747154594.6 (16 cases).
      Away from the folds zerobas follows the reference (COS(1.5707963267949#) is -6.2831853071796E-14 on both).
      ➡️ When picked up: the fold of `sn_kernel` (sub/fp_sin.asm) -- f - 1/2 or f - 1 taken with more digits than the
      14-digit p has (not yet read). Joost's 2026-07-13 accuracy ruling covers the final approximation, not the
      reduction D-TANBIG chose to copy; whether this is to be copied too is the question to settle first.
