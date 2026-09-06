#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DUPOBS — is each collapsed span OBSERVABLE? Scored HOST-side, not by the battery.

D-DUPSPAN2 collapsed 27 duplicate spans into aliases, and its own entry says what
is owed: *"a knife per canonical whose predicted set is that canonical's aliases
and nothing else"*, priced at **21 x ~7 min** of emulator battery -- about two and
a half hours, which is why nobody had done it.

🎯 THE PRICE ASSUMED THE BATTERY IS THE ONLY SCORER, AND IT IS NOT. Cutting
`c16_lt` (four aliases point at it) reddens THREE host test files --
test_control_flow, test_expr, test_float -- in **31 seconds**, no emulator
anywhere. `make unit-test` is a perfectly good observability oracle for anything
the host tests reach, and it is ~14x cheaper per arm.

⚠️ WHAT THIS CAN AND CANNOT SAY. An `equ` alias IS the canonical's address, so
there is no separate code to cut and no knife can distinguish "reached via the
alias" from "reached via the canonical" -- that is a STATIC question about who
names which symbol, not a dynamic one. What a cut answers is the other half, and
the half the entry actually calls owed: **is this shared body EXERCISED at all,
or is it a site nothing touches, which "stays green through any mistake made to
it"?**

THE CUT IS UNIFORM: a `ret` inserted as the canonical's first instruction, so the
body does nothing and returns. Same mutation everywhere, so a green arm means
"nothing reached it", never "my cut was too gentle here".

⚠️ A BUILD FAILURE IS NOT A GREEN ARM and is reported separately -- some tails
are jumped into with a dirty stack and a `ret` there may not assemble or may
diverge wildly. Either is a result; neither is "unobserved".
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = "/tmp/zerobas"


def sh(cmd, log):
    os.makedirs(os.path.dirname(log) or ".", exist_ok=True)
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, cwd=ROOT, stdout=fh,
                               stderr=subprocess.STDOUT)


def roster():
    """(alias, canonical, file, line) from the source markers -- the same
    machine-read roster D-DUPSPAN2 built, not a hand list."""
    out = subprocess.run([sys.executable, "scratchpad/dupspan2_roster.py"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    rows = []
    for m in re.finditer(r"^\s+(\S+)\s+->\s+(\S+)\s+(\S+):(\d+)\s*$", out, re.M):
        rows.append((m.group(1), m.group(2), m.group(3), int(m.group(4))))
    return rows


def _sources():
    for sub in ("basic", "sub", "disk"):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith((".asm", ".inc")):
                yield os.path.join(d, fn)


def find_label(canon, _seen=None):
    """-> (path, line index) of `canon:` in the tree, or None.

    🔴 FOLLOWS `equ` CHAINS, AND THE FIRST CUT DID NOT -- WHICH IS THE EXACT
    MISTAKE THIS ITEM ALREADY DOCUMENTS. Its own text says *"an alias is spelled
    two ways and a scanner that knows one undercounts ... my first cut looked
    only for `^name:` and resolved 22 of 27"*, and I wrote `^canon:` and got
    20 of 21. `elas_err` is `equ ems_err_pop1`: a canonical that is ITSELF an
    alias. Reading a warning is not the same as heeding it.
    """
    _seen = _seen or set()
    if canon in _seen:
        return None
    _seen.add(canon)
    equ = re.compile(r"^" + re.escape(canon) + r"\s+equ\s+([A-Za-z_][\w.]*)\s*(;.*)?$")
    for p in _sources():
        lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        for i, ln in enumerate(lines):
            if ln.startswith(canon + ":"):
                return p, i
            m = equ.match(ln)
            if m:
                return find_label(m.group(1), _seen)   # chase the chain
    return None


def main():
    rows = roster()
    canons = sorted({c for _, c, _, _ in rows})
    by_canon = {}
    for a, c, f, l in rows:
        by_canon.setdefault(c, []).append(a)
    print(f"\n{len(rows)} alias(es), {len(canons)} canonical(s); "
          f"cutting each canonical to a bare `ret` and scoring with "
          f"`make unit-test`\n")
    res = {}
    for c in canons:
        hit = find_label(c)
        if hit is None:
            print(f"  {c:22} 🔴 label not found in source")
            res[c] = "NO LABEL"
            continue
        path, idx = hit
        orig = open(path, encoding="utf-8", errors="replace").read()
        lines = orig.split("\n")
        lines.insert(idx + 1, "                ret                 ; K-DUPOBS CUT")
        try:
            open(path, "w", encoding="utf-8").write("\n".join(lines))
            # 🔴 D-KNIFEROM: A CUT THAT NEVER REACHED THE ROM REPORTS EXACTLY
            # WHAT AN HONEST "nothing observed" REPORTS -- and here a green arm
            # IS the finding, so an inert knife would manufacture one.
            # `knife-rom-guard-check` caught this runner shipping without the
            # check, correctly.
            before = knife_guard.hashes()
            if sh("make basic-reloc", f"{TMP}/dupobs_{c}_build.log"):
                res[c] = "BUILD FAILED"
            elif not knife_guard.moved(before, knife_guard.hashes()):
                res[c] = "🔴 INERT (ROM unchanged)"
            else:
                rc = sh("make unit-test", f"{TMP}/dupobs_{c}_unit.log")
                res[c] = "observed" if rc else "🔴 NOT OBSERVED"
        finally:
            open(path, "w", encoding="utf-8").write(orig)
        n = len(by_canon[c])
        print(f"  {c:22} {res[c]:16} ({n} alias{'es' if n > 1 else ''})")
    sh("make basic-reloc", f"{TMP}/dupobs_restore.log")

    print()
    obs = sum(1 for v in res.values() if v == "observed")
    unobs = [c for c, v in res.items() if v.endswith("NOT OBSERVED")]
    other = {c: v for c, v in res.items()
             if v in ("BUILD FAILED", "NO LABEL") or v.endswith("(ROM unchanged)")}
    print(f"observed by the HOST tests alone : {obs} / {len(canons)}")
    print(f"not observed                     : {len(unobs)}  {unobs}")
    if other:
        print(f"⚠️  neither (a result, not a green): {other}")
    print("\n⚠️ A canonical the host tests do not reach may still be exercised by "
          "the\n   EMULATOR battery -- this run bounds the cheap half, it does not "
          "close the\n   question for the ones it leaves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
