#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which probe call sites tuned the WRONG capture knob (out of D-TWOFILE).

A case's capture fires `step` past its `RUN`, or `run_gap` past it when one is
given; `cap_gap` is the gap AFTER the capture and never moves it
(docs/spec-probe-budget.md S1, pinned by tests/test_capture_budget.py). So a
site that passes a `cap_gap` far larger than its `step` and NO `run_gap` was
tuned on a knob that buys its cases nothing.

⚠️ **A HIT HAS TWO MEANINGS AND THIS IS THEREFORE AN ADVISORY, NOT A GATE.** A
wide `cap_gap` is legitimate as inter-case spacing -- a disk write settling
before the next case is typed. What it CANNOT be is a completion budget. The
ratio ranks suspicion; only `settle_n` (the budget instrument) can convict.

Usage:  python3 scratchpad/gapscan.py [--tracked]   # --tracked: probes/tools/tests only
        python3 scratchpad/gapscan.py --selftest
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = r"([0-9]+(?:\.[0-9]+)?)"
DRIVER_STEP_DEFAULT = 2.5          # omsx_repl's own `step` default
WINDOW = 400                       # chars either side of the match to read kwargs from


def scan_text(txt: str):
    """Yield (cap_gap, step) for each call site in `txt` that passes `cap_gap`
    and no `run_gap`. Continuations are JOINED first: a call split over lines
    would otherwise read as a site with no `step` at all, which silently
    substitutes the driver default and mis-ranks it."""
    flat = re.sub(r"\n\s*", " ", txt)
    for m in re.finditer(r"cap_gap\s*=\s*" + NUM, flat):
        seg = flat[max(0, m.start() - WINDOW):m.end() + WINDOW]
        if "run_gap" in seg:
            continue
        st = re.findall(r"step\s*=\s*" + NUM, seg)
        yield float(m.group(1)), (float(st[-1]) if st else DRIVER_STEP_DEFAULT)


DELIVERY = re.compile(r"\b(?:run_cases|run_batch|run_case|run_differential)\s*\(")


def tests_deliver():
    """True if any tests/*.py actually DELIVERS a case to the emulator.

    🔴 THE EXEMPTION IS RE-EARNED ON EVERY RUN, NOT WRITTEN DOWN ONCE. `tests/`
    is left out of the indictment because its `cap_gap` sites are ASSERTIONS
    about the schedule (test_capture_budget.py passes `cap_gap=70.0` precisely
    to prove it moves nothing) rather than budgets buying a program time. That
    is only true while no test drives the emulator -- so this checks, instead of
    trusting a list that would rot into "things someone wanted to stop failing".
    """
    d = os.path.join(ROOT, "tests")
    for fn in os.listdir(d):
        if fn.endswith(".py") and DELIVERY.search(
                open(os.path.join(d, fn), errors="replace").read()):
            return True
    return False


def scan_tree(tracked_only=False):
    hits = []
    roots = ("probes", "tools") if tracked_only else (
        "probes", "tools", "scratchpad")
    if tests_deliver():
        roots = roots + ("tests",)
    for base in roots:
        for dp, _, fns in os.walk(os.path.join(ROOT, base)):
            for fn in fns:
                if not fn.endswith(".py") or fn == "omsx_repl.py":
                    continue
                p = os.path.join(dp, fn)
                txt = open(p, errors="replace").read()
                if "cap_gap" not in txt:
                    continue
                for cg, st in scan_text(txt):
                    if cg > st:
                        hits.append((cg / st, st, cg, os.path.relpath(p, ROOT)))
    hits.sort(reverse=True)
    return hits


def selftest():
    fails = []

    def check(label, got, want):
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")
        print(f"  {'PASS' if got == want else 'FAIL'}  {label:<52} {got!r}")

    check("a site with cap_gap and step is read",
          list(scan_text("run_cases(m, c, step=3.0, cap_gap=70.0)")),
          [(70.0, 3.0)])
    # NEGATIVE CONTROL: the same site WITH a run_gap is not a hit. Without this
    # row the scanner would pass just as happily by ignoring `run_gap` entirely,
    # and would indict every correctly-tuned site in the tree.
    check("a site that already passes run_gap is NOT a hit",
          list(scan_text("run_cases(m, c, step=3.0, cap_gap=70.0, run_gap=60.0)")),
          [])
    # and a file with no cap_gap at all yields nothing -- the other direction.
    check("a site with no cap_gap yields nothing",
          list(scan_text("run_cases(m, c, step=3.0)")), [])
    # THE JOIN MATTERS: split over lines, the `step` must still be found. A
    # scanner that read line-by-line would report the 2.5 default here and rank
    # this site 28x instead of 23x.
    check("a call split over lines still finds its step",
          list(scan_text("run_cases(m, c,\n    step=3.0,\n    cap_gap=70.0)")),
          [(70.0, 3.0)])
    check("a site with no step falls back to the driver default",
          list(scan_text("run_cases(m, c, cap_gap=9.0)")),
          [(9.0, DRIVER_STEP_DEFAULT)])
    # The tests/ exemption states a FACT about the tree; assert the fact, so a
    # test that starts delivering puts tests/ back in scope instead of silently
    # keeping an exemption it no longer earns.
    check("no tests/*.py delivers a case, so the tests/ exemption is earned",
          tests_deliver(), False)
    check("the delivery pattern can SEE a delivery (knife on the row above)",
          bool(DELIVERY.search("cap = omsx_repl.run_cases(ZB, cases)")), True)
    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print(f"  {f}")
        return 1
    print("gapscan --selftest: all rows passed")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    tracked = "--tracked" in sys.argv
    hits = scan_tree(tracked)
    scope = "probes/tools" if tracked else "the whole tree"
    if tests_deliver():
        scope += " + tests (a test now DELIVERS, so the exemption lapsed)"
    print(f"{len(hits)} call site(s) in {scope} pass cap_gap > step with NO run_gap")
    print(f"{'ratio':>7} {'step':>7} {'cap_gap':>8}  file")
    for r, st, cg, p in hits:
        print(f"{r:7.1f} {st:7.1f} {cg:8.1f}  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
