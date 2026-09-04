#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-CP1..3 — the three CONTROL-FRAME-POOL gates, falsified by planting.

A gate that has never failed is not known to be ABLE to fail, and these three
(`stackpool-acceptance`, `trapdepth-acceptance`, `ctlcross-acceptance`) were
promoted out of `scratchpad/` on 2026-09-04 having never once gone red on this
tree. Each cut below has a PREDICTED red arm and PREDICTED green controls, and
the controls are the half that carries the information: a knife that reddens
every gate has only proved the machine broke.

    knife                          stackpool   trapdepth   ctlcross
    K-CP1  gosub_push drops FSP      green🟢     green🟢      RED🔴
    K-CP2  pool top ignores POOLSIZE   RED🔴     green🟢     green🟢
    K-CP3  collision floor removed     RED🔴       RED🔴     green🟢

🎯 EACH CUT IS AIMED AT ONE INVARIANT AND THE GREENS ARE THE EVIDENCE. K-CP1
leaves the pool fully working -- same depth, same CLEAR response -- and moves
ONLY the three interleave rows, which is what says `ctlcross` is measuring the
FOR-run floor and not the pool in general. K-CP2 leaves the depth large and the
interleave correct and moves ONLY sensitivity, which is what says `stackpool`
gates the MODEL rather than a number. A knife that reddened everything would
have proved only that the machine broke.

🔴 THE ROM HASH ROUND EVERY PLANT (D-KNIFEROM2). A knife whose rebuild did not
happen reports "nothing moved", which is what an arm with nothing to say looks
like. `knife_guard.build` refuses instead. [[a-knife-can-be-inert-because-the-build-did-not-happen]]

🔴 RESTORE IS `atexit` AND THE MTIME IS DELIBERATELY NOT PRESERVED
(D-KNIFEGUARD): a knife that puts the mtime back leaves `make` nothing to
rebuild, and the next gate scores the KNIFED ROM as the shipping one.

    python3 scratchpad/ctlpool_knives.py [--only K-CP1]
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)
import knife_guard                                                # noqa: E402

TMP = "scratchpad/ctlpool_knives"
PROG = "basic/program.asm"
SUBSH = "sub/strheap.asm"
STRENG = "basic/str-engine.asm"

GATES = {
    "stackpool": "probes/basic/basic_probe_stackpool.py",
    "trapdepth": "probes/basic/basic_probe_trapdepth.py",
    "ctlcross":  "probes/basic/basic_probe_ctlcross.py",
}

# tag -> (file, anchor, replacement, expected verdicts, why)
# 🔴 ALL THREE CUTS WERE REPLACED 2026-09-04 WHEN THE POOL LANDED. They used to
# shrink `GOSUB_DEPTH` and `FOR_DEPTH` and move the overflow ERR -- constants
# that no longer exist. A knife whose anchor has been deleted cuts NOTHING and
# its red arm passes by never firing; the anchor guard below is what catches
# that, and it caught it here.
KNIVES = [
    # 🎯 THE D-CTLCROSS INVARIANT, AND NOTHING ELSE. `gosub_push` sets FSP -- the
    # FOR run's floor -- to the new frame's base, which is what makes the FOR
    # frames opened OUTSIDE a subroutine invisible to a NEXT inside it. Drop that
    # one store and the pool still works, the depth is unchanged, and the three
    # interleave rows go back to their pre-pool answers.
    ("K-CP1", PROG,
     "                ld      hl,(CSP)\n"
     "                ld      (GSP),hl\n"
     "                ld      (FSP),hl",
     "                ld      hl,(CSP)\n"
     "                ld      (GSP),hl          ; K-CP1 CUT: no FSP",
     {"stackpool": "green", "trapdepth": "green", "ctlcross": "red"},
     "the FOR run's floor stops moving at a GOSUB"),

    # 🎯 THE ALLOCATION MODEL, AND NOTHING ELSE. `strheap_ceiling` is
    # min(HIMEM,TXTMAX) -- the same ceiling, WITHOUT the string pool subtracted --
    # so the pool top stops tracking POOLSIZE and `CLEAR n` no longer moves the
    # depth. The pool still works and is still big, so only the row that gates
    # SENSITIVITY can see it.
    ("K-CP2", SUBSH,
     "                call    strheap_varceil     ; HL = the pool top (= reference STKTOP)",
     "                call    strheap_ceiling     ; K-CP2 CUT: ignores POOLSIZE",
     {"stackpool": "red", "trapdepth": "green", "ctlcross": "green"},
     "the pool top stops tracking CLEAR's string space"),

    # 🎯 THE ONE OVERFLOW CHECK. With the floor at 0 the pool never collides with
    # the variable area, so a runaway recursion runs until the address space
    # wraps instead of raising ERR 7 at the boundary.
    ("K-CP3", STRENG,
     "                ld      de,(CTLLIM)         ; the variable region's first free byte",
     "                ld      de,0                ; K-CP3 CUT: no floor at all",
     {"stackpool": "red", "trapdepth": "red", "ctlcross": "green"},
     "the collision floor is removed"),
]


