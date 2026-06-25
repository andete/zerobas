#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M7: catch the FIRST stack push that descends below the legit DOS stack floor.

§8.66 banked the COMMAND.COM milestone with the proximate failure characterised
(SP ends up at $4250 in the page-1 ROM, stack full of one repeated return address)
but the *first cause* receded: the first interrupt is handled cleanly and
COMMAND.COM runs 4000+ instructions before the corruption appears. This probe takes
the recorded best-untried angle: instead of sampling the corruption's aftermath,
it watches *stack writes* and reports the first pushes that take SP below the
normal $F0xx DOS stack floor — naming the routine (or interrupt) that drives the
descent directly.

Mechanism (black-box, no disassembly): arm a write_mem watchpoint over the whole
region BELOW the legit stack ($4000-$EFFF), filtered to writes where the target
address == current SP (i.e. genuine pushes, not arbitrary stores). The normal DOS
stack lives at $F0xx, so nothing fires until SP first crosses below $F000. For each
captured push we log PC/SP/AF and the written value. The PC pattern is the
discriminator:
  * PC == $0038 (the IM1 vector)  -> interrupt-driven storm; CPU is pushing return
    addresses faster than the handler returns (interrupts never quiesce).
  * PC == a fixed routine address -> a software push loop / unbalanced subroutine.
  * a single huge SP jump          -> a bad `LD SP, nn`.
The SP delta between consecutive pushes (-2 == push cadence; large == LD SP) and the
written value (the repeated return address that fills the stack) pin the mechanism.

    python3 probes/disk/disk_probe_dosboot_stackwatch.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_stackwatch.py --dos-disk /tmp/dos.dsk --stock
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


def run(machine: str, dsk: str, settle: float, floor: int, nevents: int,
        timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    # band = everything below the legit $F0xx stack, down to the page-1 ROM.
    lo, hi = 0x4000, floor - 1
    tcl = f"""set throttle off
set renderer none
set ::ev {{}}
after time {settle:.1f} {{
  debug set_watchpoint write_mem {{{lo:#06x} {hi:#06x}}} {{[reg SP] == $::wp_last_address}} {{
    lappend ::ev [format "%04X %04X %04X %04X %04X" \\
      [reg PC] [reg SP] $::wp_last_address $::wp_last_value [reg AF]]
    if {{[llength $::ev] >= {nevents}}} {{
      set f [open {{{out}}} w]
      puts $f [join $::ev "\\n"]
      close $f
      exit
    }}
  }}
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
        if not os.path.exists(out):
            sys.exit(f"TIMEOUT running {machine} (no descent below {floor:#06x}?)")
    if not os.path.exists(out):
        sys.exit("no stack-descent events captured "
                 f"(SP never dropped below {floor:#06x} within the run)")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--settle", type=float, default=20.0)
    ap.add_argument("--floor", type=lambda s: int(s, 0), default=0xF000,
                    help="legit stack floor; first push below this is captured (default $F000)")
    ap.add_argument("--nevents", type=int, default=80)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    # mutation gotcha: never let openMSX write back to a shared .dsk
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    rows = [r.split() for r in run(machine, work, args.settle, args.floor,
                                   args.nevents, args.timeout)]
    os.unlink(work)
    print(f"=== first {len(rows)} stack pushes below {args.floor:#06x} on {machine} ===")
    print("    PC = instruction doing the push ($0038 => interrupt-driven storm)")
    print("    SP = stack pointer AFTER the push   VAL = value pushed (return addr)")
    print("    idx   PC    SP   ->dSP   VAL    AF")
    prev_sp = None
    pc_counts: dict[str, int] = {}
    val_counts: dict[str, int] = {}
    for i, c in enumerate(rows):
        pc, sp, addr, val, af = c
        spv = int(sp, 16)
        dsp = "" if prev_sp is None else f"{spv - prev_sp:+d}"
        prev_sp = spv
        pc_counts[pc] = pc_counts.get(pc, 0) + 1
        val_counts[val] = val_counts.get(val, 0) + 1
        if i < 40:
            print(f"    {i:3d}  {pc}  {sp}  {dsp:>5}  {val}  {af}")
    print("  -- summary --")
    sp0 = int(rows[0][1], 16)
    spN = int(rows[-1][1], 16)
    print(f"  SP descent: {sp0:#06x} -> {spN:#06x} over {len(rows)} captured pushes "
          f"({sp0 - spN} bytes)")
    top_pc = sorted(pc_counts.items(), key=lambda kv: -kv[1])[:4]
    top_val = sorted(val_counts.items(), key=lambda kv: -kv[1])[:4]
    print("  push-site PCs (count): " + ", ".join(f"{p}×{n}" for p, n in top_pc))
    print("  pushed values (count): " + ", ".join(f"{v}×{n}" for v, n in top_val))
    if all(c[0] == "0038" for c in rows):
        print("  VERDICT: all pushes at PC=$0038 -> INTERRUPT-DRIVEN STORM "
              "(interrupts never quiesce).")
    elif len(pc_counts) == 1:
        print(f"  VERDICT: single push-site {top_pc[0][0]} -> software push loop "
              "/ unbalanced routine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
