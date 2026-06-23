#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box: the next gap after $50A9 -- the disk RESIDENT WORK AREA
($F100-$F3FF) is unbuilt on Tier-1 (a3 §8.28).

With $50A9 implemented (§8.27) the warm-boot spin is gone and the kernel CONSUMES the
$50A9 return (HL=$F359, DE=IX=$F1AA), but it then derails: the main thread stops and
only the 60 Hz interrupt stays alive (PC idles at $0038 = `JP $41FA` = our int_h, a
NORMAL vector, not a wedge). Cause: the disk ROM's resident work area $F100-$F3FF --
which the genuine disk-ROM INIT fully populates (per-drive DPBs at $F195+, the driver
dispatch region $F100+, the $F24E/$F327 stub tables, the $F34D driver pointers, the
$F368 jump table) -- is almost entirely $FF on Tier-1. The $50A9 return pointers
$F1AA/$F359 therefore point into $FF garbage and the kernel computes a bad address.

This probe dumps $F100-$F3FF at the kernel publish site and reports:
  * the unbuilt ($FF) fraction of the work area;
  * the bytes at the $50A9 return pointers $F1AA / $F359 and the cleared cell $F242;
  * the $0038 interrupt-vector JP target.
Run --stock to see the fully-built reference work area (the build spec for §8.28).

WHAT IT MEASURES (black-box): a memory snapshot of the disk work area at one
breakpoint. No ROM or kernel code is disassembled; the populated-vs-$FF differential
defines what our INIT must build, in our own clean-room code (as DRVTBL/$F368 already
are, §8.22/§8.18).

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_workarea.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_workarea.py --stock --dos-disk ~/Documents/msx/msx/disks/test.dsk
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

PUBLISH_PC = 0xD7CB    # the kernel's BDOS-vector publish site (§8.24)
WA_BASE = 0xF100
WA_LEN = 0x300         # $F100-$F3FF


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::pub 0
debug set_bp 0x{PUBLISH_PC:04X} {{}} {{
  incr ::pub
  if {{$::pub == 1}} {{
    binary scan [debug read_block memory 0x{WA_BASE:04X} 0x{WA_LEN:04X}] H* ::wa
    binary scan [debug read_block memory 0x0038 3] H* ::j38
  }}
}}
proc cap {{}} {{
  set f [open {{{out}}} w]
  if {{[info exists ::wa]}} {{
    puts $f "wa=$::wa"
    puts $f "j0038=$::j38"
  }} else {{
    puts $f "no_publication=1"
  }}
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    os.unlink(out)
    os.unlink(tcl_path)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true",
                    help="run on the genuine CF-3300 oracle (the built reference work area)")
    ap.add_argument("--settle", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    machine = STOCK_MACHINE if args.stock else TIER1_MACHINE
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(machine, tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {machine}\n")
    if d.get("no_publication"):
        print("kernel publish site never reached (no boot?).")
        return 1

    wa = bytes.fromhex(d["wa"])
    ff = wa.count(0xFF)
    print(f"disk resident work area $F100-$F3FF at the kernel publish:")
    print(f"  unbuilt ($FF) : {ff}/{len(wa)} bytes ({100*ff//len(wa)}%)")
    print(f"  $0038 vector  : {d.get('j0038')}  "
          f"({'JP $%02X%02X' % (int(d['j0038'][4:6],16), int(d['j0038'][2:4],16))})")
    print()

    def at(addr, n=8):
        o = addr - WA_BASE
        return wa[o:o+n].hex()
    print("  key cells the kernel reads via the $50A9 return:")
    print(f"    $F195 (drive-A DPB) : {at(0xF195, 19)}")
    print(f"    $F1AA (DE/IX return): {at(0xF1AA)}")
    print(f"    $F359 (HL return)   : {at(0xF359)}")
    print(f"    $F242 ($50A9 clears): {at(0xF242)}")
    print()
    if ff > len(wa) // 2:
        print("GAP (§8.28): the work area is mostly UNBUILT -> the $50A9 return pointers")
        print("  reference $FF garbage -> the kernel derails (main thread dies; only int_h")
        print("  at $0038 stays alive). NEXT: build the resident work area in INIT (DPBs +")
        print("  dispatch/stub tables + driver pointers), as our own clean-room code.")
    else:
        print("work area is populated -- the resident environment is built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
