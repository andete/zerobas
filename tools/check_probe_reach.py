#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""probe-reach-check — which probes does no `make` target ever run?

WHY THIS EXISTS. D-WALLIT (docs/spec-wall-literals.md §3.1) found
`basic_probe_cas_verbs.py` failing two cases "for an unknown number of months":
it returns an honest `rc=1`, it is documented in README.md, and **nothing ever
ran it**. `wall-literal-check` covers the CAUSE of that particular break; this
covers the SHAPE. A probe outside every battery fails silently for any reason.

🔴 THREE STATES, NOT TWO, AND THE MIDDLE ONE IS WHY A NAIVE COUNT LIES:
  * INVOKED   -- a `make` recipe runs it by path.
  * IMPORTED  -- it is a LIBRARY for a probe that is invoked (`basic_probe_deffn`
                 is the expression harness a dozen probes drive). Its code runs
                 on every battery; it simply is not a target.
  * UNREACHED -- neither. Only these are the finding.
Counting "not named in the Makefile" would report every harness as dead, which is
the failure mode this tool exists to avoid in the first place.

🔴 AND IT REFUSES ON A DEGENERATE SCAN. If the Makefile scan finds almost no
invocations -- a moved tree, a changed recipe style -- every probe reads as
unreached and the report is loud and entirely false. Fewer than MIN_INVOKED is an
INSTRUMENT failure, exit 2, never a finding.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE_DIRS = ("probes/basic", "probes/disk", "probes/lib", "probes/tape")
MAKEFILE = os.path.join(ROOT, "Makefile")
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "probe-reach-allow.txt")
# The real count is ~60; the floor only has to be far above "the scan broke".
MIN_INVOKED = 15

INVOKE = re.compile(r"probes/[\w/]+/([\w]+)\.py")
IMPORT = re.compile(r"^\s*(?:import\s+(\w+)|from\s+(\w+)\s+import)", re.M)


def all_probes():
    out = {}
    for d in PROBE_DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for name in sorted(os.listdir(p)):
            if name.endswith(".py") and not name.startswith("__"):
                out[name[:-3]] = os.path.join(d, name)
    return out


def invoked_from_makefile():
    if not os.path.exists(MAKEFILE):
        return set()
    return set(INVOKE.findall(open(MAKEFILE, errors="replace").read()))


def import_edges(probes):
    """module -> set(probe modules it imports)."""
    edges = {}
    for mod, rel in probes.items():
        text = open(os.path.join(ROOT, rel), errors="replace").read()
        deps = set()
        for a, b in IMPORT.findall(text):
            name = a or b
            if name in probes and name != mod:
                deps.add(name)
        edges[mod] = deps
    return edges


def allowlist():
    out = {}
    if not os.path.exists(ALLOW):
        return out
    for line in open(ALLOW, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, why = line.partition(" ")
        out[name] = why.strip()
    return out


def classify():
    probes = all_probes()
    invoked = invoked_from_makefile() & set(probes)
    edges = import_edges(probes)
    reach = set(invoked)
    stack = list(invoked)
    while stack:
        m = stack.pop()
        for d in edges.get(m, ()):
            if d not in reach:
                reach.add(d)
                stack.append(d)
    imported = reach - invoked
    unreached = sorted(set(probes) - reach)
    return probes, invoked, imported, unreached


def check(verbose=True):
    probes, invoked, imported, unreached = classify()
    if len(invoked) < MIN_INVOKED:
        print(f"🔴 INSTRUMENT FAILURE: only {len(invoked)} probe invocation(s) "
              f"found in the Makefile (floor {MIN_INVOKED}). Every probe would "
              f"read as unreached. Refused, not reported.")
        return 2
    allow = allowlist()
    dead = [m for m in unreached if m not in allow]
    kept = [m for m in unreached if m in allow]
    if verbose:
        print(f"probe-reach-check: {len(probes)} probe(s) — "
              f"{len(invoked)} invoked by a make target, "
              f"{len(imported)} imported by one, {len(unreached)} unreached")
        for m in kept:
            print(f"  [allowed] {probes[m]} — {allow[m]}")
        for m in dead:
            print(f"  🔴 {probes[m]}: no `make` target runs it and no probe that "
                  f"is run imports it. Its rc is collected by NOTHING, so it "
                  f"fails silently for any reason at all. Give it a target, or "
                  f"allowlist it with a reason in "
                  f"{os.path.relpath(ALLOW, ROOT)}.")
        if not dead:
            print("  clean — every probe is invoked, imported by one that is, "
                  "or allowlisted with a reason")
    return 1 if dead else 0


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    probes, invoked, imported, unreached = classify()
    arm(f"S1 the Makefile scan is not degenerate ({len(invoked)} invocations, "
        f"floor {MIN_INVOKED})", len(invoked) >= MIN_INVOKED)
    # 🟢 THE CONTROL THAT MATTERS: a pure LIBRARY harness must land in IMPORTED,
    # not in UNREACHED. Without the import walk it would be the loudest false
    # positive in the report.
    arm("S2 a library harness is IMPORTED, not unreached "
        "(basic_probe_deffn drives a dozen probes and is no target)",
        "basic_probe_deffn" in imported or "basic_probe_deffn" in invoked)
    arm("S3 a probe with its own make target is INVOKED "
        "(basic_probe_runtail)", "basic_probe_runtail" in invoked)
    arm("S4 the three states do not overlap",
        not (invoked & imported) and not (set(unreached) & (invoked | imported)))
    # the degenerate-input refusal, DRIVEN rather than asserted
    global MAKEFILE
    saved = MAKEFILE
    try:
        MAKEFILE = os.path.join(ROOT, "no-such-makefile")
        arm("S5 a Makefile that cannot be read REFUSES (exit 2) rather than "
            "reporting every probe unreached", check(verbose=False) == 2)
    finally:
        MAKEFILE = saved
    # 🔴 THE RATCHET'S OWN ARM. An allowlist that pins everything is exactly as
    # useless as no check at all unless an UNPINNED name is still reported. Drive
    # it: drop one entry and the check must go RED.
    global allowlist
    real = allowlist
    victim = sorted(real())[0] if real() else None
    try:
        if victim:
            allowlist = lambda: {k: v for k, v in real().items() if k != victim}
            arm(f"S6 an UNPINNED unreached probe is still reported "
                f"(dropped {victim!r} from the allowlist -> RED)",
                check(verbose=False) == 1)
        else:
            arm("S6 the allowlist is not empty", False)
    finally:
        allowlist = real
    arm("S7 ...and with it back, the tree is clean again",
        check(verbose=False) == 0)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else check())
