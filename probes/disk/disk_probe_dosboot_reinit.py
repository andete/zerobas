#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box diagnosis: with the kernel correctly placed (§8.24), the boot
LOADS MSX-DOS but re-runs its resident init repeatedly (the BDOS vector is
re-published ~6x) instead of reaching A>. This probe pins the warm-boot spin to its
cause (§8.25).

FINDING (run default = Tier-1, --stock = genuine CF-3300 oracle):
  Right after the kernel publishes its BDOS vector ($0005=JP $D606) at PC $D7C8, it
  does `CALL $50A9` -- a continuation routine in PAGE 1. On the STOCK, $50A9 holds
  real MSXDOS.SYS loader code (`80 00 22 3d f2 af 32 47 ...`) and the boot proceeds
  to A> (the vector is published ONCE). On TIER-1, $50A9 is ALL ZEROS: the call
  NOP-slides ($50A9, $50AA, $50AB, ... linearly) into a crash, MSX-DOS warm-boots,
  re-runs its init, and loops (the vector is re-published ~6x).

  ppi $A8 = $FF on BOTH. NOTE: the page-1 INTERPRETATION below was WRONG -- see §8.26
  (disk_probe_dosboot_50a9.py), which re-root-caused this: at the CALL the page-1
  sub-slot is the DISK ROM (3-1), not RAM, and $50A9 is a fixed DISK-ROM ENTRY at ROM
  offset $10A9 that the kernel calls. The stock ROM implements it; ours leaves $10A9
  as $00 padding -> the call slides into zeros -> crash. MSXDOS.SYS is 2432 B (page-0
  only), so it is NOT unloaded file data. This probe still correctly MEASURES the spin
  and the zeros-vs-code at $50A9; only the cause attribution moved to §8.26.

  [SUPERSEDED framing, kept for the record:] "the defect is CONTENT: MSXDOS.SYS's
  page-1 portion was never written to RAM during the DOS-boot load."

WHAT IT MEASURES (black-box):
  * publications of the BDOS vector ($0006 writes) over the settle = the spin count;
  * at the 2nd publication: kernel regs, ppi $A8, the `CALL nnnn` opcode at $D7CB,
    and a dump of the call target -- zeros (Tier-1) vs real code (stock).

CLEAN-ROOM. Breakpoint at the kernel's publish site + RAM/register reads. No ROM or
MSXDOS.SYS code is disassembled; we read the call-TARGET bytes only to show present
(stock) vs absent (Tier-1) -- a memory-content observation, not a code analysis.

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_reinit.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_reinit.py --stock --dos-disk ~/Documents/msx/msx/disks/test.dsk
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

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
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

PUBLISH_PC = 0xD7CB        # just after the kernel writes $0005 = JP <base> (§8.24)
BDOS_BASE_CELL = 0x0006    # re-published each MSXDOS resident-init = spin counter


def run(machine: str, dsk: str, which_pub: int, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::pub 0
set ::reinit 0
set ::done 0
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
debug set_watchpoint write_mem {{0x{BDOS_BASE_CELL:04X} 0x{BDOS_BASE_CELL:04X}}} {{}} {{ incr ::reinit }}
debug set_bp 0x{PUBLISH_PC:04X} {{}} {{
  incr ::pub
  if {{$::pub == {which_pub} && !$::done}} {{
    set ::done 1
    set op [__hex 0x{PUBLISH_PC:04X} 3]
    # decode CALL nnnn (cd lo hi) target
    set tgt 0
    if {{[string range $op 0 1] eq "cd"}} {{
      scan [string range $op 2 3] %x lo; scan [string range $op 4 5] %x hi
      set tgt [expr {{$hi*256 + $lo}}]
    }}
    set ::cap_op $op
    set ::cap_tgt $tgt
    set ::cap_regs "HL=[format %04X [reg HL]] DE=[format %04X [reg DE]] SP=[format %04X [reg SP]] A=[format %02X [reg A]]"
    set ::cap_ppi [format %02X [debug read {{ioports}} 0xA8]]
    set ::cap_tgtmem [__hex $tgt 16]
  }}
}}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "publications=$::pub"
  puts $f "reinit_writes=$::reinit"
  puts $f "pc=[format %04X [reg PC]]"
  if {{[info exists ::cap_op]}} {{
    puts $f "publish_pc={PUBLISH_PC:04X}"
    puts $f "opcode=$::cap_op"
    puts $f "call_target=[format %04X $::cap_tgt]"
    puts $f "regs=$::cap_regs"
    puts $f "ppi_a8=$::cap_ppi"
    puts $f "target_mem=$::cap_tgtmem"
  }} else {{
    puts $f "no_publication_captured=1"
  }}
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
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
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    os.unlink(out)
    os.unlink(tcl_path)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true",
                    help="run on the genuine CF-3300 oracle (publishes once) instead of Tier-1")
    ap.add_argument("--settle", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    machine = STOCK_MACHINE if args.stock else TIER1_MACHINE
    # the stock publishes ONCE (clean boot); Tier-1 re-publishes (spin) -- grab the
    # 1st on stock, the 2nd on Tier-1 (a steady-state spin cycle).
    which_pub = 1 if args.stock else 2

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(machine, tmp, which_pub, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {machine}")
    print(f"BDOS-vector publications : {d.get('publications')}   "
          f"($0006 re-init writes: {d.get('reinit_writes')})")
    print(f"  (stock boots = publishes ONCE; >1 = warm-boot spin)\n")
    if d.get("no_publication_captured"):
        print(f"no kernel publication captured (settle PC ${d.get('pc')}).")
        return 1

    tgt = d.get("call_target", "????")
    mem = d.get("target_mem", "")
    print(f"at publish site $D7CB: opcode {d.get('opcode')}  ->  CALL ${tgt}")
    print(f"  kernel regs : {d.get('regs')}   ppi $A8 = ${d.get('ppi_a8')}")
    print(f"  ${tgt} mem   : {mem}")
    zeros = mem and set(mem) <= {"0"}
    print()
    if zeros:
        print(f"CRASH CAUSE: the kernel's continuation at ${tgt} (page 1) is ZEROS --")
        print(f"  MSXDOS.SYS's page-1 loader was never stored to RAM. CALL ${tgt} NOP-slides")
        print(f"  into a crash -> warm-boot spin. (Compare --stock: real code at ${tgt}.)")
    else:
        print(f"${tgt} holds code -- the continuation is present (clean boot path).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
