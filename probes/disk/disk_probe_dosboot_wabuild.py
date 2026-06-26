#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Map HOW stock's disk ROM builds the DOS work area $F100-$F3FF during boot.

Companion to disk_probe_dosboot_wadiff.py (which shows the area is unbuilt on ours).
This write-watches every store into $F100-$F3FF across stock's boot up to the
COMMAND.COM $0100 entry, then reports the LAST writer of each byte (the routine that
sets the value COMMAND.COM finally sees), coalesced into target ranges, plus a
time-phase and writer-PC histogram. Output = the construction map / sized build plan
(see disk/docs/tier2-workarea-map.md §5a): ~96 disk-ROM routines build the area in 4
phases (early clear/default ~3.8s; DPB+resident-code ~6.9s; resident routines + FCB
~10s; final cells ~11.3s).

Black-box: snapshots/watches memory; never disassembles ROM/kernel/COMMAND.COM.

    python3 probes/disk/disk_probe_dosboot_wabuild.py --dos-disk /tmp/dos.dsk
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK = "National_CF-3300"


def run(machine: str, dsk: str, lo: int, hi: int, settle: float, cap: int,
        timeout: float) -> list[tuple[int, int, int, float]]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::n 0
set ::stop 0
debug set_bp 0x0100 {{[debug read memory 0x0102]==0x05}} {{ set ::stop 1; exit }}
debug set_watchpoint write_mem {{{lo:#06x} {hi:#06x}}} {{!$::stop}} {{
  incr ::n
  set f [open {{{out}}} a]
  puts $f [format "%04X %04X %02X %.4f" [reg PC] $::wp_last_address $::wp_last_value [machine_info time]]
  close $f
  if {{$::n >= {cap}}} {{ exit }}
}}
after time {settle} {{ exit }}
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
    ev = []
    if os.path.exists(out):
        for ln in open(out).read().splitlines():
            p = ln.split()
            if len(p) == 4:
                ev.append((int(p[0], 16), int(p[1], 16), int(p[2], 16), float(p[3])))
        os.unlink(out)
    os.unlink(tcl_path)
    return ev


def reg(pc: int) -> str:
    if pc < 0x4000:
        return "BIOS"
    if 0x4000 <= pc < 0x8000:
        return "diskROM"
    if 0xC000 <= pc < 0xD600:
        return "CMD.COM"
    if 0xD600 <= pc < 0xDE00:
        return "KERNEL"
    return "hi/relocd"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK)
    ap.add_argument("--lo", type=lambda s: int(s, 16), default=0xF100)
    ap.add_argument("--hi", type=lambda s: int(s, 16), default=0xF3FF)
    ap.add_argument("--canonical", default=os.path.expanduser(
        "~/Documents/msx/msx/disks/msxdos103-cmd111.dsk"))
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--cap", type=int, default=8000)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    shutil.copy(args.canonical, args.dos_disk)
    ev = run(args.machine, args.dos_disk, args.lo, args.hi, args.settle, args.cap, args.timeout)
    print(f"raw writes captured: {len(ev)}")
    last: dict[int, tuple[int, int, float]] = {}
    for pc, a, v, t in ev:
        last[a] = (pc, v, t)
    addrs = sorted(last)
    print("FINAL writer of each work-area region (value seen at COMMAND.COM entry):")
    print(" target-range       lastPC region    t      sampleVals")
    i = 0
    while i < len(addrs):
        a = addrs[i]
        pc, v, t = last[a]
        vals = [v]
        j = i + 1
        while j < len(addrs) and addrs[j] == addrs[j - 1] + 1 and last[addrs[j]][0] == pc:
            vals.append(last[addrs[j]][1])
            j += 1
        ahi = addrs[j - 1]
        rng = f"${a:04X}-${ahi:04X}" if a != ahi else f"${a:04X}"
        sv = ' '.join('%02X' % x for x in vals[:8]) + (" .." if len(vals) > 8 else "")
        print(f"  {rng:18s} {pc:04X}  {reg(pc):9s} {t:6.3f}  {sv}")
        i = j
    phases: Counter = Counter()
    writers: Counter = Counter()
    for a in addrs:
        pc, v, t = last[a]
        if pc >= 0x4000:
            writers[pc] += 1
        ph = ("1:~3.8 clear" if t < 5 else "2:~6.9 DPB+code" if t < 8
              else "3:~10 MSXDOS" if t < 11 else "4:~11.3 CMD")
        phases[ph] += 1
    print("\nbytes finalised per phase:", dict(sorted(phases.items())))
    print(f"{len(writers)} distinct non-BIOS writer PCs; top: " +
          "  ".join(f"${pc:04X}:{n}" for pc, n in sorted(writers.items(), key=lambda x: -x[1])[:15]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
