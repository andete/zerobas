#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PREWIDEN — walk `check_probe_preflight`'s OWN rule over what it does not scan.

TODO's entry says `check_probe_preflight.py` carries the same hand-listed
`SCAN_DIRS` its sibling `injector-check` derived, that **6** out-of-scope `.py`
launch openMSX, and — the part that matters —

    "that rule has NOT been walked ... widening it on the strength of the
     sibling's measurement is exactly [[a-borrowed-window-inherits-its-corpus]].
     Re-open by walking preflight's own rule over its subject's life first."

🎯 SO THIS RUNS PREFLIGHT'S OWN CLASSIFIER, NOT A HEURISTIC. `scan_file()` is
imported and applied verbatim to every tracked `.py` OUTSIDE `SCAN_DIRS`, so the
verdicts are in the checker's terms — EXEMPT (argv is a list literal with no
`-machine`), REQUIRED-and-guarded, REQUIRED-and-not.

⚠️ WIDENING IS NOT WHAT THIS DECIDES. It reports what widening would COST: how
many sites go red, in how many files, and of what kind. A number is what the
entry asked for; the decision needs it and is not it.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_probe_preflight as P                                 # noqa: E402


def main() -> int:
    scan = tuple(P.SCAN_DIRS)
    tracked = [f for f in subprocess.run(["git", "ls-files"], cwd=ROOT,
                                         capture_output=True, text=True
                                         ).stdout.split() if f.endswith(".py")]
    inside = [f for f in tracked if f.split("/")[0] in scan]
    outside = [f for f in tracked if f.split("/")[0] not in scan]
    print(f"SCAN_DIRS = {scan}")
    print(f"tracked .py: {len(tracked)}  inside {len(inside)}  outside {len(outside)}")

    ex = req = ung = 0
    files_with_ung = {}
    for rel in outside:
        p = os.path.join(ROOT, rel)
        try:
            sites = P.scan_file(p)
        except SyntaxError:
            print(f"  \U0001f534 {rel}: does not parse — not a verdict")
            continue
        for s in sites:
            if s.verdict == "EXEMPT":
                ex += 1
            else:
                req += 1
                if not s.guarded:
                    ung += 1
                    files_with_ung.setdefault(rel, 0)
                    files_with_ung[rel] += 1
    print(f"\nOUTSIDE the window, by preflight's OWN rule:")
    print(f"  EXEMPT (argv proves no -machine)      {ex}")
    print(f"  REQUIRED                              {req}")
    print(f"    of which UNGUARDED                  {ung}   in {len(files_with_ung)} file(s)")
    if not (ex or req):
        print("\n\U0001f534 INSTRUMENT FAULT: not one spawn site found outside the "
              "window. Either the walk is broken or SCAN_DIRS already covers "
              "everything — and a clean result here would mean nothing.")
        return 2
    print("\ntop files by unguarded sites:")
    for rel, n in sorted(files_with_ung.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {n:3d}  {rel}")
    print(f"\n\U0001f3af WIDENING `SCAN_DIRS` TO INCLUDE THESE WOULD TURN {ung} SITE(S) "
          f"IN {len(files_with_ung)} FILE(S) RED ON THE NEXT `make gates`.\n"
          f"   That is the COST, not the verdict. The entry's own warning stands: "
          f"do not widen\n   on a sibling's measurement — and now not on this one "
          f"either, until someone says\n   whether a throwaway knife runner OUGHT "
          f"to preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
