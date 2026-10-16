#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S16.0(a) knife: does tests/test_subrom_bridge_stack.py see the bridge's
private stack? Test-harness only -- no ROM is built or changed.

K-WS87 the page-0 bridge runs the island on a PRIVATE stack again (SP = $F380, the
       old `sub0.call(..)` without keep_sp) and copies back everything EXCEPT
       [$F300,$F380), as before S16.0 -- BC passing kept -> the witness FAILS
       (the descriptor written into the caller's frame at $F370 never arrives)
"""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
H = "tests/msxtest.py"
EDITS = [
    ("                sub0.cpu.sp = cpu.sp                                  # the CALLER's stack\n"
     "                sub0.call(cpu.ix, keep_sp=True, hl=cpu.hl, de=cpu.de, bc=cpu.bc)\n",
     "                sub0.call(cpu.ix, hl=cpu.hl, de=cpu.de, bc=cpu.bc)   # KNIFE: private stack\n"),
    ("            dst[RAM_LO:0x10000] = src[RAM_LO:0x10000]\n",
     "            dst[RAM_LO:0xF300] = src[RAM_LO:0xF300]               # KNIFE: drop the band\n"
     "            dst[0xF380:0x10000] = src[0xF380:0x10000]\n"),
]


def test():
    r = subprocess.run([sys.executable, "tests/test_subrom_bridge_stack.py"],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-2]


saved = open(H).read()
t = saved
for old, new in EDITS:
    if t.count(old) != 1:
        raise SystemExit(f"anchor: {old[:50]!r}")
    t = t.replace(old, new)
try:
    open(H, "w").write(t)
    rc, line = test()
    print(f"K-WS87: witness rc={rc} ({line.strip()}); predicted FAIL -> {'HIT' if rc else 'MISS'}")
finally:
    open(H, "w").write(saved)
rc, line = test()
print(f"restored: witness rc={rc} ({line.strip()}) -> {'SAME (PASS)' if rc == 0 else 'STILL FAILING'}")
