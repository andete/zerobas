#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 re-trap: how far does the MSX-DOS-1 boot get on zerobas-disk now that
$4030 is implemented?

CONTEXT (zerobas Tier-2, disk/docs/provider-oracle-scope.md §8.13/§8.14). The
black-box oracle (disk_probe_dosboot_4030.py) showed disk-ROM entry $4030 returns
a fixed work-area pointer, preserving all other registers; we implemented that in
disk.asm (`$4030: ld hl,GETWRK_AREA / ret`). This probe boots a real MSX-DOS-1
disk on the Tier-1 machine (real CF-3300 BIOS + zerobas-disk in slot 3-1) and
measures whether the boot advanced past the pre-fix retry spin.

PRE-FIX BASELINE (§8.10/§8.11): MSXDOS.SYS init CALLed $4030, landed in INIT
garbage, and spun -- repeating Open ($0F) / SetDTA ($1A) / Random-Block-Read
($27) ~10x, reloading itself, never progressing.

WHAT THIS MEASURES (black-box; breakpoint counts + a work-area read-watch + a
VRAM text dump -- no ROM code read):
  * getwrk_4030  -- times our $4030 entry is called
  * bdos_open    -- times the boot Opens a file via our BDOS (a spin shows as many)
  * bdos_rdblk   -- times it block-reads (a spin reloads MSXDOS.SYS repeatedly)
  * workarea_reads / first_workread_pc -- does MSXDOS.SYS actually consume the
    pointer $4030 handed back, and from where
  * pc / vram    -- where the boot settles, and whether a DOS banner / `A>` shows

A collapse of bdos_open/bdos_rdblk from ~9/loop down to ~1-2 means $4030 broke the
spin and the boot advanced -- the win this probe locks in. (Reaching `A>` needs
the work-area LAYOUT MSXDOS.SYS expects at the returned pointer -- the next gap.)

CLEAN-ROOM. Strictly black-box: breakpoints, a RAM read-watch, register/VRAM
reads on the running reference boot. No reference ROM code is read or disassembled.

DISK SAFETY: boots only a /tmp copy of the DOS disk, never the permanent one.

Prerequisites:
  * the Tier-1 machine built from the CURRENT disk.rom:
        python3 tools/install-openmsx-machine.py --real-bios-disk --disk-rom build/disk.rom
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_retrap.py \\
        --dos-disk ~/Documents/msx/msx/disks/test.dsk
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINE = "National_CF-3300_ZEROBASDISK"

GETWRK = 0x4030      # our disk-ROM $4030 entry
BDOS_OPEN = 0x43E0   # bdos_open (per the disk.asm symbol table)
BDOS_RDBLK = 0x4485  # bdos_rdblk ($27)
WORK_BASE = 0xE780   # GETWRK_AREA -- the pointer our $4030 returns
WORK_END = 0xE7FF


def run(dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::g 0; set ::op 0; set ::rb 0; set ::wrk 0; set ::wrkpc ""
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
debug set_bp 0x{GETWRK:04X} {{}} {{ incr ::g }}
debug set_bp 0x{BDOS_OPEN:04X} {{}} {{ incr ::op }}
debug set_bp 0x{BDOS_RDBLK:04X} {{}} {{ incr ::rb }}
debug set_watchpoint read_mem {{0x{WORK_BASE:04X} 0x{WORK_END:04X}}} {{}} {{
  incr ::wrk
  if {{$::wrkpc eq ""}} {{ set ::wrkpc [format %04X [reg PC]] }}
}}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "getwrk_4030=$::g"
  puts $f "bdos_open=$::op"
  puts $f "bdos_rdblk=$::rb"
  puts $f "workarea_reads=$::wrk"
  puts $f "first_workread_pc=$::wrkpc"
  puts $f "pc=[format %04X [reg PC]]"
  puts $f "workarea=[__hex 0x{WORK_BASE:04X} 32]"
  puts $f "vram=[binary encode hex [debug read_block VRAM 0x0000 960]]"
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", MACHINE, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {MACHINE}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={MACHINE})")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    os.unlink(out)
    os.unlink(tcl_path)
    return d


def _vram_text(hexstr: str) -> list:
    """Decode the 40x24 name-table dump to printable rows (drops blank rows)."""
    v = bytes.fromhex(hexstr.strip())
    rows = []
    for i in range(0, min(len(v), 960), 40):
        row = "".join(chr(b) if 32 <= b < 127 else "." for b in v[i:i + 40]).rstrip(".")
        if row.strip(". "):
            rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="real MSX-DOS 1 system disk image")
    ap.add_argument("--settle", type=float, default=12.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    g = int(d.get("getwrk_4030", "0"))
    op = int(d.get("bdos_open", "0"))
    rb = int(d.get("bdos_rdblk", "0"))
    wrk = int(d.get("workarea_reads", "0"))

    print(f"machine : {MACHINE}\n")
    print(f"  $4030 (getwrk) calls : {g}")
    print(f"  bdos_open  calls     : {op}   (pre-fix spin was ~9)")
    print(f"  bdos_rdblk calls     : {rb}   (pre-fix spin reloaded MSXDOS.SYS repeatedly)")
    print(f"  work-area reads      : {wrk}  (first from PC ${d.get('first_workread_pc')})")
    print(f"  work-area[$E780..]   : {d.get('workarea')}")
    print(f"  settle PC            : ${d.get('pc')}")
    rows = _vram_text(d.get("vram", ""))
    banner = any("MSX-DOS" in r or "A>" in r.upper() for r in rows)
    print(f"  screen banner / A>   : {'YES' if banner else 'no (not at prompt yet)'}")

    print()
    advanced = (g >= 1 and op <= 4 and rb <= 3 and wrk > 0)
    if banner:
        print("REACHED DOS: a DOS banner/prompt is on screen -- $4030 path complete.")
        return 0
    if advanced:
        print("PROGRESS: $4030 is called and consumed (work area read); the Open/RdBlk")
        print("spin collapsed -> the boot advanced past the pre-fix retry loop.")
        print(f"Next gap: the work-area LAYOUT MSXDOS.SYS expects at $E780 (settles at "
              f"${d.get('pc')}). Characterize which offsets it reads + the values.")
        return 0
    print("NO ADVANCE: still spinning (open/rdblk high) or $4030 not consumed.")
    print("  Rebuild the Tier-1 machine from the current disk.rom and retry.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
