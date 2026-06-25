#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.8: dump a memory window the first time PC reaches a landmark.

Ours and stock stay register-identical at every checkpoint (D7B6/D7BA/D7CE) yet
ours later derails into the $DA23 loop -- so the divergence is a STALE work-area
memory cell, not a register. This dumps chosen windows the first time PC hits a
landmark (with an optional register guard so we sample the same logical pass).
Run on both machines and diff the dumps: the differing cells are what ours fails
to populate. Black-box: a memory snapshot at a landmark, no disassembly.

    python3 probes/disk/disk_probe_dosboot_memsnap.py --dos-disk /tmp/dos.dsk --at 0xD7CE --stock
    python3 probes/disk/disk_probe_dosboot_memsnap.py --dos-disk /tmp/dos.dsk --at 0xD7CE
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

# work-area + kernel data regions in play (the $DA23 loop walks $C2xx; DPB/work
# area in $F1xx-$F3xx; $DCxx is the hook's scratch; $D6xx is the kernel core).
WINS = [(0xC200, 0xC2FF), (0xDC00, 0xDCFF), (0xD600, 0xD6FF),
        (0xF190, 0xF3FF), (0xFCC0, 0xFCCF)]


def run(machine: str, dsk: str, at: int, guard: str, nth: int, timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    winexpr = " ".join(f"{{0x{lo:04X} 0x{hi:04X}}}" for lo, hi in WINS)
    tcl = f"""set throttle off
set renderer none
set ::hits 0
set ::wins [list {winexpr}]
debug set_bp 0x{at:04X} {{{guard}}} {{
  incr ::hits
  if {{$::hits >= {nth}}} {{
    set f [open {{{out}}} w]
    foreach w $::wins {{
      lassign $w lo hi
      for {{set a $lo}} {{$a <= $hi}} {{incr a}} {{
        puts $f [format "%04X %02X" $a [debug read memory $a]]
      }}
    }}
    close $f
    exit
  }}
}}
after time 30 {{ set f [open {{{out}}} w]; puts $f "NO-HIT"; close $f; exit }}
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
    ap.add_argument("--at", type=lambda s: int(s, 0), required=True)
    ap.add_argument("--guard", default="1", help="tcl expr that must hold at the landmark")
    ap.add_argument("--nth", type=int, default=1, help="dump on the Nth qualifying hit")
    ap.add_argument("--out", help="write dump to this file (else stdout)")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    txt = run(machine, args.dos_disk, args.at, args.guard, args.nth, args.timeout)
    if args.out:
        open(args.out, "w").write(txt)
        print(f"wrote {args.out} ({len(txt.splitlines())} lines) on {machine}")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
