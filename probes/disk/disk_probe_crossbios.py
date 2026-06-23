#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cross-host BIOS-independence oracle for the zerobas stack (Phase 1.5 claim).

The Phase-1.5 standardization makes zerobas-disk a STANDARD slot disk ROM driven
through the $4010 DSKIO entry, so the BASIC host should not matter. This probe proves
it on a real, non-C-BIOS, non-Japanese BIOS: the same zerobas program runs on

  * C-BIOS  — machine C-BIOS_MSX1_EU_BASIC_DISK (zerobas baked in, zerobas-disk slot 3-1)
  * Philips — machine Philips_VG_8020 (a REAL MSX1 BIOS) + the zerobas-BASIC cartridge
              + the pluggable `zerobas-disk` extension

Both must list the same directory and round-trip a file identically:

  FILES
  OPEN "Z.TXT" FOR OUTPUT AS #1 : PRINT#1,"phil" : CLOSE
  OPEN "Z.TXT" FOR INPUT  AS #1 : LINE INPUT#1,A$ : PRINT"<";A$;">"   ' -> <phil>

zerobas-disk supplies only the sector DRIVER, so the disk verbs come from the zerobas-
BASIC cartridge on BOTH hosts — i.e. this validates the BASIC+disk stack is independent
of the host BIOS, not that the host's own BASIC gained disk support. Needs `make
machines` (writes the C-BIOS machines + the `zerobas-disk` extension).

Strictly black-box: types REPL lines, reads VRAM. /tmp disk copy only.
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
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))
CART = os.path.join(ZEROBAS, "build", "basic.rom")

PROGRAM = [
    "files",
    'open"z.txt" for output as #1',
    'print#1,"phil"',
    "close",
    'open"z.txt" for input as #1',
    "line input#1,a$",
    'print"<";a$;">"',
    "close",
]


def build_tcl(out_path):
    body = ['after time 16 { type "\\r" }']
    t = 22
    for ln in PROGRAM:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += 7
    body.append(f'after time {t+6} {{ puts $__f "scr=[__hex_v 0x0000 960]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + "\n".join(body) + "\n")


def run(extra_args, out):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zxb_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out))
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX] + extra_args + ["-diska", dsk,
           "-command", "set renderer none", "-script", out + ".tcl"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 90
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT: {extra_args}")
    os.unlink(dsk)
    text = ""
    for ln in open(out):
        if ln.startswith("scr="):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    roundtrip = re.findall(r"<(.{4})>", text)
    # 8.3 filenames the FILES listing shows (NAME.EXT tokens on the screen)
    files = sorted(set(re.findall(r"\b([A-Z0-9]{1,8})\s*\.([A-Z0-9]{1,3})\b", text)))
    return (roundtrip[-1] if roundtrip else None), files


def main() -> int:
    argparse.ArgumentParser().parse_args()
    cbios = ["-machine", "C-BIOS_MSX1_EU_BASIC_DISK"]
    philips = ["-machine", "Philips_VG_8020", "-cart", CART, "-ext", "zerobas-disk"]

    c_rt, c_files = run(cbios, "/tmp/zxb_cbios.txt")
    p_rt, p_files = run(philips, "/tmp/zxb_philips.txt")

    print(f"--- C-BIOS host  ---\n  round-trip: <{c_rt}>\n  files: {c_files}")
    print(f"--- Philips VG-8020 host ---\n  round-trip: <{p_rt}>\n  files: {p_files}")

    ok_rt = c_rt == p_rt == "phil"
    ok_files = c_files == p_files and len(c_files) > 0
    print(f"\nround-trip identical + correct: {'PASS' if ok_rt else 'FAIL'}")
    print(f"directory listing identical:    {'PASS' if ok_files else 'FAIL'}")
    print("\nzerobas runs BIOS-independently (real Philips BIOS == C-BIOS):",
          "PASS" if ok_rt and ok_files else "FAIL")
    return 0 if ok_rt and ok_files else 1


if __name__ == "__main__":
    raise SystemExit(main())
