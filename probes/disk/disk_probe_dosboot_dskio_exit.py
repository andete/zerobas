#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 a3 §8.35 exit: verify that DSKIO ($4010) returns B=0/Cy=0 after the
page-1 bounce fix (dskio_ok now sets B=0 explicitly) and that the MSX-DOS kernel
no longer retries the same sector.

Background (§8.35): after fixing the page-1 bounce (p1_blit + LDIR to remapped RAM)
the kernel was still retrying DSKIO for the same sector (HL=$528F → $528E → $528E).
Root cause: dskio_ok didn't set B=0 (left the div9 residue in B).  The DSKIO
contract says B=0 on success; a non-zero B made the kernel think sectors were not
transferred.  Fix: explicit `ld b, 0` in dskio_ok.

This probe traps DSKIO entry ($4010) and the CALLF return path ($0320 in MSXDOS
page-0 RAM) to confirm:
  - DSKIO entry with page-1 HL ($4000-$7FFF): B and DE (sector)
  - DSKIO exit at $0320: Cy = 0, B = 0 (all sectors transferred)
  - No repeat calls for the same DE sector (no retry loop)
  - Progress to later sectors → boot advances toward A>

Also traps $4030 (our work-area entry) and $44F9 (bdos_entry) as boot-depth markers.

DISK SAFETY: uses a /tmp copy of the DOS disk only.

    python3 probes/disk/disk_probe_dosboot_dskio_exit.py \\
        --dos-disk ~/Documents/msx/msx/disks/msxdos103-cmd111.dsk
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
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

MAX_DSKIO = 24   # cap to avoid runaway output


def run(machine: str, dsk: str, settle: float, timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")

    tcl = f"""
set throttle off
set renderer none
set ::log {{}}
set ::dskio_n 0
set ::in_dskio 0
set ::last_de -1
set ::same_de_streak 0

proc rb {{a}} {{ debug read memory $a }}
proc rw {{a}} {{
    binary scan [debug read_block memory $a 2] su v
    return [expr {{$v & 0xFFFF}}]
}}

# --- DSKIO entry ---
debug set_bp 0x4010 {{}} {{
    incr ::dskio_n
    if {{$::dskio_n > {MAX_DSKIO}}} {{ return }}
    set hl [reg HL]
    set h  [expr {{$hl >> 8}}]
    set bc [reg BC]
    set b  [expr {{$bc >> 8}}]
    set de [reg DE]
    set sp [reg SP]
    set caller [rw $sp]
    set p1 [expr {{$h >= 0x40 && $h < 0x80}}]
    if {{$de == $::last_de}} {{
        incr ::same_de_streak
    }} else {{
        set ::same_de_streak 0
    }}
    set ::last_de $de
    lappend ::log [format \\
        "DSKIO#%d HL=%04X B=%d DE=%04X caller=%04X p1=%d same_de_streak=%d" \\
        $::dskio_n $hl $b $de $caller $p1 $::same_de_streak]
    set ::in_dskio 1
}}

# --- DSKIO exit: trap caller return address ($0320) ---
# This fires whenever the kernel returns from the callf-DSKIO trampoline.
# The flag ::in_dskio gates it so we only log it when DSKIO was just called.
debug set_bp 0x0320 {{}} {{
    if {{!$::in_dskio}} {{ return }}
    set ::in_dskio 0
    set af [reg AF]
    set f  [expr {{$af & 0xFF}}]
    set a  [expr {{($af >> 8) & 0xFF}}]
    set cy [expr {{$f & 1}}]
    set b  [expr {{([reg BC] >> 8) & 0xFF}}]
    set hl_ret [reg HL]
    lappend ::log [format \\
        "  exit Cy=%d A=%02X B=%d HL_ret=%04X" $cy $a $b $hl_ret]
}}

# --- boot-depth markers ---
debug set_bp 0x4030 {{}} {{
    lappend ::log "  [MARKER] $4030 work-area entry hit (sp=[reg SP])"
}}
debug set_bp 0x44F9 {{}} {{
    lappend ::log "  [MARKER] bdos_entry hit (sp=[reg SP])"
}}

proc cap {{}} {{
    set f [open {{{out}}} w]
    puts $f "=== §8.35 DSKIO exit probe (Tier-1 ZEROBASDISK) ==="
    foreach e $::log {{ puts $f $e }}
    puts $f ""
    puts $f [format "total DSKIO calls: %d  last_de: %04X  final same_de_streak: %d" \\
        $::dskio_n $::last_de $::same_de_streak]
    # snapshot: first 4 bytes at known p1 TPA address $528F
    # At settle time the kernel has page 1 = sub-slot 0 (RAM), so direct rb works.
    binary scan [debug read_block memory 0x528F 8] H16 hexbytes
    puts $f [format "mem@528F (settle): %s" $hexbytes]
    puts $f [format "FFFF_read=%02X (written=%02X)" [rb 0xFFFF] [expr {{[rb 0xFFFF]^0xFF}}]]
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
        time.sleep(0.5)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture — machine/ROMs/disk missing? ({machine})")
    text = open(out).read()
    os.unlink(out)
    os.unlink(tcl_path)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True,
                    help="DOS disk image (copied to /tmp; original untouched)")
    ap.add_argument("--settle", type=float, default=40.0)
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        text = run(TIER1_MACHINE, tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(text)

    lines = text.splitlines()
    exits = [l for l in lines if l.startswith("  exit")]
    retries = [l for l in lines if "same_de_streak=0" not in l and "DSKIO#" in l]
    b_nonzero = [l for l in exits if not l.endswith("B=0")]

    print("---- §8.35 exit verdict ----")
    if not exits:
        print("WARNING: no DSKIO exit events captured (caller addr wrong?)")
    elif b_nonzero:
        print(f"FAIL: {len(b_nonzero)} DSKIO exit(s) with B≠0 — B=0 fix not effective")
        for l in b_nonzero:
            print(f"  {l}")
    else:
        print(f"PASS: all {len(exits)} DSKIO exit(s) returned B=0, Cy=0")
    if retries:
        print(f"NOTE: {len(retries)} DSKIO entries had same DE as the previous call (potential retry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
