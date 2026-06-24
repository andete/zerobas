#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Scope scan 3: per-entry register contracts (entry + exit) in one run.

§8.48 sized the footprint, §8.49 (edges) mapped the call graph + entry addresses.
This captures the data contract of each entry: the registers on entry (its inputs)
and on the matching return (its outputs), for the canonical page-1 cluster entries
and the high-RAM kernel entries discovered by the edge scan, in a single pass over
the $D821 -> $47B2 -> $D824 span.

Method (black-box; never disassembles): all entry breakpoints are armed at the span
start and torn down at the span end, so kernel-init-phase calls are excluded. On an
entry's FIRST hit it records the entry registers, reads the return address off the
stack, and arms a one-shot return breakpoint (matched on the saved SP) that records
the exit registers. Entries reached by JP (e.g. the $F2xx trampolines) may show no
paired return -- expected, reported as '--'.

    python3 probes/disk/disk_probe_dosboot_contracts.py --dos-disk /tmp/dos-oracle.dsk
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
SPAN_CALL = 0xD821
SPAN_RET = 0xD824
CANON = [0x402D, 0x41FD, 0x4558, 0x46C8, 0x47B2, 0x4919, 0x4935, 0x498C,
         0x49B4, 0x4A39, 0x4B59, 0x4BE5, 0x4C25, 0x4E4B, 0x4EDE, 0x4010,
         0x5FE5, 0x607B, 0x75A5, 0x77B8, 0x782B]
# high-RAM kernel entries discovered by disk_probe_dosboot_edges.py (§8.49)
HIRAM = [0xDDAE, 0xDE54, 0xDE97, 0xDE9B, 0xDF0C, 0xEF95, 0xEF9B,
         0xF252, 0xF26A, 0xF270, 0xF27C, 0xF27F, 0xF282, 0xF285, 0xF288,
         0xF28E, 0xF291, 0xF294, 0xF2A0, 0xF2A3, 0xF365, 0xF38C, 0xF392,
         0xFD9A, 0xFD9F, 0xFDA3]


def run(machine: str, dsk: str, entries: list[int], timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    arm = "\n".join(f"  arm_entry 0x{e:04X}" for e in entries)
    tcl = f"""set throttle off
set renderer none
set ::active 0

proc regsnap {{}} {{
  return [format "AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X" \\
    [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY]]
}}
proc peek16 {{a}} {{
  return [expr {{[debug read memory $a] | ([debug read memory [expr {{($a+1)&0xFFFF}}]] << 8)}}]
}}
proc onexit {{E}} {{
  if {{[info exists ::eout($E)]}} return
  set ::eout($E) [regsnap]
}}
proc onentry {{E}} {{
  if {{[info exists ::ein($E)]}} return
  set ::ein($E) [regsnap]
  set esp [reg SP]
  set ret [peek16 $esp]
  set want [expr {{($esp + 2) & 0xFFFF}}]
  debug set_bp $ret "\\[reg SP\\] == $want" [list onexit $E]
}}
proc arm_entry {{E}} {{
  debug set_bp $E {{}} [list onentry $E]
}}

debug set_bp 0x{SPAN_CALL:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
{arm}
}}

debug set_bp 0x{SPAN_RET:04X} {{}} {{
  if {{!$::active}} return
  set f [open {{{out}}} w]
  foreach E [lsort -integer [array names ::ein]] {{
    set xo "--"
    if {{[info exists ::eout($E)]}} {{ set xo $::eout($E) }}
    puts $f [format "%04X IN  %s" $E $::ein($E)]
    puts $f [format "%04X OUT %s" $E $xo]
  }}
  close $f
  exit
}}

after time 180 {{
  set f [open {{{out}}} w]
  puts $f "NEVER reached span return within 180s"
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
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def region(addr: int) -> str:
    if addr < 0x4000:
        return "TPA"
    if addr < 0x8000:
        return "diskROM"
    if addr < 0xC000:
        return "page2"
    return "hiRAM"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    rows = run(args.machine, args.dos_disk, CANON + HIRAM, args.timeout)
    data: dict[int, dict[str, str]] = {}
    for ln in rows:
        parts = ln.split(None, 2)
        if len(parts) == 3 and parts[1] in ("IN", "OUT"):
            data.setdefault(int(parts[0], 16), {})[parts[1]] = parts[2]
        else:
            print(ln)
    if not data:
        return 0
    print(f"=== per-entry register contracts, COMMAND.COM-load span ({args.machine}) ===")
    print(f"    {len(data)} entries captured\n")
    cur = None
    for e in sorted(data):
        reg = region(e)
        if reg != cur:
            print(f"  -- {reg} --")
            cur = reg
        d = data[e]
        print(f"  {e:04X} IN   {d.get('IN','?')}")
        print(f"       OUT  {d.get('OUT','--')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
