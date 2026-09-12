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
measured divergence — but pinned to the CLASS ("this depth does not produce the
value both references produce"), not to the exact wrong answer, because past the
cap the answer is whatever byte the corrupted recursion left behind and it moves
when unrelated code moves. The SHALLOW rows are unpinned and expect the real
value, so a cap that gets WORSE is red there; the deep rows go red the day they
start answering correctly, which is the fix landing and is exactly when the pin
must be booked.

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

# 🟢 THE PINS ARE FLIPPED -- D-SPMERGE CUT 2 LANDED (2026-09-11). Every depth here
# now answers the value both references give: p16/p20/p24/p32 read 17/21/25/33,
# f16/f24/f32 read 1, s12/s16 read 1. The set below is EMPTY and every row is
# scored against the reference, so a cap that ever comes back is RED on its own
# row -- which is what this file is for now that the defect is gone.
#
# 🔴 AND THE FIRST CUT FLIPPED ALL NINE TOO, AND WAS STILL WRONG (same day). A
# bare `ld sp,(CSP)` at `repl:` produced exactly these sixteen values and took
# THIRTY-TWO other suites down with it, because `ctl_alloc` allocates DOWNWARD
# FROM `CSP`: with the stack based there as well, the first `GOSUB`/`FOR`/trap
# frame landed inside live stack. What makes the second cut different is NOT this
# file -- it is `ctl_reloc` (basic/program.asm), which moves the live block out of
# the frame's way. These rows going green was necessary and nowhere near
# sufficient, and the full battery plus the five excluded targets is what actually
# decided it. Keep this paragraph: it is the reason nobody should read a green
# parennest as the fix.
WRECKED: set[str] = set()


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
        if tag in WRECKED:
            ok = g != want                      # still broken: the pinned state
            note = (f"PINNED DEFECT (wrecked; face {g!r} is noise)" if ok
                    else f"🟢 FIXED — it answers {want!r} now: FLIP THIS PIN")
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
    print(f"\n{len(CASES)} rows, {len(WRECKED)} pinned defect(s) (D-SPMERGE flips them), "
          f"{len(bad)} unpinned divergence(s), {len(drift)} drift(s)")
    if drift:
        print("  🟢 a PINNED row ANSWERS CORRECTLY now — the fix landed: move it out "
              "of WRECKED in the same commit as the code, so the gate keeps it")
    return 1 if (bad or drift) else 0


if __name__ == "__main__":
    sys.exit(main())
