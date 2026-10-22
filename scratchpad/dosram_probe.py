#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TPAP1 step 2: which page-3 RAM does an MSX-DOS session WRITE? Write
watchpoints over candidate ranges, per address the first / last write's time and
the writing PC (an ADDRESS, never code bytes); breakpoint times at $0100 (each
.COM start). Our own disk: AUTOEXEC.BAT runs DIR, then P1VEC (probes/disk/p1vec.asm).

    python3 -u scratchpad/dosram_probe.py [--machines zb,ref] [--ranges F773-F87E,DDF0-DF92]
"""
import argparse, os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

MACH = {"ref": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK",
        "zbcf": "National_CF-3300_ZEROBASDISK"}
ap = argparse.ArgumentParser()
ap.add_argument("--machines", default="zb,ref")
ap.add_argument("--ranges", default="F773-F87E,DDF0-DF92")
ap.add_argument("--end", type=float, default=40)
ap.add_argument("--autoexec", default="DIR|P1VEC", help="commands, | between them")
a = ap.parse_args()
com = probe_tmp.tmp("p1vec.com")
subprocess.run(["pasmo", "--bin", os.path.join(REPO, "probes", "disk", "p1vec.asm"), com],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for m in a.machines.split(","):
    dsk = probe_tmp.tmp(f"dosram_{m}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "P1VEC", "COM", open(com, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", a.autoexec.encode().replace(b"|", b"\r\n") + b"\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"dosram_{m}.txt")
    if os.path.exists(out):
        os.remove(out)
    wps = "\n".join(f"debug set_watchpoint write_mem {{0x{r.split('-')[0]} 0x{r.split('-')[1]}}} {{}} {{__w}}"
                    for r in a.ranges.split(","))
    tcl = f'''set throttle off
array set ::f {{}}
array set ::l {{}}
set ::starts {{}}
proc __w {{}} {{
  set ad [format %04X $::wp_last_address]
  set t [format "%.3f@%04X" [machine_info time] [reg pc]]
  if {{![info exists ::f($ad)]}} {{ set ::f($ad) $t }}
  set ::l($ad) $t
}}
proc __s {{}} {{ if {{[llength $::starts] < 8}} {{ lappend ::starts [format %.3f [machine_info time]] }} }}
debug set_bp 0x0100 {{}} {{__s}}
{wps}
after time {a.end} {{
  set fh [open {{{out}}} w]
  puts $fh "starts@0100: $::starts"
  foreach ad [lsort [array names ::f]] {{ puts $fh "$ad first $::f($ad) last $::l($ad)" }}
  close $fh; exit
}}
'''
    s = probe_tmp.tmp(f"dosram_{m}.tcl")
    open(s, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded([RT.OMSX, "-machine", MACH[m], "-diska", dsk,
                    "-command", "set renderer none; set sound_driver null", "-script", s]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    print(f"### {m} ({MACH[m]})")
    print(open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>")
