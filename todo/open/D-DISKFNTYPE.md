- [ ] 🐛 **WITHOUT DISK BASIC, `MKI$("A")` / `MKS$("A")` / `MKD$("A")` AND `CVI(5)` / `CVS(5)` / `CVD(5)` ARE ERROR 13
      ON ZEROBAS; THE VG-8020 SAYS 5 (ILLEGAL FUNCTION CALL), AS FOR EVERY OTHER CALL OF THEM (D-DISKFNTYPE, found
      2026-11-24 by D-KWSPEC's conversion unit).**
      🎚️ TIER 6 — an error code, on the diskless target only; both refuse the call.
      🤖 **AUTONOMOUS** — measured by [`kmkcv.py`](../../probes/basic/spec/kmkcv.py) group FX ->
      [`KMC_run1.out`](../../scratchpad/KMC_run1.out); rules R-MKI-NODISK ... R-CVD-NODISK on the six pages: KMC FX 0,
      13, 26 (a string to MK*$) and 39, 46, 53 (a number to CV*). Without Disk BASIC the reference refuses the call
      with 5 after the argument is computed (its own error 11 still wins: `MKI$(1/0)` is 11 on both) and before its
      type is checked; zerobas checks the type first. On the DISK build both say 13, as the CF-3300 does.
      ➡️ When picked up: zerobas NODISK's MK*$ / CV* must raise 5 once the argument is evaluated, whatever its type.
      The acceptance is the six NODISK rules and the controls "without Disk BASIC the argument's type checked first
      (13) -- zerobas's" in [`kmkcv_controls.py`](../../probes/basic/spec/kmkcv_controls.py).
