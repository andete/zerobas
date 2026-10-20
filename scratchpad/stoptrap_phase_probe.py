#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FORINT's FULL battery (2026-10-20): stop-trap-acceptance's C_handler_baseline -- one
100 ms Ctrl-STOP tap, a counting handler that RETURNs -- reads flag=2 on zerobas (VG-8020:
1) after D-FORINT, and 1 on 508043a2. The program has no `%` variable. Is that a timing-
exposed latent edge bug in the STOP trap (a key still held when the handler starts counted
as a new press), or a regression? Sweep the tap's start across one 20 ms scan frame on the
machine as installed, the VG-8020 alongside. Prints the handler count per phase.
    python3 -u scratchpad/stoptrap_phase_probe.py        (SP_ONLY=ZB|REF)
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_stop_trap as P                   # noqa: E402

STARTS = [0.300, 0.304, 0.308, 0.312, 0.316]


def main():
    only = os.environ.get("SP_ONLY")
    sides = [(t, m) for t, m in (("REF", P.REF_MACHINE), ("ZB", P.ZB_MACHINE)) if only in (None, t)]
    for tag, m in sides:
        got = []
        for s in STARTS:
            r = P.run(m, P.CPROG, [(s, s + 0.10)])
            got.append(None if r is None else (r.get("flag"), r.get("ran"), r.get("done")))
        print(f"{tag:3} tap starts {STARTS}: (flag, ran, done) = {got}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
