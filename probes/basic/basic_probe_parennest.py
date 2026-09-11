#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""parennest-acceptance — how deep may an ORDINARY expression nest? (D-PARENNEST)

The gate for the TIER 1 defect the stack item names: a LEGAL formula corrupts the
machine. Both references evaluate every ladder below to depth 32; zerobas dies at
16 parentheses (screen garbage, then no output at all), at 16 nested `ABS(` with
`ERR 50` -- a code no expression path raises -- and at 12 nested string functions.
The cause is filed (D-FNSTK / D-SPMERGE): `SP` is C-BIOS's, ~234 B above its
floor, while ~22 KB of the free gap the reference's `STKTOP` points into sits
unused below `CTLTOP`.

🔴 THIS SHIPS **GREEN WITH THE DEFECT PINNED**, which is the tree's rule for a
measured divergence: every diverging depth carries the face zerobas gives TODAY,
so a regression (a shallower cap, a different wrong answer) is RED, and the fix
flips each pin to the reference's value IN THE SAME COMMIT AS THE CODE. A gate
that is simply red would be turned off; a pinned one keeps measuring.

⚠️ ONE ROW PER BOOT, never batch: a case that WRECKS the machine poisons every
later case in the same boot -- the first cut of the scout lost every row after
p16, including a control that had passed earlier in the same batch.
"""
from __future__ import annotations
import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402


def prog(tag, expr):
    return ["10 ON ERROR GOTO 900",
            f'20 CLS:PRINT"[{tag} ";{expr};"]":END',
            f'900 CLS:PRINT"[{tag} ERR";ERR;"AT";ERL;"]":END',
            "RUN"]


def parens(n):     # ((((1+1)+1)+1)...)          -> n+1
    return "(" * n + "1" + "+1)" * n


def absnest(n):    # ABS(ABS(...(1)...))         -> 1
    return "ABS(" * n + "1" + ")" * n


def strnest(n):    # LEN(CHR$(ASC(...CHR$(65)...))) -> 1, a temp per level
    return "LEN(" + "CHR$(ASC(" * n + "CHR$(65)" + "))" * n + ")"


CASES = ([(f"p{n:02d}", prog(f"p{n:02d}", parens(n)), str(n + 1)) for n in (8, 12, 16, 20, 24, 32)]
         + [(f"f{n:02d}", prog(f"f{n:02d}", absnest(n)), "1") for n in (8, 12, 16, 24, 32)]
         + [(f"s{n:02d}", prog(f"s{n:02d}", strnest(n)), "1") for n in (4, 8, 12, 16)]
         + [("p08r", prog("p08r", parens(8)), "9")])           # the readout's own control

# What zerobas answers TODAY (measured 2026-09-10, re-measured 2026-09-11 on the
# post-D-SPEEDPROF tree: unchanged). `None` = the machine never printed anything
# again -- it is dead, not wrong. Each entry is a DEFECT, not an accepted
# deviation: D-SPMERGE flips it to the reference's value.
PINNED = {
    "p16": None, "p20": None, "p24": None, "p32": None,
    "f16": "ERR 50 AT 20", "f24": "ERR 50 AT 20", "f32": "ERR 50 AT 20",
    "s12": None, "s16": "ERR 35 AT 20",
}


def face(cap, tag):
    """The row's OWN fence. A wrecked machine leaves the PREVIOUS row's text on
    the glass, and a batch would read that as this row's answer, so the fence
    carries its row name and anything else is `None` = nothing printed."""
    c = cap or ""
    k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0:
            return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]:
            return " ".join(c[i + len(tag) + 1:j].split())
        k = i


def read(side, cfg):
    out = {}
    for tag, lines, _ in CASES:
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, lines)], batch=False,
                                  boot=cfg["boot"], reset=cfg["reset"], run_gap=25.0)[0]
        out[tag] = face(cap, tag)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true", help="show both references too")
    a = ap.parse_args()
    sides = ("vg8020", "cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad, drift = [], []
    for tag, _, want in CASES:
        g = got["zb"][tag]
        if tag in PINNED:
            ok = g == PINNED[tag]
            note = (f"PINNED DEFECT {PINNED[tag]!r}" if ok
                    else f"🔴 DRIFT from the pinned defect {PINNED[tag]!r}")
            if not ok:
                drift.append(tag)
        else:
            ok = g == want
            note = "ok" if ok else f"🔴 want {want!r}"
            if not ok:
                bad.append(tag)
        extra = ("  " + "  ".join(f"{s}={got[s][tag]!r}" for s in ("vg8020", "cf3300"))
                 if a.survey else "")
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:5} zb={g!r:16} {note}{extra}")
    print(f"\n{len(CASES)} rows, {len(PINNED)} pinned defect(s) (D-SPMERGE flips them), "
          f"{len(bad)} unpinned divergence(s), {len(drift)} drift(s)")
    if drift:
        print("  🔴 a PINNED row moved: either the fix landed (flip the pin in the "
              "same commit) or the cap got worse -- read it, do not re-pin blind")
    return 1 if (bad or drift) else 0


if __name__ == "__main__":
    sys.exit(main())
