#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BD2FRAGILE: which address in zerobas's main ROM between ex_for ($6289) and the $6CF3 pin does Chuckie Egg depend
on? Bisection BY LAYOUT: three NOPs inserted before a code label shift everything after it by 3; if the game then
resets (the tape corpus's RESET), the address it depends on lies AT OR AFTER that label, else before it. Every probe
point is checked to change the built ROM (a label in a copy the build does not assemble changes nothing and would
read "runs" falsely). zerobas's own ROM only; the game is RUN, never decoded.

    python3 -u scratchpad/chuckie_bisect.py > scratchpad/AE_chuckie_bisect.out 2>&1
"""
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
PTS = json.load(open("/tmp/zerobas/bisect_pts.json"))
ENV = dict(os.environ, TAPECORPUS_DIR="/Users/joost/Documents/msx/msx/martos_cas")


def build():
    subprocess.run(["make", "-s", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return open("build/zerobas-main-eu.rom", "rb").read()


def chuckie():
    out = subprocess.run(["python3", "-u", "scratchpad/tapecorpus_run.py", "--only", "Chuckie"], env=ENV,
                         capture_output=True, text=True).stdout
    line = next((l for l in out.splitlines() if "Chuckie" in l), "")
    return ("RESET" if " RESET " in line else "RUNS" if "RUNS?" in line else "OTHER"), line.strip()


def probe(pt, base):
    addr, name, f, ln = pt
    src = open(f).read()
    L = src.splitlines(keepends=True)
    assert re.match(rf"^{re.escape(name)}:", L[ln - 1]), (f, ln, L[ln - 1])
    L.insert(ln - 1, "                nop\n                nop\n                nop       ; chuckie_bisect\n")
    open(f, "w").write("".join(L))
    try:
        rom = build()
        if rom == base:
            return "NOCHANGE", ""
        return chuckie()
    finally:
        open(f, "w").write(src)


def main():
    base = build()
    print("baseline:", chuckie(), flush=True)
    pts = []
    seen = set()
    for p in PTS:                       # one point per address
        if p[0] not in seen:
            seen.add(p[0])
            pts.append(p)
    lo, hi = 0, len(pts) - 1            # invariant: inserting at pts[lo] resets (ex_for: measured), at hi+1 runs
    print(f"{len(pts)} points ${pts[0][0]:04X}..${pts[-1][0]:04X}", flush=True)
    # confirm the ends first
    while lo < hi:
        mid = (lo + hi + 1) // 2
        r, line = probe(pts[mid], base)
        k = mid
        while r == "NOCHANGE" and k < hi:          # a label the build does not assemble: step on
            k += 1
            r, line = probe(pts[k], base)
        print(f"  insert before {pts[k][1]} (${pts[k][0]:04X}, {pts[k][2]}:{pts[k][3]}): {r}  {line[:70]}", flush=True)
        if r == "RESET":
            lo = k
        elif r == "RUNS":
            hi = mid - 1
        else:
            print("  stopping: an unclassified reading", flush=True)
            break
    build()
    nxt = next((p for p in pts if p[0] > pts[lo][0]), None)
    print(f"RESULT: the game depends on an address in [${pts[lo][0]:04X} {pts[lo][1]}, "
          f"{'$%04X %s' % (nxt[0], nxt[1]) if nxt else '$6CF3'}) -- inserting before {pts[lo][1]} resets, "
          f"after it runs", flush=True)


if __name__ == "__main__":
    main()
