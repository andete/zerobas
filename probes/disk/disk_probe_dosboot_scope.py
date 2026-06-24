#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Scope scan: PC-coverage map of the whole COMMAND.COM-load span.

Under the faithful-relocation model (tier2-kernel-plan.md) we must mirror the
stock's resident high-RAM kernel. To size that job up front instead of discovering
it entry-by-entry, this scan records WHERE execution goes during the bounded
$D821 -> CALL $47B2 -> $D824 window (§8.41: ~371k instructions, the entire
COMMAND.COM load + shell init, with COMMAND.COM itself running at $0100 inside it).

Black-box: it buckets the program counter into 16-byte bins (>= $0100) for every
instruction in the span and reports the executed ranges with hit counts. It records
addresses only — never disassembles COMMAND.COM or the kernel. The per-instruction
condition is installed at $D821 and removed at $D824, so the expensive part runs
only during the span, not the whole boot.

Output regions of interest:
  * page-0 TPA ($0100-...) = COMMAND.COM's executed footprint;
  * disk ROM ($4000-$7FFF) = the page-1 cluster actually exercised;
  * high RAM ($C000-$FFFF) = the relocated kernel band (a) must reproduce.

    python3 probes/disk/disk_probe_dosboot_scope.py --dos-disk /tmp/dos-oracle.dsk
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
SPAN_CALL = 0xD821   # loader: CALL $47B2
SPAN_RET = 0xD824    # return point


def run(machine: str, dsk: str, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::active 0

debug set_bp 0x{SPAN_CALL:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
  set ::cond [debug set_condition {{1}} {{
    set p [reg PC]
    if {{$p >= 0x0100}} {{
      set b [expr {{$p >> 4}}]
      if {{[info exists ::cov($b)]}} {{ incr ::cov($b) }} else {{ set ::cov($b) 1 }}
    }}
  }}]
}}

debug set_bp 0x{SPAN_RET:04X} {{}} {{
  if {{!$::active}} return
  catch {{ debug remove_condition $::cond }}
  set f [open {{{out}}} w]
  if {{[info exists ::cov]}} {{
    foreach b [lsort -integer [array names ::cov]] {{
      puts $f [format "%04X %d" [expr {{$b << 4}}] $::cov($b)]
    }}
  }} else {{
    puts $f "NO coverage captured"
  }}
  close $f
  exit
}}

after time 180 {{
  set f [open {{{out}}} w]
  puts $f "NEVER reached span return $D824 within 180s"
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
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def region(addr: int) -> str:
    if addr < 0x4000:
        return "TPA/COMMAND.COM"
    if addr < 0x8000:
        return "disk-ROM (page1)"
    if addr < 0xC000:
        return "page2"
    return "high-RAM kernel"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--timeout", type=float, default=200.0)
    ap.add_argument("--gap", type=int, default=4,
                    help="merge bins separated by <= gap*16 bytes into one range")
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    rows = run(args.machine, args.dos_disk, args.timeout)
    bins: list[tuple[int, int]] = []
    for ln in rows:
        parts = ln.split()
        if len(parts) == 2 and len(parts[0]) == 4:
            bins.append((int(parts[0], 16), int(parts[1])))
        else:
            print(ln)
    if not bins:
        return 0
    print(f"=== COMMAND.COM-load span PC-coverage map ({args.machine}) ===")
    print(f"    {len(bins)} executed 16-byte bins; merged ranges (gap<= {args.gap*16}B):\n")
    # collapse contiguous bins into ranges
    ranges = []
    start, last, hits, peak, nbins = bins[0][0], bins[0][0], bins[0][1], bins[0][1], 1
    for addr, cnt in bins[1:]:
        if addr - last <= args.gap * 16:
            last, hits, peak, nbins = addr, hits + cnt, max(peak, cnt), nbins + 1
        else:
            ranges.append((start, last, hits, peak, nbins))
            start, last, hits, peak, nbins = addr, addr, cnt, cnt, 1
    ranges.append((start, last, hits, peak, nbins))
    cur = None
    for s, e, hits, peak, nbins in ranges:
        reg = region(s)
        if reg != cur:
            print(f"  -- {reg} --")
            cur = reg
        span = e - s + 16
        print(f"  {s:04X}-{e+15:04X}  {span:5d}B  {nbins:4d} bins  "
              f"{hits:9d} hits  peak {peak}")
    # per-region totals
    print("\n  region totals:")
    tot: dict[str, list[int]] = {}
    for s, e, hits, peak, nbins in ranges:
        r = region(s)
        t = tot.setdefault(r, [0, 0])
        t[0] += (e - s + 16)
        t[1] += hits
    for r, (b, h) in tot.items():
        print(f"    {r:18} {b:6d}B executed   {h:10d} hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
