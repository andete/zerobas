#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional oracle for zerobas-BASIC OPEN device channels (CAS/device option-
closure Tier 1, Item 3): OPEN"LPT:"/"CRT:" FOR OUTPUT AS #n + PRINT# routes to the
printer (LPTOUT $00A5) / screen (CHPUT $00A2) instead of a disk file.

Keyboard-free harness (the flaky-typed-probe lesson, tier2-autoexec-bat-harness-
spec.md), modelled on disk_probe_closelist.py + disk_probe_lstout_cbios.py: an
AUTOEXEC.BAS -- tokenised by OUR OWN ROM crunch (bas_tokenise) and injected into a
fresh FAT12 image -- opens each device channel, PRINT#s a line, closes it, and ends
with a done witness. An openMSX printer `logger` is plugged, so the LP! line the
program sends to the LPT: channel physically lands in the printer log:

  10 OPEN"CRT:"FOR OUTPUT AS#1     ' screen device channel
  20 PRINT#1,"CR!"                 ' -> CHPUT (screen)
  30 CLOSE#1
  40 OPEN"LPT:"FOR OUTPUT AS#2     ' printer device channel
  50 PRINT#2,"LP!"                 ' -> LPTOUT ($00A5) -> printer logger
  60 CLOSE#2
  70 POKE&HD0FF,&H99               ' done witness

Two independent assertions:
  * done witness == $99  -> the WHOLE program ran to completion. If OPEN"CRT:" or
    OPEN"LPT:" (or their PRINT#/CLOSE) had raised a Syntax/Bad-file error, RUN would
    have halted before line 70 and the witness would stay poisoned ($11). This is
    the CRT: gate (its CHPUT sink is the shared screen path, so "opened, printed,
    closed, no abort" is the meaningful assertion) and proves the LPT: channel
    parses/opens/closes too.
  * printer log == "LP!\r\n"  -> the LPT: channel's bytes physically reached the
    printer through pchar's PRDEV=1 -> LPTOUT sink. This is the LPT: gate.

Requires C-BIOS_MSX1_EU_BASIC_DISK (C-BIOS + zerobas-tape[LPTOUT] + zerobas-disk +
zerobas BASIC), the same machine disk_probe_lstout_cbios.py uses. Offline +
deterministic; no keystrokes, no screen scrape. A fresh /tmp image; the committed
disk images are never touched.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_sys.path.insert(0, _os.path.join(_ROOT, "tools"))  # make_test_dsk.py / bas_tokenise.py

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

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
OURS_MACHINE = "C-BIOS_MSX1_EU_BASIC_DISK"

TXTBASE = 0x8001
DONE_ADDR = 0xD0FF
DONE_BYTE = 0x99
POISON = 0x11
EXPECT_PRN = b"LP!\r\n"

AUTOEXEC_LINES = [
    (5,  "MAXFILES=2"),                  # #2 needs the ceiling raised from the default 1
    (10, 'OPEN"CRT:"FOR OUTPUT AS#1'),   # screen device channel -> CHPUT
    (20, 'PRINT#1,"CR!"'),
    (40, 'OPEN"LPT:"FOR OUTPUT AS#2'),   # printer device channel -> LPTOUT (concurrent)
    (50, 'PRINT#2,"LP!"'),
    (60, "CLOSE#1,#2"),                  # close BOTH device channels (list form)
    (70, f"POKE&H{DONE_ADDR:04X},&H{DONE_BYTE:02X}"),
]


def build_disk() -> str:
    img = Fat12Image()
    img.add_file("AUTOEXEC", "BAS", make_basic_file(AUTOEXEC_LINES, TXTBASE))
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="opendev_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


def cold_boot(machine: str, dsk: str, out_path: str, prn_log: str,
              timeout: float = 90.0) -> int:
    tcl = f"""set throttle off
set renderer none
set printerlogfilename {{{prn_log}}}
catch {{ plug printerport logger }}
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
    for p in (out_path, prn_log):
        if os.path.exists(p):
            os.unlink(p)
    proc = subprocess.Popen([OMSX, "-machine", machine, "-diska", dsk,
                             "-script", out_path + ".tcl"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
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

    print("OPEN device channels: PRINT# routes to LPT: (printer) / CRT: (screen).")
    dsk = build_disk()
    prn_log = "/tmp/opendev_printer.log"
    ok = True
    try:
        done = cold_boot(args.ours_machine, dsk, "/tmp/opendev_ours.txt", prn_log)
        got = open(prn_log, "rb").read() if os.path.exists(prn_log) else b""

        c_done = done == DONE_BYTE
        print(f"  [{'PASS' if c_done else 'FAIL'}] whole program ran (CRT:+LPT: OPEN/PRINT#/CLOSE, no abort): "
              f"(${DONE_ADDR:04X})=${done:02X} (expect ${DONE_BYTE:02X})")
        c_prn = got == EXPECT_PRN
        print(f"  [{'PASS' if c_prn else 'FAIL'}] LPT: channel reached the printer through LPTOUT: "
              f"log={got!r} (expect {EXPECT_PRN!r})")
        ok = c_done and c_prn
    finally:
        os.unlink(dsk)

    print("OPEN(LPT/CRT):", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
