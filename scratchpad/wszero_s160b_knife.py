#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S16.0(b) knife: does the unit suite see the strheap JUMP TABLE?
The unit harness assembles the sub ROM from source, so no machine is rebuilt.

K-WS88 table entries 6 and 7 swapped (HEX$ runs OCT$'s builder and back) ->
       tests/test_str_fn.py FAILS
"""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
F = "sub/strheap.asm"
OLD = ("                dw      sh_hex_build        ; 6  HEX$\n"
       "                dw      sh_oct_build        ; 7  OCT$\n")
NEW = ("                dw      sh_oct_build        ; 6  KNIFE\n"
       "                dw      sh_hex_build        ; 7  KNIFE\n")


def test():
    r = subprocess.run([sys.executable, "tests/test_str_fn.py"], capture_output=True, text=True)
    fails = sum(1 for ln in r.stdout.splitlines() if ln.lstrip().startswith("FAIL"))
    return r.returncode, fails


saved = open(F).read()
if saved.count(OLD) != 1:
    raise SystemExit("anchor")
try:
    open(F, "w").write(saved.replace(OLD, NEW))
    rc, n = test()
    print(f"K-WS88: test_str_fn rc={rc}, {n} FAIL line(s); predicted FAIL -> {'HIT' if rc else 'MISS'}")
finally:
    open(F, "w").write(saved)
rc, n = test()
print(f"restored: test_str_fn rc={rc}, {n} FAIL line(s) -> {'SAME (PASS)' if rc == 0 else 'STILL FAILING'}")
