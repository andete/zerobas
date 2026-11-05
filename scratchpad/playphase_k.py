# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYPHASE: playphase.bas with a busy delay of K empty FOR passes after each
`T(B)=TIME` -- if the blocked PLAYs' return times move with K, the release is a
frame-boundary race on the main side, not the queue state. zerobas only unless --ref."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs  # noqa: E402

base = open(os.path.join(REPO, "scratchpad", "playphase.bas")).read()
machines = list(run_programs.ZB)[:1] + ([run_programs.REF] if "--ref" in sys.argv else [])
for k in (0, 3, 6, 10, 20):
    text = base.replace("T(B)=TIME:NEXT", f"T(B)=TIME:FOR W=1 TO {k}:NEXT:NEXT")
    for m in machines:
        r = run_programs.run(m, "playphase", text)
        print(f"K={k:<3} {m:30} {r[1].strip()!r}")
