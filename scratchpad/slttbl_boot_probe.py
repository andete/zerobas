#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKMSX2HOST: SLTTBL[3] ($FCC8, the slot-3 secondary-register mirror) against the live register, at each entry
of the boot sector's code ($C01E, page 3 = RAM) and at MSX-DOS's $0100 -- RAM and slot state only (clean room).
    python3 -u scratchpad/slttbl_boot_probe.py MACHINE DISK [SECONDS]
"""
import os
import subprocess
import sys
import tempfile

machine, disk = sys.argv[1], os.path.expanduser(sys.argv[2])
secs = int(sys.argv[3]) if len(sys.argv) > 3 else 25
td = tempfile.mkdtemp()
d = os.path.join(td, "d.dsk")
subprocess.run(["cp", disk, d], check=True)
log = os.path.join(td, "o.txt")
tcl = f"""set throttle off
set f [open {{{log}}} w]
set n 0
proc snap {{what}} {{
  global f n
  if {{[incr n] > 12}} return
  puts $f "[format %8.3f [machine_info time]] $what A8=[format %02X [debug read ioports 0xA8]] live=[format %02X [expr {{[peek 0xFFFF] ^ 0xFF}}]] SLTTBL3=[format %02X [peek 0xFCC8]] SLTTBL0=[format %02X [peek 0xFCC5]]"
  flush $f
}}
debug set_bp 0xC01E {{[expr {{([debug read ioports 0xA8] >> 6) == 3}}]}} {{snap C01E}}
debug set_bp 0x0100 {{[expr {{([debug read ioports 0xA8] & 3) == 3}}]}} {{snap 0100}}
after time {secs} exit
"""
sf = os.path.join(td, "s.tcl")
open(sf, "w").write(tcl)
subprocess.run(["openmsx", "-machine", machine, "-diska", d, "-command", "set renderer none; set sound_driver null",
                "-script", sf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
print(f"== {machine} {os.path.basename(disk)}")
print(open(log).read() if os.path.exists(log) else "<no log>")
