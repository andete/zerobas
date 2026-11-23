#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX1ON2: run every MSX1 BIOS spec probe (probes/bios/spec/*.asm) and biosl rung on the three MSX2 / MSX2+
references and C-BIOS's own MSX2 builds (biosl_run.py --row msx2all), one output file per probe.

Joost 2026-11-23: "we cannot assume that e.g. msx1 bios calls behave exactly the same on an msx2". The MSX1
pages' reference is the VG-8020; this measures the same cases on the NMS 8250 / HB-F900 / FS-A1WSX, so
scratchpad/m1on2_cmp.py can set each probe's MSX2 `CAP ref` against the VG-8020's committed one.
Serial (never two emulators at once); a probe whose file already exists is skipped (re-runnable after a stop).

    python3 -u scratchpad/m1on2_run.py [NAME ...]
"""
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scratchpad", "AE_m1on2")


def probes(names):
    allp = sorted(glob.glob(os.path.join(ROOT, "probes/bios/spec/*.asm"))) + \
        sorted(glob.glob(os.path.join(ROOT, "probes/bios/biosl/*.asm")))
    if names:
        allp = [p for p in allp if os.path.splitext(os.path.basename(p))[0] in names]
    return allp


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = probes(sys.argv[1:])
    for i, p in enumerate(todo):
        name = os.path.splitext(os.path.basename(p))[0]
        dest = os.path.join(OUT, name + ".out")
        if os.path.exists(dest):
            continue
        t = time.time()
        try:
            r = subprocess.run([sys.executable, "-u", os.path.join(ROOT, "probes/bios/biosl_run.py"), p,
                                "--row", "msx2all"], cwd=ROOT, capture_output=True, text=True, timeout=900)
            body, rc = r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired as e:
            body, rc = (e.stdout or "") if isinstance(e.stdout, str) else "", "TIMEOUT"
        open(dest + ".tmp", "w").write(f"# rc={rc}\n" + body)
        os.replace(dest + ".tmp", dest)
        print(f"[{i + 1}/{len(todo)}] {name} rc={rc} {time.time() - t:.0f}s", flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
