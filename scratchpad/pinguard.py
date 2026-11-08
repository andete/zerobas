#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which `ds $XXXX - $` pin in disk/*.asm did a change overrun?

An overrun makes pasmo write NO bytes (a negative `ds`), and `make` only says
"EMPTY". This copies disk/ and basic/ to the temp root, plants a label in front
of every pin, assembles the copy, and prints each pin whose label landed past
it, with the overrun in bytes -- and, with --slack, every pin's room instead.

    python3 scratchpad/pinguard.py [--slack]
"""
import glob, os, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import probe_tmp  # noqa: E402

work = os.path.join(probe_tmp.ROOT, "pinguard")
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(os.path.join(REPO, "basic"), os.path.join(work, "basic"))
shutil.copytree(os.path.join(REPO, "disk"), os.path.join(work, "disk"))
n = 0
where = {}
for f in glob.glob(os.path.join(work, "disk", "*.asm")):
    out = []
    for i, line in enumerate(open(f), 1):
        m = re.match(r"^(\s+)ds\s+\$([0-9A-Fa-f]{4})\s*-\s*\$", line)
        if m:
            n += 1
            lab = f"__PIN_{m.group(2).upper()}_{n}"
            where[lab] = f"{os.path.basename(f)}:{i}"
            out.append(lab + ":\n")
        out.append(line)
    open(f, "w").write("".join(out))
sym = os.path.join(work, "disk.sym")
subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", os.path.join(work, "disk.rom"), sym],
               cwd=work, capture_output=True)
rows = []
for line in open(sym):
    p = line.split()
    if p and p[0].startswith("__PIN_"):
        pin = int(p[0].split("_")[3], 16)
        at = int(p[-1].rstrip("H"), 16)
        rows.append((pin, at, p[0]))
bad = [(pin, at, lab) for pin, at, lab in rows if at > pin]
for pin, at, lab in sorted(bad):
    print(f"OVERRUN ${pin:04X} ({where[lab]}): reached ${at:04X}, {at - pin} B over")
if "--slack" in sys.argv:
    for pin, at, lab in sorted(rows):
        if at <= pin:
            print(f"  ${pin:04X} ({where[lab]}): {pin - at} B free")
if not bad:
    print("no pin overrun")
