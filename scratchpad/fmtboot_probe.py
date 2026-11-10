#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DSKFMT (b): does OUR boot loader (fmt_boot, the code DSKFMT writes at $C01E) boot
MSX-DOS once MSXDOS.SYS and COMMAND.COM are on the disk -- on BOTH machines?

Builds a 720K image as a choice-4 format leaves it (tools/make_test_dsk.py --empty:
the FAT12 layout), puts OUR loader -- read out of this project's own build/disk.rom
by the fmt_boot / FMT_BOOTLEN symbols -- over sector 0 from $1E, zeroes the rest of
the sector (a format does), adds MSXDOS.SYS and COMMAND.COM from the DOS disk, and
boots each machine, dumping the screen.

    python3 scratchpad/fmtboot_probe.py --dos-disk D [--machine stock|ours|both]
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add  # noqa: E402
from disk_probe_format import read_fat_file  # noqa: E402
import probe_tmp  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dos-disk", required=True)
ap.add_argument("--machine", default="both")
ap.add_argument("--dump", action="append", type=float, default=[])
ap.add_argument("--settle", type=float, default=40.0)
a = ap.parse_args()

S = {}
for l in open(os.path.join(REPO, "build", "disk.sym")):
    p = l.split()
    if len(p) >= 3 and p[1] == "EQU":
        S[p[0]] = int(p[2].rstrip("H"), 16)
rom = open(os.path.join(REPO, "build", "disk.rom"), "rb").read()
blob = rom[S["fmt_boot"] - 0x4000:S["fmt_boot"] - 0x4000 + S["FMT_BOOTLEN"]]

work = probe_tmp.tmp("fmtboot")
os.makedirs(work, exist_ok=True)
img_path = os.path.join(work, "fmtboot.dsk")
subprocess.run(["python3", os.path.join(REPO, "tools", "make_test_dsk.py"), "--empty", img_path],
               check=True, capture_output=True)
img = bytearray(open(img_path, "rb").read())
img[0x1E:0x200] = bytes(0x200 - 0x1E)                 # a format leaves the rest 0
img[0x1E:len(blob)] = blob[0x1E:]                     # OUR loader (and its FCB name)
img[0] = 0xEB                                         # a boot signature
if os.environ.get("FMTBOOT_KNIFE"):                   # the knife: the loader just returns
    img[0x1E] = 0xC9
    print("KNIFE: the loader is a bare `ret`")
src = open(a.dos_disk, "rb").read()
for n8, e3 in (("MSXDOS", "SYS"), ("COMMAND", "COM")):
    data = read_fat_file(src, n8, e3)
    if data is None:
        sys.exit(f"{n8}.{e3} not on {a.dos_disk}")
    fat12_add(img, n8, e3, data)
open(img_path, "wb").write(img)
print(f"image: {img_path}  (loader {len(blob) - 0x1E} B at $1E)")

cmd = ["python3", os.path.join(HERE, "fmtdialog_probe.py"), "--machine", a.machine,
       "--disk", img_path, "--settle", str(a.settle)]
for t in a.dump:
    cmd += ["--dump", str(t)]
sys.exit(subprocess.run(cmd).returncode)
