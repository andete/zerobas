#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B: emulated seconds for 4200 B of PRINT# + CLOSE, marker to marker.

The program POKEs &HD000 = 1 when it starts the work and 2 when it is done;
Tcl polls the cell every 20 ms of emulated time and records both instants.
(The first stopwatch keyed on the cursor ROW settling and was wrong twice: a
silent loop never moves the row, and JIFFY/TIME stop while a sector op holds
DI -- so neither the row nor TIME is a clock here.)

    python3 -u scratchpad/s10b_stopwatch.py [new] [app] [cf]
      new  ours, OPEN FOR OUTPUT (disk.rom's record writer)
      app  ours, the same through APPEND (main's engine) on a created file
      cf   the CF-3300, OPEN FOR OUTPUT
"""
import os, shutil, subprocess, sys
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import probe_tmp, omsx_preflight
S = probe_tmp.tmp("")  # the one temp root
LOOP = 'for i=1 to 200:print#1,\\"abcdefghijklmnopqrs\\":next:close#1:poke \\&hd000,2'
def run(machine, pre, tag):
    dsk = probe_tmp.tmp(f"dw_{tag}.dsk"); shutil.copyfile("/Users/joost/projects/zerobas/disk/test720.dsk", dsk)
    out = os.path.join(S, f"dw_{tag}.txt")
    if os.path.exists(out): os.remove(out)
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set t1 0
set t2 0
proc poll {{}} {{
  set v [debug read memory 0xD000]
  if {{$v == 1 && $::t1 == 0}} {{ set ::t1 [machine_info time] }}
  if {{$v == 2 && $::t2 == 0}} {{ set ::t2 [machine_info time] }}
  if {{$::t2 == 0}} {{ after time 0.02 poll }} else {{ puts $::f "t=[expr {{$::t2 - $::t1}}]"; close $::f; exit }}
}}
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; type "{pre}:poke \\&hd000,1:{LOOP}\\r"; poll }}
after time 400 {{ set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM $i]; if {{$c < 32 || $c > 126}} {{append s " "}} else {{append s [format %c $c]}} }}; puts $f "timeout m=[debug read memory 0xD000] t1=$::t1 scr=$s"; close $f; exit }}
'''
    tf = os.path.join(S, f"dw_{tag}.tcl"); open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", machine, "-diska", dsk, "-command",
                    "set renderer none; set sound_driver null; set save_settings_on_exit false", "-script", tf]),
                   capture_output=True, timeout=900)
    print(f"{tag}: {open(out).read().strip() if os.path.exists(out) else 'no reading'} s for 4200 B", flush=True)
which = sys.argv[1:] or ["new", "app", "cf"]
if "new" in which: run("C-BIOS_MSX1_EU_REPACK_DISK", 'open\\"big.txt\\" for output as #1', "new")
if "app" in which: run("C-BIOS_MSX1_EU_REPACK_DISK", 'open\\"big.txt\\" for output as #1:close#1:open\\"big.txt\\" for append as #1', "app")
if "cf" in which: run("National_CF-3300", 'open\\"big.txt\\" for output as #1', "cf")
