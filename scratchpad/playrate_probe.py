# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYRATE: what sets the VG-8020's floor on short PLAY notes? Runs a .bas
(default scratchpad/playrate_measure.bas) on the VG-8020 and a zerobas target and
prints both outputs side by side. Clean-room: a tape in, the printer port out;
PLAY(0) and TIME are the only readings."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs  # noqa: E402

bas = sys.argv[1] if len(sys.argv) > 1 else "playrate_measure.bas"
text = open(os.path.join(REPO, "scratchpad", bas)).read()
outs = []
for m in [run_programs.REF] + list(run_programs.ZB)[:1]:
    r = run_programs.run(m, "playrate", text)
    outs.append((m, r[0], r[1].replace("\r", "").splitlines()))
    print(f"{m:30} {r[0]}")
print("row   ref(A ret, B end)    zb(A ret, B end)")
for a, b in zip(outs[0][2], outs[1][2]):
    print(f"  {a:24} {b}")
