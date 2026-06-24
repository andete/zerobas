#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Disambiguate the M5.4 baseline: did COMMAND.COM really start, or is $0100 a
crash-walk false positive?

The progress baseline showed PC reaching $0100 with near-COMMAND.COM regs but then
derailing to $F1CE. Two hypotheses: (H1) COMMAND.COM loaded + started (loader works,
blocker is post-$0100); (H2) an early crash walked PC through page-0 RAM, hitting
$0100 transiently. This sets breakpoints at the discriminating addresses on OUR
zerobas-disk machine and records each one's hit count + first-hit regs + caller:

  $D821  MSXDOS.SYS loader does CALL $47B2 (is the loader path even reached?)
  $47B2  our k_47B2 veneer (does MSXDOS.SYS call our stubbed loader?)
  $0100  COMMAND.COM image entry
  $0200  COMMAND.COM's REAL code (the jp $0100 target) -> proves H1 if reached
  $5454  our CONOUT (did DOS try to print?)
  $4462  the §8.40 spin
Black-box: counts + regs only.

    python3 probes/disk/disk_probe_dosboot_path.py --dos-disk /tmp/dos-oracle.dsk
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
ZEROBAS_MACHINE = "National_CF-3300_ZEROBASDISK"
WATCH = [0xD821, 0x47B2, 0x0100, 0x0200, 0x5454, 0x4462, 0x544E]


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    bps = "\n".join(
        f"""debug set_bp 0x{a:04X} {{}} {{
  if {{[info exists ::c{a:04X}]}} {{ incr ::c{a:04X} }} else {{
    set ::c{a:04X} 1
    set ra [expr {{([debug read memory [reg SP]] | ([debug read memory [expr {{([reg SP]+1)&0xFFFF}}]] << 8)) & 0xFFFF}}]
    set ::r{a:04X} [format "regs AF=%04X BC=%04X DE=%04X HL=%04X SP=%04X ra=%04X" \\
      [reg AF] [reg BC] [reg DE] [reg HL] [reg SP] $ra]
  }}
}}"""
        for a in WATCH
    )
    addrlist = " ".join(f"0x{a:04X}" for a in WATCH)
    tcl = f"""set throttle off
set renderer none
{bps}
after time {settle:.1f} {{
  set f [open {{{out}}} w]
  foreach a {{{addrlist}}} {{
    set k [format c%04X $a]
    set r [format r%04X $a]
    if {{[info exists ::$k]}} {{
      puts $f [format "%04X x%d [set ::$r]" $a [set ::$k]]
    }} else {{
      puts $f [format "%04X x0 (never)" $a]
    }}
  }}
  puts $f [format "end_pc %04X" [reg PC]]
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
    if not os.path.exists(out):
        sys.exit(f"no capture (machine '{machine}' installed?)")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=ZEROBAS_MACHINE)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== boot path discriminators ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.settle, args.timeout):
        print(" ", ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
