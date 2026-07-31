#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC INPUT$(n,#f).

INPUT$(n,#f) reads EXACTLY n raw bytes from sequential file channel f and returns
them as a string (no delimiter handling, unlike INPUT#/LINE INPUT#). On a /tmp COPY
of test720.dsk (HI.TXT = "Hello from zerobas-disk!\\r\\n"):

  OPEN "HI.TXT" FOR INPUT AS #1
  A$ = INPUT$(5,#1) : PRINT "<";A$;">"      -> <Hello>   (first 5 bytes)
  B$ = INPUT$(6,#1) : PRINT "<";B$;">"      -> < from >  (next 6 bytes; cursor advanced)
  CLOSE #1

The two reads in a row prove the file cursor advances byte-exactly. The printed
results are wrapped in <...> so they extract cleanly from either screen layout
(zerobas SCREEN 0 40-col / CF-3300 SCREEN 1 32-col). Checks:
  1. functional — zerobas prints <Hello> then < from >;
  2. differential — the real National CF-3300 prints the identical pair.

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

PROGRAM = [
    'open"hi.txt" for input as #1',
    'a$=input$(5,#1):print"<";a$;">"',
    'b$=input$(6,#1):print"<";b$;">"',
    "close#1",
]
EXPECT = ["Hello", " from "]


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
    if cf3300:
        body.append('after time 11 { type "\\r" }')
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += 6
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    body.append(f'after time {t+4} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=140.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zind_", delete=False).name
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
    cols = 32 if cf3300 else 40
    key = "scr1=" if cf3300 else "scr0="
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else "\n"
                           for c in d).replace("\n", " ")
    # Extract every <...> delimited result, in order. The echoed command line also
    # contains `<";a$;">`, so drop matches carrying command punctuation (" ; $) —
    # the real INPUT$ results are plain file text. Spaces are significant (" from "),
    # so do NOT strip.
    return [x for x in re.findall(r"<([^<>]*)>", text)
            if not any(c in x for c in '";$')]


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

    got = run(args.machine, PROGRAM, "/tmp/zind.txt")
    print(f"--- zerobas INPUT$ ---\nextracted: {got}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zind_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nextracted: {ref}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — byte-identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
