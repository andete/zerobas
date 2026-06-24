#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.5 ownership probe: who writes the $F365 page-3 work-area jump table?

The §8.57 differential showed the kernel CALLs through $F368/$F36B/... and stock
dispatches to distinct hiRAM routines ($DF57/$DF59/$DF70) while ours dispatches to
a single RET stub. To decide whether WE must install those routines or whether
MSXDOS.SYS owns the table, watch every write into $F365-$F373 and log the writing
PC. A disk-ROM PC ($4000-$7FFF) => the disk ROM owns it (our job to reimplement);
a hiRAM PC ($C000+) => MSXDOS.SYS owns it. Result (stock): all writers are disk-ROM
(plus an early page-0 relocation stub) -- no hiRAM writer -- so the $DFxx bodies are
disk-ROM-installed resident routines we reimplement from contract.

Black-box: watch memory writes + read back the byte; no disassembly.

    python3 probes/disk/disk_probe_dosboot_watchwa.py --dos-disk /tmp/dos.dsk          # ours
    python3 probes/disk/disk_probe_dosboot_watchwa.py --dos-disk /tmp/dos.dsk --stock  # oracle
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


def region(pc: int) -> str:
    if pc < 0x4000:
        return "page0"
    if pc < 0x8000:
        return "disk-ROM"
    if pc < 0xC000:
        return "page2"
    return "hiRAM"


def run(machine: str, dsk: str, lo: int, hi: int, settle: float, timeout: float) -> list[tuple[int, int]]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::hits {{}}
debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{
  lappend ::hits [format "%04X %04X" [reg PC] $::wp_last_address]
}}
after time {settle:.1f} {{
  set f [open {{{out}}} w]
  puts $f [join $::hits "\\n"]
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
    rows = []
    for ln in open(out).read().splitlines():
        if not ln.strip():
            continue
        pc, addr = ln.split()
        rows.append((int(pc, 16), int(addr, 16)))
    os.unlink(out)
    os.unlink(tcl_path)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--lo", type=lambda s: int(s, 0), default=0xF365)
    ap.add_argument("--hi", type=lambda s: int(s, 0), default=0xF373)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    rows = run(machine, args.dos_disk, args.lo, args.hi, args.settle, args.timeout)
    print(f"=== writes to {args.lo:04X}-{args.hi:04X} on {machine} ({len(rows)} writes) ===")
    from collections import Counter
    pcs = Counter(pc for pc, _ in rows)
    print("  -- writer PCs (by region) --")
    for pc, c in sorted(pcs.items()):
        print(f"   PC={pc:04X} [{region(pc):8}] x{c}")
    for pc, addr in rows:
        print(f"   PC={pc:04X} -> {addr:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
