#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC ASCII SAVE (SAVE"name",A).

SAVE"A:F",A writes the current program as an ASCII listing (numbered detokenised
lines + CR/LF, Ctrl-Z terminator) — the same format MERGE / ASCII LOAD read
(basic/docs/spec-ascii-saveload.md §5). Implementation reuses the LIST detokeniser
walk (list_walk) with the PRINT#-to-file sink (PRDEST=1 / pchar). Round-trip test
on a /tmp COPY of test720.dsk, with a string-literal line to exercise detok:

  10 A=6
  20 A=A*7
  30 PRINT "<";A;">"
  SAVE "S.BAS",A          (write the ASCII listing to disk)
  20 A=999                (CORRUPT the in-memory program AFTER saving)
  LOAD "S.BAS"            (reload the ASCII file -> restores 20 A=A*7, clears the corruption)
  RUN                     (-> A = 6*7 = 42)

<42> proves the whole chain: SAVE",A" detokenised the program (incl. the quoted
string in line 30) to a valid ASCII file, ASCII LOAD read it back, and LOAD
replaced the corrupted memory. <999> => the saved file was wrong or LOAD didn't
restore it; no <..> => SAVE or LOAD failed. Differential: the real National
CF-3300 runs the identical sequence to the identical <42> (its SAVE",A" writes an
ASCII file our LOAD... — here BOTH machines self-round-trip, so this is a
behavioural-parity differential on the same operations).

Strictly black-box: types REPL lines, reads VRAM. /tmp copy only.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

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
    "10 a=6",
    "20 a=a*7",
    '30 print"<";a;">"',      # string literal -> exercises detok's dt_string
    'save"s.bas",a',          # write the ASCII listing to disk
    "20 a=999",               # corrupt the in-memory program AFTER saving
    'load"s.bas"',            # reload the ASCII file: restores 20 a=a*7, clears line 999
    "run",                    # -> a = 6*7 = 42 iff SAVE",A" + LOAD round-tripped
]
EXPECT = "42"


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
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
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zsva_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, lines, cf3300))
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

    got = run(args.machine, PROGRAM, "/tmp/zsva.txt")
    print(f"--- zerobas SAVE\",A\" -> LOAD -> RUN ---\nresult: <{got}>")
    okf = got == EXPECT
    print("functional:", "PASS" if okf
          else f"FAIL (expected <{EXPECT}>; <999> => reload got corrupted memory, "
               "no <..> => SAVE\",A\" or LOAD failed)")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zsva_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nresult: <{ref}>")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
