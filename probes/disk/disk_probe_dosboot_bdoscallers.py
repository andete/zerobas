#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Trace WHO calls $0005 (the BDOS vector) across a whole DOS boot — fork-B gate.

Fork B (tier2-bdos-scope.md) re-points the page-0 $0005 BDOS vector to our own
bdos_entry so application BDOS calls dispatch to our implementation. That is only
safe if the relocated MSX-DOS kernel ($D606-$DD0E) does NOT call its own BDOS via
$0005 (it must dispatch internally via $D606/$D831 directly). This probe breaks at
every $0005 and logs the caller's return address + function number, classifying the
caller region. Expected (verified on stock 2026-06-26): every caller is COMMAND.COM
(its transient $C200-$D5FF); zero callers in the kernel range $D606-$DDFF.

    python3 probes/disk/disk_probe_dosboot_bdoscallers.py --dos-disk /tmp/dos.dsk \
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
from collections import Counter

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")


def region(ret: int) -> str:
    if ret < 0x0100:
        return "page0"
    if 0x0100 <= ret < 0x0600:
        return "MSXDOS.SYS-low"
    if 0xC200 <= ret < 0xD600:
        return "COMMAND.COM-transient"
    if 0xD600 <= ret < 0xDE00:
        return "KERNEL($D6-DD)"
    return "other"


def run(machine: str, dsk: str, settle: float, maxhits: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::n 0
debug set_bp 0x0005 {{}} {{
  incr ::n
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  set f [open {{{out}}} a]
  puts $f [format "n=%d C=%02X ret=%04X t=%.4f" $::n [expr {{[reg BC]&0xFF}}] $ret [machine_info time]]
  close $f
  if {{$::n >= {maxhits}}} {{ exit }}
}}
after time {settle} {{ set f [open {{{out}}} a]; puts $f "DONE n=$::n"; close $f; exit }}
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
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--maxhits", type=int, default=200)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== $0005 callers ({args.machine}) ===")
    tally: Counter = Counter()
    for ln in run(args.machine, args.dos_disk, args.settle, args.maxhits, args.timeout):
        if ln.startswith("n="):
            ret = int(ln.split("ret=")[1].split()[0], 16)
            reg = region(ret)
            tally[reg] += 1
            print(f"  {ln}  {reg}")
        else:
            print(f"  {ln}")
    print("CALLER REGION TALLY:", dict(tally))
    if tally.get("KERNEL($D6-DD)", 0) == 0:
        print("GATE: PASS — kernel never calls its own BDOS via $0005 (redirect is safe).")
    else:
        print("GATE: FAIL — kernel calls $0005 internally; a redirect would hijack it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
