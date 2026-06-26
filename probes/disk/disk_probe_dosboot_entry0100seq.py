#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Capture the SEQUENCE of $0100 entries during a full DOS boot — ours vs stock.

Structural question (Tier-2, post-$47B2): does our boot run MSXDOS.SYS at $0100
(its init: banner + DOS-env setup) before launching COMMAND.COM, or does it skip
straight to COMMAND.COM? On MSX-DOS 1, $0100 is loaded and executed TWICE:

  * MSXDOS.SYS first  — first instruction `jp $0200` (byte at $0102 == $02);
  * COMMAND.COM second — first instruction `jp $0500` (byte at $0102 == $05).

This probe breaks at every execution of $0100 (anchored on the boot, not a mid-
stream snapshot) and logs, per hit: the $0102 discriminator byte, a few bytes of
$0100 (content only, never disassembled), the entry registers, and the time. The
sequence of $0102 values tells us directly which program ran at $0100 and in what
order — answering whether ours skips the MSXDOS.SYS-init step.

    python3 probes/disk/disk_probe_dosboot_entry0100seq.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300_ZEROBASDISK
    python3 probes/disk/disk_probe_dosboot_entry0100seq.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300
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


def run(machine: str, dsk: str, settle: float, maxhits: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::n 0
proc hx {{addr n}} {{
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format "%02X" [debug read memory [expr {{($addr + $i) & 0xFFFF}}]]]
  }}
  return $s
}}
debug set_bp 0x0100 {{}} {{
  incr ::n
  set f [open {{{out}}} a]
  puts $f [format "HIT n=%d b0102=%02X b0100=%s AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X t=%.6f" \\
    $::n [debug read memory 0x0102] [hx 0x0100 3] \\
    [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP] [machine_info time]]
  close $f
  if {{$::n >= {maxhits}}} {{ exit }}
}}
after time {settle:.1f} {{
  set f [open {{{out}}} a]
  puts $f "DONE-SETTLE hits=$::n"
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
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--maxhits", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=220.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== $0100 entry sequence ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.settle, args.maxhits, args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
