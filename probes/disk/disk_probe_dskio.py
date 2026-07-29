#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential DSKIO oracle: zerobas-disk vs the National CF-3300 reference.

Reads sectors from the SAME FAT12 image on two machines and compares the
observed results byte-for-byte:

  * the reference  -- openMSX's `National_CF-3300` (its proprietary disk ROM)
  * zerobas-disk   -- our clean-room disk ROM in slot 3-1 (a `*_BASIC_DISK`
                      machine from zerobas-disk's install-openmsx-machine.py)

CLEAN-ROOM DISCIPLINE. The reference disk ROM is used ONLY as a black box. The
probe calls its DSKIO entry at the standard offset $4010 (MSX2 Technical
Handbook, disk ROM interface -- an allowed source) via the BIOS inter-slot call
CALSLT ($001C), and observes ONLY the returned data buffer (which is our own
test image's bytes) and the carry/A result. It never reads, dumps, or
disassembles the reference ROM's code (slot 3-1 $4000-$7FFF is never captured).
That is the sanctioned oracle use: identical inputs in, observed outputs out.

The injected Z80 stub (assembled separately; hex embedded below):

    di
    xor a            ; A=0 drive; xor clears carry => DSKIO read direction
    ld b,1           ; one sector
    ld c,$F9         ; media descriptor (720K)
    ld de,SEC        ; logical sector
    ld hl,BUF        ; transfer buffer (page-3 RAM)
    ld ix,$4010      ; DSKIO entry (standard disk-ROM offset, MSX2 TH)
    ld iy,$8700      ; expanded slot 3-1 (F | ss<<2 | ps)
    call $001C       ; CALSLT
    ...store A + carry, repeat for the next sector...
  done: jr done

Prerequisites:
  * openMSX with the CF-3300 ROMs installed (you provide ROMs you may use;
    this script never fetches them).
  * zerobas-disk's `*_BASIC_DISK` machine installed
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`).
  * the test image `disk/test720.dsk` (`make test-dsk`).

    python3 probes/disk/disk_probe_dskio.py \\
        --dsk /path/to/zerobas-disk/disk/test720.dsk
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
import signal
import subprocess
import shutil
import sys
import time

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

# Stub reads sector 0 -> $C200 and sector 14 -> $C400, storing for each call:
#   $C100 = returned A (sector 0), $C101 = carry (0=ok),
#   $C102 = returned A (sector 14), $C103 = carry.
# Assembled with pasmo (org $C000); `done` self-loop at $C043.
STUB_HEX = ("f3af06010ef91100002100c2dd211040fd210087cd1c003200c13e0030013c3201c1"
            "af06010ef9110e002100c4dd211040fd210087cd1c003202c13e0030013c3203c118fe")
STUB_ADDR = 0xC000
DONE_BP = 0xC043
SECTORS = {"sec0": (0, 0xC200), "sec14": (14, 0xC400)}


def run_machine(machine: str, dsk: str, out: str, boot_secs: float = 8.0,
                timeout: float = 55.0) -> dict:
    """Boot `machine` with `dsk`, inject the stub, capture results to a dict."""
    caps = "\n".join(
        f'  puts $f "{name}=[__hex 0x{buf:04X} 512]"' for name, (_, buf) in SECTORS.items())
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "res=[__hex 0x{0xC100:04X} 4]"
{caps}
  close $f; exit
}}
proc go {{}} {{
  debug write_block memory 0x{STUB_ADDR:04X} [binary format H* {STUB_HEX}]
  reg PC 0x{STUB_ADDR:04X}
  debug set_bp 0x{DONE_BP:04X} {{}} {{ cap }}
}}
after time {boot_secs} {{ go }}
after time {boot_secs + 30} {{ cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none", "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine missing? ROMs absent?)")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dsk", required=True, help="FAT12 test image (.dsk)")
    ap.add_argument("--our-machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    args = ap.parse_args()
    if not args.our_machine:
        sys.exit("no zerobas machine: pass --our-machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    host = open(args.dsk, "rb").read()
    ours = run_machine(args.our_machine, args.dsk, "/tmp/disk_probe_ours.txt")
    ref = run_machine(args.ref_machine, args.dsk, "/tmp/disk_probe_ref.txt")

    ok = True
    print(f"results (A0,cy0,A14,cy14): ours={ours['res']} ref={ref['res']}")
    if ours["res"] != ref["res"]:
        ok = False
        print("  MISMATCH: DSKIO return codes differ")
    for name, (sec, _) in SECTORS.items():
        hexpect = host[sec * 512:sec * 512 + 512].hex()
        o, r = ours[name], ref[name]
        good = (o == r == hexpect)
        ok = ok and good
        print(f"{name:6} sector {sec:3}: ours==ref={o == r} ours==disk={o == hexpect} "
              f"ref==disk={r == hexpect}  {'PASS' if good else 'FAIL'}")
    print("\n" + ("ALL PASS — zerobas-disk DSKIO is byte-identical to the CF-3300 reference"
                  if ok else "FAIL — see mismatches above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
