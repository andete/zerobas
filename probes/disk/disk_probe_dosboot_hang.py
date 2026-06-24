#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.7: capture the steady-state hang loop body WITH registers, find the cycle.

§8.59 collapsed the $D87F spin; the boot now settles into a larger ~1105-instr loop
over $D7B0-$DC00 (disk_probe_dosboot_loop.py, n=30000). To pin the exit condition
the kernel polls, this lets the boot settle, logs N consecutive PCs + registers,
then (in Python) finds the repeating cycle, reports whether the registers at the
cycle boundary are IDENTICAL across iterations (a true deterministic hang) or
drifting (a slow convergent loop), and prints one annotated iteration so the
decision branch + the cell it reads can be located. Black-box: register/PC
observation only, no disassembly.

    python3 probes/disk/disk_probe_dosboot_hang.py --dos-disk /tmp/dos.dsk          # ours
    python3 probes/disk/disk_probe_dosboot_hang.py --dos-disk /tmp/dos.dsk --stock  # oracle
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
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, settle: float, n: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
after time {settle:.1f} {{
  set ::trace {{}}
  debug set_condition {{1}} {{
    lappend ::trace [format "%04X %04X %04X %04X %04X %04X %04X %04X" \\
      [reg PC] [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
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


def find_cycle(pcs: list[int]) -> tuple[int, int]:
    """Return (start_index, period) of the first repeating cycle, or (0, 0)."""
    # the loop top is the most frequent PC; period = gap between its occurrences
    from collections import Counter
    top = Counter(pcs).most_common(1)[0][0]
    idxs = [i for i, p in enumerate(pcs) if p == top]
    if len(idxs) < 3:
        return (0, 0)
    period = idxs[1] - idxs[0]
    return (idxs[0], period)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--settle", type=float, default=24.0)
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--iters", type=int, default=1, help="how many full iterations to print")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    rows = run(machine, args.dos_disk, args.settle, args.n, args.timeout)
    cols = [r.split() for r in rows]
    pcs = [int(c[0], 16) for c in cols]
    start, period = find_cycle(pcs)
    print(f"=== steady-state hang loop on {machine} ({len(pcs)} instrs) ===")
    print(f"  distinct PCs: {len(set(pcs))}  range {min(pcs):04X}-{max(pcs):04X}")
    print(f"  loop top PC: {pcs[start]:04X}  period: {period} instrs")
    if period:
        # compare registers at successive loop tops: identical => deterministic hang
        tops = [i for i, p in enumerate(pcs) if p == pcs[start]]
        print("  -- registers at successive loop-top hits (AF BC DE HL IX IY SP) --")
        prev = None
        for k, i in enumerate(tops[:8]):
            regs = " ".join(cols[i][1:])
            same = "  (== prev)" if regs == prev else "  <-- CHANGED" if prev else ""
            print(f"   iter {k}: {regs}{same}")
            prev = regs
        print(f"  -- one annotated iteration ({min(period*args.iters, 1400)} instrs from loop top) --")
        for i in range(start, min(start + period * args.iters, len(cols))):
            c = cols[i]
            print(f"   {c[0]} AF={c[1]} BC={c[2]} DE={c[3]} HL={c[4]} IX={c[5]} IY={c[6]} SP={c[7]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
