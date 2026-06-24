#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.5 diagnostic: capture the steady-state spin loop after the k_47B2 loader.

§8.55 left COMMAND.COM stuck: CONOUT $5454 hammered from $0320 (COMMAND.COM) and
$544E from $D88A (kernel), ~14k each. To see whether it's one interleaved cycle and
what it does, this lets the boot settle into the spin then logs a window of
consecutive program counters (addresses only -- black-box, no disassembly). Python
finds the repeating cycle and the regions it spans.

    python3 probes/disk/disk_probe_dosboot_loop.py --dos-disk /tmp/dos-oracle.dsk
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


def run(machine: str, dsk: str, settle: float, n: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
after time {settle:.1f} {{
  set ::trace {{}}
  debug set_condition {{1}} {{
    lappend ::trace [format %04X [reg PC]]
    if {{[llength $::trace] >= {n}}} {{
      set f [open {{{out}}} w]
      puts $f [join $::trace "\\n"]
      close $f
      exit
    }}
  }}
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
        sys.exit("no trace captured")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def region(a: int) -> str:
    if a < 0x4000:
        return "COMMAND.COM"
    if a < 0x8000:
        return "disk-ROM"
    if a < 0xC000:
        return "page2"
    return "hiRAM-kernel"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=ZEROBAS_MACHINE)
    ap.add_argument("--settle", type=float, default=22.0)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    pcs = [int(x, 16) for x in run(args.machine, args.dos_disk, args.settle, args.n, args.timeout)]
    print(f"=== steady-state PC trace ({len(pcs)} instrs) ===")
    from collections import Counter
    uniq = sorted(set(pcs))
    print(f"  distinct PCs: {len(uniq)}   range {min(pcs):04X}-{max(pcs):04X}")
    # region histogram
    rh: Counter = Counter(region(a) for a in pcs)
    print("  -- time by region --")
    for r, c in rh.most_common():
        print(f"   {r:14} {c:5d}  ({100*c/len(pcs):.0f}%)")
    # contiguous region spans actually executed
    spans: dict[str, tuple[int, int]] = {}
    for a in pcs:
        r = region(a)
        lo, hi = spans.get(r, (a, a))
        spans[r] = (min(lo, a), max(hi, a))
    print("  -- executed address span per region --")
    for r, (lo, hi) in spans.items():
        print(f"   {r:14} {lo:04X}-{hi:04X}")
    print("  -- top 12 PCs --")
    for a, c in Counter(pcs).most_common(12):
        print(f"   {a:04X} [{region(a):12}] x{c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
