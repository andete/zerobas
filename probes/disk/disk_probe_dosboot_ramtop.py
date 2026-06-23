#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box oracle + differential: where does MSX-DOS 1 get the top-of-RAM
value it uses to PLACE its resident kernel? (the §8.24 kernel-placement-lever tool.)

CONTEXT (disk/docs/provider-oracle-scope.md §8.19-8.23). MSXDOS.SYS relocates its
resident kernel to high RAM. On the genuine CF-3300 the BDOS base ($0005 JP target,
== $0006-7 word) lands at $D606; on our Tier-1 boot it lands at $E106 -- exactly
$1000 higher, straight onto our disk-ROM scratch ($E2A0-$E780) -> the §8.19 stack
collision -> the derail. HIMEM ($FC4A, §8.20) and DRVTBL+1 reserved-top (§8.23) were
both RULED OUT as the placement lever. This probe finds the cell MSXDOS-1 actually
reads to derive the kernel base, by trapping the WRITER of the $0005-$0007 BDOS
vector and capturing its register inputs + the candidate source cells at that PC.

WHAT IT MEASURES (black-box):
  * every write into $0005-$0007 (the CP/M BDOS-entry vector) after boot, with the
    writing PC, the full register file at the write, and the value -- the moment the
    kernel base is published;
  * the differential stock-vs-Tier1: same writer PC? then the divergence is in that
    PC's *input* -> we dump the candidate top-of-RAM cells (DRVTBL+1/+3, HIMEM, the
    $4030 work-area pointer, $0006-7 pre-write) at the write instant to see which one
    is $D6xx/$DDxx on the stock and $E1xx/$E7xx on ours.

CLEAN-ROOM. Strictly black-box: a RAM write-watchpoint on $0005-$0007, register +
RAM reads at that instant. We observe which cells MSXDOS.SYS reads/writes and the
register contract; we never read, dump, or disassemble disk-ROM or MSXDOS.SYS code.

DISK SAFETY: boots only a /tmp copy of the DOS disk, never the permanent one.

Prerequisites:
  * openMSX with the genuine National CF-3300 ROMs (you provide them) for the stock
    oracle; the National_CF-3300_ZEROBASDISK machine for --tier1.
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_ramtop.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_ramtop.py --tier1 --dos-disk ~/Documents/msx/msx/disks/test.dsk
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

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

BDOS_VEC = 0x0005   # CP/M-style: $0005 = JP BDOS; $0006-7 = BDOS base = top-of-TPA


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    # Watch the 3-byte BDOS vector. Each write logs PC + the full register file +
    # the value, and a snapshot of the candidate top-of-RAM source cells at that
    # instant. We keep every event (the vector is written a handful of times).
    tcl = f"""set throttle off
set renderer none
set ::ev {{}}
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc snap {{}} {{
  # candidate top-of-RAM / placement sources at the write instant
  set himem   [__hex 0xFC4A 2]
  set drvtbl1 [__hex 0xF349 2]
  set drvtbl3 [__hex 0xF34B 2]
  set wrk     [__hex 0xF1C9 2]
  set bdosv   [__hex 0x0006 2]
  return "himem=$himem drvtbl+1=$drvtbl1 drvtbl+3=$drvtbl3 wrk=$wrk bdos06=$bdosv"
}}
debug set_watchpoint write_mem {{0x{BDOS_VEC:04X} 0x{BDOS_VEC + 2:04X}}} {{}} {{
  set regs "AF=[format %04X [reg AF]] BC=[format %04X [reg BC]] DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] IY=[format %04X [reg IY]] SP=[format %04X [reg SP]]"
  lappend ::ev "w [format %04X $::wp_last_address]=[format %02X $::wp_last_value] @PC=[format %04X [reg PC]] $regs | [snap]"
}}
proc final {{}} {{
  set f [open {{{out}}} w]
  puts $f "events=[llength $::ev]"
  foreach e $::ev {{ puts $f "EV $e" }}
  puts $f "final_bdos=[__hex 0x0005 3]"
  puts $f "final_drvtbl=[__hex 0xF348 16]"
  puts $f "final_himem=[__hex 0xFC4A 2]"
  puts $f "pc=[format %04X [reg PC]]"
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
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
    lines = [l.rstrip("\n") for l in open(out)]
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="real MSX-DOS 1 system disk image")
    ap.add_argument("--settle", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--tier1", action="store_true",
                    help="run on the zerobas-disk Tier-1 machine instead of the stock oracle")
    ap.add_argument("--machine", default=None)
    args = ap.parse_args()

    machine = args.machine or (TIER1_MACHINE if args.tier1 else STOCK_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        lines = run(machine, tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {machine}")
    print(f"watch   : writes to $0005-$0007 (BDOS vector) = kernel-base publication\n")
    for l in lines:
        print(l)
    print("\n(black-box; RAM write-watch + register/RAM reads only -- no ROM/MSXDOS code read.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
