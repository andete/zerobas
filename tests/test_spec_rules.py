#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""tools/spec_rules.py (docs/spec-method.md §3a): the executable-rules checker must FAIL when a page
says more than its data, or when the page's rendered tables drift -- a checker that always passes
would turn every page into unchecked prose again. Pinned:
  - a rule that holds on the reference: --check passes once the page is rendered;
  - a rule FALSE on one reference case: --check fails and names the case;
  - a stale page (tables not re-rendered): --check fails;
  - a zerobas failure is reported as a difference, NOT as a false rule;
  - a rule that selects no case refuses.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, "tools", "spec_rules.py")
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root

MODULE = '''
import sys
sys.path.insert(0, {tools!r})
from types import SimpleNamespace as NS
from spec_rules import Rule
PAGE = {page!r}
def cases():
    ref = [NS(src="T", id=f"T {{i}}", v=i, out=i * 2) for i in range(4)]
    zb = [NS(src="T", id=f"T {{i}}", v=i, out=i * 2 + (1 if i == 3 else 0)) for i in range(4)]
    return {{"ref": ref, "zb": zb}}
OUTPUTS = {{"T": ["out"]}}
RULES = [Rule("R-DOUBLE", "S", "out is twice v.", lambda c: True, lambda c: c.out == ({expr}))]
'''


def run(mod, *args):
    p = subprocess.run([sys.executable, TOOL, mod, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    fails = []

    def check(ok, msg):
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")
        if not ok:
            fails.append(msg)

    with tempfile.TemporaryDirectory() as td:
        page = os.path.join(td, "PAGE.md")
        open(page, "w").write("# page\n\n<!-- RULES BEGIN -->\n<!-- RULES END -->\n")
        mod = os.path.join(td, "t_rules.py")

        def write(expr):
            open(mod, "w").write(MODULE.format(tools=os.path.join(ROOT, "tools"), page=page, expr=expr))

        write("c.v * 2")
        rc, out = run(mod, "--check")
        check(rc == 1 and "stale" in out, "an unrendered page is STALE: --check fails")
        run(mod, "--write")
        rc, out = run(mod, "--check")
        check(rc == 0, "a rendered page whose rule holds on the reference: --check passes")
        check("✗ 1: T 3" in open(page).read(), "zerobas's failure is rendered as a difference (case T 3)")
        write("c.v * 2 if c.v != 2 else -1")
        rc, out = run(mod, "--check")
        check(rc == 1 and "FALSE" in out and "T 2" in out, "a rule false on reference case T 2: fails, names it")
        write("c.v * 2")
        open(mod, "a").write('OUTPUTS = {"T": ["out", "id"]}\n')     # 'id' recorded, no check reads it
        rc, out = run(mod)
        check("uncovered outputs: 4 of 8" in out, "an output no check reads is UNCOVERED (field-level)")
        open(mod, "a").write('RULES[0].select = lambda c: False\n')
        rc, out = run(mod)
        check(rc != 0 and "selects no case" in out, "a rule that selects no case refuses")
    print()
    print(f"{len(fails)} CHECK(S) FAILED" if fails else "ALL CHECKS PASSED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
