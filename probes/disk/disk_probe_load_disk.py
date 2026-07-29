#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: LOAD"A:PROG.BAS"[,R] from a real FAT12 disk.

This exercises the disk tokenised-BASIC LOAD path in basic/cload.asm
(`do_load` disk dispatch + `disk_prog_load`) on the combined
C-BIOS_MSX1_BASIC_DISK machine (zerobas-BASIC in slot 0 page 1, zerobas-disk in
slot 3-1) with disk/test720.dsk attached as drive A. The path:

  * non-destructively peek the device string -> "CAS:" is tape, else disk;
  * parse_disk_fcb builds DISK_FCB; parse_close_run consumes the closing quote
    and an optional ,R (setting RUNFLAG);
  * disk_prog_load: cross-slot Set-DTA -> writable page-3 buffer, Open, require
    the leading $FF tokenised-BASIC marker (BASIC_DISK_ID), stream the line-link
    image into the stored-program area at TXTBASE ($8001), close, relink;
  * back in do_load: if ,R, jp run_prog to RUN the freshly loaded program.

PROG.BAS (built by zerobas tools/make_test_dsk.py) is a real on-disk tokenised
BASIC file: a leading $FF marker followed by the in-memory line-link image of:

    10 POKE &HD002,123

So after LOAD"A:PROG.BAS" the relinked program sits at $8001 and, for the ,R
form, RUN executes the single POKE, writing $7B to $D002. We assert:

  (a) LOAD"A:PROG.BAS"     -> the store at $8001 equals the relinked image AND the
                              program did NOT auto-run ($D002 stays the sentinel);
  (b) LOAD"A:PROG.BAS",R   -> the store loaded AND RUN executed ($D002 == $7B).

Strictly black-box: we type a line into the REPL and observe RAM. No ROM is read
or disassembled. Neither case has a clean instruction landmark (the loaded
program is interpreted and returns to the REPL), so we sync on time after the
load (and run) are guaranteed complete.

Prerequisites (CURRENT zerobas tree):
  * python3 tools/install-openmsx-machine.py --disk-rom disk.rom   (slot 0 IPS +
    slot 3-1 disk.rom reflect the build under test);
  * python3 tools/make_test_dsk.py                                 (PROG.BAS);

    python3 probes/disk/disk_probe_load_disk.py
    python3 probes/disk/disk_probe_load_disk.py --machine C-BIOS_MSX1_EU_BASIC_DISK
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
import struct
import subprocess
import shutil
import sys
import time

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
ZEROBAS = os.environ.get(
    "ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# PROG.BAS fixture parameters (must match zerobas tools/make_test_dsk.py).
TXTBASE = 0x8001           # stored-program text base
MARKER_ADDR = 0xD002       # the POKEd landmark address
MARKER_BYTE = 0x7B         # the landmark byte RUN writes
SENTINEL = 0xC4            # pre-poison MARKER_ADDR with this (!= MARKER_BYTE)
POKE_TOKEN = 0x98
HEX_TOKEN = 0x0C
INT1_TOKEN = 0x0F

# Expected relinked store image at TXTBASE. One line `10 POKE &HD002,123`:
#   [link:2 LE][lineno:2 LE][body...00][0000 end-link]
# body = POKE, ' ', &HD002 (HEX_TOKEN + LE), ',', 123 (INT1_TOKEN + byte), 00.
# 123 ($7B) uses the 1-byte INT1 form (NOT &H) so the body holds no embedded $00
# (the streamed line-link reader is not token-aware). This matches the bytes a
# typed-in `10 POKE &HD002,123` crunches to.
_BODY = bytes([POKE_TOKEN, 0x20,
               HEX_TOKEN, MARKER_ADDR & 0xFF, MARKER_ADDR >> 8,
               0x2C,
               INT1_TOKEN, MARKER_BYTE,
               0x00])
_LINE = struct.pack("<H", 0) + struct.pack("<H", 10) + _BODY   # link placeholder
_NEXT = TXTBASE + len(_LINE)                                   # $0000 end-link addr
EXP_IMAGE = (struct.pack("<H", _NEXT) + _LINE[2:]             # relinked link word
             + struct.pack("<H", 0))                          # final $0000 end-link
IMG_LEN = len(EXP_IMAGE)


def _hexproc() -> str:
    return ("proc __hex {a l} { binary scan "
            "[debug read_block memory $a $l] H* h; return $h }\n")


def _run_case(machine: str, out: str, line: str, timeout: float = 90.0) -> dict:
    """Type a LOAD line, poison MARKER, then capture the store image + MARKER on a
    time well after the load (and any run) completes."""
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "image=[__hex 0x{TXTBASE:04X} {IMG_LEN}]"
  puts $f "marker=[__hex 0x{MARKER_ADDR:04X} 1]"
  close $f; exit
}}
after time 5 {{ debug write memory 0x{MARKER_ADDR:04X} 0x{SENTINEL:02X} }}
after time 8  {{ type {{{line}}} }}
after time 11 {{ type "\\r" }}
after time 30 {{ cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", DSK,
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
        sys.exit(f"no capture from {machine} (machine missing? disk absent?)")
    d = {}
    for ln in open(out):
        k, _, v = ln.strip().partition("=")
        d[k] = v
    return d


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    if not os.path.exists(DSK):
        sys.exit(f"missing test image {DSK} (run tools/make_test_dsk.py)")

    ok = True

    # --- (a) plain LOAD (no ,R): loads into the store, does NOT auto-run ------
    d = _run_case(args.machine, "/tmp/disk_load_plain.txt", 'load"a:prog.bas"')
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    norun_ok = marker == SENTINEL
    plain_ok = img_ok and norun_ok
    ok = ok and plain_ok
    print('LOAD"A:PROG.BAS"  (no ,R)')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked line-link image")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if norun_ok else 'FAIL'}] NO auto-run: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect untouched sentinel ${SENTINEL:02X})")

    # --- (b) LOAD",R": loads AND runs (the POKE writes the landmark) ---------
    d = _run_case(args.machine, "/tmp/disk_load_run.txt", 'load"a:prog.bas",r')
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    run_ok = marker == MARKER_BYTE
    case_ok = img_ok and run_ok
    ok = ok and case_ok
    print('\nLOAD"A:PROG.BAS",R')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked line-link image")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if run_ok else 'FAIL'}] RUN executed: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect ${MARKER_BYTE:02X}, sentinel was ${SENTINEL:02X})")

    print("\n" + ("ALL PASS -- disk LOAD rebuilds the program store; ,R runs it, "
                  "plain does not"
                  if ok else
                  "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
