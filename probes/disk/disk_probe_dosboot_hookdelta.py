#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.8: net memory delta of one work-area hook call (contract, not algorithm).

§8.60 showed stock's $DF57 ($F368 long path) is a ~170-instruction inter-slot
routine that returns register-transparent -- so its whole effect is in memory.
To reimplement it clean-room we need the CONTRACT: which bytes change, from what
to what. This arms when PC first reaches a chosen call site (default $D7B0, the
phase that drives the $DA23 wrong-path loop) with an optional register guard,
snapshots a memory window, runs until the hook returns to a chosen address, snaps
again, and prints the byte-level diff. Black-box: a before/after memory diff, no
disassembly of the routine body.

    python3 probes/disk/disk_probe_dosboot_hookdelta.py --dos-disk /tmp/dos.dsk --stock
    python3 probes/disk/disk_probe_dosboot_hookdelta.py --dos-disk /tmp/dos.dsk          # ours
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


def run(machine: str, dsk: str, arm: int, ret: int, guard: str,
        wins: list[tuple[int, int]], timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    winexpr = " ".join(f"{{0x{lo:04X} 0x{hi:04X}}}" for lo, hi in wins)
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::done 0
set ::wins [list {winexpr}]

proc snap {{}} {{
  set s {{}}
  foreach w $::wins {{
    lassign $w lo hi
    for {{set a $lo}} {{$a <= $hi}} {{incr a}} {{
      lappend s [format "%04X:%02X" $a [debug read memory $a]]
    }}
  }}
  return $s
}}

debug set_bp 0x{arm:04X} {{!$::armed && {guard}}} {{
  set ::armed 1
  set ::before [snap]
  set ::esp [reg SP]
  debug set_bp 0x{ret:04X} {{$::armed && !$::done}} {{
    if {{$::done}} return
    set ::done 1
    set ::after [snap]
    set f [open {{{out}}} w]
    foreach b $::before a $::after {{
      if {{$b ne $a}} {{ puts $f "$b -> $a" }}
    }}
    puts $f "ENTRY AF=[format %04X [reg AF]]"
    close $f
    exit
  }}
}}
after time 30 {{ if {{!$::done}} {{ set f [open {{{out}}} w]; puts $f "NO-RETURN armed=$::armed"; close $f; exit }} }}
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
        sys.exit("no capture")
    txt = open(out).read()
    os.unlink(out)
    os.unlink(tcl_path)
    return txt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--arm", type=lambda s: int(s, 0), default=0xD7B0)
    ap.add_argument("--ret", type=lambda s: int(s, 0), default=0xD7B6)
    ap.add_argument("--guard", default="[reg DE] == 0xDC80",
                    help="tcl expr that must hold at the arm site (default DE==DC80)")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    # work-area windows likely touched: $DC00 area + SLTTBL ($FCC1-$FCC8) + $F340 area
    wins = [(0xDC00, 0xDCFF), (0xFCC0, 0xFCCF), (0xF340, 0xF37F)]
    print(f"=== hook memory delta on {machine}  arm={args.arm:04X} ret={args.ret:04X} "
          f"guard='{args.guard}' ===")
    print(run(machine, args.dos_disk, args.arm, args.ret, args.guard, wins, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
