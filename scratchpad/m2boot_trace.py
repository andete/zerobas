#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKMSX2HOST: the disk ROM's boot path on a C-BIOS NOBASIC_DISK variant -- which of our own boot labels run, in
what order, and the restart ($0000 with page 0 on the BIOS). Our ROM's symbols + RAM-side $C01E / $0100 only.
    python3 -u scratchpad/m2boot_trace.py MACHINE [SUBSLOT e.g. 3-1] [SECONDS]
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
machine = sys.argv[1]
ps, ss = (int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "3-1").split("-"))
secs = int(sys.argv[3]) if len(sys.argv) > 3 else 70
syms = {}
for ln in open(os.path.join(REPO, "build", "disk.sym")):
    p = ln.split()
    if len(p) >= 3 and p[1] == "EQU":
        syms[p[0]] = int(p[2].rstrip("H"), 16)
labels = ["init", "hrunc_h", "boot_disk", "boot_sig_ok", "boot_date", "boot_call0", "bdos_entry", "install_basic_hooks"]
td = tempfile.mkdtemp()
dsk = os.path.join(td, "d.dsk")
subprocess.run(["cp", os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), dsk], check=True)
log = os.path.join(td, "o.txt")
tcl = ["set throttle off", f"set f [open {{{log}}} w]", "array set seen {}",
       "proc hit {what} { global f seen; if {[incr seen($what)] > 3} return; "
       "puts $f \"[format %8.3f [machine_info time]] $what SP=[format %04X [reg SP]] A8=[format %02X "
       "[debug read ioports 0xA8]] SS=[format %02X [expr {[peek 0xFFFF] ^ 0xFF}]] HIMEM=[format %04X [peek16 0xFC4A]] "
       "SCRMOD=[peek 0xFCAF]\"; flush $f }"]
for n in labels:
    tcl.append(f"debug set_bp 0x{syms[n]:04X} {{[pc_in_slot {ps} {ss}]}} {{hit {n}}}")
tcl.append("debug set_bp 0xC01E {[expr {([debug read ioports 0xA8] >> 6) == 3}]} {hit C01E-boot-sector}")
tcl.append("debug set_bp 0x0100 {[expr {([debug read ioports 0xA8] & 3) == 3}]} {hit 0100-dos-start}")
tcl.append("debug set_bp 0x0000 {[expr {([debug read ioports 0xA8] & 3) == 0 && [machine_info time] > 2}]} "
           "{hit RESET-bios-0000}")
tcl.append(f"after time {secs} exit")
sf = os.path.join(td, "s.tcl")
open(sf, "w").write("\n".join(tcl) + "\n")
subprocess.run(["openmsx", "-machine", machine, "-diska", dsk, "-command",
                "set renderer none; set sound_driver null", "-script", sf],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
print(f"== {machine} (disk {ps}-{ss})")
print(open(log).read() if os.path.exists(log) else "<no log>")
