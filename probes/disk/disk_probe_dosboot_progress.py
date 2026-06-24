#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.4 progress probe: how far does the boot get toward A> on zerobas-disk?

The single metric that says a milestone advanced the boot. Runs OUR zerobas-disk
ROM (Tier-1 machine National_CF-3300_ZEROBASDISK) on the DOS oracle disk and
reports:
  * reached_0100 — did COMMAND.COM ever start (PC hit $0100)? + its entry regs;
  * end_pc       — where the CPU is after settling (spin detector);
  * screen       — decoded SCREEN-0/1 text (does "A>" / "MSX-DOS" / "BASIC" show?).

Baseline (k_47B2 stubbed): expect reached_0100=NO and end_pc in the $4462/$544E
spin (§8.40). After M5.4: expect reached_0100=YES (COMMAND.COM at $0200).

Black-box: reads PC/regs/VRAM only.

    python3 probes/disk/disk_probe_dosboot_progress.py --dos-disk /tmp/dos-oracle.dsk
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
ZEROBAS_MACHINE = "National_CF-3300_ZEROBASDISK"


def decode_msx(b: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b)


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    scr0 = tempfile.mktemp(suffix=".bin")
    scr1 = tempfile.mktemp(suffix=".bin")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none

debug set_bp 0x0100 {{}} {{
  if {{![info exists ::r100]}} {{
    set ::r100 [format "AF=%04X BC=%04X DE=%04X HL=%04X SP=%04X" \\
      [reg AF] [reg BC] [reg DE] [reg HL] [reg SP]]
  }}
}}

after time {settle:.1f} {{
  set f [open {{{out}}} w]
  if {{[info exists ::r100]}} {{
    puts $f "reached_0100 YES $::r100"
  }} else {{
    puts $f "reached_0100 NO"
  }}
  puts $f [format "end_pc %04X" [reg PC]]
  close $f
  set d [debug read_block VRAM 0x0000 960]
  set g [open {{{scr0}}} wb]; puts -nonewline $g $d; close $g
  set d [debug read_block VRAM 0x1800 768]
  set g [open {{{scr1}}} wb]; puts -nonewline $g $d; close $g
  exit
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
        sys.exit(f"no capture (machine '{machine}' installed? run: make machines-oracle)")
    res = {"lines": open(out).read().splitlines()}
    for key, path in (("scr0", scr0), ("scr1", scr1)):
        res[key] = open(path, "rb").read() if os.path.exists(path) else b""
    for p in (out, scr0, scr1, tcl_path):
        if os.path.exists(p):
            os.unlink(p)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=ZEROBAS_MACHINE)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== boot progress ({args.machine}) ===")
    res = run(args.machine, args.dos_disk, args.settle, args.timeout)
    for ln in res["lines"]:
        print(" ", ln)
    for tag, key, width in (("SCREEN0", "scr0", 40), ("SCREEN1", "scr1", 32)):
        txt = decode_msx(res[key])
        rows = [txt[i:i + width] for i in range(0, len(txt), width)]
        nonblank = [r for r in rows if r.strip(".")]
        if nonblank:
            print(f"  -- {tag} text --")
            for r in nonblank[:24]:
                print("   |" + r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
