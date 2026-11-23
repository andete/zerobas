#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC: run every BIOS spec probe (probes/bios/spec/*.asm -- the MSX1, MSX2 and MSX2+ probes) and biosl rung
on the two turbo R references (biosl_run.py --row turbor: FS-A1GT = "ref", FS-A1ST = "ours"), one output file per
probe in scratchpad/AE_trall/.

Joost 2026-11-23: nothing is assumed unchanged from an earlier generation. scratchpad/trall_cmp.py sets each probe's
A1GT `CAP ref` against the reading the page it serves is based on (the VG-8020 for an MSX1 probe, the FS-A1WSX for
an MSX2 / MSX2+ probe). The turbo R twin of scratchpad/m1on2_run.py.

Each probe runs in an isolated instance (tools/agent_wt.py INSTANCE --fresh: empty clock-chip / persistent state, so
readings are reproducible). Serial; a probe whose file exists is skipped (re-runnable after a stop). A wall-clock
timeout (default 1800 s) is a backstop only -- biosl_run.py's own emulated-time timeout bounds a hang (rc=2).

    python3 -u scratchpad/trall_run.py [--instance NAME] [PROBE ...]
"""
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scratchpad", "AE_trall")


def probes(names):
    allp = sorted(glob.glob(os.path.join(ROOT, "probes/bios/spec/*.asm"))) + \
        sorted(glob.glob(os.path.join(ROOT, "probes/bios/biosl/*.asm")))
    if names:
        allp = [p for p in allp if os.path.splitext(os.path.basename(p))[0] in names]
    return allp


def main():
    args = sys.argv[1:]
    inst = "tr3"
    if "--instance" in args:
        i = args.index("--instance")
        inst = args[i + 1]
        del args[i:i + 2]
    os.makedirs(OUT, exist_ok=True)
    todo = probes(args)
    for i, p in enumerate(todo):
        name = os.path.splitext(os.path.basename(p))[0]
        dest = os.path.join(OUT, name + ".out")
        if os.path.exists(dest):
            continue
        t = time.time()
        rel = os.path.relpath(p, ROOT)
        try:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "agent_wt.py"), inst, "--fresh", "--",
                                "python3", "-u", "probes/bios/biosl_run.py", rel, "--row", "turbor"],
                               cwd=ROOT, capture_output=True, text=True, timeout=1800)
            body, rc = r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired as e:
            body, rc = (e.stdout or "") if isinstance(e.stdout, str) else "", "TIMEOUT"
        open(dest + ".tmp", "w").write(f"# rc={rc}\n" + body)
        os.replace(dest + ".tmp", dest)
        print(f"[{i + 1}/{len(todo)}] {name} rc={rc} {time.time() - t:.0f}s", flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
