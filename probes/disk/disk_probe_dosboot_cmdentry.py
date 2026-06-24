#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Characterise the COMMAND.COM entry environment ($0100) on the stock oracle.

The $47B2 kernel entry (spec §5.1) is the COMMAND.COM loader: it reads
COMMAND.COM off the disk, lays out the MSX-DOS page-0 environment, and transfers
to $0100. To reimplement k_47B2 (milestone 4) we need its OUTPUT contract: the
exact machine state the moment control reaches $0100. This probe (black-box, no
disassembly) breaks at the first execution of $0100 and captures:

  * the CPU registers handed to COMMAND.COM;
  * page-0 ($0000-$00FF): the RST vectors, the $0005 BDOS entry (JP + address),
    the default FCBs ($005C/$006C), the command tail / DTA ($0080);
  * a few bytes at $0100 itself (COMMAND.COM's first instruction, to confirm it
    was actually loaded — content only summarised, never disassembled).

Run against the stock oracle:

    python3 probes/disk/disk_probe_dosboot_cmdentry.py --dos-disk /tmp/dos.dsk
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


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none

proc hexdump {{addr n}} {{
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format "%02X " [debug read memory [expr {{($addr + $i) & 0xFFFF}}]]]
  }}
  return $s
}}

debug set_bp 0x0100 {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  puts $f [format "regs AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
  puts $f "page0_0000 [hexdump 0x0000 16]"
  puts $f "page0_0005 [hexdump 0x0005 8]"
  puts $f "page0_005C [hexdump 0x005C 16]"
  puts $f "page0_0080 [hexdump 0x0080 16]"
  puts $f "cmd_0100   [hexdump 0x0100 16]"
  close $f
  exit
}}

after time {settle:.1f} {{
  if {{![info exists ::done]}} {{
    set f [open {{{out}}} w]
    puts $f "NEVER reached 0100 within {settle:.0f}s"
    close $f
    exit
  }}
}}
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
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== COMMAND.COM entry environment at $0100 ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.settle, args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
