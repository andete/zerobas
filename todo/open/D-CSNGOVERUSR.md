- [ ] 🐛 **`USR(CSNG(9.999995D62))` RUNS THE USR ROUTINE (VALTYP 8, DAC ZERO) BEFORE ERROR 6 ON ZEROBAS; THE
      VG-8020 RAISES OVERFLOW INSIDE CSNG AND NEVER REACHES USR (D-CSNGOVERUSR, found 2026-11-24 by D-KWSPEC's
      conversion unit).**
      🎚️ TIER 6 — the error is the same (6) and `R=CSNG(x)` assigns nothing on both; only an enclosing USR routine
      sees a call it should not (a double zero).
      🤖 **AUTONOMOUS** — measured by [`kconv.py`](../../probes/basic/spec/kconv.py) group CD ->
      [`KCV_run1.out`](../../scratchpad/KCV_run1.out); rule R-CSNG-OVER on [CSNG.md](../../docs/keywords/CSNG.md):
      KCV CD CSNG 9.999995D62, -9.999995D62, 9.9999999999999D62 -- the reference's type cell stays 255, zerobas's
      reads 8 with DAC 00 ... 00, ERR 6 on both. The overflow is raised after CSNG returns here, not by CSNG.
      ➡️ When picked up: CSNG's double -> single rounding must raise Overflow itself when the carry passes exponent
      &H7F. The acceptance is R-CSNG-OVER and R-CSNG-ASSIGN.
      Goldfish pass 1 (2026-11-24): the negative end too, CSNG(-9.9999999999999D62) (KCV FY 21).
