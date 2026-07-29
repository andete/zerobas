#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC EOF()/LOF() (Phase 2).

On a /tmp COPY of test720.dsk (committed image never mounted; HI.TXT is the
26-byte "Hello from zerobas-disk!\\r\\n"):

  Case A (differential, read-model-independent):
    OPEN"HI.TXT" FOR INPUT AS #1 : PRINT LOF(1);EOF(1) : CLOSE#1
    -> LOF(1)=26 (file size), EOF(1)=0 (not at end just after OPEN).
    The real CF-3300 must print the same two values.

  Case B (functional, zerobas read model):
    OPEN"HI.TXT" FOR INPUT AS #1 : LINE INPUT#1,A$ : LINE INPUT#1,A$
                                 : PRINT EOF(1) : CLOSE#1
    -> EOF(1)=-1 once every byte has been delivered.

Strictly black-box: types REPL lines, reads VRAM. /tmp copy deleted after.
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

CASE_A = 'open"hi.txt" for input as #1:print lof(1);eof(1):close#1'
CASE_B = ('open"hi.txt" for input as #1:line input#1,a$:line input#1,a$'
          ':print eof(1):close#1')


def build_tcl(out_path, line, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + pre +
            f'after time {t} {{ type {{{line}}} }}\n'
            f'after time {t+3} {{ type "\\r" }}\n'
            f'after time {t+9} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
            f' flush $__f; close $__f; exit }}\n')


def run(machine, line, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zeof_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, line, cf3300))
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
    cols = 32 if cf3300 else 40
    key = "scr1=" if cf3300 else "scr0="
    rows = []
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            rows = ["".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*cols:(r+1)*cols]).rstrip()
                    for r in range(len(d)//cols)]
    return rows


def nums_after_cmd(rows, cmd_tail):
    """Integer tokens printed on the lines after the command echo."""
    out, started = [], False
    for r in rows:
        if not started:
            if cmd_tail in r.replace(" ", ""):
                started = True
            continue
        if "Ok" in r or r.strip().endswith(">"):
            if out:
                break
            continue
        out += re.findall(r"-?\d+", r)
    return out


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

    rows = run(args.machine, CASE_A, "/tmp/zeof_a.txt")
    nums = nums_after_cmd(rows, "close#1")
    print("--- Case A: LOF(1);EOF(1) just after OPEN ---")
    for r in rows:
        if r.strip():
            print("  " + r)
    okA = nums[:2] == ["26", "0"]
    print("got:", nums[:2], "-> functional:", "PASS" if okA else "FAIL (want ['26','0'])")
    rc = rc or (0 if okA else 1)

    rowsB = run(args.machine, CASE_B, "/tmp/zeof_b.txt")
    numsB = nums_after_cmd(rowsB, "closebar") or \
        [t for r in rowsB for t in re.findall(r"-?\d+", r) if t in ("-1", "0")]
    print("\n--- Case B: EOF(1) after reading the whole file ---")
    for r in rowsB:
        if r.strip():
            print("  " + r)
    okB = "-1" in [t for r in rowsB for t in re.findall(r"-?\d+", r)]
    print("EOF after full read:", "PASS (-1)" if okB else "FAIL (want -1)")
    rc = rc or (0 if okB else 1)

    if not args.no_ref:
        refrows = run(args.ref_machine, CASE_A, "/tmp/zeof_ref.txt", cf3300=True)
        refnums = nums_after_cmd(refrows, "close#1")
        print("\n--- CF-3300 differential (Case A) ---")
        for r in refrows:
            if r.strip():
                print("  " + r)
        okR = refnums[:2] == nums[:2] == ["26", "0"]
        print("CF-3300 got:", refnums[:2],
              "-> differential:", "PASS" if okR else "FAIL")
        rc = rc or (0 if okR else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
