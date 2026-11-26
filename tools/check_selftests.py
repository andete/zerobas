#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
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


# ⏱ B2 (2026-11-25, gate_time_review): the selftests that PLANT into tracked files (content or mtime), measured by
# `--classify` (2026-11-25: these two of 90). They run ALONE, first; every other selftest runs on a pool. A script that
# plants and is not listed here is caught by the guard around the pool (tracked files' (mtime, size) before / after)
# and turns this check RED, naming the files -- re-run `--classify` and update the list.
PLANTERS = {
    "tools/check_disk_deps.py": "plants a dependency into the Makefile and restores it",
    "tools/check_wall_literals.py": "plants a literal into basic/sysvars.inc and a probe, and restores them",
}
JOBS = max(1, min(8, os.cpu_count() or 1))


def tracked_stat():
    """{tracked path: (mtime_ns, size)}"""
    out = {}
    for f in subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True).stdout.split(b"\0"):
        if f:
            try:
                st = os.stat(os.path.join(ROOT, f.decode()))
                out[f.decode()] = (st.st_mtime_ns, st.st_size)
            except OSError:
                pass
    return out


def collected_elsewhere():
    """⏱ A4 (2026-11-25): {script: the unit of THIS battery whose recipe runs `<script> --selftest`}. Only inside a
    battery (run_gates sets ZEROBAS_BATTERY_UNITS to the units of the run); standalone, nothing is skipped."""
    units = set(os.environ.get("ZEROBAS_BATTERY_UNITS", "").split())
    if not units:
        return {}
    out, target = {}, None
    for line in open(os.path.join(ROOT, "Makefile"), errors="replace"):
        m = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if m:
            target = m.group(1)
            continue
        m = re.match(r"^\tpython3 (\S+\.py) --selftest\s*$", line)
        if m and target in units and target != "selftest-check":
            out.setdefault(m.group(1), target)
    return out


def run_one(rel):
    r = subprocess.run([sys.executable, os.path.join(ROOT, rel), "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    return rel, r.returncode, r.stdout


def classify():
    """each selftest alone: does it move a tracked file? (the measurement PLANTERS records)"""
    import time
    for rel in advertised():
        if rel in EXPECT_ARG:
            continue
        a = tracked_stat()
        t = time.time()
        _, rc, _ = run_one(rel)
        b = tracked_stat()
        moved = sorted(f for f in set(a) | set(b) if a.get(f) != b.get(f))
        print(f"{time.time() - t:6.1f}s rc={rc} {'PLANTS ' + ' '.join(moved) if moved else 'pure'}  {rel}", flush=True)
    return 0


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
    if "--classify" in argv:
        return classify()
    import concurrent.futures
    red, skipped, green = [], [], []
    elsewhere = collected_elsewhere()
    pool_list, plant_list = [], []
    for rel in advertised():
        if rel in EXPECT_ARG:
            skipped.append(rel)
        elif rel in elsewhere:
            pass
        elif rel in PLANTERS:
            plant_list.append(rel)
        else:
            pool_list.append(rel)
    results = [run_one(rel) for rel in plant_list]          # alone, first
    before = tracked_stat()
    with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as ex:
        results += list(ex.map(run_one, pool_list))
    after = tracked_stat()
    planted = sorted(f for f in set(before) | set(after) if before.get(f) != after.get(f))
    # ⏱ B2 follow-up (2026-11-26): a POOLED selftest that fails is re-run ALONE once -- the battery's own
    # flake-vs-real rule. selftest-check went red once in a B4 A/B battery and green in 6 runs alone; a mutator is
    # never retried by run_gates, so the pool's contention must be told from a defect HERE. Green alone = FLAKE,
    # printed with its pooled output, never silent; red alone stays RED.
    flakes = []
    for k, (rel, rc, out) in enumerate(results):
        if rc != 0 and rel in pool_list:
            r2 = run_one(rel)
            if r2[1] == 0:
                flakes.append((rel, rc, out))
                results[k] = r2
    for rel, rc, out in results:
        (green if rc == 0 else red).append((rel, rc, out))
    print(f"check_selftests — {len(green) + len(red)} script(s) run ({len(plant_list)} planter(s) alone, "
          f"{len(pool_list)} on {JOBS} workers), {len(skipped)} skipped by declaration, "
          f"{len(elsewhere)} run by their own unit in this battery")
    for rel in skipped:
        print(f"  SKIP  {rel}\n        {EXPECT_ARG[rel]}")
    for rel, unit in sorted(elsewhere.items()):
        print(f"  BY    {rel}  ({unit})")
    for rel, rc, out in flakes:
        tail = [l for l in out.strip().split("\n") if l.strip()][-4:]
        print(f"  FLAKE {rel}  (rc={rc} on the pool, GREEN alone -- contention, not a defect; its pooled output:)")
        for l in tail:
            print(f"        {l}")
    if planted:
        print(f"  🔴 A SELFTEST NOT IN PLANTERS MOVED TRACKED FILE(S) while the pool ran: {' '.join(planted)} -- "
              f"run `python3 tools/check_selftests.py --classify` and add it to PLANTERS")
        red.append(("(the pool guard)", 1, ""))
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
    arm("S5 every PLANTERS entry carries a reason and names a script that exists",
        all(v.strip() and os.path.exists(os.path.join(ROOT, k)) for k, v in PLANTERS.items()))
    old = os.environ.get("ZEROBAS_BATTERY_UNITS")
    try:
        os.environ["ZEROBAS_BATTERY_UNITS"] = "dead-alias-check"
        got = collected_elsewhere()
        os.environ["ZEROBAS_BATTERY_UNITS"] = ""
        alone = collected_elsewhere()
    finally:
        if old is None:
            os.environ.pop("ZEROBAS_BATTERY_UNITS", None)
        else:
            os.environ["ZEROBAS_BATTERY_UNITS"] = old
    arm("S6 inside a battery, a selftest its own unit runs is skipped here (and ONLY that unit's)",
        got == {"tools/check_dead_aliases.py": "dead-alias-check"}, f"got {got}")
    arm("S7 NEGATIVE: standalone (no battery), nothing is skipped", alone == {})
    shutil.rmtree(d, ignore_errors=True)
    print()
    print("ALL PASS — check_selftests" if not fails else f"🔴 {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
