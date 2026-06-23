#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box: building the resident work-area routine $F1C9 moves the boot past
the $50A9/$0038 death into the kernel's COMMAND.COM phase -- where Tier-1 takes the
"Insert DOS disk" ERROR path (a3 §8.28).

After $50A9 (§8.27) the kernel CALLs a fixed work-area address $F1C9 -- a resident
$-terminated STRING-PRINT helper the genuine disk ROM relocates into RAM. With $F1C9
absent ($FF) the main thread died at $0038; with our clean-room $F1C9 installed
(build_resident in disk.asm) the kernel executes it and runs on into its COMMAND.COM
load. This probe traps the FIRST post-publish $F1C9 call and decodes the string at DE:

  STOCK : DE -> "\\r\\nCOMMAND ver..."   = loading COMMAND.COM (normal boot to A>)
  TIER-1: DE -> "\\r\\nInsert DOS disk"   = the kernel REJECTED the disk

So the boot now reaches the kernel's disk-validation / COMMAND.COM phase and FAILS
there. The failure is INTERNAL: after publish Tier-1 issues NO real DSKIO/DSKCHG/GETDPB
(only a derailed garbage jump into $4010 with random regs) -- the kernel dispatches its
disk I/O through resident work-area routines ($F100-$F17C, $F327, …) that are still
unbuilt ($FF), derails, and concludes "not a DOS disk". NEXT: build those resident
routines (as $F1C9), re-trapping each, until COMMAND.COM loads.

WHAT IT MEASURES (black-box): the string a known resident routine is asked to print
(an observation of kernel control flow), plus the post-publish disk-entry call counts.
No ROM/kernel code is disassembled; our $F1C9 body is our own (it does not copy the
stock's CALL $53A8 / segment-hook body).

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_resident.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_resident.py --stock --dos-disk ~/Documents/msx/msx/disks/test.dsk
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
RES_PRINT = 0xF1C9     # the resident $-string print routine the kernel CALLs (§8.28)


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::dskio 0
set ::dskchg 0
set ::getdpb 0
debug set_bp 0x{PUBLISH_PC:04X} {{}} {{ set ::armed 1 }}
debug set_bp 0x{RES_PRINT:04X} {{$::armed && ![info exists ::de]}} {{
  set ::de [reg DE]
  set s ""
  for {{set i 0}} {{$i < 24}} {{incr i}} {{
    set b [debug read memory [expr {{$::de + $i}}]]
    if {{$b == 0x24}} break
    append s [format %02x $b]
  }}
  set ::str $s
}}
debug set_bp 0x4010 {{$::armed}} {{ incr ::dskio }}
debug set_bp 0x4013 {{$::armed}} {{ incr ::dskchg }}
debug set_bp 0x4016 {{$::armed}} {{ incr ::getdpb }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  if {{[info exists ::str]}} {{
    puts $f "de=[format %04X $::de]"
    puts $f "str=$::str"
  }} else {{
    puts $f "no_f1c9_call=1"
  }}
  puts $f "post_dskio=$::dskio"
  puts $f "post_dskchg=$::dskchg"
  puts $f "post_getdpb=$::getdpb"
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
                    help="run on the genuine CF-3300 oracle (the reference boot to A>)")
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
    if d.get("no_f1c9_call"):
        print("the resident $F1C9 routine was never CALLed (boot did not reach it).")
        return 1

    raw = d.get("str", "")
    text = bytes.fromhex(raw).decode("latin1") if raw else ""
    printable = text.replace("\r", "\\r").replace("\n", "\\n")
    print(f"first post-publish $F1C9 (resident string-print) call:")
    print(f"  DE = ${d.get('de')}   string = \"{printable}\"")
    print(f"  post-publish disk-entry calls: DSKIO={d.get('post_dskio')} "
          f"DSKCHG={d.get('post_dskchg')} GETDPB={d.get('post_getdpb')}")
    print()
    low = text.lower()
    if "command" in low:
        print("BOOT OK path: the kernel is loading COMMAND.COM (-> A>).")
    elif "insert" in low or "disk" in low:
        print("GAP (§8.28): the kernel took the \"Insert DOS disk\" ERROR path -- it")
        print("  rejected the disk and never issued a real disk read for COMMAND.COM.")
        print("  The disk dispatch goes through resident work-area routines still $FF")
        print("  ($F100-$F17C / $F327). NEXT: build those (as $F1C9), re-trapping each.")
    else:
        print("kernel printed an unrecognised string at $F1C9 (characterise next).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
