#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: RUN"A:PROG.BAS" from a real FAT12 disk.

This exercises the disk RUN"filename" path in basic/cload.asm (`do_run`, reached
via the RUN_TOKEN dispatch added to basic/interp.asm) on the combined
C-BIOS_MSX1_BASIC_DISK machine (zerobas-BASIC in slot 0 page 1, zerobas-disk in
slot 3-1) with disk/test720.dsk attached as drive A.

RUN"filename" is a thin wrapper: it reuses the LOAD"filename" plumbing
(parse_disk_fcb + disk_prog_load) and then RUNs the loaded program. Unlike
LOAD"name", there is NO ,R option -- running is implicit. The path:

  * do_run sees a '"' after RUN -> disk load+run; inc past the quote;
  * parse_disk_fcb builds DISK_FCB; parse_close_run consumes the closing quote
    (and tolerates a stray ,R harmlessly);
  * disk_prog_load: cross-slot Set-DTA -> writable page-3 buffer, Open, require
    the leading $FF tokenised-BASIC marker (BASIC_DISK_ID), stream the line-link
    image into the stored-program area at TXTBASE ($8001), close, relink;
  * jp run_prog -> RUN the freshly loaded program.

PROG.BAS (built by zerobas tools/make_test_dsk.py) is a real on-disk tokenised
BASIC file: a leading $FF marker followed by the in-memory line-link image of:

    10 POKE &HD002,123

So after RUN"A:PROG.BAS" the relinked program sits at $8001 AND it has run: the
single POKE writes $7B to $D002. We assert BOTH:

  (a) the store at $8001 equals the relinked line-link image (it LOADED), and
  (b) the landmark byte ($D002) == $7B (it RAN).

Strictly black-box: we type a line into the REPL and observe RAM. No ROM is read
or disassembled. The loaded program is interpreted and returns to the REPL, so
there is no clean instruction landmark; we sync on time after the load+run is
guaranteed complete (identical technique to disk_probe_load_disk.py).

Prerequisites (CURRENT zerobas tree):
  * python3 tools/install-openmsx-machine.py --disk-rom disk.rom   (slot 0 IPS +
    slot 3-1 disk.rom reflect the build under test);
  * python3 tools/make_test_dsk.py                                 (PROG.BAS);

    python3 probes/disk/disk_probe_run_disk.py
    python3 probes/disk/disk_probe_run_disk.py --machine C-BIOS_MSX1_EU_BASIC_DISK
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

# PROG.BAS fixture parameters (must match zerobas tools/make_test_dsk.py and
# disk_probe_load_disk.py).
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
    """Type a RUN line, poison MARKER, then capture the store image + MARKER on a
    time well after the load+run completes."""
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

    # --- RUN"A:PROG.BAS": loads the tokenised program AND runs it (implicit) ---
    d = _run_case(args.machine, "/tmp/disk_run.txt", 'run"a:prog.bas"')
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    run_ok = marker == MARKER_BYTE
    ok = img_ok and run_ok
    print('RUN"A:PROG.BAS"')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked line-link image")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if run_ok else 'FAIL'}] RUN executed: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect ${MARKER_BYTE:02X}, sentinel was ${SENTINEL:02X})")

    print("\n" + ("ALL PASS -- disk RUN loads the tokenised program AND runs it"
                  if ok else
                  "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
