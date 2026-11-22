# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Discover and run every tests/test_*.py, aggregate, exit nonzero on any fail.

Each test file is self-contained (assembles its own ROM to /tmp, asserts, exits
0 on pass) so adding coverage means only dropping a new test_*.py here — no need
to touch this runner, the Makefile, or the shared harness. `make unit-test`
calls this.
"""

import concurrent.futures
import glob
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# ⏱ D-STATICSLOW (4) (2026-11-22): the files run on a worker pool -- 379 serial seconds,
# the slowest file 82 (scratchpad/AE_unit_times.out). The base above is shared by every
# child ON PURPOSE (a test reads another's ROM), so files that share an artifact name,
# or take another test module's build (whose build() writes ITS artifacts: a whole-module
# `import test_x`, or a `from test_x import` naming build*), are one GROUP -- importing a
# pure helper (test_paintcell's _timing, test_forfast's Runner, which builds the paths
# it is given) does not group, or the five slowest files would be one serial group:
# a group runs in one worker, in sorted order, exactly as the serial run did.
# ZB_UNIT_JOBS=1 runs everything serially.
TP_NAME = re.compile(r"""\btp\(\s*f?["']([^"']+)["']""")
MOD_IMPORT = re.compile(r"^\s*import\s+(test_\w+)", re.M)
FROM_IMPORT = re.compile(r"^\s*from\s+(test_\w+)\s+import\s+(\([^)]*\)|[^\n]*)", re.M)


def _builds_from(src):
    """the test modules whose build this source can run"""
    mods = set(MOD_IMPORT.findall(src))
    for mod, names in FROM_IMPORT.findall(src):
        names = re.sub(r"#[^\n]*", "", names).strip("() \n")
        if any(n.strip().split(" as ")[0].startswith("build") for n in names.split(",")):
            mods.add(mod)
    return mods


def groups(tests):
    """Union-find over (a shared tp() literal, an import of a test module)."""
    parent = {t: t for t in tests}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def union(a, b):
        parent[find(a)] = find(b)

    by_name, by_stem = {}, {os.path.basename(t)[:-3]: t for t in tests}
    for t in tests:
        src = open(t, encoding="utf-8").read()
        for n in TP_NAME.findall(src):
            n = re.sub(r"\{[^}]*\}", "*", n)      # an f-string's field: same family
            if n in by_name:
                union(t, by_name[n])
            by_name.setdefault(n, t)
        for m in _builds_from(src):
            if m in by_stem:
                union(t, by_stem[m])
    out = {}
    for t in tests:
        out.setdefault(find(t), []).append(t)
    return [sorted(g) for g in out.values()]


def run_group(group):
    res = []
    for t in group:
        r = subprocess.run([sys.executable, t], capture_output=True, text=True)
        res.append((t, r))
    return res


def main():
    tests = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if not tests:
        print("no tests found", file=sys.stderr)
        return 1
    # 🔴 ISOLATE THIS INVOCATION BY DEFAULT (2026-09-01, Joost's call). Eight
    # artifact names are shared by 2-4 test files, and three
    # `scratchpad/paint*.py` probes share `zb_graphics_sub.*` with a unit test --
    # so a scratch probe run alongside a bare `make unit-test` can read or
    # overwrite the other's ROM mid-build. `tools/run_gates.py` already sets this
    # for the battery; a bare run had nothing.
    # 🎯 PER-INVOCATION, NOT PER-PROCESS, AND THAT DISTINCTION IS LOAD-BEARING.
    # Some sharing is DELIBERATE: `test_rdblk_randrecord.py` reads
    # `test_wrblk_body_e2e.py`'s ROM and says so on the line that names it. Every
    # child inherits this ONE base, so that sharing is preserved exactly while
    # concurrent invocations stop colliding. A per-process directory would have
    # been the obvious reading and would have broken it
    # [[a-mechanical-fix-can-break-a-different-invariant]].
    # An outer runner that has already chosen a base keeps it.
    if not os.environ.get("ZB_TEST_TMP"):
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
        import probe_tmp
        os.environ["ZB_TEST_TMP"] = tempfile.mkdtemp(prefix="unit-",
                                                     dir=probe_tmp.ROOT)
        print(f"isolated build artifacts: {os.environ['ZB_TEST_TMP']}")
    fails = []
    gs = groups(tests)
    jobs = int(os.environ.get("ZB_UNIT_JOBS") or os.cpu_count() or 1)
    # the longest groups first, so the slowest file does not start last
    gs.sort(key=lambda g: -sum(os.path.getsize(t) for t in g))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for res in ex.map(run_group, gs):
            results.update(res)
    for t in tests:
        name = os.path.basename(t)
        r = results[t]
        ok = r.returncode == 0
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            fails.append(name)
            sys.stdout.write(r.stdout)
            sys.stderr.write(r.stderr)
    print()
    if fails:
        print(f"{len(fails)}/{len(tests)} FILE(S) FAILED: {', '.join(fails)}")
        return 1
    print(f"ALL {len(tests)} TEST FILE(S) PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
