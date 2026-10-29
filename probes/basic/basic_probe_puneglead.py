#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""puneglead-acceptance (D-PUNEGLEAD): a sign with no room takes the column's
`0`, and a leading sign makes a trailing one a literal.

Found measuring D-PUTINY: `PRINT USING "#.##";-.5` is `-.50` on the VG-8020 and
was `%-0.50` here. Measured (scratchpad/puneglead_measure.out,
puneglead_both.out):
  * a lone `0.` loses its `0` when the finished field would not fit: `-.50`,
    `-.00`, `#.#`;-.04 `-.0`, `+.##`;.5 `+.50`; with room it stays (`-0.50`), and
    a real integer digit still overflows (-.996 is `%-1.00`);
  * `+.##` and `$$.##` are fields (they were a literal and a field): `-.50`,
    `-$.50`, and `$$.##`;.5 keeps its `0` (`$0.50`) -- `$$` has the column;
  * after a leading `+`, a trailing `+` / `-` is a literal: `+.##+`;-.25 is
    `-.25+`, `+#.##-`;.25 is `+0.25-`. It used to replace the leading sign.
One program, scratchpad/puneglead_probe.bas; both zerobas targets against the
VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/puneglead_probe.bas"
ROWS = 11


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "puneglead", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "puneglead", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: negative fractions and sign pairs fill "
          f"PRINT USING fields as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
