#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KNIFEROM gate — a knife runner must be able to prove its cut reached the ROM.

A knife writes a source file and invokes `make`. If the rebuild does not happen,
the probe measures the PREVIOUS machine and the runner reports "moved 0 row(s)"
-- indistinguishable from an arm that legitimately found nothing, and that is the
verdict specs quote as evidence. Measured 2026-08-28: one runner gave two
different answers on an unchanged tree, the wrong run reproducing the PREVIOUS
knife's output byte-for-byte (docs/spec-basic-ngram2.md §3).

🎯 THE CONVENTION ALREADY EXISTED; THE GATE DID NOT. 36 of 41 runners already
hashed the built images. This gate says so out loud and refuses the next runner
that omits it -- which is the whole reason the five that lacked it went unnoticed.

THE RULE: a file under scratchpad/ that CUTS A SOURCE FILE and rebuilds must
either
  * `import knife_guard`  (the shared implementation), or
  * hash the build images itself (`hashlib` / `getsize` over build/*.rom).
⚠️ The second arm is deliberately loose. This gate polices the PRESENCE of
evidence, not its correct USE -- a runner can hash and never compare. Reading
whether all 41 compare correctly is a separate audit, filed rather than claimed.
Do not let this gate's green be read as "every knife is guarded".
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir
# the selftest's scratch dir would otherwise escape /tmp/zerobas [[one-temp-root]]
BUILDS = re.compile(r"repack-machine")
SHARED = re.compile(r"^\s*import\s+knife_guard\b", re.M)
# 🔴 WHAT A KNIFE CUTS IS THE SIGNATURE -- a path under basic/ or sub/.
# The first rule policed anything that rebuilt, and reddened a race REPRODUCER
# that cuts nothing. The SECOND rule keyed on the write-back shape and silently
# excused FOURTEEN real runners, because they restore in four different ways
# (`open(src,"w").write`, `p.write_text`, `src.write_text`, ...). A false
# negative is worse than the false positive it replaced: the first is loud, the
# second lets a runner escape the gate without anyone noticing. Key on the
# SUBJECT, not on the syntax that happens to touch it.
CUTS = re.compile(r"\b(basic|sub)/[a-z0-9_-]+\.(asm|inc)\b")
# ...and the project's OWN naming convention, because five real runners name
# their source through a variable and match no path literal. Two signals, ORed:
# missing a knife is the failure that matters.
NAMED = re.compile(r"knife|knives")
OWN = re.compile(r"hashlib|getsize|st_size")


def audit(paths):
    guarded, unguarded, other = [], [], []
    for p in sorted(paths):
        try:
            s = open(p, errors="replace").read()
        except OSError:
            continue
        if not BUILDS.search(s):
            continue
        rel = os.path.relpath(p, ROOT)
        # 🔴 BUILDING IS NOT CUTTING. The first cut of this rule policed anything
        # that invoked `repack-machine` and reddened `machxml_repro.py` -- a race
        # REPRODUCER that rebuilds but never touches a source file, so there is
        # no cut for a hash to witness. A gate that reddens a file for which its
        # own claim is meaningless teaches people to ignore it.
        if not (CUTS.search(s) or NAMED.search(os.path.basename(p))):
            other.append(rel)
            continue
        how = ("shared" if SHARED.search(s)
               else "own" if OWN.search(s) else None)
        (guarded if how else unguarded).append((rel, how))
    return guarded, unguarded, other


def main(argv):
    if "--selftest" in argv:
        return selftest()
    guarded, unguarded, other = audit(glob.glob(os.path.join(ROOT, "scratchpad", "*.py")))
    shared = sum(1 for _, h in guarded if h == "shared")
    print(f"check_knife_guard — {len(guarded) + len(unguarded)} runner(s) invoke "
          f"repack-machine; {len(guarded)} can prove the cut landed "
          f"({shared} via knife_guard, {len(guarded) - shared} own)")
    for rel, _ in unguarded:
        print(f"  RED   {rel}")
        print(f"        invokes repack-machine but never hashes the built images, so "
              f"an INERT cut would report as 'moved 0 rows'")
    if other:
        print(f"  (not policed: {len(other)} file(s) rebuild but cut nothing — "
              f"{', '.join(os.path.basename(o) for o in other)})")
    print(f"\n{len(unguarded)} violation(s)")
    return 1 if unguarded else 0


def selftest():
    """🔴 THE ARM THAT MATTERS: a runner with no evidence must go RED. A gate
    that only ever sees a clean tree has never been shown to fire."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="knifeguard-gate-")
    fails = []

    def arm(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not cond:
            fails.append(name)

    good_shared = os.path.join(d, "a_knives.py")
    good_own = os.path.join(d, "b_knives.py")
    bad = os.path.join(d, "c_knives.py")
    unrelated = os.path.join(d, "d_probe.py")
    CUT = "open('basic/interp.asm', 'w')\n"
    open(good_shared, "w").write("import knife_guard\nsh('make repack-machine')\n" + CUT)
    open(good_own, "w").write("import hashlib\nsh('make repack-machine')\n" + CUT)
    open(bad, "w").write("sh('make repack-machine')   # no evidence at all\n" + CUT)
    open(unrelated, "w").write("print('I never build anything')\n")
    builds_no_cut = os.path.join(d, "e_repro.py")
    open(builds_no_cut, "w").write("sh('make repack-machine')  # a reproducer, cuts nothing\n")
    g, u, o = audit([good_shared, good_own, bad, unrelated, builds_no_cut])
    arm("S1 a runner importing knife_guard is GREEN",
        ("a_knives.py", "shared") in [(os.path.basename(r), h) for r, h in g])
    arm("S2 a runner hashing on its own is GREEN",
        ("b_knives.py", "own") in [(os.path.basename(r), h) for r, h in g])
    arm("S3 🔴 a runner with NO evidence is RED",
        [os.path.basename(r) for r, _ in u] == ["c_knives.py"],
        f"red set = {[os.path.basename(r) for r, _ in u]}")
    arm("S4 a file that never builds is not policed at all",
        "d_probe.py" not in [os.path.basename(r) for r, _ in g + u])
    arm("S5 a file that BUILDS but cuts nothing is not RED",
        [os.path.basename(x) for x in o] == ["e_repro.py"]
        and "e_repro.py" not in [os.path.basename(r) for r, _ in u])
    shutil.rmtree(d, ignore_errors=True)
    print()
    print("ALL PASS — check_knife_guard selftest" if not fails
          else f"🔴 {len(fails)} FAILED: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