def run_gate(name, tag):
    log = f"{TMP}/{tag}_{name}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATES[name], "--gate"],
                             stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run just this knife tag")
    args = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)

    sel = [k for k in KNIVES if not args.only or k[0] == args.only]
    if not sel:
        print(f"no knife matches {args.only!r}")
        return 2

    # --- every anchor must EXIST before anything is cut. An anchor that has
    #     drifted makes the knife cut nothing, and a red arm then passes by
    #     never firing. Checked for ALL of them up front, so a late drift does
    #     not surface halfway through a run that has already rebuilt twice.
    originals = {}
    for tag, path, anchor, _w, _e, _why in sel:
        if path not in originals:
            originals[path] = open(path).read()
        if originals[path].count(anchor) != 1:
            print(f"INSTRUMENT FAULT: {tag}'s anchor occurs "
                  f"{originals[path].count(anchor)} time(s) in {path}, not once:\n"
                  f"    {anchor.strip()!r}\n"
                  f"  The knife would cut nothing (or too much) and its red arm "
                  f"would pass by never firing.")
            return 2

    digests = {p: hashlib.sha256(s.encode()).hexdigest()
               for p, s in originals.items()}

    def restore():
        for p, s in originals.items():
            open(p, "w").write(s)
            assert hashlib.sha256(open(p).read().encode()).hexdigest() == digests[p], \
                f"{p} was NOT restored!"
        print(f"  restored {', '.join(originals)} byte-identically "
              f"(mtime deliberately bumped so make rebuilds)")
    atexit.register(restore)

    print("=== baseline: every gate must be GREEN before a knife means anything")
    base_rom = knife_guard.hashes()
    print(f"  ROM {base_rom}")
    base = {}
    for name in GATES:
        rc, log = run_gate(name, "base")
        base[name] = rc
        print(f"  {name:<10} rc={rc}  {'green' if rc == 0 else '🔴 ALREADY RED'}"
              f"   {log}")
    if any(base.values()):
        print("INSTRUMENT FAULT: a gate is red BEFORE any cut -- no knife below "
              "is readable.")
        return 2

    rows, faults = [], []
    for tag, path, anchor, repl, expect, why in sel:
        print(f"\n=== {tag}: {why}")
        # restore everything first so knives never compound
        for p, s in originals.items():
            open(p, "w").write(s)
        open(path, "w").write(originals[path].replace(anchor, repl, 1))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/{tag}_build.log", before)
        if rc:
            print(f"INSTRUMENT FAULT: the KNIFED tree does not build "
                  f"({TMP}/{tag}_build.log)")
            faults.append(tag)
            continue
        print(knife_guard.report(tag, moved, before, after))
        if not moved:
            faults.append(tag)
            continue
        for name in GATES:
            grc, log = run_gate(name, tag)
            got = "red" if grc else "green"
            ok = got == expect[name]
            rows.append((tag, name, expect[name], got, ok))
            print(f"  {name:<10} expected {expect[name]:<5} got {got:<5} "
                  f"{'ok' if ok else '🔴 WRONG'}   {log}")

    print("\n=== verdict")
    for tag, name, want, got, ok in rows:
        print(f"  {tag}  {name:<10} want {want:<5} got {got:<5} "
              f"{'ok' if ok else '🔴'}")
    bad = [r for r in rows if not r[4]]
    if faults:
        print(f"🔴 INSTRUMENT FAULT on {faults} -- those knives measured nothing.")
    if bad:
        print(f"🔴 {len(bad)} cell(s) did not match the prediction. A red arm that "
              f"stayed green means the gate cannot see its own subject; a green "
              f"control that reddened means the gate is pinned to more than it "
              f"claims.")
    print("KNIVES: PASS" if not bad and not faults
          else f"KNIVES: RED ({len(bad)} cell(s), {len(faults)} fault(s))")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
