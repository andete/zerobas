#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M8: read the live slot configuration at COMMAND.COM entry, to design a correct
inter-slot CHPUT ($00A2) call for the $5454 CONOUT veneer (§8.67).

Black-box: at the first $0100, dump the documented slot work-area bytes —
EXPTBL[0..3] ($FCC1, the main-ROM slot id + expanded flags), the primary-slot
register $A8, and the page-0 secondary-slot state ($FFFF, read complemented).
That tells us (a) which slot holds the main BIOS ROM (CHPUT), (b) whether it is
expanded, and (c) what page-0 slot we must save and restore around the call.

    python3 probes/disk/disk_probe_dosboot_slotcfg.py --dos-disk /tmp/dos.dsk            # ours
    python3 probes/disk/disk_probe_dosboot_slotcfg.py --dos-disk /tmp/dos.dsk --stock    # oracle
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

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
debug set_bp 0x0100 {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  puts $f [format "EXPTBL  %02X %02X %02X %02X" \\
    [debug read memory 0xFCC1] [debug read memory 0xFCC2] \\
    [debug read memory 0xFCC3] [debug read memory 0xFCC4]]
  puts $f [format "SLTTBL  %02X %02X %02X %02X" \\
    [debug read memory 0xFCC5] [debug read memory 0xFCC6] \\
    [debug read memory 0xFCC7] [debug read memory 0xFCC8]]
  puts $f [format "PSL_A8  %02X" [debug read memory 0xA8 ]]
  puts $f [format "PPI_A8reg present? (port) -> use slot reg byte above"]
  puts $f [format "SSL_FFFF(raw) %02X" [debug read memory 0xFFFF]]
  puts $f [format "CHPUT@00A2 first3 %02X %02X %02X (RAM image; ROM hidden in pg0)" \\
    [debug read memory 0x00A2] [debug read memory 0x00A3] [debug read memory 0x00A4]]
  close $f
  exit
}}
after time {settle:.1f} {{
  if {{![info exists ::done]}} {{ set f [open {{{out}}} w]; puts $f "NEVER 0100"; close $f; exit }}
}}
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
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== slot config at $0100 on {machine} ===")
    for ln in run(machine, work, args.settle, args.timeout):
        print(ln)
    os.unlink(work)
    print("  note: EXPTBL[0]=$FCC1 = main-ROM slot id (bit7=expanded, [3:2]=sub, [1:0]=prim);")
    print("        SLTTBL[3]=$FCC8 mirrors page-? secondary for slot 3 (expanded).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
