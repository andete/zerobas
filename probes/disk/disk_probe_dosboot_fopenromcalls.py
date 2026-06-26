#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Trace the disk-ROM entries the kernel FOPEN invokes — ours vs stock.

The kernel's FOPEN ($0005, fn $0F) for AUTOEXEC.BAT returns $FF (not found) on
stock but $21 on ours — same kernel code, so ours fed it different data from the
disk ROM. This probe brackets exactly that one FOPEN call (arm at COMMAND.COM's
$0100, the Nth fn-$0F BDOS call → start; its return address → stop) and logs every
ENTRY into page 1 ($4000-$7FFF): the disk ROM executes there only when the kernel
maps+calls it, so each entry-transition is a disk-ROM routine the kernel invoked.
Per entry it records the entry PC + A/BC/DE/HL. The kernel is identical on both, so
it calls the same canonical addresses; a divergence in the entry sequence (or in a
veneer's output regs) names the disk-ROM contract that misbehaves.

Black-box: logs PCs/regs only; never disassembles ROM or kernel.

    python3 probes/disk/disk_probe_dosboot_fopenromcalls.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300            # stock reference
    python3 probes/disk/disk_probe_dosboot_fopenromcalls.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300_ZEROBASDISK
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


def run(machine: str, dsk: str, which: int, settle: float, maxlog: int,
        timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::nopen 0
set ::trace 0
set ::inrom 0
set ::n 0
debug set_bp 0x0100 {{}} {{
  if {{[debug read memory 0x0102] == 0x05}} {{ set ::armed 1 }}
}}
debug set_bp 0x0005 {{}} {{
  if {{!$::armed || $::trace}} return
  if {{([reg BC] & 0xFF) != 0x0F}} return
  incr ::nopen
  if {{$::nopen != {which}}} return
  set ::trace 1
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  set f [open {{{out}}} a]
  puts $f [format "FOPEN-START nopen=%d DE=%04X ret=%04X" $::nopen [reg DE] $ret]
  close $f
  debug set_bp $ret {{$::trace}} {{
    set f [open {{{out}}} a]
    puts $f [format "FOPEN-END A=%02X entries=%d" [expr {{([reg AF]>>8)&0xFF}}] $::n]
    close $f
    exit
  }}
}}
debug set_condition {{$::trace}} {{
  set pc [reg PC]
  if {{$pc >= 0x4000 && $pc <= 0x7FFF}} {{
    if {{!$::inrom}} {{
      set ::inrom 1
      incr ::n
      if {{$::n <= {maxlog}}} {{
        set f [open {{{out}}} a]
        puts $f [format "E %d PC=%04X A=%02X BC=%04X DE=%04X HL=%04X" \\
          $::n $pc [expr {{([reg AF]>>8)&0xFF}}] [reg BC] [reg DE] [reg HL]]
        close $f
      }}
    }}
  }} else {{
    set ::inrom 0
  }}
}}
after time {settle:.1f} {{
  set f [open {{{out}}} a]
  puts $f "DONE-SETTLE armed=$::armed nopen=$::nopen trace=$::trace entries=$::n"
  close $f
  exit
}}
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
        sys.exit(f"TIMEOUT running {machine}")
    lines = open(out).read().splitlines() if os.path.exists(out) else ["(no capture)"]
    if os.path.exists(out):
        os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", required=True)
    ap.add_argument("--which", type=int, default=1)
    ap.add_argument("--settle", type=float, default=35.0)
    ap.add_argument("--maxlog", type=int, default=60)
    ap.add_argument("--timeout", type=float, default=240.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== disk-ROM entries during FOPEN #{args.which} ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.which, args.settle, args.maxlog,
                  args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
