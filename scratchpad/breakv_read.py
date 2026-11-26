#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BUFINCTL: the Ctrl-C handler vector BREAKV ($F325) and the disk-error vector DISKVE ($F323) --
the work-area pointers and the 2-byte cell each names (an address: data, never the code it points
at) -- under MSX-DOS (A>) and under BASIC (no disk), CF-3300 and zerobas. Clean room: RAM cells only."""
import os, shutil, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight, probe_tmp  # noqa: E402
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
    for env in ("dos", "basic"):
        td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
        out = os.path.join(td, "o.txt")
        tcl = os.path.join(td, "s.tcl")
        open(tcl, "w").write(f"""set throttle off
proc rd {{a}} {{ return [expr {{[debug read memory $a] + 256*[debug read memory [expr {{$a+1}}]]}}] }}
after time 30 {{
  set f [open {{{out}}} w]
  foreach {{n a}} {{DISKVE 0xF323 BREAKV 0xF325}} {{
    set p [rd $a]
    if {{$p >= 0x8000}} {{ set c [format %04X [rd $p]] }} else {{ set c "-" }}
    puts $f "$n ptr=[format %04X $p] cell=$c"
  }}
  close $f; exit }}
""")
        cmd = ["openmsx", "-machine", m, "-command", "set renderer none; set sound_driver null", "-script", tcl]
        if env == "dos":
            d = os.path.join(td, "d.dsk"); shutil.copyfile(DOS, d); cmd[3:3] = ["-diska", d]
        subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        print(side, env, open(out).read().replace("\n", "  ") if os.path.exists(out) else "NO READING")
        shutil.rmtree(td, ignore_errors=True)
