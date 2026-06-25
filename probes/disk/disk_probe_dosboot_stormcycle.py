#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Capture the *instruction-level cycle* of the $4251 runaway storm.

§8.71 left the runaway diagnosed as aftermath: the stackwatch (a memory-WRITE
watchpoint) sees PC=$4251 (the int_h trampoline = $0038 vector) pushing the
constant return-address $0052, SP trending down -2 each. A write-watchpoint sees
only pushes, never pops, so it cannot tell a balanced-but-derailed loop from a
genuinely leaking one. This probe single-steps and logs EVERY PC for a window
once SP first dips below the healthy floor (~$8F00), so we see the full cycle:
  - int acceptance -> $0038 -> $4251 (jp int_h_body) -> int_h_body instructions
  - whether it RETs (pop, SP+2) back to $0052 and what executes at $0052
  - or whether it never returns (real leak) and where it actually loops.
It also dumps the bytes at $0050-$005F and $07E0-$07FF (the jp $07EC target) so
the interrupted PC can be disassembled by hand, deciding no-ack vs derail.

Black-box: single-step trace + memory read of a booting proprietary DOS. No
disassembly of our ROM or of MSXDOS.SYS/COMMAND.COM.

    python3 probes/disk/disk_probe_dosboot_stormcycle.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_stormcycle.py --dos-disk /tmp/dos.dsk --stock
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


def run(machine: str, dsk: str, floor: int, nsteps: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::n 0
set ::seq {{}}

proc hx {{a n}} {{
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format "%02X " [debug read memory [expr {{($a+$i)&0xFFFF}}]]]
  }}
  return $s
}}

proc step {{}} {{
  if {{!$::armed}} {{
    # arm the instruction log the first time SP dips below the healthy floor
    if {{[reg SP] < {floor}}} {{ set ::armed 1 }} else {{ return }}
  }}
  set pc [reg PC]
  lappend ::seq [format "%04X AF=%04X BC=%04X DE=%04X HL=%04X SP=%04X" \\
    $pc [reg AF] [reg BC] [reg DE] [reg HL] [reg SP]]
  incr ::n
  if {{$::n >= {nsteps}}} {{ finish }}
}}

proc finish {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  catch {{
    puts $f "-- mem 0050-005F: [hx 0x0050 16]"
    puts $f "-- mem 0038-003F: [hx 0x0038 8]"
    puts $f "-- mem 07E0-07FF: [hx 0x07E0 32]"
    puts $f "-- instruction cycle (every PC, from first SP<{floor:#06x}) --"
    set i 0
    foreach e $::seq {{ puts $f "$i $e"; incr i }}
  }} err
  if {{$err ne ""}} {{ puts $f "TCL-ERROR: $err" }}
  close $f
  exit
}}

debug set_condition {{1}} {{ step }}
after time 40 {{ finish }}
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
    ap.add_argument("--floor", type=lambda s: int(s, 0), default=0x8F00)
    ap.add_argument("--nsteps", type=int, default=120)
    ap.add_argument("--timeout", type=float, default=160.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== storm instruction-cycle on {machine} (floor {args.floor:#06x}) ===")
    for ln in run(machine, work, args.floor, args.nsteps, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
