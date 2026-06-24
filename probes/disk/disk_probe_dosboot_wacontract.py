#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M5.6 per-vector contract probe for the $F368 work-area jump table (§8.57).

The kernel CALLs the seven slots $F368/$F36B/.../$F37A; stock dispatches each to a
distinct resident routine ($DF57/$DF59/$DF70/$F327/$F32C; last two null). To
reimplement those bodies clean-room we need each one's CONTRACT, not its bytes. For
a chosen slot this probe arms on the FIRST CALL through it and records:
  * entry registers (AF BC DE HL IX IY SP) and the return address on the stack,
  * every write into page 3 ($C000-$FFFF) made while the routine runs,
  * exit registers (captured when PC returns to the caller at the entry stack level),
  * total call count over the settle window (to see if the contract is stateful).
Black-box: registers + memory writes only, no disassembly of the routine body.

    python3 probes/disk/disk_probe_dosboot_wacontract.py --dos-disk /tmp/dos.dsk --slot 0xF368 --stock
    python3 probes/disk/disk_probe_dosboot_wacontract.py --dos-disk /tmp/dos.dsk --slot 0xF368   # ours
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
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, slot: int, settle: float, timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::done 0
set ::ncalls 0
set ::entry ""
set ::exit ""
set ::ret 0
set ::esp 0
set ::writes {{}}

proc regs {{}} {{
  return [format "AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
}}

# count every entry to the slot; capture the first call's contract
debug set_bp 0x{slot:04X} {{}} {{
  incr ::ncalls
  if {{!$::armed && !$::done}} {{
    set ::armed 1
    set ::esp [reg SP]
    set ::ret [expr {{[debug read memory $::esp] + 256*[debug read memory [expr {{$::esp+1}}]]}}]
    set ::entry [regs]
    debug set_watchpoint write_mem {{0xC000 0xFFFF}} {{$::armed && !$::done}} {{
      lappend ::writes [format "%04X<-%02X@PC%04X" $::wp_last_address \\
        [debug read memory $::wp_last_address] [reg PC]]
    }}
  }}
}}

# fire when the routine returns to the caller at the entry stack level
debug set_condition {{$::armed && !$::done && [reg PC] == $::ret && [reg SP] == [expr {{$::esp + 2}}]}} {{
  set ::done 1
  set ::exit [regs]
}}

after time {settle:.1f} {{
  set f [open {{{out}}} w]
  puts $f "slot     0x{slot:04X}"
  puts $f "ncalls   $::ncalls"
  puts $f "ret      [format %04X $::ret]"
  puts $f "entry    $::entry"
  puts $f "exit     $::exit"
  puts $f "nwrites  [llength $::writes]"
  puts $f "writes   [join $::writes " "]"
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
    txt = open(out).read()
    os.unlink(out)
    os.unlink(tcl_path)
    return txt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--slot", type=lambda s: int(s, 0), required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== work-area slot 0x{args.slot:04X} contract on {machine} ===")
    print(run(machine, args.dos_disk, args.slot, args.settle, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
