#!/usr/bin/env python3
"""loops4_time.bas's four loops (300 passes each, TIME ticks), printed on screen:
A=I+7 / A=I*7 / empty I% / empty default. python3 -u scratchpad/loops4_run.py"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402
lines = [l for l in open(os.path.join(REPO, "scratchpad", "loops4_time.bas")).read().splitlines()
         if l.strip() and not l.startswith("60")]
prog = ["NEW"] + lines + ['60 PRINT CHR$(91);"T";A1;A2;A3;A4;CHR$(93)', "RUN"]
cfg = probe_sides.sides("vg8020", "zbnodisk") if "zbnodisk" in probe_sides.MACHINES else None
sides = [("Philips_VG_8020", None), ("C-BIOS_MSX1_EU_REPACK_NODISK", None)]
for mach, _ in sides:
    cap = omsx_repl.run_cases(mach, [("t", prog)], batch=False, run_gap=12.0)[0] or ""
    got = [m for m in re.findall(r"\[T([^\]]*)\]", cap) if '";' not in m]
    print(mach, " ".join(got[-1].split()) if got else "<none>", flush=True)
