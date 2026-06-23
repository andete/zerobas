#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box: trace the work-area DISPATCH sequence the kernel runs to load
COMMAND.COM (a3 §8.29, the spec for the next resident routines).

§8.28a established the divergence is BEFORE the first $F1C9 print: on the stock the
first post-publish $F1C9 already prints COMMAND.COM's own "COMMAND version 1.08"
banner (COMMAND.COM is loaded + running by then; DSKIO=6 DSKCHG=2), while Tier-1
prints the kernel's "Insert DOS disk" error (DSKIO=1 garbage). So the COMMAND.COM
LOAD -- the part that fails on Tier-1 -- happens between the $50A9 return and that
first $F1C9. The kernel drives it by CALLing resident CODE entry points inside the
disk work area ($F100-$F3FF) that the disk ROM relocated into RAM.

This probe records, on the working STOCK boot, the ORDERED set of work-area entry
points the kernel jumps into after publish, up to the first real DSKIO ($4010):
each time PC crosses from outside into $F100-$F3FF it logs the target address + the
entry registers. That ordered list is the dispatch contract we must reconstruct
(build_resident currently provides only $F1C9).

Implementation: a global debug condition (armed at publish $D7CB) checks each step
whether PC entered the work-area code window from outside; bounded to N entries and
self-removed once the first $4010 fires or the cap is hit, so the per-instruction
condition only runs over the short COMMAND.COM-load window.

WHAT IT MEASURES (black-box): the addresses the kernel TRANSFERS CONTROL to (an
observation of control flow) + entry registers. No ROM/kernel bytes are
disassembled; we learn WHICH work-area addresses are live and their call contract,
then write our own bodies.

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_dispatch.py --stock --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_dispatch.py        --dos-disk ~/Documents/msx/msx/disks/test.dsk
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

PUBLISH_PC = 0xD7CB
WA_LO = 0xF100
WA_HI = 0xF3FF
MAX_ENTRIES = 48


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::prev_in 0
set ::dskio 0
set ::seq {{}}
set ::done 0

proc record {{}} {{
  set pc [reg PC]
  set in [expr {{$pc >= {WA_LO} && $pc <= {WA_HI}}}]
  if {{$in && !$::prev_in}} {{
    lappend ::seq [format "%04X|AF=%04X|BC=%04X|DE=%04X|HL=%04X|IX=%04X|IY=%04X|SP=%04X" \\
      $pc [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
    if {{[llength $::seq] >= {MAX_ENTRIES}}} {{ finish }}
  }}
  set ::prev_in $in
}}

proc finish {{}} {{
  if {{$::done}} return
  set ::done 1
  if {{[info exists ::cond]}} {{ catch {{ debug remove_condition $::cond }} }}
  set f [open {{{out}}} w]
  puts $f "n=[llength $::seq]"
  puts $f "dskio_before=$::dskio"
  set i 0
  foreach e $::seq {{ puts $f "e$i=$e"; incr i }}
  close $f
  exit
}}

debug set_bp 0x{PUBLISH_PC:04X} {{}} {{
  set ::armed 1
  set ::cond [debug set_condition {{$::armed}} {{ record }}]
}}
debug set_bp 0x4010 {{$::armed}} {{ incr ::dskio ; finish }}
after time {settle:.1f} {{ finish }}
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
                    help="run on the genuine CF-3300 oracle (the reference boot to A>)")
    ap.add_argument("--settle", type=float, default=20.0)
    ap.add_argument("--timeout", type=float, default=90.0)
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

    n = int(d.get("n", "0"))
    print(f"machine : {machine}")
    print(f"work-area code entries (PC crossing into ${WA_LO:04X}-${WA_HI:04X}) "
          f"before first DSKIO: {n}\n")
    if n == 0:
        print("the kernel made NO work-area code calls before DSKIO "
              "(or never reached publish).")
        return 1

    # Tally distinct entry addresses in first-seen order.
    seen: list[str] = []
    for i in range(n):
        e = d.get(f"e{i}", "")
        if not e:
            continue
        addr = e.split("|", 1)[0]
        regs = e.split("|", 1)[1] if "|" in e else ""
        first = addr not in seen
        if first:
            seen.append(addr)
        print(f"  [{i:2}] ${addr}  {regs}{'   <-- new' if first else ''}")
    print(f"\ndistinct work-area entry points (order of first call): "
          f"{', '.join('$' + a for a in seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
