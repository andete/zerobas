#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Regression probe: LOAD"A:PROG2.BAS"[,R] of a program with EMBEDDED $00 operands.

This pins the fix for the streamed line-link loader bug (basic/cload.asm
`do_tape_prog` / `disk_prog_load`): the pre-fix readers copied a line's token
body until the FIRST $00, treating it as the line terminator. But token operands
legitimately contain $00 bytes (e.g. a two-byte `&H` literal `$0C lo hi`), so any
saved program with an interior $00 was truncated mid-line on load. The fix copies
each line's body by the length DERIVED FROM THE SAVED LINK-WORD DIFFERENCES, so
embedded $00s round-trip.

PROG2.BAS (built by zerobas tools/make_test_dsk.py) is:

    10 POKE &HD100,&H7B

whose tokenised body is `98 20 0C 00 D1 2C 0C 7B 00 00` — note the interior $00
(the &HD100 address low/high pairing `0C 00 D1`, a $00 with a whole statement
tail after it) and the &H7B value high byte (`0C 7B 00`). The pre-fix loader
stored only `98 20 0C 00` and mis-framed the rest; the fixed loader stores the
full body byte-identical.

We assert, on the combined C-BIOS_MSX1_BASIC_DISK machine with test720.dsk as
drive A:

  (a) LOAD"A:PROG2.BAS"    -> the store at $8001 equals the relinked line-link
                              image (embedded $00s intact) AND it did NOT auto-run
                              ($D100 stays the sentinel);
  (b) LOAD"A:PROG2.BAS",R  -> the store loaded byte-identical AND RUN executed the
                              POKE ($D100 == $7B). A truncated load could never
                              reach the POKE, so the landmark doubly proves the
                              full body survived.

Strictly black-box: type a line into the REPL and observe RAM. No ROM is read or
disassembled.

Prerequisites (CURRENT zerobas tree):
  * python3 tools/install-openmsx-machine.py --disk-rom disk.rom
  * python3 tools/make_test_dsk.py        (builds PROG2.BAS into test720.dsk)

    python3 probes/disk/disk_probe_load_embedded_nul.py
    python3 probes/disk/disk_probe_load_embedded_nul.py --machine C-BIOS_MSX1_EU_BASIC_DISK
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

# PROG2.BAS fixture parameters (must match zerobas tools/make_test_dsk.py).
TXTBASE = 0x8001           # stored-program text base
MARKER_ADDR = 0xD100       # the POKEd landmark address (interior $00 in its &H token)
MARKER_BYTE = 0x7B         # the landmark byte RUN writes (&H7B low byte)
SENTINEL = 0xC4            # pre-poison MARKER_ADDR with this (!= MARKER_BYTE)
POKE_TOKEN = 0x98
HEX_TOKEN = 0x0C

# Expected relinked store image at TXTBASE. One line `10 POKE &HD100,&H7B`:
#   [link:2 LE][lineno:2 LE][body...00][0000 end-link]
# body = POKE, ' ', &HD100 (HEX_TOKEN + LE -> 0C 00 D1), ',',
#        &H7B (HEX_TOKEN + LE -> 0C 7B 00), 00 terminator.
# The two interior $00 bytes are exactly what the pre-fix loader truncated on.
_BODY = bytes([POKE_TOKEN, 0x20,
               HEX_TOKEN, MARKER_ADDR & 0xFF, MARKER_ADDR >> 8,
               0x2C,
               HEX_TOKEN, MARKER_BYTE, 0x00,
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
    ap.add_argument("--machine", default="C-BIOS_MSX1_BASIC_DISK")
    args = ap.parse_args()

    if not os.path.exists(DSK):
        sys.exit(f"missing test image {DSK} (run tools/make_test_dsk.py)")

    ok = True

    # --- (a) plain LOAD (no ,R): full body loads, does NOT auto-run -----------
    d = _run_case(args.machine, "/tmp/disk_load_nul_plain.txt", 'load"a:prog2.bas"')
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    norun_ok = marker == SENTINEL
    ok = ok and img_ok and norun_ok
    print('LOAD"A:PROG2.BAS"  (no ,R) -- embedded-$00 body')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked image "
          f"(embedded $00s intact)")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if norun_ok else 'FAIL'}] NO auto-run: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect untouched sentinel ${SENTINEL:02X})")

    # --- (b) LOAD",R": full body loads AND runs (the POKE writes the landmark) -
    d = _run_case(args.machine, "/tmp/disk_load_nul_run.txt", 'load"a:prog2.bas",r')
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    run_ok = marker == MARKER_BYTE
    ok = ok and img_ok and run_ok
    print('\nLOAD"A:PROG2.BAS",R')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked image")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if run_ok else 'FAIL'}] RUN executed the (post-$00) POKE: "
          f"(${MARKER_ADDR:04X})=${marker:02X} (expect ${MARKER_BYTE:02X})")

    print("\n" + ("ALL PASS -- embedded-$00 program loads byte-identical; the body "
                  "is no longer truncated at the first interior $00"
                  if ok else
                  "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
