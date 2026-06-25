#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Find the instruction that corrupts SP to ~$0000 (the true runaway onset).

§8.72: the stormcycle probe showed the hang is a tight page-0 loop in COMMAND.COM
running with SP=$0000 — a one-shot stack-pointer corruption, not a gradual leak.
The "$4251 pushing $0052" storm is just interrupts wrapping around $FFFF once SP=0.
This probe keeps a ring of the last N executed instructions (PC + regs) and fires
the first time SP drops below a threshold (default $0200), dumping the ring so the
instruction that zeroed SP — and the caller context — is named. That is the first
real divergence; everything after is aftermath.

Black-box: instruction-stream + register observation of a booting proprietary DOS.
No disassembly of our ROM or of MSXDOS.SYS/COMMAND.COM is required to read this.

    python3 probes/disk/disk_probe_dosboot_spdrop.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_spdrop.py --dos-disk /tmp/dos.dsk --stock
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


def run(machine: str, dsk: str, thresh: int, ring: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::ring {{}}
set ::prevsp 0xFFFF

proc step {{}} {{
  set sp [reg SP]
  lappend ::ring [format "%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    [reg PC] [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] $sp]
  if {{[llength $::ring] > {ring}}} {{ set ::ring [lrange $::ring end-[expr {{{ring}-1}}] end] }}
  # fire on the first DOWNWARD crossing into the danger zone (ignore SP already low at reset)
  if {{$sp < {thresh} && $::prevsp >= {thresh}}} {{
    set f [open {{{out}}} w]
    catch {{
      puts $f [format "SP crossed below {thresh:#06x}: prev=%04X now=%04X" $::prevsp $sp]
      puts $f "-- ring (oldest first; last line is the crossing instr) --"
      foreach e $::ring {{ puts $f $e }}
    }} err
    if {{$err ne ""}} {{ puts $f "TCL-ERROR: $err" }}
    close $f
    exit
  }}
  set ::prevsp $sp
}}

debug set_condition {{1}} {{ step }}
after time 40 {{ if {{![file exists {{{out}}}]}} {{ set f [open {{{out}}} w]; puts $f "SP never crossed below {thresh:#06x}"; close $f; exit }} }}
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
        if not os.path.exists(out):
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
    ap.add_argument("--thresh", type=lambda s: int(s, 0), default=0x0200)
    ap.add_argument("--ring", type=int, default=32)
    ap.add_argument("--timeout", type=float, default=160.0)
    args = ap.parse_args()
    machine = STOCK_MACHINE if args.stock else OURS_MACHINE
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== SP-drop onset on {machine} (thresh {args.thresh:#06x}, ring {args.ring}) ===")
    for ln in run(machine, work, args.thresh, args.ring, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
