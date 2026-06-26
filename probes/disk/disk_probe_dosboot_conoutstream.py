#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Capture the CONOUT character stream during a full DOS boot — ours vs stock.

$5454 is the disk-ROM CONOUT entry (shared address on ours+stock); A = the char
to emit. On stock, MSXDOS.SYS init drives it with the banner string
("MSX-DOS version 1.03 ... Copyright 1984 by Microsoft"); the review queue reports
ours feeds it a repeating $00/$80 garbage stream. This probe breaks at every $5454
(anchored on the boot) and logs, per hit: the char (A low byte) + a printable
rendering, the caller's return address (top of stack), and the time. The two char
streams side by side show exactly what each machine tries to print and where ours
diverges — the first-visible-output divergence.

    python3 probes/disk/disk_probe_dosboot_conoutstream.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300            # stock reference
    python3 probes/disk/disk_probe_dosboot_conoutstream.py --dos-disk /tmp/dos.dsk \
        --machine National_CF-3300_ZEROBASDISK
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


def run(machine: str, dsk: str, addr: int, settle: float, maxhits: int,
        timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::n 0
debug set_bp {addr:#06x} {{}} {{
  incr ::n
  set af [reg AF]
  set ch [expr {{($af >> 8) & 0xFF}}]
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  set f [open {{{out}}} a]
  puts $f [format "C n=%d ch=%02X ret=%04X HL=%04X DE=%04X t=%.6f" \\
    $::n $ch $ret [reg HL] [reg DE] [machine_info time]]
  close $f
  if {{$::n >= {maxhits}}} {{ exit }}
}}
after time {settle:.1f} {{
  set f [open {{{out}}} a]
  puts $f "DONE-SETTLE hits=$::n"
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
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    lines = open(out).read().splitlines() if os.path.exists(out) else ["(no capture)"]
    if os.path.exists(out):
        os.unlink(out)
    os.unlink(tcl_path)
    return lines


def render(lines: list[str]) -> None:
    chars = []
    for ln in lines:
        print(ln)
        if ln.startswith("C ") and "ch=" in ln:
            cv = int(ln.split("ch=")[1].split()[0], 16)
            chars.append(cv)
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in chars)
    print(f"--- char stream ({len(chars)}): |{printable}|")
    print(f"--- hex: {' '.join('%02X' % c for c in chars)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", required=True)
    ap.add_argument("--addr", default="0x5454")
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--maxhits", type=int, default=80)
    ap.add_argument("--timeout", type=float, default=220.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== CONOUT stream @ {args.addr} ({args.machine}) ===")
    render(run(args.machine, args.dos_disk, int(args.addr, 16), args.settle,
               args.maxhits, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
