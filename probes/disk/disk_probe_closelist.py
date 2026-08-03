#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional oracle for zerobas-BASIC CLOSE channel LIST (option-closure Item 4):
CLOSE #1,#2 closes (and FLUSHES) BOTH channels in one statement.

Keyboard-free harness (the flaky-typed-probe lesson, tier2-autoexec-bat-harness-
spec.md): an AUTOEXEC.BAS -- tokenised by OUR OWN ROM crunch (bas_tokenise) and
injected into a fresh FAT12 image -- opens ONE OUTPUT channel, PRINT#s a line, then
closes it with a comma-LIST that also names two un-opened channels:

  5  MAXFILES=3
  10 OPEN"C1.DAT"FOR OUTPUT AS#1
  20 PRINT#1,"HELLO"
  30 CLOSE#1,#2,#3          ' list: close #1 (open) + #2,#3 (in range, not open)
  40 POKE&HD0FF,&H99        ' done witness

This isolates the list PARSER: the old single-channel CLOSE stopped after #1, so
the trailing ",#2,#3" was a Syntax error that halts the program BEFORE line 40 --
the done witness would stay poisoned. The list form consumes the whole comma list
(a no-op for the un-opened channels), reaches line 40, and flushes #1. So a PASS =
done witness $99 AND C1.DAT present + non-empty (proving #1 was closed/flushed
through the list). Offline + deterministic; no keystrokes, no screen scrape.

⚠️ LINE 5 WAS ADDED 2026-07-31 BY D-BADFNUM, AND IT MATTERS. This program used to
run at the default MAXFILES=1, which made #2/#3 OUT OF RANGE, and this docstring
described that as a "lenient no-op" -- a claim about zerobas's own behaviour that
had no reference column and turned out to be false. `CLOSE #1,#2,#3` at MAXFILES=1
answers ERR 52 on the CF-3300 (measured), after flushing #1. Raising the ceiling
keeps the subject (the list parser) and drops the unmeasured premise.

Clean-room: our own `.bas`, our own ROM tokeniser, a FAT12 image per the public
spec. A fresh /tmp image; disk/test720.dsk is never touched.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_sys.path.insert(0, _os.path.join(_ROOT, "tools"))  # make_test_dsk.py

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from make_test_dsk import Fat12Image  # noqa: E402
from bas_tokenise import make_basic_file  # noqa: E402

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
OURS_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")

TXTBASE = 0x8001
DONE_ADDR = 0xD0FF
DONE_BYTE = 0x99
POISON = 0x11

AUTOEXEC_LINES = [
    # ⚠️ MAXFILES=3 IS LOAD-BEARING, AND IT WAS ADDED BECAUSE THE ORIGINAL FORM
    # RESTED ON AN ASSUMPTION NOBODY HAD MEASURED. This program used to run at the
    # default MAXFILES=1, so #2/#3 were BEYOND THE CEILING, and the docstring
    # called that a "lenient no-op". D-BADFNUM typed it on the CF-3300
    # (2026-07-31): `CLOSE #1,#2,#3` at MAXFILES=1 answers **ERR 52 bad file
    # number** there -- after flushing #1 -- and so does zerobas now. The
    # leniency the reference actually has is about channel **0** only.
    # Raising the ceiling keeps this probe aimed at what it exists to test -- the
    # LIST PARSER consuming the whole comma list instead of stopping after #1 --
    # while dropping a premise that was never a measurement.
    (5,  "MAXFILES=3"),
    (10, 'OPEN"C1.DAT"FOR OUTPUT AS#1'),
    (20, 'PRINT#1,"HELLO"'),
    (30, "CLOSE#1,#2,#3"),          # comma list; #2/#3 in range, not open -> no-op
    (40, f"POKE&H{DONE_ADDR:04X},&H{DONE_BYTE:02X}"),
]


def build_disk() -> str:
    img = Fat12Image()
    img.add_file("AUTOEXEC", "BAS", make_basic_file(AUTOEXEC_LINES, TXTBASE))
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="closelist_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


def dir_size(dsk_path: str, name8: str, ext3: str):
    """Offline FAT12 root-dir lookup -> file size (bytes), or None if absent."""
    img = open(dsk_path, "rb").read()
    rsvd = int.from_bytes(img[14:16], "little")
    nfat = img[16]
    spf = int.from_bytes(img[22:24], "little")
    rootents = int.from_bytes(img[17:19], "little")
    root_off = (rsvd + nfat * spf) * 512
    want = name8.ljust(8).upper().encode() + ext3.ljust(3).upper().encode()
    for i in range(rootents):
        e = img[root_off + i*32: root_off + i*32 + 32]
        if not e or e[0] in (0x00, 0xE5):
            continue
        if bytes(e[0:11]).upper() == want:
            return int.from_bytes(e[28:32], "little")
    return None


def cold_boot(machine: str, dsk: str, out_path: str, timeout: float = 60.0) -> int:
    tcl = f"""set throttle off
set renderer none
set sound_driver null
after time 1 {{ debug write memory 0x{DONE_ADDR:04X} 0x{POISON:02X} }}
proc cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "done=[format %02X [debug read memory 0x{DONE_ADDR:04X}]]"
  close $f
  exit
}}
after time 20 {{ cap }}
"""
    open(out_path + ".tcl", "w").write(tcl)
    if os.path.exists(out_path):
        os.unlink(out_path)
    proc = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk, "-script", out_path + ".tcl"]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT cold-booting {machine}")
    if not os.path.exists(out_path):
        sys.exit(f"no capture from {machine} (ROMs/machine missing?)")
    for ln in open(out_path):
        k, _, v = ln.strip().partition("=")
        if k == "done":
            return int(v, 16)
    sys.exit("capture missing 'done'")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours-machine", default=OURS_MACHINE)
    args = ap.parse_args()
    if not args.ours_machine:
        sys.exit("no zerobas machine: pass --ours-machine or set $ZEROBAS_BASIC_MACHINE; there is no\n"
                 "default, one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    print("CLOSE list: a comma-separated channel list is consumed as one statement.")
    dsk = build_disk()
    ok = True
    try:
        done = cold_boot(args.ours_machine, dsk, "/tmp/closelist_ours.txt")
        s1 = dir_size(dsk, "C1", "DAT")

        c_done = done == DONE_BYTE
        print(f"  [{'PASS' if c_done else 'FAIL'}] list consumed (no Syntax-error halt on ',#2,#3'): "
              f"(${DONE_ADDR:04X})=${done:02X} (expect ${DONE_BYTE:02X})")
        c1 = s1 is not None and s1 > 0
        print(f"  [{'PASS' if c1 else 'FAIL'}] channel #1 closed+flushed through the list: "
              f"C1.DAT size={s1} (expect present + non-empty)")
        ok = c_done and c1
    finally:
        os.unlink(dsk)

    print("CLOSE-list:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
