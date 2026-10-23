#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BOOTREGS: what does `JP 0` -- CP/M's warm boot -- do from a boot sector's code at
step 7 (the "load the system" call, Cy = 1), BEFORE any MSXDOS.SYS? frayd1.dsk's
program relies on it (the CF-3300's disk ROM fills $0001/$0002 just before step 7).

Our OWN boot code (written into a copy of the DOS test disk's boot sector at $1E):
    RET NC            ; step 5 (Cy = 0): back to the disk ROM
    LD A,$5A / LD ($C800),A   ; a mark: step 7 ran
    JP 0
Black box: breakpoints on $F37D and $0005 (the C register, SP), PC samples, and the
mark. Nothing of the reference is read.

    python3 -u scratchpad/wboot_probe.py [--machines ref,zb]
"""
import argparse, os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

MACH = {"ref": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}
CODE = bytes([0xD0, 0x3E, 0x5A, 0x32, 0x00, 0xC8, 0xC3, 0x00, 0x00])
ap = argparse.ArgumentParser()
ap.add_argument("--machines", default="ref,zb")
ap.add_argument("--end", type=float, default=20)
a = ap.parse_args()
for m in a.machines.split(","):
    dsk = probe_tmp.tmp(f"wboot_{m}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    img[0x1E:0x1E + len(CODE)] = CODE
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"wboot_{m}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = f'''set throttle off
set ::n 0
proc __put {{s}} {{ set f [open {{{out}}} a]; puts $f $s; close $f }}
proc __w {{a}} {{ expr {{[debug read memory [expr {{$a & 0xFFFF}}]] + 256*[debug read memory [expr {{($a+1) & 0xFFFF}}]]}} }}
proc __b {{t}} {{ if {{[incr ::n] > 30}} return; __put [format "%8.3f %s C=%02X DE=%04X SP=%04X ret=%04X A8=%02X" [machine_info time] $t [reg c] [reg de] [reg sp] [__w [reg sp]] [debug read ioports 0xA8]] }}
debug set_bp 0xF37D {{}} {{__b F37D}}
debug set_bp 0x0005 {{}} {{__b 0005}}
debug set_bp 0x0000 {{}} {{__b JP0}}
proc __s {{}} {{ __put [format "%8.3f sample PC=%04X SP=%04X A8=%02X mark=%02X" [machine_info time] [reg pc] [reg sp] [debug read ioports 0xA8] [debug read memory 0xC800]]; after time 1 __s }}
after time 1 __s
after time {a.end} {{ exit }}
'''
    s = probe_tmp.tmp(f"wboot_{m}.tcl")
    open(s, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded([RT.OMSX, "-machine", MACH[m], "-diska", dsk,
                    "-command", "set renderer none; set sound_driver null", "-script", s]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    print(f"### {m} ({MACH[m]})")
    print(open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>")
