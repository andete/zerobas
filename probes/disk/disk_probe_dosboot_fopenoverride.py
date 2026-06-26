#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Contract test: force the kernel FOPEN result to stock's, see if COMMAND.COM unblocks.

Pre-implementation validation for the fork-B "intercept FOPEN" idea. Our kernel
FOPEN of AUTOEXEC.BAT returns A=$21 (vs stock A=$FF, AF=$FF45, HL=$00FF); the idea
was that returning the right value fixes COMMAND.COM's branch. This probe overrides
the FOPEN return registers to stock's exact values at the return site ($C24E) and
then logs COMMAND.COM's subsequent BDOS calls — if the override flips the branch to
stock's (STROUT, ret $CBA6), the result is register-conveyed; if it stays on ours'
path (SELDSK, ret $C30A), COMMAND.COM is reading WORK-AREA MEMORY the kernel's full
FOPEN populates, not the return registers.

RESULT (2026-06-26): even AF=$FF45 + HL=$00FF does NOT flip the branch — COMMAND.COM
reads work-area memory, so a register-level FOPEN intercept is insufficient.

Black-box: overrides registers + reads memory; never disassembles COMMAND.COM/kernel.

    python3 probes/disk/disk_probe_dosboot_fopenoverride.py --dos-disk /tmp/dos.dsk
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
OURS = "National_CF-3300_ZEROBASDISK"
BDOS = {0x02: "CONOUT", 0x06: "DIRIO", 0x09: "STROUT", 0x0A: "BUFIN", 0x0E: "SELDSK",
        0x0F: "FOPEN", 0x19: "CURDRV", 0x2A: "SDATE"}


def run(machine: str, dsk: str, af: int, hl: int, settle: float, maxn: int,
        timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::done 0
set ::n 0
debug set_bp 0x0100 {{}} {{ if {{[debug read memory 0x0102]==0x05}} {{ set ::armed 1 }} }}
debug set_bp 0x0005 {{$::armed && !$::done && ([reg BC]&0xFF)==0x0F}} {{
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  debug set_bp $ret {{!$::done}} {{
    reg AF {af}
    reg HL {hl}
    set ::done 1
    set f [open {{{out}}} a]; puts $f [format "OVERRIDE AF:=%04X HL:=%04X at %04X" {af} {hl} [reg PC]]; close $f
  }}
}}
debug set_bp 0x0005 {{$::done}} {{
  incr ::n
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  set f [open {{{out}}} a]
  puts $f [format "B %d C=%02X ret=%04X" $::n [expr {{[reg BC]&0xFF}}] $ret]
  close $f
  if {{$::n >= {maxn}}} {{ exit }}
}}
after time {settle} {{ set f [open {{{out}}} a]; puts $f "DONE"; close $f; exit }}
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
    ap.add_argument("--machine", default=OURS)
    ap.add_argument("--af", type=lambda s: int(s, 16), default=0xFF45,
                    help="AF to force at the FOPEN return (default stock $FF45)")
    ap.add_argument("--hl", type=lambda s: int(s, 16), default=0x00FF)
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--maxn", type=int, default=12)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== FOPEN-return override AF=${args.af:04X} HL=${args.hl:04X} ({args.machine}) ===")
    print("    stock's next call after FOPEN is STROUT ret=$CBA6; ours is SELDSK ret=$C30A")
    for ln in run(args.machine, args.dos_disk, args.af, args.hl, args.settle, args.maxn,
                  args.timeout):
        if ln.startswith("B "):
            fn = int(ln.split("C=")[1].split()[0], 16)
            ln += "  ; " + BDOS.get(fn, "?")
        print(" ", ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
