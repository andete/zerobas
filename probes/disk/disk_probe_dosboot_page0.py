#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Capture the COMPLETE page-0 environment k_47B2 hands to COMMAND.COM.

§8.44 (disk_probe_dosboot_cmdentry.py) sampled four 16-byte windows of page 0 at
the $0100 COMMAND.COM entry and flagged that $0005 is NOT a CP/M-style `JP BDOS`
("to be characterised"). To reimplement the $47B2 loader (milestone 4) we need its
full OUTPUT contract, so this probe captures ALL 256 bytes of page 0 ($0000-$00FF)
plus the registers, the moment control first reaches $0100 on the stock oracle.

Black-box: it reads RAM at a breakpoint and never disassembles COMMAND.COM or the
kernel. The $0005 field is reported as raw bytes; if it is a `C3` (JP) we also
note the target address so the BDOS-call path can be characterised — observed,
not inferred from any MS source.

Run against the stock oracle (use the preferred 1.03+COMMAND-1.11 disk):

    python3 probes/disk/disk_probe_dosboot_page0.py \\
        --dos-disk /tmp/dos-oracle.dsk
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

proc hexrow {{addr}} {{
  set s ""
  for {{set i 0}} {{$i < 16}} {{incr i}} {{
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
  for {{set r 0}} {{$r < 256}} {{incr r 16}} {{
    puts $f [format "page0_%04X %s" $r [hexrow $r]]
  }}
  set b5 [debug read memory 0x0005]
  set b6 [debug read memory 0x0006]
  set b7 [debug read memory 0x0007]
  if {{$b5 == 0xC3}} {{
    set tgt [expr {{$b6 | ($b7 << 8)}}]
    puts $f [format "vec0005 JP -> %04X" $tgt]
  }} else {{
    puts $f [format "vec0005 NOT-JP first=%02X (%02X %02X)" $b5 $b6 $b7]
  }}
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
    print(f"=== Full page-0 env at $0100 COMMAND.COM entry ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.settle, args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
