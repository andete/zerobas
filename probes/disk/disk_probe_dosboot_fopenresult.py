#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Capture the result of COMMAND.COM's startup FOPEN ($0F) — ours vs stock.

The BDOS-sequence differential localised the first divergence to COMMAND.COM's
2nd BDOS call: FOPEN (function $0F) on the FCB at $D62F (identical entry state on
both machines), after which ours and stock branch to different code. So our FOPEN
returns a different result. This probe arms at COMMAND.COM's $0100, finds the
FOPEN call (C==0F at $0005), and captures:

  * the FCB at the DE pointer BEFORE the call (drive + filename + ext) — which file;
  * the result AFTER the call: A (00=ok / FF=not-found in MSX-DOS 1), and the FCB's
    first 16 bytes (FOPEN fills in record size, extent, etc. on success).

Comparing the two tells us whether ours mis-reports found/not-found, or fills the
FCB wrong. Black-box: never disassembles the kernel/BDOS; reads memory + A only.

    python3 probes/disk/disk_probe_dosboot_fopenresult.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300            # stock reference
    python3 probes/disk/disk_probe_dosboot_fopenresult.py --dos-disk /tmp/dos.dsk \
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


def run(machine: str, dsk: str, which: int, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::nopen 0
set ::pending 0
proc hx {{addr n}} {{
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format "%02X " [debug read memory [expr {{($addr + $i) & 0xFFFF}}]]]
  }}
  return $s
}}
proc asc {{addr n}} {{
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    set b [debug read memory [expr {{($addr + $i) & 0xFFFF}}]]
    if {{$b >= 32 && $b < 127}} {{ append s [format "%c" $b] }} else {{ append s "." }}
  }}
  return $s
}}
debug set_bp 0x0100 {{}} {{
  if {{[debug read memory 0x0102] == 0x05}} {{ set ::armed 1 }}
}}
debug set_bp 0x0005 {{}} {{
  if {{!$::armed}} return
  if {{([reg BC] & 0xFF) != 0x0F}} return
  incr ::nopen
  if {{$::nopen != {which}}} return
  set de [reg DE]
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  set f [open {{{out}}} a]
  puts $f [format "FOPEN-IN  nopen=%d DE=%04X ret=%04X" $::nopen $de $ret]
  puts $f [format "  FCB.drive=%02X  name=|%s|  hx=%s" [debug read memory $de] [asc [expr {{$de+1}}] 11] [hx [expr {{$de+1}}] 11]]
  close $f
  set ::pending $ret
  set ::fcbde $de
  debug set_bp $ret {{[info exists ::pending] && $::pending != 0}} {{
    set f [open {{{out}}} a]
    puts $f [format "FOPEN-OUT A=%02X  FCB16=%s" [expr {{([reg AF]>>8)&0xFF}}] [hx $::fcbde 16]]
    close $f
    set ::pending 0
    exit
  }}
}}
after time {settle:.1f} {{
  set f [open {{{out}}} a]
  puts $f "DONE-SETTLE armed=$::armed nopen=$::nopen"
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
    ap.add_argument("--which", type=int, default=1, help="which FOPEN (1=first)")
    ap.add_argument("--settle", type=float, default=35.0)
    ap.add_argument("--timeout", type=float, default=220.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== FOPEN #{args.which} result ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.which, args.settle, args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
