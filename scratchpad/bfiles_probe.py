#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q7 + Q8 (Joost 2026-11-28 "Measure Disk BASIC first"). Q7: where does the reference keep Disk BASIC
CHANNEL state? Disk BASIC (via `BASIC` at A>): MAXFILES=2, OPEN for output, PRINT# ~720 B, CLOSE, OPEN for input,
INPUT#, CLOSE. Every RAM write in $C000-$F37F is counted per 16 B block and per step -- ADDRESSES ONLY, no byte, no
PC (clean room) -- and HIMEM ($FC4A, a work-area cell) is read at each step's end. Q8 falls out of the same counts:
any write to $DE77-$DF93 or to drive B's image span ($DF94-$E593) with B: never used.
Every step waits 8 s before the still-screen test (the CF-3300's silent disk work fooled a 3 s one, 2026-11-28).
    python3 -u scratchpad/bfiles_probe.py [MACHINE ...]
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
STEPS = [("mf", "MAXFILES=2"), ("op", 'OPEN "F.TXT" FOR OUTPUT AS #1'),
         ("pr", 'FOR I=1 TO 60:PRINT #1,"0123456789":NEXT'), ("cl", "CLOSE #1"),
         ("oi", 'OPEN "F.TXT" FOR INPUT AS #2'), ("ip", "INPUT #2,A$:PRINT A$"), ("cl2", "CLOSE")]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 8)] + [(t, x, 8) for t, x in STEPS]
order = ["basic"] + [t for t, _ in STEPS]
SPANS = [(0xDE77, 0xDF93, "below B's image"), (0xDF94, 0xE593, "B's FAT image"), (0xE595, 0xEB94, "A's FAT image"),
         (0xEB95, 0xED94, "dir buf"), (0xED95, 0xEF94, "data buf"), (0xEF95, 0xF194, "mount buf"),
         (0xF195, 0xF1C8, "DPB + after"), (0xF1C9, 0xF37F, "fixed area")]
CMD = ("set ::step basic; set ::cells [dict create]\n"
       "debug set_watchpoint write_mem {0xC000 0xF37F} {$::counting} { dict incr ::cells "
       "\"$::step:[expr {$::wp_last_address >> 4}]\" }\n")
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cells.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = "  puts $::fl \"HIMEM $tag [rd16 0xFC4A]\"\n  if {$tag eq \"basic\"} {set ::counting 1}\n"
    for k, v in zip(order, order[1:]):
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"{order[-1]}\"}} {{set ::counting 0; puts $::fl \"CELLS $::cells\"; flush $::fl}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    b = "{boot datecmd basic basicmem}"
    assert tcl.count(b) == 1
    tcl = tcl.replace(b, "{boot datecmd basic basicmem " + " ".join(t for t, _ in STEPS) + "}")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    lines = open(fl).read().splitlines()
    print(f"== {m}   (log {td})")
    print("   HIMEM after each step: " + "  ".join(f"{ln.split()[1]}=${int(ln.split()[2]):04X}"
                                                   for ln in lines if ln.startswith("HIMEM")))
    cl = next((ln for ln in lines if ln.startswith("CELLS ")), "CELLS").split()[1:]
    if not cl:
        print("   NO WRITES RECORDED -- instrument failed, not a finding")
    per = {}
    for i in range(0, len(cl) - 1, 2):
        step, blk = cl[i].split(":")
        per.setdefault(step, {})[int(blk) * 16] = int(cl[i + 1])
    for step in order[1:]:
        blks = per.get(step, {})
        runs, st, prev, tot = [], None, None, 0
        for a in sorted(blks):
            if st is None or a != prev + 16:
                if st is not None:
                    runs.append((st, prev + 15, tot))
                st, tot = a, 0
            prev = a
            tot += blks[a]
        if st is not None:
            runs.append((st, prev + 15, tot))
        print(f"   {step:4s} " + "  ".join(f"${lo:04X}-${hi:04X}:{n}" for lo, hi, n in runs))
    allb = {}
    for step in per:
        for a, n in per[step].items():
            allb[a] = allb.get(a, 0) + n
    print("   by CF span (all steps): " + "  ".join(
        f"{name}={sum(n for a, n in allb.items() if lo <= a + 15 and a <= hi)}" for lo, hi, name in SPANS))
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    if order[-1] in snaps:
        p = snaps[order[-1]].split()
        wd = int(p[1][2:])
        bb = bytes.fromhex(p[3])
        rows = [bb[k * wd:(k + 1) * wd].decode("latin1").rstrip() for k in range(24)]
        print("   final screen: " + " / ".join(r.strip() for r in rows if r.strip())[-300:])
