#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Diff the DOS work area ($F100-$F3FF) at COMMAND.COM entry — ours vs stock.

The decisive Tier-2 characterisation. COMMAND.COM's startup branch reads $F338
(stock=00, ours=$FF uninitialised); tracing that back showed it is only the first
byte of a much larger gap. This probe snapshots the whole disk-ROM/DOS work area at
the COMMAND.COM $0100 entry on both machines and diffs it, grouping runs and flagging
ours=$FF (uninitialised) regions. Result (2026-06-26): ~460 of 768 bytes differ;
stock holds executable RAM-resident routines ($F100-$F17C, $F327-$F33F), the DPB +
drive table ($F1A8+), the device-name table ($F21C "PRN LST NUL AUX CON"), the
"COMMAND COM" FCB structure ($F2B8), and the DOS pointer block ($F34D-$F37F) — ours
is almost entirely $FF. I.e. stock's disk ROM CONSTRUCTS the DOS work area during
boot; ours does not. That is the disk-ROM-resident shared MSX-DOS-1 kernel.

Black-box: snapshots memory only; never disassembles ROM/kernel/COMMAND.COM.

    python3 probes/disk/disk_probe_dosboot_wadiff.py --dos-disk /tmp/dos.dsk
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
STOCK = "National_CF-3300"
OURS = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, lo: int, hi: int, settle: float, timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
debug set_bp 0x0100 {{[debug read memory 0x0102]==0x05}} {{
  set s ""
  for {{set a {lo}}} {{$a <= {hi}}} {{incr a}} {{ append s [format "%02X" [debug read memory $a]] }}
  set f [open {{{out}}} w]; puts $f $s; close $f
  exit
}}
after time {settle} {{ set f [open {{{out}}} w]; puts $f "NOHIT"; close $f; exit }}
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
    data = open(out).read().strip() if os.path.exists(out) else ""
    if os.path.exists(out):
        os.unlink(out)
    os.unlink(tcl_path)
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--lo", type=lambda s: int(s, 16), default=0xF100)
    ap.add_argument("--hi", type=lambda s: int(s, 16), default=0xF3FF)
    ap.add_argument("--canonical", default=os.path.expanduser(
        "~/Documents/msx/msx/disks/msxdos103-cmd111.dsk"),
        help="pristine disk to copy over --dos-disk before each run (mutation guard)")
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    import shutil
    shutil.copy(args.canonical, args.dos_disk)
    st = run(STOCK, args.dos_disk, args.lo, args.hi, args.settle, args.timeout)
    shutil.copy(args.canonical, args.dos_disk)
    ou = run(OURS, args.dos_disk, args.lo, args.hi, args.settle, args.timeout)
    if "NOHIT" in (st, ou) or not st or not ou:
        sys.exit(f"capture failed (stock={len(st)} ours={len(ou)})")
    sb = bytes.fromhex(st)
    ob = bytes.fromhex(ou)
    diffs = [(args.lo + i, sb[i], ob[i]) for i in range(len(sb)) if sb[i] != ob[i]]
    print(f"work-area ${args.lo:04X}-${args.hi:04X} diff at COMMAND.COM $0100 (stock vs ours)")
    print(f"{len(diffs)} of {len(sb)} bytes differ")
    i = 0
    while i < len(diffs):
        a, s, o = diffs[i]
        rs, ro = [s], [o]
        j = i + 1
        while j < len(diffs) and diffs[j][0] == diffs[j - 1][0] + 1:
            rs.append(diffs[j][1])
            ro.append(diffs[j][2])
            j += 1
        end = diffs[j - 1][0]
        tag = "  <ours=FF (uninit)" if all(x == 0xFF for x in ro) else ""
        print(f"  ${a:04X}-${end:04X}: stock={' '.join('%02X' % x for x in rs)}  "
              f"ours={' '.join('%02X' % x for x in ro)}{tag}")
        i = j
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
