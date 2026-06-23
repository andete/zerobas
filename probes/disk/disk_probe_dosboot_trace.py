#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Gap-A reference trace: how does the *working* MSX-DOS-1 boot reach the sector
driver?

CONTEXT (zerobas Tier-2, disk/disk/docs/provider-oracle-scope.md §8.5). zerobas's own
DOS-boot build runs the MSX2-TH ch.3 boot hand-off (read sector 0 -> $C01E CY=0
-> RAM into page 0 -> page-0 env -> $C01E CY=1) far enough to print "MSX system
version 1.0" and execute relocated code in page-0 RAM -- then **hangs at $1418**
having called **neither** the standard DSKIO ($4010) **nor** our H.PHYD hook
($FFA7) (both breakpoint counts were 0). So the boot locates the sector driver by
some path our page-0 environment did not provide ("gap A").

THE ONE DECISIVE BIT THIS PROBE ANSWERS. Boot the genuine National CF-3300 (its
own BASIC + disk ROMs, which you supply) from a real MSX-DOS 1 system disk and
count how often the standard disk-ROM **DSKIO entry ($4010)** is reached during
boot+settle, plus dump the page-0 vector area once DOS is up.

  * If the working boot DOES hit $4010 -> the driver IS the standard DSKIO; our
    build's failure is that our $4010 was not *reachable* from page-0 RAM (an
    inter-slot/paging gap) -> fix = route the boot's call to our $4010.
  * If it does NOT hit $4010 -> the boot uses a resident driver vector instead;
    our env must install that vector (shape per TH ch.3 -- never the proprietary
    kernel's code).

CLEAN-ROOM. Strictly black-box: we set CPU breakpoints and read RAM on the
reference machine as it runs its own boot. No ROM is read or disassembled; the
page-0 dump records the *shape* of the resident environment (which cells hold
vectors), corroborating §8.1, never the kernel bytes behind those vectors.

DISK SAFETY. openMSX can write back to a mounted image; this probe boots only a
**/tmp copy** of the DOS disk, never the permanent/committed one.

Prerequisites:
  * openMSX with the National CF-3300 system ROMs installed (you provide ROMs you
    may use): cf-3300_basic-bios1.rom + cf-3300_disk.rom in systemroms.
  * A real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_trace.py --dos-disk /path/to/msxdos.dsk
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

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE = "National_CF-3300"

# Standard MSX disk-ROM jump-table entries (offsets from the disk ROM base
# $4000; MSX2 Technical Handbook ch.3 / standard disk interface). These are the
# documented entry points, not anything proprietary.
DSKIO = 0x4010   # physical sector read/write
DSKCHG = 0x4013  # disk-change test
GETDPB = 0x4016  # build drive parameter block
PHYDIO = 0x0144  # BIOS PHYDIO (the documented BIOS-level sector entry)


def run(dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    # Count entries to each documented driver address; dump the page-0 vector
    # area once settled. Counters are cheap (one incr per hit).
    tcl = f"""set throttle off
set renderer none
set ::dskio 0
set ::dskchg 0
set ::getdpb 0
set ::phydio 0
debug set_bp {DSKIO:#06x}  {{}} {{ incr ::dskio }}
debug set_bp {DSKCHG:#06x} {{}} {{ incr ::dskchg }}
debug set_bp {GETDPB:#06x} {{}} {{ incr ::getdpb }}
debug set_bp {PHYDIO:#06x} {{}} {{ incr ::phydio }}
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "dskio_4010=$::dskio"
  puts $f "dskchg_4013=$::dskchg"
  puts $f "getdpb_4016=$::getdpb"
  puts $f "phydio_0144=$::phydio"
  puts $f "pc=[format 0x%04X [reg PC]]"
  puts $f "page0=[__hex 0x0000 64]"
  close $f
  exit
}}
after time {settle:.0f} {{ cap }}
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", required=True, help="real MSX-DOS 1 system disk image")
    ap.add_argument("--settle", type=float, default=10.0, help="emulated seconds before capture")
    ap.add_argument("--timeout", type=float, default=40.0)
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

    print(f"machine        : {MACHINE}")
    print(f"settle PC      : {d.get('pc')}")
    print(f"DSKIO  (0x4010): {d.get('dskio_4010')}")
    print(f"DSKCHG (0x4013): {d.get('dskchg_4013')}")
    print(f"GETDPB (0x4016): {d.get('getdpb_4016')}")
    print(f"PHYDIO (0x0144): {d.get('phydio_0144')}")
    p0 = d.get("page0", "")
    print(f"page0[00..3F]  : {p0}")
    # decode a few documented page-0 cells (shape only)
    if len(p0) >= 0x40 * 2:
        b = bytes.fromhex(p0)
        def w(a): return b[a] | (b[a + 1] << 8)
        print("  $0001-2 (BIOS/driver hook lo) : %02X %02X" % (b[1], b[2]))
        print("  $0005-7 (BDOS jp + addr)      : %02X %04X" % (b[5], w(6)))
        print("  $000C   (vector)              : %02X" % b[0x0C])
        print("  $0030   (RST30/CALLF)         : %02X" % b[0x30])
        print("  $0038   (int vector)          : %02X %04X" % (b[0x38], w(0x39)))

    dskio = int(d.get("dskio_4010", "0"))
    print()
    if dskio > 0:
        print(f"VERDICT: the working boot REACHES standard DSKIO ($4010) {dskio}x ->")
        print("  the driver is standard; our gap is reachability of $4010 from page-0 RAM.")
    else:
        print("VERDICT: the working boot does NOT reach $4010 ->")
        print("  it uses a resident driver vector; our env must install one (TH ch.3 shape).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
