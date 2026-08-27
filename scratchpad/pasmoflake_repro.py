#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Drive the `unit-test` pasmo flake until it SAYS WHY, or measure it silent.

The filed item (TODO.md) is explicit: *"Do not close this on the next green
battery; close it on a captured message."* So this does not wait for a battery.
It runs the exact command `tests/test_expr.py::build()` runs --
`pasmo --bin basic/main.asm <rom> <sym>` -- under the pressure the battery
applies, and captures stderr on any non-zero exit.

THREE ARMS. 🔴 THE FIRST CUT USED THE SHARED-OUTPUT-PATH ARM AS ITS POSITIVE
CONTROL AND IT CAME BACK 0/32 -- so the run had no proof it could detect a pasmo
failure at all, and a silent subject would have been the ALL-CONVERGED shape.
The detection control has to be something that CANNOT pass:

  DETECT   pasmo on a source with a deliberate syntax error. MUST fail, with a
           message. Proves rc and stderr capture work; exit 2 if it passes.
  SHARED   N workers writing the SAME output pair -- the collision hypothesis
           `tests/_tmp.py` was written for. A result either way.
  PRESSURE N workers, each with its OWN output pair, at high concurrency. This
           is the battery's actual condition for `zb_eval.rom` (one test file
           owns the name, `tests/run.py` is serial), so a failure here is
           resource pressure and nothing else.

⚠️ THE POINT IS THE MESSAGE, NOT THE COUNT. Every non-zero exit is printed with
its stderr; a bare rate would reproduce the exact defect that filed this item.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402

SRC = os.path.join(ROOT, "basic", "main.asm")


def one(paths):
    rom, sym = paths
    r = subprocess.run(["pasmo", "--bin", SRC, rom, sym],
                       capture_output=True, cwd=ROOT)
    return r.returncode, r.stderr.decode("utf-8", "replace").strip(), \
        r.stdout.decode("utf-8", "replace").strip()


def detect_control():
    """A failure the harness MUST see: pasmo on a source it cannot assemble."""
    d = probe_tmp.tmp("pasmoflake-detect")
    os.makedirs(d, exist_ok=True)
    bad = os.path.join(d, "bad.asm")
    open(bad, "w").write("    this is not z80\n")
    r = subprocess.run(["pasmo", "--bin", bad, os.path.join(d, "b.rom"),
                        os.path.join(d, "b.sym")], capture_output=True, cwd=ROOT)
    msg = (r.stderr or r.stdout).decode("utf-8", "replace").strip()
    return r.returncode, msg


def arm(name, rounds, workers, shared):
    d = probe_tmp.tmp(f"pasmoflake-{name}")
    os.makedirs(d, exist_ok=True)
    fails = []
    for rnd in range(rounds):
        jobs = []
        for w in range(workers):
            tag = "shared" if shared else f"w{w}"
            jobs.append((os.path.join(d, f"{tag}.rom"),
                         os.path.join(d, f"{tag}.sym")))
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for i, (rc, err, out) in enumerate(ex.map(one, jobs)):
                if rc != 0:
                    fails.append((rnd, i, rc, err, out))
    return fails, rounds * workers


def report(name, fails, n):
    print(f"  {name:8s} {len(fails):4d} failure(s) in {n} run(s)")
    seen = set()
    for rnd, i, rc, err, out in fails:
        key = (rc, err[:200])
        if key in seen:
            continue
        seen.add(key)
        print(f"      round {rnd} worker {i} rc={rc}")
        for label, blob in (("stderr", err), ("stdout", out)):
            if blob:
                for line in blob.splitlines()[:6]:
                    print(f"        {label}: {line}")
    if fails and not any(f[3] or f[4] for f in fails):
        print("      🔴 EVERY FAILURE WAS SILENT — pasmo exited non-zero and "
              "wrote NOTHING to either stream. That is a finding about pasmo, "
              "not about the harness.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    print(f"pasmo flake repro: {a.rounds} rounds x {a.workers} workers per arm, "
          f"assembling {os.path.relpath(SRC, ROOT)}")
    rc, msg = detect_control()
    if rc == 0 or not msg:
        print(f"\nINSTRUMENT FAULT (rc 2): the DETECTION control did not fail "
              f"with a message (rc={rc}, message={msg!r}). Nothing below is a "
              f"reading.")
        return 2
    print(f"  DETECT   rc={rc} and it said: {msg.splitlines()[0][:90]!r} ✅")

    sh, nsh = arm("shared", max(2, a.rounds // 3), a.workers, shared=True)
    report("SHARED", sh, nsh)
    pr, npr = arm("pressure", a.rounds, a.workers, shared=False)
    report("PRESSURE", pr, npr)

    print(f"\nSHARED   {len(sh)}/{nsh} non-zero exits, {a.workers} workers on ONE output pair")
    print(f"PRESSURE {len(pr)}/{npr} non-zero exits, {a.workers} workers on their own pairs")
    if not sh and not pr:
        print("NOT REPRODUCED at this denominator, and the detection control "
              "proves the harness would have seen it. A measured negative, not "
              "a diagnosis — the item stays open and now names a number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
