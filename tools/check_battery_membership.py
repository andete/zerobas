#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""battery-membership-check — every `*-acceptance` target is COLLECTED, or its
absence has a written reason.

🔴 WHY THIS EXISTS (D-UNCOLLECTED, 2026-09-01). `make gates` collects **22 of
the Makefile's 68 `*-acceptance` targets**. Nothing recorded that, nothing
justified it, and the project's own memory called `make gates` "the whole
acceptance-gate battery". Running the other 46 by hand found **three RED**:

  * `cursor-acceptance`  a real divergence (`X=TAB(5)` outside PRINT) AND a
                         stale KNOWN_RED exemption whose 8 rows now all agree
  * `namspc-acceptance`  a POSITIVE CONTROL failing on the reference, so it
                         refuses and measures nothing
  * `time-acceptance`    `is_jiffy` off by one

Same shape as `check_selftests.py` ("a script outside the battery can be RED FOR
MONTHS and nobody learns") and `check_probe_reach.py` ("a probe no make target
runs"). 🎯 THE GAP BETWEEN THEM IS WHAT BIT: probe-reach asks whether SOME target
runs the probe, which is weaker than whether the BATTERY does. All 46 pass
probe-reach and none was collected.

Excluding a suite is legitimate. Excluding it SILENTLY is not: an entry in
`tools/battery-exclusions.txt` needs a reason, so the list can grow but never
quietly -- the discipline `EXPECT_ARG` and `REGENERATED` already use.

Exit: 0 clean, 1 an acceptance target is neither collected nor excused,
2 the INSTRUMENT could not measure (a degenerate parse).

    python3 tools/check_battery_membership.py [--selftest]
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir
# the selftest's fixture dir would otherwise escape /tmp/zerobas [[one-temp-root]]
EXCL = os.path.join(ROOT, "tools", "battery-exclusions.txt")
MIN_GATES = 40          # a battery smaller than this means the parse broke
MIN_TARGETS = 30        # ditto for the Makefile scan


def battery(src: str) -> set[str]:
    out: set[str] = set()
    for name in ("STATIC", "EMULATOR"):
        m = re.search(rf'^{name}\s*=\s*"""(.*?)"""', src, re.S | re.M)
        if m:
            out |= set(m.group(1).split())
    return out


def acceptance_targets(mk: str) -> set[str]:
    """`*-acceptance` targets that actually have a recipe."""
    out, target = set(), None
    for line in mk.splitlines():
        m = re.match(r"^([A-Za-z0-9_./-]+):", line)
        if m and not line.startswith("\t"):
            target = m.group(1)
        elif line.startswith("\t") and target and target.endswith("-acceptance"):
            out.add(target)
    return out


def exclusions(path: str) -> dict[str, str]:
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _, reason = line.partition("\t")
        out[name.strip()] = reason.strip()
    return out


def check(root=ROOT) -> int:
    src = open(os.path.join(root, "tools", "run_gates.py")).read()
    mk = open(os.path.join(root, "Makefile")).read()
    gates, targets = battery(src), acceptance_targets(mk)
    # 🔴 REFUSE ON A DEGENERATE PARSE. The first cut of this measurement used a
    # regex that matched nothing, reported an EMPTY battery, and would have
    # called all 86 probes uncollected -- a plausible table from an input it
    # misread [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
    if len(gates) < MIN_GATES or len(targets) < MIN_TARGETS:
        print(f"INSTRUMENT: parsed {len(gates)} gate name(s) and {len(targets)} "
              f"acceptance target(s); floors are {MIN_GATES}/{MIN_TARGETS}. The "
              f"scan broke — nothing was measured.")
        return 2
    exc = exclusions(os.path.join(root, "tools", "battery-exclusions.txt"))
    collected = sorted(t for t in targets if t in gates)
    unlisted = sorted(t for t in targets if t not in gates and t not in exc)
    noreason = sorted(t for t, r in exc.items() if t in targets and not r)
    stale = sorted(t for t in exc if t in gates)

    print(f"battery-membership: {len(targets)} acceptance target(s) — "
          f"{len(collected)} collected by `make gates`, "
          f"{len(targets) - len(collected)} excluded with a reason.")
    rc = 0
    if unlisted:
        print(f"🔴 {len(unlisted)} acceptance target(s) are neither COLLECTED nor "
              f"EXCUSED — a suite nobody runs fails silently, for any reason:")
        for t in unlisted:
            print(f"     {t}")
        print(f"     → add it to run_gates.py's battery, or to "
              f"tools/battery-exclusions.txt WITH ITS REASON.")
        rc = 1
    if noreason:
        print(f"🔴 {len(noreason)} exclusion(s) carry no reason: "
              + " ".join(noreason))
        rc = 1
    if stale:
        print(f"⚠️  {len(stale)} exclusion(s) name a target that IS collected now "
              f"— delete the line: " + " ".join(stale))
        rc = max(rc, 1)
    unreviewed = sum(1 for t, r in exc.items()
                     if t in targets and r.startswith("UNREVIEWED"))
    if unreviewed:
        print(f"   ({unreviewed} of the exclusions are still UNREVIEWED — the "
              f"debt is visible and counted, which is the point.)")
    return rc


def selftest() -> int:
    """A planted gap must go RED, and the live tree must be GREEN."""
    import shutil
    import tempfile
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else '🔴 FAIL'}  {name}")
        ok = ok and bool(cond)

    arm("S1 the live tree is clean", check() == 0)
    tmp = tempfile.mkdtemp(prefix="battmem-")
    for rel in ("tools", ):
        os.makedirs(os.path.join(tmp, rel), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "Makefile"), os.path.join(tmp, "Makefile"))
    shutil.copy(os.path.join(ROOT, "tools", "run_gates.py"),
                os.path.join(tmp, "tools", "run_gates.py"))
    src = open(EXCL).read().splitlines(keepends=True)
    # drop the first non-comment entry -> that target is now unexcused
    kept = [l for l in src if l.lstrip().startswith("#") or not l.strip()]
    body = [l for l in src if l not in kept]
    open(os.path.join(tmp, "tools", "battery-exclusions.txt"), "w").writelines(
        kept + body[1:])
    arm("S2 a target with no entry and no battery slot goes RED",
        check(tmp) == 1)
    open(os.path.join(tmp, "tools", "battery-exclusions.txt"), "w").writelines(
        kept + body)
    arm("S3 ...and putting it back goes green again (the control)",
        check(tmp) == 0)
    open(os.path.join(tmp, "tools", "run_gates.py"), "w").write(
        'STATIC = """basic-reloc"""\nEMULATOR = """deadcode"""\n')
    arm("S4 a degenerate battery parse REFUSES (rc 2), never reports a finding",
        check(tmp) == 2)
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(check())
