#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DOMAIN — out-of-range VALUES for the screen/graphics/sound verbs.

The argument-shape family (5 axes, 123 rows) and D-CHANFACE covered SHAPE, TYPE
and CHANNEL. This is the remaining axis: a well-formed argument of the right type
whose VALUE is outside the verb's domain.

⚠️ IT IS NOT A DUPLICATE OF `intarg-acceptance`, WHICH IS ALREADY A GATE. That one
covers the raw-I/O and string family -- OUT, POKE, VPOKE, PEEK, VPEEK, WAIT,
WIDTH, ON, SPACE$, STRING$, INP -- with `_neg`/`_ovf`/`_hi`/`_ill` variants. The
SCREEN/graphics/sound verbs have no such rows, and the review tier's own note says
so from the other side: "the coercion SURFACE is gated, the port/address MECHANISM
never reviewed".

\U0001f3af TWO ANSWERS ARE BOTH PLAUSIBLE AND THEY ARE NOT THE SAME BUG. A verb can
REJECT an out-of-range value (ERR 5) or CLAMP it and carry on -- this tree already
has a clamp finding ([[drawclamp-slice]]) -- so a row reading `no error` is not
automatically wrong. What matters is whether zerobas does what the references do.

  d.ctl   a legal in-range form -- must be `no error` everywhere, or the rows
          below are measuring the verb rather than the value
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
    ("d.ctl",      "COLOR 15,4,4",   "CONTROL: in range"),
    # 🎯 THE BOUNDARY, because "COLOR 99 is ERR 5" does not say WHERE the
    # domain ends, and a fix written against 99 alone could reject 15 or accept 16.
    ("col.fg0",    "COLOR 0",        "BOUNDARY: 0 is legal"),
    ("col.fg15",   "COLOR 15",       "BOUNDARY: 15 is legal"),
    ("col.fg16",   "COLOR 16",       "BOUNDARY: 16 is the first illegal one"),
    ("col.fg255",  "COLOR 255",      "a full byte"),
    ("col.fg256",  "COLOR 256",      "past a byte -- does it wrap to 0 and pass?"),
    ("col.fg99",   "COLOR 99",       "foreground past 15"),
    ("col.fgneg",  "COLOR -1",       "negative foreground"),
    ("col.bg99",   "COLOR 15,99",    "background past 15"),
    ("col.bd99",   "COLOR 15,4,99",  "border past 15"),
    ("loc.col99",  "LOCATE 99,0",    "column past the 40-column screen"),
    ("loc.row99",  "LOCATE 0,99",    "row past 24"),
    ("loc.neg",    "LOCATE -1,0",    "negative column"),
    ("loc.big",    "LOCATE 999,999", "both far out of range"),
    ("scr.99",     "SCREEN 99",      "mode past 3"),
    ("scr.neg",    "SCREEN -1",      "negative mode"),
    ("snd.reg99",  "SOUND 99,0",     "PSG register past 13"),
    ("snd.val999", "SOUND 0,999",    "value past 255"),
    ("snd.neg",    "SOUND -1,0",     "negative register"),
    ("pset.big",   "PSET(999,999)",  "coordinates off the screen"),
    ("pset.neg",   "PSET(-1,-1)",    "negative coordinates"),
    ("pset.col99", "PSET(0,0),99",   "colour past 15"),
]


def value(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9]+)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return int(g)
    return None


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            # SCREEN rows can leave the display unreadable, so every case gets a
            # fresh boot and the fence is printed in SCREEN 0 by the reset.
            p = ['10 ON ERROR GOTO 900', f'20 {stmt}',
                 '25 SCREEN 0', '30 PRINT"ZQ";0;"QZ":END',
                 '900 SCREEN 0:PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=14.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  ("ACCEPTED" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        v = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[v]
        print(f"  {tag:11s} {stmt:16s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if any(out.get("d.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('d.ctl')}) -- every row "
              f"is measuring the verb, not the value.")
        return 2
    vd = {k: probe_sides.verdict(v["vg8020"], v["cf3300"], v["zb"])
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    split = [k for k, x in vd.items() if x == "REFS-SPLIT"]
    clamp = [k for k, v in out.items()
             if k != "d.ctl" and v["vg8020"] == v["cf3300"] == v["zb"] == 0]
    blank = [k for k, v in out.items() if any(v[s_] is None for s_ in SIDES)]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    if clamp:
        print(f"    \U0001f7e2 CLAMPED (accepted on all three): {clamp} -- the "
              f"reference's own behaviour, which a faithful reimplementation KEEPS.")
    if blank:
        print(f"    \U0001f534 {blank} gave NO reading on a side -- an absence, and "
              f"each needs a reason before it is read as anything.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
