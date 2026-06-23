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

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    tests = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if not tests:
        print("no tests found", file=sys.stderr)
        return 1
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
