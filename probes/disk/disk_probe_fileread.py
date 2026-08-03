#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional oracle for zerobas-BASIC sequential file READ (Phase 2 Step 2).

Boots the combined zerobas machine on a /tmp copy of test720.dsk (which holds
HI.TXT = "Hello from zerobas-disk!\\r\\n") and exercises the read-path verbs:

  OPEN "HI.TXT" FOR INPUT AS #1 : LINE INPUT #1,A$ : CLOSE #1 : PRINT A$

The expected screen line is the file's text with the CR/LF stripped:
  Hello from zerobas-disk!

A second case checks INPUT# (field mode, same file — no comma, so it also yields
the whole first line). Strictly black-box: types REPL lines, reads VRAM. No ROM
read. DISK SAFETY: /tmp copy only.
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
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

EXPECT = "Hello from zerobas-disk!"


def build_tcl(out_path: str, line: str, cf3300: bool) -> str:
    # The real CF-3300 boots to Disk BASIC (SCREEN 1, name table at VRAM 0x1800)
    # behind an "Enter date" prompt cleared with Enter ~t=12; zerobas (C-BIOS) is
    # SCREEN 0 (VRAM 0x0000) with no date prompt.
    if cf3300:
        return f"""set throttle off
set __f [open {{{out_path}}} w]
proc __hex_v {{a l}} {{ binary scan [debug read_block VRAM $a $l] H* h; return $h }}
after time 12 {{ type "\\r" }}
after time 16 {{ type {{{line}}} }}
after time 20 {{ type "\\r" }}
after time 26 {{
  puts $__f "scr1=[__hex_v 0x1800 768]"
  flush $__f; close $__f; exit
}}
"""
    return f"""set throttle off
set __f [open {{{out_path}}} w]
proc __hex_v {{a l}} {{ binary scan [debug read_block VRAM $a $l] H* h; return $h }}
after time 8  {{ type {{{line}}} }}
after time 12 {{ type "\\r" }}
after time 18 {{
  puts $__f "scr0=[__hex_v 0x0000 960]"
  flush $__f; close $__f; exit
}}
"""


def run(machine, line, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zread_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, line, cf3300))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", out + ".tcl"]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT running {machine}")
    os.unlink(dsk)
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine}")
    rows, cols, key = [], (32 if cf3300 else 40), ("scr1=" if cf3300 else "scr0=")
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            rows = ["".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*cols:(r+1)*cols]).rstrip()
                    for r in range(len(d)//cols)]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300",
                    help="real Disk BASIC reference for the differential")
    ap.add_argument("--no-ref", action="store_true", help="skip the CF-3300 run")
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
    rc = 0
    cases = [
        ('LINE INPUT#', 'open"hi.txt" for input as #1:line input#1,a$:close#1:print a$'),
        ('INPUT#',      'open"hi.txt" for input as #1:input#1,a$:close#1:print a$'),
    ]
    for tag, line in cases:
        slug = tag.strip('#').lower().replace(' ', '')
        rows = run(args.machine, line, f"/tmp/zread_{slug}.txt")
        print(f"--- zerobas {tag}: {line} ---")
        for i, r in enumerate(rows):
            if r.strip():
                print(f"{i:2}|{r}")
        ok = any(r.strip() == EXPECT for r in rows)
        print("PASS — read matches ground-truth file content\n" if ok
              else f"FAIL — expected a line == {EXPECT!r}\n")
        rc = rc or (0 if ok else 1)

    if not args.no_ref:
        # Differential: the real CF-3300 Disk BASIC must print the same line.
        line = cases[0][1]
        rows = run(args.ref_machine, line, "/tmp/zread_cf3300.txt", cf3300=True)
        print(f"--- CF-3300 reference {cases[0][0]}: {line} ---")
        for i, r in enumerate(rows):
            if r.strip():
                print(f"{i:2}|{r}")
        ok = any(r.strip() == EXPECT for r in rows)
        print("PASS — CF-3300 prints the identical line (differential)\n" if ok
              else f"FAIL — CF-3300 did not print {EXPECT!r}\n")
        rc = rc or (0 if ok else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
