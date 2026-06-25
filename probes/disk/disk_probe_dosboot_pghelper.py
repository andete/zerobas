#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M9: catch the first transfer into the page-0 inter-slot helper region
($0039-$0054) and name the caller.

§8.68 left a runaway whose pushes are at PC=$4251 (int_h) with value $0052. Stock's
page 0 holds a slot-select helper at $003B-$0054 (e.g. $0052 = `out ($A8),a; ret`);
ours leaves it $FF (lay_page0_env installs only the 6 JP vectors + int_h). So a
`call $0052` runs $FF=RST38 -> int_h storm on ours. This arms a condition that fires
the first time PC enters [$0039,$0054], and dumps a ring of the preceding PCs + regs
+ the return address on the stack — naming the caller and confirming the derail.
Run on stock too: there the helper runs normally and returns.

    python3 probes/disk/disk_probe_dosboot_pghelper.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_pghelper.py --dos-disk /tmp/dos.dsk --stock
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, lo: int, hi: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::ring {{}}
debug set_condition {{1}} {{
  set pc [reg PC]
  lappend ::ring [format "%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    $pc [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
  if {{[llength $::ring] > 16}} {{ set ::ring [lrange $::ring end-15 end] }}
  if {{$pc >= {lo} && $pc <= {hi}}} {{
    set sp [reg SP]
    set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
    set f [open {{{out}}} w]
    puts $f [format "FIRST PC in \\[%04X,%04X\\]: %04X  return-on-stack=%04X" {lo} {hi} $pc $ret]
    puts $f "-- preceding ring (oldest first) --"
    foreach e $::ring {{ puts $f $e }}
    close $f
    exit
  }}
}}
after time 40 {{ if {{![file exists {{{out}}}]}} {{ set f [open {{{out}}} w]; puts $f "NEVER entered region"; close $f; exit }} }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        if not os.path.exists(out):
            sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit("no capture")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--lo", type=lambda s: int(s, 0), default=0x0039)
    ap.add_argument("--hi", type=lambda s: int(s, 0), default=0x0054)
    ap.add_argument("--timeout", type=float, default=160.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== first entry into page-0 helper [{args.lo:04X},{args.hi:04X}] on {machine} ===")
    for ln in run(machine, work, args.lo, args.hi, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
