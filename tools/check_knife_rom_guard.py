#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KNIFEROM2 gate — every knife runner must ACT on its ROM hash, not print it.

🔴 THE HAZARD (recorded as a recurring class): a knife can be silently inert
because the build did not happen. Writing the cut source and immediately running
`make` can leave the previous ROM in place, and the probe then measures the
UNCUT machine -- which reports as `moved 0 rows`, i.e. exactly what an arm that
legitimately found nothing looks like. The defence is to hash the images around
the plant and REFUSE the arm when they did not move.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]

🔴 AND THIS FILE EXISTS BECAUSE A REGEX COULD NOT ANSWER IT. The question "how
many runners act on their hash?" was classified three times by hand on
2026-08-29 and answered 33, then 10, then 24 print-only -- each pass finding an
idiom the previous one missed, and each OVERSTATING the gap. It is the second
time this same claim was filed too pessimistically. Counting by pattern-match
over free-form Python is the wrong instrument; this reads the AST.

WHAT COUNTS AS ACTING. A runner ACTS when some `if` or `assert` test mentions a
name bound from a ROM-hash source -- `knife_guard.hashes()`, `knife_guard.build()`
(whose first return value is `moved`), `knife_guard.moved()`, or a module-local
`hashes()` that reads the built images. All four idioms in the tree are covered
by one rule because the rule is about DATA FLOW, not spelling:

    if not moved: ...                      # knife_guard.build
    if after == before: ...                # explicit compare
    assert h[0] != base_h[0], "..."        # paint4 / himdom
    if not knife_guard.moved(b, a): ...

