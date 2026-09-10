#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RUNLINE2 — does `RUN <lineno>` AT THE PROMPT still ignore its argument?

TODO.md's R2 (filed 2026-08-22 by D-RUNLINE §4) says it does:

    "`RUN 20` typed at the PROMPT never reaches `do_run`: `dispatch_line` runs
     `is_cmd` against the raw LINEBUF, before `tokenise`, so direct mode never
     sees `$0E` and `dl_run` still ignores the number."

\U0001f534 BUT `basic/program.asm`'s `dl_bare` HEADER DESCRIBES THAT EXACT CLASS
BEING FIXED, under D-RUNARG, and it is dated AFTER R2 was filed. Its own table
records `RUN 20` running from the top here against the CF-3300 running from line
20, and its fix is "only the bare form belongs on the fast path; everything else
is crunched and reaches `do_run` as a statement".

\U0001f3af SO THE FILED CLAIM AND THE CODE COMMENT CONTRADICT EACH OTHER, AND A
COMMENT IS NOT A MEASUREMENT EITHER. This probe is the arbiter. It types at the
PROMPT -- which is the whole point, since the claim is specifically about direct
mode -- and reads WHICH LINE the program started from.

    10 PRINT "A";   20 PRINT "B";   30 PRINT "C";

so a run from the top prints `ABC`, a run from 20 prints `BC`, and a run from 30
prints `C`. The letters ARE the reading: an ERR column cannot tell "started at
the top" from "started where it was asked", which is the whole defect
[[an-unnamed-outcome-reads-as-no-outcome]].

⚠️ `r.ctl` IS NOT OPTIONAL. A bare `RUN` must print `ABC` everywhere; if it does
not, the fixture never ran and every row below is an artefact of that rather than
a statement about `RUN`.
⚠️ AND `r.nospace` IS THE ROW THAT SEPARATES TWO RULES. `RUN20` (no space) never
matched `is_cmd` even before D-RUNARG, so it has always been crunched. If it
agrees while `RUN 20` does not, the defect is in the SPACE-delimited fast path
specifically -- not in `do_run`'s handling of a line number
[[two-rules-that-coincide-on-every-row-you-have]].
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

# \U0001f534 LINE 40 IS A BARE `PRINT`, AND IT IS THE WITNESS, NOT DECORATION.
# Round 1 typed a `PRINT "ZQ";` marker before the RUN and looked for the letters
# after it. With the trailing `;` the cursor stays mid-line, so the ECHO of the
# next typed line lands there instead -- the screen reads `ZQRUN` and the letters
# are somewhere else entirely. Every row read empty and the control refused the
# run, which is exactly what it is for. The letters now get a line of their own
# and are matched as a whole line, so no marker is needed at all.
PROG = ['10 PRINT "A";', '20 PRINT "B";', '30 PRINT "C";', '40 PRINT', '50 END']

CASES = [
    ("r.ctl",     "RUN",      "ABC", "CONTROL: bare RUN starts at the top"),
    ("r.20",      "RUN 20",   "BC",  "\U0001f3af THE SUBJECT: a line number at the PROMPT"),
    ("r.30",      "RUN 30",   "C",   "a second line number -- one row could be luck"),
    ("r.nospace", "RUN20",    "BC",  "no space: never took the fast path, even before D-RUNARG"),
    ("r.colon",   "RUN 20:",  "BC",  "a trailing colon, which `dl_bare` treats as bare"),
]


def main() -> int:
    out = {}
    for tag, stmt, want, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = list(PROG) + [stmt]
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p)],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=12.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            # \U0001f534 THE CAPTURE HAS NO NEWLINES. It is a flat 40-column
            # screen dump: each row is space-padded to the full width and the
            # rows are concatenated, so a line-anchored regex matches NOTHING
            # and every row reads `<none>`. Round 2 failed exactly that way and
            # the control refused the run -- twice, before I stopped guessing at
            # the format and printed the raw string. LOOK AT THE READOUT.
            # Splitting on the column padding gives one token per screen row:
            # 'ZBRUN', then 'ABC', then the 'ZB' prompt. No other token in the
            # dump is made only of A/B/C -- the echoed program lines carry those
            # letters solely inside quotes, alongside digits and PRINT.
            toks = [t for t in re.split(r"\s{2,}", raw) if t]
            m = [t for t in toks if t and all(ch in "ABC" for ch in t)]
            row[side] = (m[-1] if m else None)
        out[tag] = row
        f = {s: ("<none>" if row[s] is None else f"[{row[s]}]") for s in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:10s} {stmt:9s} want={want:4s} vg={f['vg8020']:7s} "
              f"cf={f['cf3300']:7s} zb={f['zb']:7s}{mark}\n"
              f"             {note}", flush=True)

    ctl = out["r.ctl"]
    if any(ctl[s] != "ABC" for s in SIDES):
        print(f"\n  \U0001f534 THE CONTROL DID NOT PRINT ABC ({ctl}) -- the fixture "
              f"never ran, so no row below is a statement about RUN.")
        return 2
    dis = [t for t, *_ in CASES
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    for t, *_ in CASES:
        print(f"   {t:10s} vg {out[t]['vg8020']!r}   cf {out[t]['cf3300']!r}   "
              f"zb {out[t]['zb']!r}")
    if "r.20" not in dis:
        print("\n\U0001f7e2 R2's FILED CLAIM IS REFUTED: `RUN 20` at the prompt "
              "agrees with both references, so D-RUNARG already closed it and "
              "the entry is stale rather than outstanding.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
