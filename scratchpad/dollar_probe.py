#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUDOLLAR -- the `$$` floating-dollar SUB-VOCABULARY, swept.

D-USING measured ONE `$$` row (`u.dollar`, `USING"$$###";42`) and found the
references split: the VG-8020 renders `  $42` -- two positions reserved, one of
them spent on a `$` that floats against the number -- and the CF-3300 echoes
`$$ 42`, i.e. does not implement the specifier at all. Its own `**` row
(`u.star`, `***42` on all three) is what proves that: `**` and `$$` are the same
grammatical construct, a two-character prefix that reserves its own positions and
then fills or floats, and the CF-3300 gets `**` right. So this is a CAPABILITY
gap, not a house style, and the call was made to follow the VG-8020.

\U0001f534 BUT ONE ROW IS NOT A VOCABULARY, AND THE IMPLEMENTATION NEEDS THE
REST OF IT. `**`'s own spec (docs/spec-basic-pufloat.md) needed THREE rows to
separate its two claims -- the prefix is consumed, and it still counts toward the
width -- and a fourth, `a.full`, to show the width half alone. `$$` has strictly
more surface than `**` because a floating character has a POSITION as well as a
width, and that position has to be settled against the sign, the decimal point
and the overflow marker before any of it can be built.

\U0001f3af AND THE STATE BUDGET IS WHY THIS RUNS FIRST. `PU_FLAGS` is FULL --
bit0 trailing separator, bit1 wrapped, bit2 asterisk fill, bits3-5 the sign
specifier, bit6 `.`, bit7 `,` -- so `$$` cannot have a flag bit for free. Whether
it NEEDS one depends on `s.stardol`: if `**$$` is not a legal combination on the
reference, `$$` can ride bit2 with one discriminator; if it is, the two are
independent and the state question is real. That is a design fork settled by a
row, written down BEFORE the reading.

\U0001f534 THE WITNESS IS THE RENDERED TEXT, BRACKETED, exactly as D-USING has
it: `PRINT USING` produces LAYOUT, and every column of it is invisible to an
error code and destroyed by stripping.
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

# The CONTROL is `s.star`: it is D-USING's `u.star`, which read `***42` on all
# three machines. It is here so a run where the whole readout has gone wrong
# cannot be mistaken for "the references disagree about `$$`" -- the same job
# `u.int` does in D-USING, but closer to the subject.
CASES = [
    ("s.star",    '**###',    '42',      "CONTROL: `**` agreed on all 3 in D-USING"),
    ("d.basic",   '$$###',    '42',      "the D-USING row, repeated as the anchor"),
    ("s.wide",    '$$#####',  '42',      "how many columns the pair reserves"),
    ("s.full",    '$$###',    '12345',   "digits fill the field: does the `$` survive?"),
    ("s.neg",     '$$###',    '-42',     "sign vs dollar: which is nearer the digits?"),
    ("s.dec",     '$$##.##',  '3.5',     "with a decimal field"),
    ("s.ovf",     '$$#',      '1234',    "overflow: is the `%` marker still emitted?"),
    ("s.one",     '$###',     '42',      "a LONE `$` -- literal, as a lone `*` is?"),
    ("s.last",    '##$',      '42',      "`$` at the very end of the format"),
    ("s.trail",   '###$$',    '42',      "`$$` NOT before a `#` run"),
    ("s.stardol", '**$$###',  '42',      "THE STATE FORK: is the combination legal?"),
    ("s.comma",   '$$#####,', '12345',   "with comma grouping"),
    ("s.plus",    '+$$###',   '42',      "with the leading-sign specifier"),
]


def main() -> int:
    out = {}
    for tag, fmt, val, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ['10 PRINT "ZQ[";',
                 f'20 PRINT USING "{fmt}";{val};',
                 '30 PRINT "]QZ" : END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            # The typed LINE 20 is echoed and itself contains the format, so a
            # capture that never reached the PRINT would read the SOURCE back as
            # a value ([[trapsvc-echo-fence]]). Both fences below are that guard:
            # the echo carries a `"` and a `;`, the rendered field cannot.
            v = [g for g in re.findall(r'ZQ\[([^\]]*)\]QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"[{row[s_]}]")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} USING\"{fmt}\";{val:6s} vg={f['vg8020']:14s} "
              f"cf={f['cf3300']:14s} zb={f['zb']:14s}{mark}", flush=True)

    ctl = out.get("s.star", {})
    if any(ctl.get(s_) is None for s_ in SIDES):
        print(f"\n\U0001f534 THE `**` CONTROL READ <none> SOMEWHERE ({ctl}) -- the "
              f"bracketed readout is not surviving, and no row means anything.")
        return 2
    if len({ctl[s_] for s_ in SIDES}) != 1:
        print(f"\n\U0001f534 THE `**` CONTROL DISAGREES ({ctl}) -- D-USING read it "
              f"the same on all three. Something other than `$$` has moved; a "
              f"`$$` split read out of this run would have two candidate causes.")
        return 2
    splits = [t for t in out
              if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                     out[t]["zb"]) == "REFS-SPLIT"]
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} DIFF: {dis or 'none'} ; "
          f"{len(splits)} REFS-SPLIT: {splits or 'none'} ===")
    for t in out:
        print(f"   {t:9s} vg {out[t]['vg8020']!r}   cf {out[t]['cf3300']!r}   "
              f"zb {out[t]['zb']!r}")
    print("\n\U0001f3af THE STATE FORK IS `s.stardol`: if the VG-8020 refuses or "
          "ignores `**$$`, the two prefixes are MUTUALLY EXCLUSIVE and `$$` can "
          "ride PU_FLAGS bit2 with one discriminator; if it honours both, they "
          "are independent and `$$` needs state PU_FLAGS does not have.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
