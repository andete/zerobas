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

🔴 RANK 1 IS A KNOWN MUST-NOT-TOUCH, AND THE RANK IS WHY THIS WARNING IS HERE.
`basic_probe_input_devices.py` (10.0) heads the list and was MEASURED on
2026-09-24: giving it a `run_gap` moves the key-matrix PRESS past the program's
sampling window and collapses all five hold rows to idle -- `Z 7 0` -> `Z 0 0`
and so on -- **while the suite still reports PASS, because both machines flip
together.** Widening it would replace five readings with five vacuous
agreements. The same applies to any `NEEDS-HOLD:`-style site.
🎯 SO THIS LIST IS A SUSPICION ORDER, NOT A WORK ORDER. All twelve original
sites were resolved under D-CAPGAP: nine identical, two genuinely fixed
(`deffn-acceptance`, and `kwsweep`'s TAPE rows via `TAPE_TIMING` -- per-RIG,
never per-suite), one that must not be widened, one that was not a site at all.
**The ratio predicted none of it**: 10.0 breaks, 9.0 is fine, and 1.2 was one of
the two real faults.
"""
import ast
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


# 🔴 A SELFTEST'S `cap_gap` IS NOT A BUDGET, AND ONE OF THEM REACHED THE
# INDICTMENT (D-CAPGAP, 2026-09-24). `probes/lib/probe_refcache.py` was ranked
# as a `cap_gap > step` SITE on the strength of two hits inside its own
# `_selftest`: one a `dict(...)` used only to derive a cache KEY -- it never
# boots a machine -- and one a run of `PRINT "REFCACHE"`, which finishes
# instantly against an 8 s budget. Neither can capture a case early because
# neither has a case to capture. **The 12-site list the arc was scoped on
# therefore contained a site that could not belong to it.**
# ⚠️ SIGNATURES ARE DELIBERATELY *NOT* MASKED, and that is a measurement rather
# than an oversight: `cap_gap` appears as a function PARAMETER at five places,
# all in `scratchpad/` (i2_char, i2_pinmap, sncap/emutime, sncap/emutotal,
# rungap/check_timeline), so none reaches `--tracked`. And a parameter's default
# IS the effective budget for every caller that does not override it, so masking
# it would hide a real site. A first note on this claimed "signature defaults
# and selftest constants" were both false positives; the signature half was
# WRONG and is corrected here [[a-justification-parenthesis-is-an-unrun-claim]].
def mask_selftests(txt: str) -> str:
    """`txt` with every selftest FUNCTION BODY blanked, line for line.

    Blanked rather than deleted so every surviving line keeps its number, which
    matters because the flattening in `scan_text` joins continuations and a
    dropped line would silently fuse two unrelated calls.
    ⚠️ Returns `txt` unchanged when it does not parse: `scan_text` is also fed
    bare SNIPPETS by the selftest below, and refusing those would make the
    scanner's own arms unrunnable."""
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return txt
    drop = set()
    for n in ast.walk(tree):
        if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and "selftest" in n.name):
            drop.update(range(n.lineno, (n.end_lineno or n.lineno) + 1))
    if not drop:
        return txt
    return "\n".join("" if i + 1 in drop else l
                     for i, l in enumerate(txt.split("\n")))


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
                txt = mask_selftests(txt)
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

    # 🔴 D-CAPGAP: THE SELFTEST MASK, IN BOTH DIRECTIONS. Without the negative
    # arm the mask could blank the whole file and every arm above would still
    # pass, because "no sites" is what a clean corpus looks like too.
    _sf = ("def _selftest():\n"
           "    KW = dict(step=8.0, cap_gap=10.0)\n")
    _real = ("def run(m):\n"
             "    return run_cases(m, c, step=3.0, cap_gap=70.0)\n")
    check("a selftest body is masked away",
          list(scan_text(mask_selftests(_sf))), [])
    check("NEGATIVE: a REAL site outside a selftest survives the mask",
          list(scan_text(mask_selftests(_real))), [(70.0, 3.0)])
    check("NEGATIVE: the mask keeps a real site that FOLLOWS a selftest",
          list(scan_text(mask_selftests(_sf + _real))), [(70.0, 3.0)])
    # A snippet that is not a parseable module must pass through untouched --
    # `scan_text`'s own arms below feed it bare expressions.
    check("NEGATIVE: an unparseable snippet is returned unchanged",
          mask_selftests("run_cases(m, c, step=3.0, cap_gap=70.0"),
          "run_cases(m, c, step=3.0, cap_gap=70.0")
    # 🎯 AND THE SUBJECT THAT STARTED IT: probe_refcache's two hits are both in
    # `_selftest`, so the masked file must offer NO site at all.
    _rc = os.path.join(ROOT, "probes", "lib", "probe_refcache.py")
    if os.path.exists(_rc):
        _t = open(_rc, errors="replace").read()
        check("probe_refcache offers sites BEFORE the mask (the control)",
              bool(list(scan_text(_t))), True)
        check("...and NONE after it -- both hits were selftest constants",
              list(scan_text(mask_selftests(_t))), [])
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
