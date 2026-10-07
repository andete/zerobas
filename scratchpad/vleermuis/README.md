# Vleermuis — a side experiment (2026-10-07)

`VLEERMUIS.BAS` and `LICENSE` are taken unchanged from
https://github.com/egonw/vleermuis (MIT, Copyright (c) 2021 Egon Willighagen): a
1989 type-in game from the C.U.C. journal, retyped, for the SV-328 and MSX.

Not a gate. `vleermuis_exp.py` builds an ASCII tape from the listing
(`probes/lib/cas_encode.py` `build_cas_ascii`), loads it with `LOAD"CAS:"` on
the diskless VG-8020 and on zerobas's diskless machine, and compares what each
machine made of it. The tapes and screen captures it writes here are generated.

## Findings, 2026-10-07

- **The tape round trip works.** `build_cas_ascii` makes a tape the VG-8020
  reads (`Found:VLEER`), and after `LOAD"CAS:"` the TOKENISED program in RAM
  (TXTTAB $F676 .. VARTAB $F6C2) is the same on both machines: 9106 bytes, byte
  sum 643700, position-weighted sum 2869264152 (`exp_load.out`, the `.screen`
  files). Our tokeniser agrees with the reference on 273 real lines, the
  duplicated line 2680 included.
- **RUN diverges, and the divergence is a real zerobas defect.** The VG-8020
  stops at `Syntax error in 1290`; ours at `Out of string space in 1070` with
  A=5 (`exp_diag_*.screen`, read after the stop / a Ctrl-STOP). Line 1070 READs
  the 120 forty-character DATA rows into `A$()`: the reference points a READ
  string at the program text and charges the 200-byte default string space
  nothing; ours copies it, and the fifth row fills it. That is TODO's
  "A STORED `DATA` LITERAL CHARGES THE STRING POOL NOTHING" item (ruled
  2026-09-27: point at the program text), filed at TIER 6 -- an ordinary 1989
  program shows it is a happy-path failure.
- **The reference's own stop is the listing's**: after the one-pass font loop
  (start above end: A = 3825 at the stop) the VG-8020 flows into the font DATA
  lines and raises 2 in 1290, whose last item is `80/q` (a retyping slip for
  `:'q`). Not yet isolated; ours must match it once it gets that far.
- Predictions scored: the load equivalence -- hit; `RUN` stopping at
  `Syntax error in 1580` (the `ON KEY GOSUC` typo) -- MISSED on both machines,
  neither got that far.
