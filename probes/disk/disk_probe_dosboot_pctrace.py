#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Trace executed PC from the MSXDOS.SYS entry ($0200), for stock-vs-Tier-1 diff.

Both machines load the IDENTICAL MSXDOS.SYS file to $0100 (JP $0200). So any
divergence in the executed instruction stream is caused purely by differing
DATA/register state, not different code. This probe arms on the FIRST time PC
reaches $0200 and records the next N instruction PCs (+ AF/BC/DE/HL/SP). Run it
on both machines and diff the two lists: the first index where they differ is the
branch where the genuine boot proceeds and ours peels off to warm-boot, and the
logged flags/regs at that point name the input cell responsible.

This is black-box oracle observation (two boots of the same DOS, diff the state),
NOT a disassembly of the disk ROM or of MSXDOS.SYS.

Usage:
    python3 probes/disk/disk_probe_dosboot_pctrace.py --dos-disk /tmp/dos.dsk          # Tier-1
    python3 probes/disk/disk_probe_dosboot_pctrace.py --dos-disk /tmp/dos.dsk --stock  # oracle
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

ENTRY = 0x0200
NSTEPS = 160


def run(machine: str, dsk: str, timeout: float, arm: int, nsteps: int) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::n 0
set ::seq {{}}

proc step {{}} {{
  if {{!$::armed}} return
  set pc [reg PC]
  # annotate a CHPUT ($00A2) console-output call with the character in A
  set note ""
  if {{$pc == 0x00A2}} {{ set note [format " CHPUT=%02X" [expr {{[reg AF] >> 8}}]] }}
  lappend ::seq [format "%04X AF=%04X BC=%04X DE=%04X HL=%04X SP=%04X%s" \\
    $pc [reg AF] [reg BC] [reg DE] [reg HL] [reg SP] $note]
  incr ::n
  if {{$::n >= {nsteps}}} {{ finish }}
}}

proc finish {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  set i 0
  foreach e $::seq {{ puts $f "$i $e"; incr i }}
  close $f
  exit
}}

# Arm exactly once, on the first entry to the --arm address, then log every instruction.
debug set_bp 0x{arm:04X} {{!$::armed}} {{ set ::armed 1 }}
debug set_condition {{1}} {{ step }}
after time 30 {{ finish }}
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
    ap.add_argument("--machine", help="override: trace an arbitrary openMSX machine "
                    "(e.g. a different-vendor real disk ROM for a universality check)")
    ap.add_argument("--arm", type=lambda s: int(s, 0), default=ENTRY,
                    help="address to arm the trace on (default $0200 = MSXDOS.SYS entry)")
    ap.add_argument("--nsteps", type=int, default=NSTEPS)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else TIER1_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    for ln in run(machine, args.dos_disk, args.timeout, args.arm, args.nsteps):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
