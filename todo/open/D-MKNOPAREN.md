- [ ] 🐛 **`MKI$`, `MKS$` AND `MKD$` WITHOUT A PARENTHESIS (`S$=MKI$`) ARE ERROR 24 (MISSING OPERAND) ON ZEROBAS,
      ERROR 2 (SYNTAX ERROR) ON THE CF-3300 AND THE VG-8020 (D-MKNOPAREN, found 2026-11-24 by D-KWSPEC's conversion
      unit).**
      🎚️ TIER 6 — an error code; both refuse the statement.
      🤖 **AUTONOMOUS** — measured by [`kmkcv.py`](../../probes/basic/spec/kmkcv.py) groups FX / DFX ->
      [`KMC_run1.out`](../../scratchpad/KMC_run1.out); rules R-MKI-SYNTAX, R-MKS-SYNTAX, R-MKD-SYNTAX on
      [MKI$.md](../../docs/keywords/MKI$.md) and its siblings: KMC FX 5, 18, 31 and DFX 5, 18, 31 (zerobas NODISK and
      DISK alike). The other functions' `F` without a parenthesis (`R=CVI`, `R=ABS` ...) are 2 on zerobas too, so it
      is the three MK*$ tokens' own path.
      ➡️ When picked up: the MK*$ dispatch must require `(` and raise 2, as the one-argument functions do. The
      acceptance is the three SYNTAX rules.
