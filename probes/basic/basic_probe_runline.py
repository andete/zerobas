#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RUNLINE2 — `RUN <lineno>` AT THE PROMPT, gated.

`dispatch_line` has a fast path for the REPL's own bare `RUN`, and `is_cmd`
matches when the next input byte is a DELIMITER -- right for telling `RUN` from
`RUNNER`, and wrong as a "takes no argument" test. D-RUNARG fixed that: only the
bare form stays on the fast path, everything else is crunched and reaches
`do_run` as a statement. Before it, `RUN 20` at the prompt ran from the TOP --
a SILENT WRONG PROGRAM RUN, the class this project ranks worst.

\U0001f534 AND THAT FIX WAS UNROWED. TODO.md's R2 carried the defect as still
open and ⛔ BLOCKED ("needs a fixture") until 2026-09-10, when measuring it
showed all five rows already agreeing on all three machines -- D-RUNARG had
closed it and nothing recorded that. An unrowed fix is one knife away from
silently regressing, and `namspc`'s own denominator names direct mode as NOT
COVERED, so no other battery would have caught it either.

\U0001f3af THE LETTERS ARE THE READING. The stored program is

    10 PRINT "A";   20 PRINT "B";   30 PRINT "C";   40 PRINT   50 END

so a run from the top prints `ABC`, from line 20 `BC`, from line 30 `C`. An ERR
column cannot tell "started at the top" from "started where it was asked", which
is the entire defect [[an-unnamed-outcome-reads-as-no-outcome]]. Line 40's bare
`PRINT` is what gives the letters a screen row of their own.

⚠️ `r.ctl` IS NOT DECORATION: if a bare `RUN` does not print `ABC` the
fixture never ran, and every row below is an artefact rather than a statement
about `RUN`. `r.nospace` separates two rules -- `RUN20` never matched `is_cmd`
even before D-RUNARG, so if it agreed while `RUN 20` did not, the defect would
be in the space-delimited fast path specifically and not in `do_run`
[[two-rules-that-coincide-on-every-row-you-have]].

\U0001f534 THE CAPTURE HAS NO NEWLINES -- it is a flat 40-column screen dump,
each row space-padded and concatenated. Two rounds of a line-anchored regex read
`<none>` everywhere before I printed the raw string and looked at it. Splitting
on the column padding gives one token per screen row.

Gate: `make runline-acceptance`. Scores zerobas against EXPECT (both references
measured 2026-09-10 and agreeing on every row); `--survey` re-measures all three.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

PROG = ['10 PRINT "A";', '20 PRINT "B";', '30 PRINT "C";', '40 PRINT', '50 END']

CASES = [
    ("r.ctl",     "RUN",      "CONTROL: bare RUN starts at the top"),
    ("r.20",      "RUN 20",   "the subject: a line number at the PROMPT"),
    ("r.30",      "RUN 30",   "a second line number -- one row could be luck"),
    ("r.nospace", "RUN20",    "no space: never took the fast path at all"),
    ("r.colon",   "RUN 20:",  "a trailing colon, which dl_bare treats as bare"),
]

# Measured 2026-09-10 on vg8020 AND cf3300, which agree on every row.
EXPECT = {
    "r.ctl":     "ABC",
    "r.20":      "BC",
    "r.30":      "C",
    "r.nospace": "BC",
    "r.colon":   "BC",
}


def read(side, cfg, stmt):
    raw = "".join(omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + PROG + [stmt])],
        batch=False, reset=(), boot=cfg["boot"], step=4.0, run_gap=12.0,
        cap_gap=4.0, timeout=420.0)[0] or "")
    toks = [t for t in re.split(r"\s{2,}", raw) if t]
    hits = [t for t in toks if all(ch in "ABC" for ch in t)]
    return hits[-1] if hits else None


def run(sides):
    cfg = probe_sides.sides(*sides)
    return {t: {s: read(s, cfg[s], stmt) for s in cfg} for t, stmt, _ in CASES}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true",
                    help="re-measure all three machines instead of gating")
    a = ap.parse_args()
    sides = ("vg8020", "cf3300", "zb") if a.survey else ("zb",)
    out = run(sides)

    if out["r.ctl"].get("zb") != EXPECT["r.ctl"]:
        print(f"\U0001f534 THE CONTROL DID NOT PRINT ABC "
              f"({out['r.ctl']!r}) -- the fixture never ran, so no row below is "
              f"a statement about RUN.")
        return 2
    bad = []
    for t, stmt, note in CASES:
        got, want = out[t]["zb"], EXPECT[t]
        ok = got == want
        if not ok:
            bad.append(t)
        extra = ""
        if a.survey:
            extra = (f"  vg={out[t]['vg8020']!r} cf={out[t]['cf3300']!r}")
        print(f"  {'ok ' if ok else '\U0001f534 '} {t:10s} {stmt:9s} "
              f"want={want!r:6s} zb={got!r:6s}{extra}   {note}")
    print(f"\nRUNLINE: {len(CASES) - len(bad)}/{len(CASES)} "
          f"{'PASS' if not bad else 'FAIL ' + ' '.join(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
