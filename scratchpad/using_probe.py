#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-USING — the PRINT USING format surface, swept.

`ex_print_using` is the largest thinly-commented handler in the tree: 251 lines of
code at 0.49 comments per line, where the tree's median is near 1.0. Ranking every
handler that way is what put `ex_get` last and found two defects there, so this
takes the next one down.

PRINT USING is a DENOMINATOR question rather than an edge question: the format
language has a fixed, documented vocabulary (`#`, `.`, `+`, `-`, `**`, `$$`, `,`,
`^^^^`, `!`, `\ \`, `&`, literals), and either a specifier is implemented or it is
not. So the rows enumerate the vocabulary instead of hunting corners.

\U0001f534 THE WITNESS IS THE RENDERED TEXT, BRACKETED. `PRINT USING` produces
LAYOUT -- leading spaces, fill characters, a `%` overflow marker -- and every one
of those is invisible to an error code and destroyed by stripping. The rows wrap
the output in `[`...`]` so column counts survive the read.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
CASES = [
    ("u.int",    '###',        '42',      "integer field"),
    ("u.ovf",    '###',        '12345',   "value wider than the field -> % marker"),
    ("u.dec",    '##.##',      '3.14159', "decimal places"),
    ("u.round",  '##.#',       '2.35',    "rounding at the last place"),
    ("u.plus",   '+###',       '42',      "leading sign"),
    ("u.minus",  '###-',       '-42',     "TRAILING sign"),
    ("u.star",   '**###',      '42',      "asterisk fill"),
    ("u.dollar", '$$###',      '42',      "floating dollar"),
    ("u.comma",  '#####,',     '12345',   "comma grouping"),
    ("u.expo",   '##.##^^^^',  '123.456', "exponential"),
    ("u.lit",    'X#Y',        '5',       "literal text around the field"),
    ("u.bang",   '!',          '"ABC"',   "first character of a string"),
    ("u.amp",    '&',          '"ABC"',   "variable-length string"),
    ("u.slash",  '\\   \\',    '"ABCDE"', "fixed-width string field"),
]


def main() -> int:
    out = {}
    for tag, fmt, val, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ['10 PRINT"ZQ[";',
                 f'20 PRINT USING "{fmt}";{val};',
                 '30 PRINT"]QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\[([^\]]*)\]QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"[{row[s_]}]")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} USING\"{fmt}\";{val:9s} vg={f['vg8020']:14s} "
              f"cf={f['cf3300']:14s} zb={f['zb']:14s}{mark}", flush=True)

    ctl = out.get("u.int", {})
    if any(ctl.get(s_) is None for s_ in SIDES):
        print(f"\n\U0001f534 THE BASIC INTEGER FIELD READ <none> SOMEWHERE ({ctl}) -- "
              f"the bracketed readout is not surviving, and no row means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    for t in out:
        print(f"   {t:9s} vg {out[t]['vg8020']!r}   cf {out[t]['cf3300']!r}   "
              f"zb {out[t]['zb']!r}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
