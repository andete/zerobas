#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Histogram the disk-ROM ENTRY points the MSX-DOS kernel calls during boot.

Black-box discipline (the $4030/$50A9 playbook): we never read the disk ROM's
code; we only observe which fixed entry addresses the kernel transfers into and
with what register state. This probe logs every rising edge where PC crosses
from outside the disk-ROM page ($4000-$7FFF) to inside it *and* the return
address on top of the stack is in high RAM ($C000+), i.e. a genuine call from
the relocated MSX-DOS kernel (not our ROM calling itself). For each distinct
entry address it counts hits and records the first-seen register snapshot.

The high-count entries are the sector-load body (DSKIO); the interesting ones
are non-standard fixed entries the kernel expects the disk ROM to implement
(e.g. $4030, $50A9, and any further ones) -- the next black-box reimplem targets.

Usage:
    python3 probes/disk/disk_probe_dosboot_entries.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_entries.py --dos-disk /tmp/dos.dsk --stock
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

ROM_LO = 0x4000
ROM_HI = 0x7FFF
MAX_DISTINCT = 64


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::prev_in 0
array set ::cnt {{}}
array set ::first {{}}
set ::order {{}}

proc record {{}} {{
  set pc [reg PC]
  set in [expr {{$pc >= {ROM_LO} && $pc <= {ROM_HI}}}]
  if {{$in && !$::prev_in}} {{
    # return address = word on top of stack (caller of this entry)
    set sp [reg SP]
    set ra [expr {{[debug read memory $sp] | ([debug read memory [expr {{$sp+1}}]] << 8)}}]
    if {{$ra >= 0xC000}} {{
      set key [format %04X $pc]
      if {{![info exists ::cnt($key)]}} {{
        set ::cnt($key) 0
        set ::first($key) [format "ra=%04X|AF=%04X|BC=%04X|DE=%04X|HL=%04X|IX=%04X|IY=%04X|SP=%04X" \\
          $ra [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] $sp]
        lappend ::order $key
        if {{[llength $::order] >= {MAX_DISTINCT}}} {{ finish }}
      }}
      incr ::cnt($key)
    }}
  }}
  set ::prev_in $in
}}

proc finish {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  puts $f "distinct=[llength $::order]"
  foreach k $::order {{ puts $f "$k cnt=$::cnt($k) $::first($k)" }}
  close $f
  exit
}}

debug set_condition {{1}} {{ record }}
after time {settle:.1f} {{ finish }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    machine = STOCK_MACHINE if args.stock else TIER1_MACHINE
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    lines = run(machine, args.dos_disk, args.settle, args.timeout)
    print(f"=== disk-ROM entry histogram ({machine}) ===")
    for ln in lines:
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
