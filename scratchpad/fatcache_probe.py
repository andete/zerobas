#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q3 (Joost 2026-11-28 "as much info as possible before ... any code"): WHEN does the reference re-read
its FAT image? One MSX-DOS session: COPY, DIR, COPY again, then the disk image is SWAPPED (openMSX `diska`) for a
fresh copy of the original disk, then DIR and a third COPY. Every FDC command is logged with the step it fell in
(track / sector registers only -- no RAM byte, no PC), so each step's FAT-sector reads and writes are counted; both
images are listed at the end, so a stale FAT written onto the swapped disk shows as a damaged listing.
    python3 -u scratchpad/fatcache_probe.py [MACHINE ...]
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
D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4),
             ("copy1", "COPY MSXBUNSE.ROM BIG.ROM", 1), ("dir1", "DIR BIG*.*", 2),
             ("copy2", "COPY MSXBUNSE.ROM BIG2.ROM", 1),
             ("dir2", "DIR BIG*.*", 2), ("copy3", "COPY MSXBUNSE.ROM BIG3.ROM", 1)]
CMD = ("set ::step mode\n"
       "proc __cmd {base} { if {!$::counting} return; "
       "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; "
       "puts $::fl \"C $::step $c $t $s\" }\n"
       "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
       "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n")
NEXT = {"mode": "copy1", "copy1": "dir1", "dir1": "copy2", "copy2": "dir2", "dir2": "copy3"}
for m in machines:
    td = tempfile.mkdtemp()
    dsk, dsk2 = os.path.join(td, "d.dsk"), os.path.join(td, "d2.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    subprocess.run(["cp", SRC, dsk2], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cmd.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = "  if {$tag eq \"mode\"} {set ::counting 1}\n"
    for k, v in NEXT.items():
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"copy2\"}} {{diska {{{dsk2}}}; puts $::fl \"SWAP\"}}\n"
    hook += "  if {$tag eq \"copy3\"} {set ::counting 0; flush $::fl}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    print(f"== {m}   (log {td})")
    lines = open(fl).read().splitlines()
    if not any(ln.startswith("C ") for ln in lines):
        print("   NO FDC COMMANDS RECORDED -- instrument failed, not a finding")
    cnt = {}
    for ln in lines:
        p = ln.split()
        if p[0] != "C":
            continue
        step, c, t, s = p[1], int(p[2]), int(p[3]), int(p[4])
        kind = ("FATread" if c == 8 else "FATwrite" if c == 10 else None) if t == 0 and 2 <= s <= 7 else \
               ("t0read" if c == 8 else "t0write" if c == 10 else None) if t == 0 else \
               ("read" if c == 8 else "write" if c == 10 else None)
        if kind:
            cnt.setdefault(step, {}).setdefault(kind, 0)
            cnt[step][kind] += 1
    for step in ["copy1", "dir1", "copy2", "dir2", "copy3"]:
        tag = "  (after the swap)" if step == "dir2" else ""
        print(f"   {step:6s} " + "  ".join(f"{k}={v}" for k, v in sorted(cnt.get(step, {}).items())) + tag)
    for lbl, f in (("first image", dsk), ("swapped-in image", dsk2)):
        big = [e for e in D.disk_listing(bytearray(open(f, "rb").read())) if e.startswith("BIG")]
        print(f"   {lbl}: " + (" | ".join(big) or "no BIG*"))
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    for step in ("dir1", "dir2", "copy3"):
        if step in snaps:
            p = snaps[step].split()
            w = int(p[1][2:])
            b = bytes.fromhex(p[3])
            rows = [b[i * w:(i + 1) * w].decode("latin1").rstrip() for i in range(24)]
            print(f"   screen at {step}: " + " / ".join(r for r in rows if r.strip())[-260:])