⚠️ A SOURCE HASH IS NOT A ROM HASH, AND IT LOOKS EXACTLY LIKE ONE TO A GREP.
`banner_knife.py` hashes its own SOURCE text to verify its restore -- a real
check, of a different claim. Runners whose only hashing is over source text are
reported as NO ROM HASH, not as acting.
"""
from __future__ import annotations

import argparse
import ast
import glob
import re
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A call that yields a ROM-hash-derived value.
GUARD_ATTRS = {"hashes", "build", "moved"}
# A module-local def that reads the built images.
LOCAL_HASH_DEF = "hashes"
IMAGE_HINTS = ("basic-reloc.rom", "sub.rom", "zerobas-main-eu.rom", "disk.rom")


def _call_is_romhash(node, local_hash_names):
    """-> True when this Call produces a ROM-hash-derived value."""
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in GUARD_ATTRS:
        if isinstance(f.value, ast.Name) and f.value.id == "knife_guard":
            return True
    if isinstance(f, ast.Name) and f.id in local_hash_names:
        return True
    return False


def analyse(path):
    """-> (verdict, detail) for one knife runner."""
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return "unparsable", str(e)

    # 🔴 THE FIRST VERSION OF THIS FUNCTION WAS WRONG IN THE SAME DIRECTION AS
    # THE REGEXES IT REPLACED, and for the same reason: it required a SPELLING
    # (a build/*.rom path INSIDE the `def hashes()` body) instead of following
    # the data. `screen3_knives.py` and `missop_knives.py` both define
    # `def hashes()` over a MODULE-LEVEL `ROMS = [...]` list, so the path is
    # nowhere near the function, and both were reported as having no ROM hash
    # at all. An instrument built to settle a question a regex kept getting
    # wrong has to be falsified against the cases that broke the regex -- S8/S9
    # below are exactly those two files.
    # 🟢 THE RULE NOW: a module that references a BUILT ROM IMAGE anywhere is
    # ROM-aware, and in a ROM-aware module a local `hashes()` is a ROM-hash
    # source wherever its paths are written.
    # 🔴 AND THE SECOND VERSION WAS WRONG THE SAME WAY A THIRD TIME. It accepted
    # only a function literally NAMED `hashes`, so `circdom_knives.py`,
    # `forret_knives.py` and `y192_knife.py` -- which hash the ROM inside
    # `rom_hash()`, `romh()` and friends -- all read as having no ROM hash.
    # 🎯 STOP ENCODING A SPELLING. A function is a ROM-hash source when its BODY
    # CALLS hashlib and the module references a built ROM image. The name is not
    # part of the question and never was. S8..S10 pin the five real files that
    # broke the three earlier versions.
    # 🔴 FIFTH MISS, AND THE NARROWEST YET. `grpac_knife.py` builds its path as
    # `f"{rom}.rom"`, so NO literal image name appears anywhere in the file and
    # a hint list of four filenames could not see it. Ask the weaker, honest
    # question -- does this module deal in ROM images at all -- and let the
    # FUNCTION-level test (does its body call hashlib) carry the precision.
    rom_aware = (any(h in src for h in IMAGE_HINTS) or "knife_guard" in src
                 or ".rom" in src)
    local_hash_names = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls_hashlib = any(
            isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "hashlib"
            for sub in ast.walk(node))
        body = ast.get_source_segment(src, node) or ""
        if calls_hashlib and (rom_aware or any(h in body for h in IMAGE_HINTS)):
            local_hash_names.add(node.name)
        elif node.name == LOCAL_HASH_DEF and (
                rom_aware or any(h in body for h in IMAGE_HINTS)):
            local_hash_names.add(node.name)

    # 🔴 AND A FOURTH TIME, ONE FRAME FURTHER OUT. `circdom_knives.py` hashes in
    # `sub_sha()`, RETURNS it from `build()`, and tests `if sha != POST_SLICE_
    # SUB_SHA` on `ok, sha = build()`. `build` calls no hashlib of its own, so it
    # was not a source and the taint never started. A function that RETURNS a
    # hash-derived value is a hash source too -- to a fixpoint, because the chain
    # can be any depth.
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    changed = True
    while changed:
        changed = False
        for fn in funcs:
            if fn.name in local_hash_names:
                continue
            for ret in ast.walk(fn):
                if not isinstance(ret, ast.Return) or ret.value is None:
                    continue
                if any(isinstance(sub, ast.Call)
                       and _call_is_romhash(sub, local_hash_names)
                       for sub in ast.walk(ret.value)):
                    local_hash_names.add(fn.name)
                    changed = True
                    break

    # Names bound from a ROM-hash source (incl. tuple unpacking), and then
    # everything derived from those.
    # 🔴 ONE LEVEL OF TAINT IS NOT ENOUGH. `missop_knives.py` computes
    # `base_h = hashes()` / `h = hashes()` and then passes BOTH through a local
    # `moved(base, now)` helper, testing `if mv != MAIN_MOVES`. Stopping at the
    # direct binding reported it as hashing-and-not-reading -- the same
    # false-negative shape this tool exists to remove. Propagate to a fixpoint:
    # any assignment whose value MENTIONS a tainted name is itself tainted.
    tainted = set()
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]

    def _targets(node):
        out = set()
        for tgt in node.targets:
            for sub in ast.walk(tgt):
                if isinstance(sub, ast.Name):
                    out.add(sub.id)
        return out

    for node in assigns:
        if (isinstance(node.value, ast.Call)
                and _call_is_romhash(node.value, local_hash_names)):
            tainted |= _targets(node)

    changed = True
    while changed:
        changed = False
        for node in assigns:
            if any(isinstance(sub, ast.Name) and sub.id in tainted
                   for sub in ast.walk(node.value)):
                new_names = _targets(node) - tainted
                if new_names:
                    tainted |= new_names
                    changed = True

    has_source = bool(tainted) or any(
        _call_is_romhash(n, local_hash_names)
        for n in ast.walk(tree) if isinstance(n, ast.Call))
    if not has_source:
        return "no-rom-hash", "no call yields a ROM-image hash"

    # does any if/assert test depend on one of those names -- or call moved()?
    for node in ast.walk(tree):
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.Assert):
            test = node.test
        if test is None:
            continue
        for sub in ast.walk(test):
            if isinstance(sub, ast.Name) and sub.id in tainted:
                return "acts", ast.dump(test)[:60]
            if isinstance(sub, ast.Call) and _call_is_romhash(sub, local_hash_names):
                return "acts", ast.dump(test)[:60]
    return "prints-only", f"binds {sorted(tainted)} but no if/assert reads them"


# 🟢 NOT EVERY RUNNER CAN HASH A ROM, AND SAYING SO BY NAME BEATS A HEURISTIC.
# Each entry carries the reason, so the exemption can be argued with instead of
# being an unexplained hole. A runner that builds no ROM is detected
# automatically (below); this dict is only for ones that DO build.
EXEMPT = {
    "scratchpad/xreg_knife.py":
        "the subject IS the build's verdict -- K-XR1 requires `make basic-reloc` "
        "to go RED, so there is no post-cut ROM to hash",
}

# A runner that never invokes a ROM-building target has no ROM to hash. The
# source-sweep knives (prologue / seedhole2 / seedprose) knife a SOURCE READER;
# seedprose_knives.py says so in its own header: "No ROM is built."
# 🔴 MENTIONING A BUILD PATH IS NOT BUILDING. All three of those read
# `build/*.sym` and never run make, so a hint list containing `build/` counted
# them as ROM-building and demanded a hash they have nothing to hash. Require an
# actual INVOCATION.
_BUILD_TARGETS = ('repack-machine', 'basic-reloc')


def builds_a_rom(src):
    if 'knife_guard.build(' in src:
        return True
    for t in _BUILD_TARGETS:
        for m in re.finditer(re.escape(t), src):
            # 'make' must appear within the 12 chars before the target,
            # so a bare path like build/basic-reloc.sym does not count.
            if 'make' in src[max(0, m.start() - 12):m.start()]:
                return True
    return False


def runners():
    pats = ("scratchpad/*_knives.py", "scratchpad/*_knife.py",
            "scratchpad/*_knife_run.py")
    out = set()
    for p in pats:
        out |= set(glob.glob(os.path.join(ROOT, p)))
    return sorted(out)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true",
                    help="print every runner and its verdict")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    files = runners()
    buckets = {"acts": [], "prints-only": [], "no-rom-hash": [], "unparsable": [],
               "n/a": []}
    for f in files:
        rel = os.path.relpath(f, ROOT)
        v, detail = analyse(f)
        if v != "acts":
            if rel in EXEMPT:
                buckets["n/a"].append((rel, EXEMPT[rel])); continue
            if not builds_a_rom(open(f, errors="replace").read()):
                buckets["n/a"].append((rel, "builds no ROM -- knifes a source reader"))
                continue
        buckets[v].append((rel, detail))

    print(f"check_knife_rom_guard — {len(files)} knife runner(s)\n")
    for name, label in (("acts", "✅ acts on the ROM hash"),
                        ("n/a", "➖ no ROM to hash (reason given)"),
                        ("prints-only", "⚠️  hashes but never reads it back"),
                        ("no-rom-hash", "🔴 no ROM-image hash at all"),
                        ("unparsable", "🔴 unparsable")):
        rows = buckets[name]
        print(f"{label}: {len(rows)}")
        if a.list or name != "acts":
            for rel, detail in rows:
                print(f"    {rel}" + (f"    {detail}" if a.list else ""))
    gap = len(buckets["prints-only"]) + len(buckets["no-rom-hash"]) \
        + len(buckets["unparsable"])
    print(f"\n{len(buckets['acts'])}/{len(files)} act, "
          f"{len(buckets['n/a'])} n/a; {gap} unguarded")
    # The threshold is a RATCHET: it may only ever go down. At 0 a new runner
    # cannot ship without either a ROM-hash check or a stated reason.
    ratchet = 0
    if gap > ratchet:
        print(f"🔴 the gap GREW: {gap} > {ratchet} — a new runner shipped without "
              f"a ROM-hash check")
        return 1
    if gap < ratchet:
        print(f"🟢 the gap SHRANK to {gap}; lower the ratchet in this file to {gap}")
    return 0


def selftest():
    """🔴 Each arm plants a runner of a known shape and requires the verdict."""
    import tempfile
    ok = True

    def arm(name, cond, got=None):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  (got {got})" if not cond else ""))
        ok = ok and bool(cond)

    # 🔴 The fixtures go under THIS PROCESS's own scratch dir, never a hardcoded
    # temp path -- `temp-root-check` caught exactly that on this gate's first
    # run, and then caught the same literal again inside the comment explaining
    # the fix (the scan is textual by design; pinning it would be worse than
    # rewording). probe_tmp owns the root and clears it at exit. [[one-temp-root]]
    sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
    import probe_tmp
    d = probe_tmp.tmp("kromguard")
    os.makedirs(d, exist_ok=True)

    def write(n, body):
        p = os.path.join(d, n)
        open(p, "w").write(body)
        return p

    a1 = write("a1_knives.py", "import knife_guard\n"
               "m, af, rc = knife_guard.build('l', b)\n"
               "if not m:\n    raise SystemExit(1)\n")
    arm("S1 `if not moved` from knife_guard.build -> acts", analyse(a1)[0] == "acts",
        analyse(a1)[0])

    a2 = write("a2_knives.py", "import knife_guard\n"
               "before = knife_guard.hashes()\n"
               "after = knife_guard.hashes()\n"
               "if after == before:\n    raise SystemExit(1)\n")
    arm("S2 an explicit before/after compare -> acts", analyse(a2)[0] == "acts",
        analyse(a2)[0])

    a3 = write("a3_knives.py", "def hashes():\n    return open('build/sub.rom','rb')\n"
               "base_h = hashes()\n"
               "h = hashes()\n"
               "assert h[0] != base_h[0], 'did not move'\n")
    arm("S3 `assert h[0] != base_h[0]` over a LOCAL hashes() -> acts",
        analyse(a3)[0] == "acts", analyse(a3)[0])

    a4 = write("a4_knives.py", "import knife_guard\n"
               "before = knife_guard.hashes()\n"
               "after = knife_guard.hashes()\n"
               "print(before, after)\n")
    arm("S4 🔴 hashing and only PRINTING is caught", analyse(a4)[0] == "prints-only",
        analyse(a4)[0])

    a5 = write("a5_knife.py", "import hashlib\n"
               "d = hashlib.sha256(open('src.asm').read().encode()).hexdigest()\n"
               "assert d == d2, 'source not restored'\n")
    arm("S5 a SOURCE hash is not a ROM hash (the banner_knife shape)",
        analyse(a5)[0] == "no-rom-hash", analyse(a5)[0])

    a6 = write("a6_knives.py", "def hashes():\n    return 1\n"
               "h = hashes()\n"
               "assert h != 0\n")
    arm("S6 a local hashes() that reads NO image does not count as one",
        analyse(a6)[0] == "no-rom-hash", analyse(a6)[0])

    # 🔴 A POSITIVE CONTROL ON THE DISCOVERY GLOB: an arm set that only ever
    # examines files it was handed cannot tell an empty tree from a broken glob.
    arm("S7 positive control: the runner glob finds the real tree",
        len(runners()) > 40, len(runners()))

    # 🔴 S8/S9 ARE THE TWO REAL FILES THAT BROKE THE FIRST VERSION OF THIS TOOL.
    # Both define `def hashes()` over a module-level `ROMS = [...]`, so the image
    # path is nowhere inside the function -- and both were reported as having no
    # ROM hash at all. An arm that only ever sees synthetic fixtures cannot catch
    # that; these two are pinned by name on purpose.
    for real in ("missop_knives.py", "screen3_knives.py",
                 "circdom_knives.py", "forret_knives.py", "y192_knife.py",
                 "grpac_knife.py"):
        rp = os.path.join(ROOT, "scratchpad", real)
        got = analyse(rp)[0] if os.path.exists(rp) else "<absent>"
        arm(f"S8 {real} (module-level ROMS + local hashes()) reads as acting",
            got == "acts", got)

    # 🟢 banner_knife.py WAS the last unguarded runner: it hashed its own SOURCE
    # (anchor + restore) and never asked whether the cut reached the ROM. D-
    # KNIFEROM2 added the check; this arm pins it, so the fix cannot quietly go
    # back out. The synthetic source-hash negative control is S5.
    bp = os.path.join(ROOT, "scratchpad", "banner_knife.py")
    got = analyse(bp)[0] if os.path.exists(bp) else "<absent>"
    arm("S9 banner_knife.py now acts on a ROM hash, not just its source",
        got == "acts", got)

    import shutil
    shutil.rmtree(d, ignore_errors=True)   # probe_tmp also clears its own root
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
