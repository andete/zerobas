#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC random-access GET/PUT
(Phase 2c slice 2).

A random file's record buffer (FIELDed into A$/B$) is written to disk record N with
PUT #f,N and read back with GET #f,N. The record length is 256 bytes, so records 1
and 2 share one 512-byte disk sector — PUT #1,2 must read-modify-write that sector to
preserve record 1. The test writes two records, CLOSES, REOPENS (proving the
directory entry was stamped with size + first cluster so the file is found again),
re-FIELDs, and reads both records back:

  OPEN "D.DAT" AS #1 : FIELD #1,5 AS A$,5 AS B$
  LSET A$="alpha" : RSET B$="bet" : PUT #1,1     ' record 1 = "alpha" + "  bet"
  LSET A$="gamma" : LSET B$="delta" : PUT #1,2    ' record 2 = "gamma" + "delta"
  CLOSE
  OPEN "D.DAT" AS #1 : FIELD #1,5 AS A$,5 AS B$
  GET #1,1 : PRINT "<";A$;"|";B$;">"              ' -> <alpha|  bet>
  GET #1,2 : PRINT "<";A$;"|";B$;">"              ' -> <gamma|delta>
  CLOSE

The two printed lines are each `<` + 11 chars + `>` (5 + '|' + 5). Reading the right
bytes back after a close/reopen proves the whole path: chain allocation, the shared-
sector read-modify-write, and the directory stamp. The real National CF-3300 produces
the byte-identical pair.

Strictly black-box: types REPL lines, reads VRAM. /tmp copy of the disk only.
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

PROGRAM = [
    'open"d.dat" as #1',
    'field#1,5 as a$,5 as b$',
    'lset a$="alpha"',
    'rset b$="bet"',
    "put#1,1",
    'lset a$="gamma"',
    'lset b$="delta"',
    "put#1,2",
    "close",
    'open"d.dat" as #1',
    'field#1,5 as a$,5 as b$',
    "get#1,1",
    'print"<";a$;"|";b$;">"',
    "get#1,2",
    'print"<";a$;"|";b$;">"',
    "close",
]
EXPECT = ["alpha|  bet", "gamma|delta"]   # record 1 (RSET "bet"), record 2 (LSET "delta")


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
    step = 8 if cf3300 else 5      # CF-3300 is slower and stays busy after disk I/O
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


def run(machine, lines, out, cf3300=False, timeout=220.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zgp_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, lines, cf3300))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none", "-script", out + ".tcl"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT running {machine}")
    os.unlink(dsk)
    key = "scr1=" if cf3300 else "scr0="
    # Each output line is `<` + 11 chars + `>`; the echoed PRINT command has a
    # different interior length, so an exact-11 capture isolates the real outputs.
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    return re.findall(r"<(.{11})>", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="C-BIOS_MSX1_EU_BASIC_DISK")
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    rc = 0

    got = run(args.machine, PROGRAM, "/tmp/zgp.txt")
    print(f"--- zerobas GET/PUT round-trip ---\nrecords: {got}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zgp_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nrecords: {ref}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
