#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional probe: does zerobas's BLOAD disk-filename parser build the right FCB?

This exercises the disk-filename PARSER in basic/bload.asm. BLOAD"A:TEST.BIN"
parses the device string, builds a scratch File Control Block in RAM, then enters
do_disk_bload. We break at do_disk_bload -- a deterministic landmark reached
exactly once the FCB is fully built, just before the real disk read -- and read
the FCB there. Sync on an event, never on time (docs/dev-workflow.md). This runs
on the plain C-BIOS_MSX1_BASIC machine (no disk slot), where do_disk_bload's first
act is to find DISKSLOT_OK=0 and bail to load_error; the FCB is already complete
at the breakpoint, so the parser is fully validated regardless. The end-to-end
disk read (open/header/data/close + ,R) is covered by disk_probe_bload_disk.py on
the combined machine.

The scratch FCB lives at DISK_FCB ($E0DB, 12 bytes; basic/sysvars.inc):
  +0       drive code (CP/M / MSX-DOS convention: 0=default, 1=A, 2=B)
  +1..+11  11-byte 8.3 name field (8 name + 3 ext, space-padded $20, upper-case)

Cases:
  BLOAD"A:TEST.BIN"  -> drive 1 (A), name "TEST    BIN"
  BLOAD"TEST.BIN"    -> drive 1 (A, default), name "TEST    BIN"
  BLOAD"B:HI.TXT"    -> drive 2 (B), name "HI      TXT"

Strictly an observation of zerobas's own scratch RAM after it executes the line;
no ROM is read or disassembled.

Machine. The disk path is PARSE-ONLY pure interpreter code -- it builds an FCB in
RAM and never touches the disk hardware -- so this runs on the plain
C-BIOS_MSX1_BASIC machine (zerobas patched into page 1, no disk slot). The
combined C-BIOS_MSX1_BASIC_DISK machine's extra INIT-scan boot time shifts the
keystroke-injection window and makes typing flaky; the plain machine is reliable
and equally valid for a parse-only test. Either way, reinstall from the current
tree first so the slot-0 zerobas IPS reflects the build under test:
  python3 tools/install-openmsx-machine.py --disk-rom disk.rom

  python3 probes/disk/disk_probe_bload_fcb.py
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
import subprocess
import sys
import tempfile
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")

DISK_FCB = 0xE0DB          # scratch FCB base (basic/sysvars.inc)
FCB_LEN = 12               # drive code (1) + 8.3 name field (11)

# Landmark: do_disk_bload (basic/bload.asm) — reached exactly once the disk path
# has finished building the FCB, just before the placeholder error. Breaking
# here is deterministic (sync on an event, never on time -- docs/dev-workflow.md).
# Address from `pasmo --bin basic/main.asm out.rom syms.txt` (do_disk_bload). If
# bload.asm changes, refresh it (or pass --landmark). Bumped to $5355 when the
# SAVE/BSAVE write handler (basic/save.asm) was added to the include chain ahead
# of program.asm, shifting later symbols upward — a pure address shift, not a
# behaviour change.
DO_DISK_BLOAD = 0x5355

# (typed line, expected drive code, expected 11-byte name field)
CASES = [
    ('bload"a:test.bin"', 1, b"TEST    BIN"),
    ('bload"test.bin"',   1, b"TEST    BIN"),
    ('bload"b:hi.txt"',   2, b"HI      TXT"),
]


def run_case(machine: str, line: str, landmark: int) -> bytes:
    """Type `line` into the zerobas REPL, break at `landmark`, return FCB bytes."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="fcb_probe_")
    os.close(out_fd)
    cmd = [
        sys.executable, OMSX_RUN,
        "--machine", machine,
        # zerobas REPL: reaches the prompt late, and a trailing Enter in the same
        # burst is dropped under `throttle off` -- send the line, then a separate
        # later Enter (mirrors basic_probe_bload.py's REPL path).
        "--type", line, "--type-delay", "8",
        "--type", "\r", "--type-delay", "12",
        # Break at do_disk_bload: deterministic, fires once the FCB is fully built
        # (sync on an event, never on time -- docs/dev-workflow.md).
        "--bp", hex(landmark),
        "--reg", "PC",
        "--mem", f"memory:0x{DISK_FCB:04X}:{FCB_LEN}",
        "--out", out_path,
        "--timeout", "120",
    ]
    rc = subprocess.call(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL)
    if rc != 0:
        if os.path.exists(out_path):
            os.unlink(out_path)
        sys.exit(f"omsx_run failed (rc={rc}) for line {line!r} "
                 f"(landmark 0x{landmark:04X} not hit? refresh do_disk_bload addr)")
    key = f"mem.memory:0x{DISK_FCB:04X}:{FCB_LEN}="
    fcb = None
    for ln in open(out_path):
        ln = ln.strip()
        if ln.startswith(key):
            fcb = bytes.fromhex(ln[len(key):])
    os.unlink(out_path)
    if fcb is None or len(fcb) != FCB_LEN:
        sys.exit(f"no FCB capture for line {line!r}")
    return fcb


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default="C-BIOS_MSX1_BASIC")
    ap.add_argument("--landmark", type=lambda s: int(s, 0), default=DO_DISK_BLOAD,
                    help="do_disk_bload address to break at (default "
                         f"0x{DO_DISK_BLOAD:04X}; refresh from pasmo syms if "
                         "bload.asm moves)")
    args = ap.parse_args()

    ok = True
    for line, exp_drv, exp_name in CASES:
        fcb = run_case(args.machine, line, args.landmark)
        drv = fcb[0]
        name = fcb[1:12]
        drv_ok = drv == exp_drv
        name_ok = name == exp_name
        good = drv_ok and name_ok
        ok = ok and good
        # Render the name field readably (spaces shown as '.')
        shown = "".join(chr(b) if 0x20 < b < 0x7F else "." for b in name)
        print(f"  [{'PASS' if good else 'FAIL'}] {line:<20} "
              f"drive={drv} (expect {exp_drv}) "
              f"name=[{shown}] (expect [{exp_name.decode():s}])")
        if not good:
            print(f"        raw FCB: {fcb.hex()}")

    print("\n" + ("ALL PASS -- BLOAD disk parser builds the correct FCB"
                  if ok else
                  "FAIL -- FCB contents do not match expectation"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
