#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BDOSFCB residual (2): MSX-DOS's own SETRND ($0005, $24), both machines -- the
ten rows of scratchpad/setrnd_probe.py's $F37D series (scratchpad/setrnd_dos.asm).

    python3 scratchpad/setrnd_dos_probe.py --dos-disk D
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add  # noqa: E402
import probe_tmp  # noqa: E402

ROWS = ["EX0 CR0", "EX0 CR1", "EX0 CR2", "EX0 CR5", "EX1 CR0", "EX1 CR3",
        "EX0 CR2 +24=0", "EX0 CR2 +13=1", "EX0 CR2 RS=1", "EX0 CR2 RR=$77"]
ap = argparse.ArgumentParser()
ap.add_argument("--dos-disk", required=True)
ap.add_argument("--asm", default="setrnd_dos.asm")
ap.add_argument("--rows", default="")
a = ap.parse_args()
if a.rows:
    ROWS = a.rows.split(",")
work = probe_tmp.tmp("setrnd_dos")
os.makedirs(work, exist_ok=True)
com, sym = os.path.join(work, "setrnd.com"), os.path.join(work, "setrnd.sym")
subprocess.run(["pasmo", "--bin", os.path.join(HERE, a.asm), com, sym], check=True)
done = next(int(l.split()[-1].rstrip("H"), 16) for l in open(sym) if l.startswith("done"))
dsk = os.path.join(work, "setrnd.dsk")
shutil.copyfile(a.dos_disk, dsk)
img = bytearray(open(dsk, "rb").read())
fat12_add(img, "SETRND", "COM", open(com, "rb").read())
fat12_add(img, "AUTOEXEC", "BAT", b"SETRND\r\n")
open(dsk, "wb").write(img)
cap = subprocess.run(["python3", "-u", os.path.join(REPO, "probes", "disk", "disk_probe_diff.py"), "capture",
                      "--at", hex(done), "--arm-addr", hex(done), "--arm-check-addr", "0x04F0",
                      "--arm-check-val", "0xA5", "--settle", "120", "--machine", "both",
                      "--mem", "0x0400:0x40", "--diska", dsk], capture_output=True, text=True)
txt = cap.stdout + cap.stderr
print(txt.split("head stock")[0][-400:] if "head stock" not in txt else "", end="")
for side in ("stock", "ours "):
    m = re.search(r"head %s: ([0-9A-F ]+)" % side, txt)
    if not m:
        print(f"{side}: no capture\n{txt[-1500:]}")
        continue
    b = [int(x, 16) for x in m.group(1).split()]
    print(f"== {side.strip()} (MSX-DOS $0005)")
    for i, what in enumerate(ROWS):
        r = b[i * 5:i * 5 + 5]
        print(f"  {what:16s} A={r[0]:02X}  RR={r[4]:02X}{r[3]:02X}{r[2]:02X}{r[1]:02X}")
