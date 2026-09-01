# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Discover and run every tests/test_*.py, aggregate, exit nonzero on any fail.

Each test file is self-contained (assembles its own ROM to /tmp, asserts, exits
0 on pass) so adding coverage means only dropping a new test_*.py here — no need
to touch this runner, the Makefile, or the shared harness. `make unit-test`
calls this.
"""

import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


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
    for t in tests:
        name = os.path.basename(t)
        r = subprocess.run([sys.executable, t], capture_output=True, text=True)
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
