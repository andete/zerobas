#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Boundary contract + scope of the COMMAND.COM-loader entry `$47B2` (stock oracle).

Tier-2 §8.40 found that the `$4462`/`$544E` ×24k spin is a *symptom*: the real
first divergence is inside `$47B2`, a shared-kernel entry the relocated kernel
calls once (from `$D821`, returning to `$D824`) during the COMMAND.COM load. This
probe measures `$47B2`'s BOUNDARY (not its internals — black-box, no disassembly):

  * entry register state (what the kernel hands it) at `$D821`;
  * exit register state + flags at the return to `$D824`;
  * how many instructions it runs (effort proxy);
  * which disk-ROM sub-entries it calls (rising edges into `$4000-$7FFF` with
    their callers) — i.e. the entangled shared-kernel cluster it depends on;
  * the copy it performs: min/max of HL (dest) and DE (src) while in its block
    loop (`$4916-$492E`), bracketing what it relocates and how long.

The result tells us the size of the reimplementation (the "scope it precisely
first" decision) without committing to a build. Run against the stock oracle:

    python3 probes/disk/disk_probe_dosboot_47b2.py --dos-disk /tmp/dos.dsk
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

CALL_SITE = 0xD821   # CALL $47B2
RET_SITE = 0xD824    # the instruction after it (where $47B2 returns)
LOOP_LO, LOOP_HI = 0x4916, 0x492E   # the observed block-copy loop body


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::state idle
set ::prev_in 0
set ::icount 0
array set ::subcnt {{}}
array set ::subra {{}}
set ::suborder {{}}
set ::hlmin 0xFFFF
set ::hlmax 0x0000
set ::demin 0xFFFF
set ::demax 0x0000

proc snap {{}} {{
  return [format "AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X" \\
    [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] [reg SP]]
}}

proc finish {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  puts $f "entry [expr {{[info exists ::ent] ? $::ent : {{(never reached $D821)}}}}]"
  puts $f "exit  [expr {{[info exists ::ext] ? $::ext : {{(never returned to $D824)}}}}]"
  puts $f "instr $::icount"
  puts $f "hl_range [format %04X $::hlmin] [format %04X $::hlmax]"
  puts $f "de_range [format %04X $::demin] [format %04X $::demax]"
  puts $f "subentries [llength $::suborder]"
  foreach k $::suborder {{ puts $f "  sub $k cnt=$::subcnt($k) ra=$::subra($k)" }}
  close $f
  exit
}}

# entry: first time we hit the CALL site
debug set_bp 0x{CALL_SITE:04X} {{$::state eq "idle"}} {{
  set ::ent [snap]
  set ::state armed
}}

# exit: return to the instruction after the call
debug set_bp 0x{RET_SITE:04X} {{$::state eq "armed"}} {{
  set ::ext [snap]
  set ::state done
  finish
}}

# while inside $47B2: count instructions, map sub-entries, bracket the copy
debug set_condition {{$::state eq "armed"}} {{
  incr ::icount
  set pc [reg PC]
  set in [expr {{$pc >= 0x4000 && $pc <= 0x7FFF}}]
  if {{$in && !$::prev_in}} {{
    set sp [reg SP]
    set ra [expr {{[debug read memory $sp] | ([debug read memory [expr {{$sp+1}}]] << 8)}}]
    set key [format %04X $pc]
    if {{![info exists ::subcnt($key)]}} {{
      set ::subcnt($key) 0
      set ::subra($key) [format %04X $ra]
      lappend ::suborder $key
    }}
    incr ::subcnt($key)
  }}
  set ::prev_in $in
  if {{$pc >= {LOOP_LO} && $pc <= {LOOP_HI}}} {{
    set hl [reg HL]; set de [reg DE]
    if {{$hl < $::hlmin}} {{ set ::hlmin $hl }}
    if {{$hl > $::hlmax}} {{ set ::hlmax $hl }}
    if {{$de < $::demin}} {{ set ::demin $de }}
    if {{$de > $::demax}} {{ set ::demax $de }}
  }}
}}

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
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--settle", type=float, default=20.0)
    ap.add_argument("--timeout", type=float, default=150.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== $47B2 boundary contract ({args.machine}) ===")
    for ln in run(args.machine, args.dos_disk, args.settle, args.timeout):
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
