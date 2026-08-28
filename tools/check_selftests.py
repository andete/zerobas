#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SELFTEST gate — every script that advertises a `--selftest` must PASS it.

🔴 A SCRIPT OUTSIDE THE BATTERY CAN BE RED FOR MONTHS AND NOBODY LEARNS. Measured
2026-08-28: of 15 scripts advertising `--selftest`, **THREE were red** and none
of them was in any gate --

  * `scratchpad/popraise_sweep.py` -- its known-answer set named `elas_abort_fp`,
    which D-POPRAISE'S OWN FIX had turned into an `equ` alias. The selftest went
    red the moment the slice shipped.
  * `tools/dupspan_indep.py` -- matched the literal bytes `c39a42`, i.e.
    `jp $429A`: raise_error's address WHEN THE ARM WAS WRITTEN. Every carve since
    relaid the ROM out, so the group matched nothing and it reported
    "got 0, want 6". One of the six spans had also been legitimately carved.
  * (a third was a FALSE positive of the first sweep -- see EXPECT_ARG below.)

🎯 THE CLASS: **a known-answer test keyed to a LIVE artifact rots every time the
artifact legitimately improves**, and rots SILENTLY when nothing collects its
exit code. Both fixes derive the answer instead of freezing it. Same shape as
D-WALLIT, where a README-listed probe had been failing for months on a stale
address because no battery collected its honest rc=1.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir
# the selftest's fixture dir would otherwise escape /tmp/zerobas [[one-temp-root]]
TREES = ("scratchpad", "tools", "probes/lib", "probes/basic")
ADVERTISES = re.compile(r'"--selftest"')

# ⚠️ `--selftest` that REQUIRES an argument is not a failing selftest, it is a
# different interface. The first sweep ran these bare, got a usage error, and
# counted them RED -- a false positive of the instrument, not a finding.
# Each entry needs its reason, so the list cannot quietly grow.
EXPECT_ARG = {
    "probes/lib/omsx_repl.py":
        "--selftest takes a MACHINE and boots an emulator; it is an emulator "
        "check, not a static one",
}


def advertised():
    out = []
    for t in TREES:
        for p in sorted(glob.glob(os.path.join(ROOT, t, "*.py"))):
            if ADVERTISES.search(open(p, errors="replace").read()):
                out.append(os.path.relpath(p, ROOT))
    return out


def main(argv):
    if "--selftest" in argv:
        return selftest()
    red, skipped, green = [], [], []
    for rel in advertised():
        if rel in EXPECT_ARG:
            skipped.append(rel)
            continue
        r = subprocess.run([sys.executable, os.path.join(ROOT, rel), "--selftest"],
                           capture_output=True, text=True, cwd=ROOT)
        (green if r.returncode == 0 else red).append((rel, r.returncode, r.stdout))
    print(f"check_selftests — {len(green) + len(red)} script(s) run, "
          f"{len(skipped)} skipped by declaration")
    for rel in skipped:
        print(f"  SKIP  {rel}\n        {EXPECT_ARG[rel]}")
    for rel, rc, out in red:
        tail = [l for l in out.strip().split("\n") if l.strip()][-3:]
        print(f"  RED   {rel}  (rc={rc})")
        for l in tail:
            print(f"        {l}")
    print(f"\n{len(red)} failing selftest(s)")
    return 1 if red else 0


def selftest():
    """🔴 The arm that matters: a script whose selftest FAILS must be reported."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="selftests-")
    fails = []

    def arm(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not cond:
            fails.append(name)

    good = os.path.join(d, "g.py")
    bad = os.path.join(d, "b.py")
    silent = os.path.join(d, "s.py")
    open(good, "w").write('import sys\nif "--selftest" in sys.argv: sys.exit(0)\n')
    open(bad, "w").write('import sys\nprint("FAIL x")\n'
                         'if "--selftest" in sys.argv: sys.exit(1)\n')
    open(silent, "w").write('print("I advertise nothing")\n')
    found = []
    for p in (good, bad, silent):
        if ADVERTISES.search(open(p).read()):
            found.append(os.path.basename(p))
    arm("S1 only scripts advertising --selftest are picked up",
        sorted(found) == ["b.py", "g.py"], f"found {sorted(found)}")
    rcs = {os.path.basename(p): subprocess.run(
        [sys.executable, p, "--selftest"], capture_output=True).returncode
        for p in (good, bad)}
    arm("S2 a passing selftest is rc=0", rcs["g.py"] == 0)
    arm("S3 🔴 a FAILING selftest is rc!=0 and would be reported", rcs["b.py"] != 0)
    arm("S4 every EXPECT_ARG entry carries a reason",
        all(v.strip() for v in EXPECT_ARG.values()))
    shutil.rmtree(d, ignore_errors=True)
    print()
    print("ALL PASS — check_selftests" if not fails else f"🔴 {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
