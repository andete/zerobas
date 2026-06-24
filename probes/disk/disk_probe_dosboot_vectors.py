#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Characterise the page-0 JP vector table k_47B2 lays for COMMAND.COM.

§8.45 found the loader hands COMMAND.COM six page-0 JP vectors into the relocated
kernel band ($000C/$0014/$001C/$0024/$0030/$0038 -> $DDxx/$DExx). The load-bearing
question for the reimplementation plan: does COMMAND.COM (and the loader) reach
those kernel routines *through* the page-0 entry points (which we lay, so we can
redirect them to our own handlers), or does it call the $DDxx/$DExx targets
directly (which would force reproducing the kernel at those exact addresses)?

Black-box: arm a breakpoint at each page-0 vector address, and for every hit record
the caller (the return address on top of stack). Group callers by region so we can
see whether the COMMAND.COM region ($0100-$1FFF, its loaded image) drives the
vectors. Never disassembles COMMAND.COM or the kernel.

    python3 probes/disk/disk_probe_dosboot_vectors.py --dos-disk /tmp/dos-oracle.dsk
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
VECTORS = [0x000C, 0x0014, 0x001C, 0x0024, 0x0030, 0x0038]


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    bp_lines = "\n".join(
        f"""debug set_bp 0x{v:04X} {{}} {{
  set ra [expr {{([debug read memory [reg SP]] | ([debug read memory [expr {{([reg SP]+1)&0xFFFF}}]] << 8)) & 0xFFFF}}]
  set k v{v:04X}_$ra
  if {{[info exists ::seen($k)]}} {{ incr ::seen($k) }} else {{ set ::seen($k) 1 }}
}}"""
        for v in VECTORS
    )
    tcl = f"""set throttle off
set renderer none

{bp_lines}

after time {settle:.1f} {{
  set f [open {{{out}}} w]
  if {{[info exists ::seen]}} {{
    foreach k [lsort [array names ::seen]] {{
      puts $f [format "%s x%d" $k $::seen($k)]
    }}
  }} else {{
    puts $f "NO vector hits within {settle:.0f}s"
  }}
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
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def region(ra: int) -> str:
    if 0x0100 <= ra <= 0x1FFF:
        return "COMMAND.COM"
    if ra < 0x0100:
        return "page0"
    if 0x4000 <= ra <= 0x7FFF:
        return "diskROM"
    if ra >= 0xC000:
        return "hiRAM-kernel"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== page-0 vector callers during boot to A> ({args.machine}) ===")
    rows = run(args.machine, args.dos_disk, args.settle, args.timeout)
    for ln in rows:
        if ln.startswith("v") and "_" in ln:
            vec, rest = ln.split("_", 1)
            ra_s, cnt = rest.split(" ")
            ra = int(ra_s)
            print(f"  {vec}  <- ra={ra:04X} [{region(ra):12}] {cnt}")
        else:
            print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
