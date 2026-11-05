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

args = [a for a in sys.argv[1:] if not a.startswith("--")]
bas = args[0] if args else "playrate_measure.bas"
text = open(os.path.join(REPO, "scratchpad", bas)).read()
# --cf3300: the second reference as a third column (Joost 2026-11-05: "cross-check
# against the 3300").
machines = [run_programs.REF] + list(run_programs.ZB)[:1]
if "--cf3300" in sys.argv:
    machines.insert(1, run_programs.DISK_REF)
outs = []
for m in machines:
    # the CF-3300 boots its disk ROM: a `1 REM @DISK` line gets it the harness's date
    # answer and a disk (run_programs.needs_disk); without it the run TIMES OUT.
    r = run_programs.run(m, "playrate", ("1 REM @DISK\n" + text) if m == run_programs.DISK_REF else text)
    outs.append((m, r[0], r[1].replace("\r", "").splitlines()))
    print(f"{m:30} {r[0]}")
print("row  " + "  |  ".join(f"{m[:16]} (A ret, B end)" for m, _, _ in outs))
for row in zip(*(o[2] for o in outs)):
    print("  " + "  |  ".join(f"{r.split(' T')[0] if len(outs) > 2 else r:24}" for r in row))
