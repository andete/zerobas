#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Scope scan 5 (definitive): the COMMAND.COM-phase footprint, $D821 -> A> idle.

Scans 1+4 split the phase at the false $D824 boundary; this merges them into one
authoritative coverage map of the entire remaining-work phase: from the start of the
COMMAND.COM load ($D821) through to the A> idle keyboard loop. Coverage is gated ON
at $D821 (NOT from reset) on purpose -- a from-reset scan would re-include the
already-built §1-4 init phase, whose disk-ROM code shares regions with this phase, so
it could not separate done-work from remaining-work. Gating at $D821 isolates exactly
the scope (a) must build.

Stop is auto-detected: when COMMAND.COM's idle loop ($0B90-$0D8F, §8.51) has been hit
past a threshold, the shell has reached A> and is waiting for the keyboard -> dump.

Black-box: PC histogram (16-byte bins, PC >= $0100), addresses + counts only, never
disassembles. Output is the merged executed ranges with per-region byte totals -- the
sizing for M5.2 (high-RAM kernel) and M5.6..N (disk-ROM cluster).

    python3 probes/disk/disk_probe_dosboot_phasecov.py --dos-disk /tmp/dos-oracle.dsk
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
SPAN_CALL = 0xD821
IDLE_LO, IDLE_HI = 0x0B9, 0x0D8     # bins of COMMAND.COM idle loop $0B90-$0D8F


def run(machine: str, dsk: str, idle_thresh: int, cap: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::active 0
set ::n 0
set ::idle 0

proc dump {{reason}} {{
  set f [open {{{out}}} w]
  puts $f "stop $reason instrs $::n"
  if {{[info exists ::cov]}} {{
    foreach b [lsort -integer [array names ::cov]] {{
      puts $f [format "%04X %d" [expr {{$b << 4}}] $::cov($b)]
    }}
  }}
  close $f
  exit
}}

debug set_bp 0x{SPAN_CALL:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
  debug set_condition {{1}} {{
    set p [reg PC]
    if {{$p >= 0x0100}} {{
      set b [expr {{$p >> 4}}]
      if {{[info exists ::cov($b)]}} {{ incr ::cov($b) }} else {{ set ::cov($b) 1 }}
      if {{$b >= {IDLE_LO} && $b <= {IDLE_HI}}} {{
        incr ::idle
        if {{$::idle >= {idle_thresh}}} {{ dump idle }}
      }}
    }}
    incr ::n
    if {{$::n >= {cap}}} {{ dump cap }}
  }}
}}

after time 240 {{ if {{$::active}} {{ dump timeout-active }} else {{ dump never-D821 }} }}
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
    ap.add_argument("--idle-thresh", type=int, default=150_000)
    ap.add_argument("--cap", type=int, default=8_000_000)
    ap.add_argument("--gap", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    bins: list[tuple[int, int]] = []
    for ln in run(args.machine, args.dos_disk, args.idle_thresh, args.cap, args.timeout):
        parts = ln.split()
        if len(parts) == 2 and len(parts[0]) == 4:
            try:
                bins.append((int(parts[0], 16), int(parts[1])))
                continue
            except ValueError:
                pass
        print(ln)
    if not bins:
        return 0
    bins.sort()
    # merge to ranges, excluding COMMAND.COM's idle loop from sizing (proprietary)
    ranges = []
    start, last, hits, peak = bins[0][0], bins[0][0], bins[0][1], bins[0][1]
    for addr, cnt in bins[1:]:
        if addr - last <= args.gap * 16:
            last, hits, peak = addr, hits + cnt, max(peak, cnt)
        else:
            ranges.append((start, last, hits, peak))
            start, last, hits, peak = addr, addr, cnt, cnt
    ranges.append((start, last, hits, peak))
    print(f"=== COMMAND.COM-phase footprint, $D821 -> A> idle ({args.machine}) ===")
    print(f"    {len(bins)} bins, {len(ranges)} merged ranges\n")
    cur = None
    tot: dict[str, list[int]] = {}
    for s, e, hits, peak in ranges:
        reg = region(s)
        if reg != cur:
            print(f"  -- {reg} --")
            cur = reg
        span = e - s + 16
        t = tot.setdefault(reg, [0, 0, 0])
        t[0] += span
        t[1] += hits
        t[2] += 1
        print(f"  {s:04X}-{e+15:04X}  {span:5d}B  {hits:10d} hits  peak {peak}")
    print("\n  region totals (the sizing):")
    for r, (b, h, n) in tot.items():
        note = "  (proprietary: load+run, NOT our code)" if r.startswith("TPA") else ""
        print(f"    {r:18} {b:6d}B  {n:3d} ranges  {h:11d} hits{note}")
    ours = sum(v[0] for k, v in tot.items() if not k.startswith("TPA"))
    print(f"\n  => code WE must build (disk-ROM + high-RAM + page2): {ours} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
