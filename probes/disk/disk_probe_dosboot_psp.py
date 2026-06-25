#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Dump the PSP + COMMAND.COM prologue at the SP-setup instruction ($0326).

§8.72: spdrop showed SP is corrupted to $0000 by the instruction at $0326, with
HL=$0000 the line before — the CP/M/MSX-DOS transient-program prologue
`ld hl,(0006) ; ld sp,hl`. If PSP word $0006 (the BDOS entry = top of TPA) is
$0000 because our loader never set it, SP becomes $0000 and COMMAND.COM is dead.
This dumps PSP $0000-$001F and the prologue bytes $02E0-$032F the first time PC
reaches $0326. Run on both machines and diff: the cell ours leaves zero that
stock fills is the unmet Interface-A loader contract.

Black-box: a register-guarded memory snapshot at a landmark PC. No disassembly of
our ROM; the COMMAND.COM bytes are read only to identify which input cell differs.

    python3 probes/disk/disk_probe_dosboot_psp.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_psp.py --dos-disk /tmp/dos.dsk --stock
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


def run(machine: str, dsk: str, at: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
proc row {{a n}} {{
  set s [format "%04X:" $a]
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format " %02X" [debug read memory [expr {{($a+$i)&0xFFFF}}]]]
  }}
  return $s
}}
debug set_bp 0x{at:04X} {{1}} {{
  set f [open {{{out}}} w]
  catch {{
    puts $f [format "HIT %04X  SP=%04X HL=%04X DE=%04X BC=%04X AF=%04X" \\
      [reg PC] [reg SP] [reg HL] [reg DE] [reg BC] [reg AF]]
    puts $f "-- PSP --"
    puts $f [row 0x0000 16]
    puts $f [row 0x0010 16]
    puts $f "-- prologue 02E0-032F --"
    for {{set a 0x02E0}} {{$a < 0x0330}} {{incr a 16}} {{ puts $f [row $a 16] }}
  }} err
  if {{$err ne ""}} {{ puts $f "TCL-ERROR: $err" }}
  close $f
  exit
}}
after time 30 {{ set f [open {{{out}}} w]; puts $f "NO-HIT"; close $f; exit }}
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
    ap.add_argument("--at", type=lambda s: int(s, 0), default=0x0326)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== PSP + prologue at {args.at:#06x} on {machine} ===")
    for ln in run(machine, work, args.at, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
