#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BOOTREGS: CALLF ($0030) to a PAGE-0 target from a boot sector's code at step 7,
BEFORE any MSXDOS.SYS (page 0 is RAM then). frayd1.dsk's boot code does
`RST 30h / $80 / $0141` there. Does the disk ROM's CALLF run the RAM at the target,
or page the BIOS in?

Our OWN boot code: RET NC (step 5); then writes `LD A,$A5 / RET` at $0141 in page-0
RAM, and CALLFs slot $80 and slot $00 at $0141 with A = 7; the answers go to
$C800 / $C801, a mark $5A to $C802; then it waits (JR $). Black box: the answers.

    python3 -u scratchpad/bootcallf_probe.py [--machines ref,zb]
"""
import argparse, os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

MACH = {"ref": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}
CODE = bytes([0xD0,                                   # RET NC
              0x3E, 0x3E, 0x32, 0x41, 0x01,           # LD A,$3E / LD ($0141),A
              0x3E, 0xA5, 0x32, 0x42, 0x01,           # LD A,$A5 / LD ($0142),A
              0x3E, 0xC9, 0x32, 0x43, 0x01,           # LD A,$C9 / LD ($0143),A
              0x3E, 0x07, 0xF7, 0x80, 0x41, 0x01,     # LD A,7 / RST 30h $80 $0141
              0x32, 0x00, 0xC8,                       # LD ($C800),A
              0x3E, 0x07, 0xF7, 0x00, 0x41, 0x01,     # LD A,7 / RST 30h $00 $0141
              0x32, 0x01, 0xC8,                       # LD ($C801),A
              0x3E, 0x5A, 0x32, 0x02, 0xC8,           # LD A,$5A / LD ($C802),A
              0x18, 0xFE])                            # JR $
ap = argparse.ArgumentParser()
ap.add_argument("--machines", default="ref,zb")
ap.add_argument("--end", type=float, default=20)
a = ap.parse_args()
for m in a.machines.split(","):
    dsk = probe_tmp.tmp(f"bcallf_{m}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    img[0x1E:0x1E + len(CODE)] = CODE
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"bcallf_{m}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = f'''set throttle off
set ::n 0
proc __put {{s}} {{ set f [open {{{out}}} a]; puts $f $s; close $f }}
proc __w {{a}} {{ expr {{[debug read memory [expr {{$a & 0xFFFF}}]] + 256*[debug read memory [expr {{($a+1) & 0xFFFF}}]]}} }}
proc __b {{t}} {{ if {{[incr ::n] > 30}} return; __put [format "%8.3f %s C=%02X DE=%04X SP=%04X ret=%04X A8=%02X" [machine_info time] $t [reg c] [reg de] [reg sp] [__w [reg sp]] [debug read ioports 0xA8]] }}
proc __s {{}} {{ __put [format "%8.3f sample PC=%04X SP=%04X A8=%02X C800=%02X C801=%02X C802=%02X" [machine_info time] [reg pc] [reg sp] [debug read ioports 0xA8] [debug read memory 0xC800] [debug read memory 0xC801] [debug read memory 0xC802]]; after time 1 __s }}
after time 1 __s
after time {a.end} {{ exit }}
'''
    s = probe_tmp.tmp(f"bcallf_{m}.tcl")
    open(s, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded([RT.OMSX, "-machine", MACH[m], "-diska", dsk,
                    "-command", "set renderer none; set sound_driver null", "-script", s]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    print(f"### {m} ({MACH[m]})")
    print(open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>")
