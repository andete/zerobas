#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Scope scan 4: coverage AFTER the $D824 span return, to A> idle.

§8.48-8.50 mapped the $D821->$47B2->$D824 load span. This closes the last scope
gap: what runs *after* $D824, as the kernel finishes and COMMAND.COM prints the A>
prompt and enters its keyboard-idle loop. It buckets the PC (>= $0100) for every
instruction from $D824 onward, up to an instruction budget (enough to reach idle),
then classifies each executed range as KNOWN (within the §8.48 load-span footprint)
or NEW (additional scope to mirror). Black-box: addresses + counts only.

    python3 probes/disk/disk_probe_dosboot_tail.py --dos-disk /tmp/dos-oracle.dsk
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
SPAN_RET = 0xD824

# executed footprint of the load span (§8.48) — known scope
KNOWN = [
    (0x0200, 0x02DF), (0x0C30, 0x0D6F), (0x1100, 0x111F), (0x1200, 0x123F),
    (0x4010, 0x402F), (0x41F0, 0x422F), (0x4420, 0x443F), (0x4550, 0x456F),
    (0x46C0, 0x46EF), (0x47B0, 0x47DF), (0x4840, 0x49BF), (0x4A30, 0x4A7F),
    (0x4B20, 0x4C4F), (0x4E40, 0x4EFF), (0x5FA0, 0x609F), (0x6370, 0x637F),
    (0x7490, 0x74DF), (0x7580, 0x75AF), (0x7690, 0x77BF), (0x7820, 0x784F),
    (0x7940, 0x797F),
    (0xDDA0, 0xDDEF), (0xDE50, 0xDF1F), (0xEF90, 0xF05F), (0xF0F0, 0xF17F),
    (0xF250, 0xF2AF), (0xF360, 0xF39F), (0xFD90, 0xFDAF), (0xFFC0, 0xFFDF),
]


def run(machine: str, dsk: str, budget: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::active 0
set ::n 0

proc dump {{}} {{
  set f [open {{{out}}} w]
  if {{[info exists ::cov]}} {{
    puts $f "instrs $::n"
    foreach b [lsort -integer [array names ::cov]] {{
      puts $f [format "%04X %d" [expr {{$b << 4}}] $::cov($b)]
    }}
  }} else {{
    puts $f "NO coverage captured (active=$::active)"
  }}
  close $f
  exit
}}

debug set_bp 0x{SPAN_RET:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
  debug set_condition {{1}} {{
    set p [reg PC]
    if {{$p >= 0x0100}} {{
      set b [expr {{$p >> 4}}]
      if {{[info exists ::cov($b)]}} {{ incr ::cov($b) }} else {{ set ::cov($b) 1 }}
    }}
    incr ::n
    if {{$::n >= {budget}}} {{ dump }}
  }}
}}

after time 90 {{ dump }}
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


def known(addr: int) -> bool:
    return any(s <= addr <= e for s, e in KNOWN)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--budget", type=int, default=3_000_000)
    ap.add_argument("--gap", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    bins: list[tuple[int, int]] = []
    for ln in run(args.machine, args.dos_disk, args.budget, args.timeout):
        parts = ln.split()
        if len(parts) == 2 and len(parts[0]) == 4 and ln[:1] != " ":
            try:
                bins.append((int(parts[0], 16), int(parts[1])))
                continue
            except ValueError:
                pass
        print(ln)
    if not bins:
        return 0
    bins.sort()
    print(f"=== post-$D824 coverage to A> idle ({args.machine}) ===\n")
    ranges = []
    start, last, hits, peak = bins[0][0], bins[0][0], bins[0][1], bins[0][1]
    for addr, cnt in bins[1:]:
        if addr - last <= args.gap * 16:
            last, hits, peak = addr, hits + cnt, max(peak, cnt)
        else:
            ranges.append((start, last, hits, peak))
            start, last, hits, peak = addr, addr, cnt, cnt
    ranges.append((start, last, hits, peak))
    cur = None
    new_ranges = []
    for s, e, hits, peak in ranges:
        reg = region(s)
        if reg != cur:
            print(f"  -- {reg} --")
            cur = reg
        # is the whole range within known scope?
        is_known = all(known(a) for a in range(s, e + 16, 16))
        tag = "KNOWN" if is_known else "** NEW **"
        if not is_known:
            new_ranges.append((s, e))
        print(f"  {s:04X}-{e+15:04X}  {hits:9d} hits  peak {peak:8d}  {tag}")
    print()
    if new_ranges:
        print(f"  {len(new_ranges)} NEW range(s) beyond the load-span footprint:")
        for s, e in new_ranges:
            print(f"    {s:04X}-{e+15:04X} [{region(s)}]")
    else:
        print("  NO new ranges — the post-$D824 tail stays within the §8.48 footprint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
