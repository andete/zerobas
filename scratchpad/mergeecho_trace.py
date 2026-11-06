# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MERGEECHO: S5_disk's `MERGE "SUBS"` is echoed TWICE on the DISK target (only
at the session's own pacing). zerobas ONLY (our own ROM and BIOS): log every CHPUT
($00A2, a published BIOS entry) with its character and time, and every key
injection, between two times."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_sessions as rs  # noqa: E402

T0, T1 = float(sys.argv[1]), float(sys.argv[2])
rs.TCL = rs.TCL.replace("proc __poll {} {", r"""
set ::__tf [open {%s} w]
proc __cp {} {
  set t [machine_info time]
  if {$t > %s && $t < %s} { puts $::__tf "CHPUT [format %%.4f $t] [format %%02X [reg A]] GET=[format %%04X [__rd16 0xF3FA]] PUT=[format %%04X [__rd16 0xF3F8]]"; flush $::__tf }
}
debug set_bp 0x00A2 {} __cp
rename __key __key0
proc __key {s} {
  puts $::__tf "KEY [format %%.4f [machine_info time]] [string map {\r <CR>} $s]"; flush $::__tf
  __key0 $s
}
proc __poll {} {""" % (os.path.join(REPO, "scratchpad", "mergeecho_trace.out"), T0, T1), 1)
text = open(os.path.join(REPO, "probes", "sessions", "S5_disk.ses")).read()
snaps, lpt, steps = rs.run("C-BIOS_MSX1_EU_REPACK_DISK", "mergeecho", text)
print(len(snaps), "snapshots")
