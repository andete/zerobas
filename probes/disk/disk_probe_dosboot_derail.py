#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Catch the control transfer that derails PC into the hiRAM kernel gap-sweep.

§8.73: the steady-state hang is runaway execution sweeping LINEARLY through the
partially-built hiRAM kernel ($D7B0-$DC00), PC incrementing by 1 and wrapping,
executing unfilled padding as no-ops (stock instead reaches the A> idle loop at
$0D87). The slide itself is aftermath; the bug is the jump/call/ret that first
lands PC in a gap. This detects the first long run of consecutive PC+1 steps in
hiRAM (no real routine runs N sequential bytes without a branch) and dumps the
ring of preceding instructions — the last real branch is the derail.

Black-box: instruction-stream observation of a booting proprietary DOS; the ring
names an address in OUR relocated kernel, which is own-design (readable) code.

    python3 probes/disk/disk_probe_dosboot_derail.py --dos-disk /tmp/dos.dsk
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


def run(machine: str, dsk: str, lo: int, hi: int, linrun: int, ring: int,
        timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::ring {{}}
set ::prev -1
set ::lin 0
proc step {{}} {{
  set pc [reg PC]
  lappend ::ring [format "%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    $pc [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
  if {{[llength $::ring] > {ring}}} {{ set ::ring [lrange $::ring end-[expr {{{ring}-1}}] end] }}
  # count consecutive +1 steps inside the hiRAM band
  if {{$pc == [expr {{($::prev + 1) & 0xFFFF}}] && $pc >= {lo} && $pc <= {hi}}} {{
    incr ::lin
  }} else {{
    set ::lin 0
  }}
  set ::prev $pc
  if {{$::lin >= {linrun}}} {{
    set f [open {{{out}}} w]
    catch {{
      puts $f [format "LINEAR RUN of %d in %04X-%04X reached at PC=%04X" $::lin {lo} {hi} $pc]
      puts $f "-- ring (oldest first; the branch INTO the slide is near the top) --"
      foreach e $::ring {{ puts $f $e }}
    }} err
    if {{$err ne ""}} {{ puts $f "TCL-ERROR: $err" }}
    close $f
    exit
  }}
}}
debug set_condition {{1}} {{ step }}
after time 40 {{ if {{![file exists {{{out}}}]}} {{ set f [open {{{out}}} w]; puts $f "NO LINEAR RUN seen"; close $f; exit }} }}
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
    ap.add_argument("--lo", type=lambda s: int(s, 0), default=0xD000)
    ap.add_argument("--hi", type=lambda s: int(s, 0), default=0xDFFF)
    ap.add_argument("--linrun", type=int, default=40)
    ap.add_argument("--ring", type=int, default=48)
    ap.add_argument("--timeout", type=float, default=160.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== derail-into-gap detector on {machine} (band {args.lo:04X}-{args.hi:04X}, "
          f"linrun {args.linrun}) ===")
    for ln in run(machine, work, args.lo, args.hi, args.linrun, args.ring, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
