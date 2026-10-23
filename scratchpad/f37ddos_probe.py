#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TPAPTAIL (a): an MSX-DOS program calls $F37D (CPMVER) instead of $0005
from the TPA (probes/disk/f37ddos.asm, our own program, run from AUTOEXEC.BAT).
$C000 = the last step STARTED (8 = all done), $C001.. the answers.

    python3 -u scratchpad/f37ddos_probe.py [--machines ref,zb,zbcf]
"""
import argparse, os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402

MACH = {"ref": RT.REF_MACHINE, "zb": "C-BIOS_MSX1_EU_REPACK_DISK", "zbcf": "National_CF-3300_ZEROBASDISK"}
NAMES = ["step", "L", "H", "A"]

ap = argparse.ArgumentParser()
ap.add_argument("--machines", default="ref,zb,zbcf")
a = ap.parse_args()
com = probe_tmp.tmp("f37ddos.com")
subprocess.run(["pasmo", "--bin", os.path.join(REPO, "scratchpad", "f37ddos.asm"), com],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for m in a.machines.split(","):
    dsk = probe_tmp.tmp(f"f37ddos_{m}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "F37DDOS", "COM", open(com, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", b"F37DDOS\r\n")
    open(dsk, "wb").write(img)
    dump = probe_tmp.tmp(f"f37ddos_{m}.mem")
    if os.path.exists(dump):
        os.remove(dump)
    tcl = (f"after time 40 {{ set f [open {{{dump}}} w]; "
           "binary scan [debug read_block {Main RAM} 0xC000 4] H* b; "
           "puts $f $b; close $f }\n")
    W.run_once(MACH[m], dsk, 14, 42, 300, cmd="F37DDOS", extra_tcl=tcl, type_cmd=False)
    h = open(dump).read().split()[0] if os.path.exists(dump) else ""
    b = bytes.fromhex(h)
    print(f"{m:5s} ({MACH[m]}): " + ("<NO OUTPUT>" if not b else
          "  ".join(f"{n}={v:02X}" for n, v in zip(NAMES, b))))
