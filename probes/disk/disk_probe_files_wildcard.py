#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC WILDCARD FILES (option-
closure Item 4).

On a /tmp copy of test720.dsk (TEST.BIN HI.TXT PROG.BIN PROG.BAS PROG2.BAS),
types a filtered directory listing and dumps the text screen:

  FILES "*.BAS"    ' -> only PROG.BAS and PROG2.BAS
  FILES "PROG*.*"  ' -> PROG.BIN, PROG.BAS, PROG2.BAS

The listed 8.3 names (order preserved) are compared to the real National CF-3300
Disk BASIC given the identical command -- a live differential that also confirms
CF-3300 filters the same way. Screen is dumped at WIDTH 40 so each name is one
`NAME    .EXT` token, order-preserved.

Strictly black-box: types REPL lines, reads VRAM. /tmp copy only.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes

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

CASES = [
    ('files"*.bas"',   ["PROG    .BAS", "PROG2   .BAS"]),
    ('files"prog*.*"', ["PROG    .BIN", "PROG    .BAS", "PROG2   .BAS"]),
]
# A FILES listing token is the fixed 12-char 8.3 field: an 8-char name (first
# char alnum, padded with spaces) + '.' + a 3-char ext. This deliberately does
# NOT match the CF-3300 on-screen version banner ("...1.0"), which has no padding.
NAME_RE = re.compile(r"[A-Z0-9][A-Z0-9 ]{7}\.[A-Z0-9 ]{3}")


def build_tcl(out_path, cmd, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    va = "0x1800" if cf3300 else "0x0000"
    sz = 768 if cf3300 else 960
    # WIDTH 40 on both so a 12-char 8.3 token never wraps mid-name.
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + pre +
            f'after time {t} {{ type "width 40" }}\nafter time {t+2} {{ type "\\r" }}\n'
            f'after time {t+4} {{ type {{{cmd}}} }}\nafter time {t+7} {{ type "\\r" }}\n'
            f'after time {t+13} {{ puts $__f "scr=[__hex_v {va} {sz}]";'
            f' flush $__f; close $__f; exit }}\n')


def run(machine, cmd, out, cf3300=False, timeout=110.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zfilw_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, cmd, cf3300))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", out + ".tcl"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT running {machine}")
    os.unlink(dsk)
    cols = 40
    names = []
    for ln in open(out):
        if ln.startswith("scr="):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            for r in range(len(d) // cols):
                row = "".join(chr(c) if 32 <= c < 127 else " " for c in d[r*cols:(r+1)*cols])
                # skip the echoed command line (contains '"')
                if '"' in row or "FILES" in row.upper() and "." not in row:
                    continue
                names += NAME_RE.findall(row)
    # de-dup consecutive (the echo may re-list) while preserving order
    return names


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

    for cmd, expect in CASES:
        got = run(args.machine, cmd, "/tmp/zfilw.txt")
        okf = got == expect
        print(f"--- {cmd} ---\nzerobas: {got}\nfunctional: {'PASS' if okf else f'FAIL (expected {expect})'}")
        rc = rc or (0 if okf else 1)
        if not args.no_ref:
            ref = run(args.ref_machine, cmd, "/tmp/zfilw_ref.txt", cf3300=True)
            okr = ref == got == expect
            print(f"CF-3300: {ref}\ndifferential: {'PASS — identical' if okr else 'FAIL'}")
            rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
