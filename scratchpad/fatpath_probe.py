#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW sizing: WHICH zerobas code paths issue the FAT-sector commands of a COPY? ZEROBAS ONLY -- its own ROM's
return addresses (the clean room forbids this on a reference; this never boots one). At every read / write command
to track 0 sectors 2-7 (the 720 KB FATs) during `COPY <src> BIG.ROM`, the top stack words are read and those inside
the disk ROM's page 1 ($4000-$7FFF, slot 3-1) are named from build/disk.sym. Prints a histogram of call chains.
    python3 -u scratchpad/fatpath_probe.py [SRC]
"""
import collections
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

src = sys.argv[1] if len(sys.argv) > 1 else "MSXBUNSE.ROM"
MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"      # zerobas only, never a reference
syms = sorted((int(p[2].rstrip("H"), 16), p[0]) for p in (ln.split() for ln in open(os.path.join(REPO, "build",
              "disk.sym"))) if len(p) >= 3 and p[1] == "EQU" and p[0][:1].islower())


def name(a):
    best = None
    for v, n in syms:
        if v <= a:
            best = (v, n)
        else:
            break
    return f"{best[1]}+{a - best[0]:X}" if best else f"{a:04X}"


D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4), ("copy", f"COPY {src} BIG.ROM", 1)]
td = tempfile.mkdtemp()
dsk = os.path.join(td, "d.dsk")
subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
out = os.path.join(td, "o.txt")
log = os.path.join(td, "fat.txt")
tcl = D.tcl(out)
tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
    f"set ::fl [open {{{log}}} w]\n"
    "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {"
    "set c [expr {$::wp_last_value >> 4}]; set s [peek 0x7FBA]; "
    "if {($c == 8 || $c == 10) && [peek 0x7FB9] == 0 && $s >= 2 && $s <= 7} {"
    "set w {}; for {set i 0} {$i < 24} {incr i 2} {lappend w [format %04X [peek16 [expr {[reg SP] + $i}]]]}; "
    "puts $::fl \"$c $s $w\"}}}", 1)
a = "  close $f }"
assert tcl.count(a) == 1
tcl = tcl.replace(a, "  if {$tag eq \"mode\"} {set ::counting 1}\n  if {$tag eq \"copy\"} {set ::counting 0; flush $::fl}\n" + a)
tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
sf = os.path.join(td, "s.tcl")
open(sf, "w").write(tcl)
subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", MACHINE, "-diska", dsk, "-command",
               "set renderer none; set sound_driver null", "-script", sf]),
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2400)
hist = collections.Counter()
for ln in open(log).read().splitlines():
    p = ln.split()
    c, s, words = int(p[0]), int(p[1]), [int(w, 16) for w in p[2:]]
    chain = " < ".join(name(w) for w in words if 0x4000 <= w < 0x8000)[:150]
    hist[(("R" if c == 8 else "W") + f"{s}", chain)] += 1
for (k, chain), n in hist.most_common(16):
    print(f"{n:4d}  {k:3s}  {chain}")
