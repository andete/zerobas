#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST: which RAM does the Philips NMS 1200 disk ROM WRITE on the VG-8020 (the reference), from power-on to
MSX-DOS's prompt -- every address in $8000-$FFFF written by code running in the CARTRIDGE'S slot, as ranges, with the
first write's time. These are the cells a stock disk ROM uses at fixed or HIMEM-relative addresses; zerobas must keep
none of its own private variables there (Joost 2026-11-24: "investigate why we still have RAM variables that diverge
from reference").

Black box: a write watchpoint on RAM; recorded are the ADDRESS written and the page@slot of the code writing it. No PC
values, no ROM bytes, no values of the reference's RAM-resident code.

    python3 -u scratchpad/nmsram_probe.py [DOSDISK] > scratchpad/AE_nmsram_ref.out 2>&1
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402

DOS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
SECONDS = int(os.environ.get("NMSRAM_SECONDS", "30"))

TCL = r"""
set renderer none
set throttle off
set ::seen [dict create]
proc slotof {pg} { lassign [get_selected_slot $pg] ps ss; if {$ss eq "X"} {return "$ps"} ; return "$ps-$ss" }
proc on_w {} {
  set pg [expr {[reg pc] >> 14}]
  if {[slotof $pg] ne $::env(CARTSLOT) || $pg != 1} { return }
  set a $::wp_last_address
  if {![dict exists $::seen $a]} { dict set ::seen $a [format %.6f [machine_info time]] }
}
debug set_watchpoint write_mem {0x8000 0xFFFF} {} on_w
after time """ + str(SECONDS) + r""" {
  set f [open $::env(LOGF) w]
  foreach a [lsort -integer [dict keys $::seen]] { puts $f "[format %04X $a] [dict get $::seen $a]" }
  puts $f "SCREEN"
  puts $f [get_screen]
  close $f
  exit
}
"""


def ranges(addrs):
    out, start, prev = [], None, None
    for a in addrs:
        if start is None:
            start = prev = a
        elif a == prev + 1:
            prev = a
        else:
            out.append((start, prev))
            start = prev = a
    if start is not None:
        out.append((start, prev))
    return out


def main():
    dsk = probe_tmp.tmp("nmsram_ref.dsk")
    shutil.copyfile(DOS, dsk)
    tcl = probe_tmp.tmp("nmsram.tcl")
    open(tcl, "w").write(TCL)
    log = probe_tmp.tmp("nmsram_ref.log")
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", "Philips_VG_8020", "-ext", "Philips_NMS_1200",
           "-diska", dsk, "-script", tcl]
    subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log, CARTSLOT="1"),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    text = open(log).read()
    body, _, screen = text.partition("SCREEN\n")
    rows = [ln.split() for ln in body.splitlines() if ln.strip()]
    first = {int(a, 16): float(t) for a, t in rows}
    print(f"VG-8020 + NMS 1200, {SECONDS} s: RAM written by code in the cartridge's slot (page 1, slot 1)")
    print(f"{len(first)} distinct addresses in $8000-$FFFF")
    for s, e in ranges(sorted(first)):
        print(f"  ${s:04X}-${e:04X}  {e - s + 1:5d} B  first write {min(first[a] for a in range(s, e + 1)):.3f} s")
    print("screen at the end:")
    for ln in screen.splitlines():
        if ln.strip():
            print("  " + ln.rstrip())


if __name__ == "__main__":
    main()
