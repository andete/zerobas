#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC MERGE (Phase 2).

MERGE reads a SAVE",A"-style ASCII (line-numbered text) program file and stores
each line into the CURRENT program (insert-or-replace by line number) — the
existing lines are KEPT, unlike LOAD. On a /tmp COPY of test720.dsk:

  REM build the ASCII merge source with the sequential write path:
  OPEN "M.BAS" FOR OUTPUT AS #1 : PRINT#1,"10 a=1" : PRINT#1,"30 a=a*10+3" : CLOSE
  20 a=a*10+2              (typed into the current program)
  40 print"<";a;">"       (typed)
  MERGE "M.BAS"
  RUN

After MERGE the program is 10/20/30/40 interleaved (10 and 30 from the file inserted
AROUND the typed 20). RUN computes a = ((1*10+2)*10+3) = 123 — a value that only
comes out right if BOTH file lines merged into the correct positions (a missing or
mis-ordered line gives a different number). The result is printed wrapped in <...>
for robust extraction. Differential: the real National CF-3300 MERGEs the identical
file and RUNs to the identical 123.

Strictly black-box: types REPL lines, reads VRAM. /tmp copy only.
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
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# Kept as SHORT separate lines: a very long typed line does not finish before the
# next `type` fires (openMSX types one key event per char), which silently drops the
# next line's start. One statement per REPL line + generous spacing types reliably.
PROGRAM = [
    'open"m.bas" for output as #1',
    'print#1,"10 a=1"',
    'print#1,"30 a=a*10+3"',
    "close#1",
    "20 a=a*10+2",
    '40 print"<";a;">"',
    'merge"m.bas"',
    "run",
]
EXPECT = "123"


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
    # The CF-3300 is much slower and stays busy after disk I/O (e.g. CLOSE), so it
    # needs a wider gap or it drops the NEXT line's opening characters.
    step = 8 if cf3300 else 5
    if cf3300:
        body.append('after time 11 { type "\\r" }')
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += step
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    body.append(f'after time {t+5} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=150.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zmrg_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, lines, cf3300))
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
    cols = 32 if cf3300 else 40
    key = "scr1=" if cf3300 else "scr0="
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    m = re.findall(r"<\s*(\d+)\s*>", text)
    return m[-1] if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
    rc = 0

    got = run(args.machine, PROGRAM, "/tmp/zmrg.txt")
    print(f"--- zerobas MERGE -> RUN ---\nresult: <{got}>")
    okf = got == EXPECT
    print("functional:", "PASS" if okf
          else f"FAIL (expected <{EXPECT}>; merged 10/20/30 -> ((1*10+2)*10+3))")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zmrg_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nresult: <{ref}>")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
