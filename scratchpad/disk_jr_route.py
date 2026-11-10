#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Route D for disk.rom: every `jp [z|nz|c|nc,] label` that can be a `jr`, becomes
one (1 B each). Converts all candidates, builds, and reverts each line the
assembler reports out of range, until the build is clean. The assembler enforces
range, so a wrong guess cannot ship -- it fails the build by name and is reverted.

EXCLUDED, because a relative jump there is WRONG, not just out of range:
  * code copied to RAM and run there: every block from a `*tmpl*` label to the next
    `*_end` label, init.asm and pageenv.asm whole, and fmt_boot (the boot sector
    a format writes);
  * a target that is not a label of the disk sources (an equ / an absolute address);
  * the shared basic/*.inc bodies (the sub-ROM assembles them too).

    python3 scratchpad/disk_jr_route.py [--dry]
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
FILES = [f for f in sorted(glob.glob("disk/*.asm")) if os.path.basename(f) not in ("init.asm", "pageenv.asm")]
LAB = re.compile(r"^([A-Za-z_]\w*):")
JP = re.compile(r"^(\s+)jp(\s+)((?:nz|z|nc|c)\s*,\s*)?([A-Za-z_]\w*)(\s*(?:;.*)?)$", re.I)

labels = set()
for f in glob.glob("disk/*.asm"):
    for l in open(f):
        m = LAB.match(l)
        if m:
            labels.add(m.group(1))

changed = {}                                   # (file, line index) -> original text
for f in FILES:
    L = open(f).read().split("\n")
    in_tmpl = False
    for i, l in enumerate(L):
        m = LAB.match(l)
        if m:
            name = m.group(1)
            if "tmpl" in name or name == "fmt_boot":
                in_tmpl = True
            elif in_tmpl and (name.endswith("_end") or name == "fmt_bfcb"):
                in_tmpl = name == "fmt_bfcb"     # fmt_boot's FCB is data: still inside
                if name == "fmt_bfcb":
                    in_tmpl = False
                continue
        if in_tmpl:
            continue
        j = JP.match(l)
        if not j or j.group(4) not in labels:
            continue
        changed[(f, i)] = l
        L[i] = f"{j.group(1)}jr{j.group(2)}{j.group(3) or ''}{j.group(4)}{j.group(5)}"
    if "--dry" not in sys.argv:
        open(f, "w").write("\n".join(L))
print(f"candidates: {len(changed)}")
if "--dry" in sys.argv:
    sys.exit(0)

reverted = 0
for _ in range(len(changed) + 1):
    r = subprocess.run(["make", "-s", "repack-machine"], capture_output=True, text=True)
    out = r.stdout + r.stderr
    m = re.search(r"Relative jump out of range\s+on line (\d+) of file ([\w.]+)", out)
    if not m:
        if r.returncode:
            print(out[-1500:])
            sys.exit("build failed for another reason -- inspect before keeping anything")
        break
    ln, fn = int(m.group(1)), "disk/" + m.group(2)
    key = (fn, ln - 1)
    if key not in changed:
        sys.exit(f"out of range at {fn}:{ln}, which this tool did not touch")
    L = open(fn).read().split("\n")
    L[ln - 1] = changed.pop(key)
    open(fn, "w").write("\n".join(L))
    reverted += 1
print(f"kept {len(changed)} jp -> jr, reverted {reverted} out of range; build clean")
