#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC random-access FIELD/LSET/RSET
(Phase 2c slice 1).

A random file (OPEN "name" AS #n, no FOR clause) has a fixed record buffer that
FIELD partitions into named string slices. LSET stores a value left-justified into
its slice (space-padded on the right); RSET right-justifies it (space-padded on the
left). Reading a fielded variable yields its current slice of the buffer. With:

  OPEN "R.DAT" AS #1
  FIELD #1, 5 AS A$, 10 AS B$
  LSET A$ = "HI"          -> A$ = "HI   "        (left in a 5-wide field)
  RSET B$ = "END"         -> B$ = "       END"   (right in a 10-wide field)
  PRINT "<";A$;"|";B$;">"

the printed line is exactly `<HI   |       END>` (16 chars between the < and >:
5 + '|' + 10). The exact interior spaces are the whole point — they prove the
justification + padding. The real National CF-3300 prints the byte-identical line.

This is slice 1: FIELD/LSET/RSET over an in-RAM record buffer; GET/PUT (the disk
record I/O) are slice 2, so the test never reads the record back from disk.

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
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# One statement per REPL line + generous spacing types reliably on both machines
# (a long typed line can drop the next line's opening characters).
PROGRAM = [
    'open"r.dat" as #1',
    'field#1,5 as a$,10 as b$',
    'lset a$="HI"',
    'rset b$="END"',
    'print"<";a$;"|";b$;">"',
    "close",
]
EXPECT = "HI   |       END"   # 5-wide "HI", '|', 10-wide right-justified "END"


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
    step = 8 if cf3300 else 5     # CF-3300 is slower; wider gap or it drops chars
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
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zfld_", delete=False).name
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
    # The output line is exactly `<` + 16 chars + `>`; the echoed PRINT command has a
    # different interior length, so an exact-16 capture isolates the real output.
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    m = re.findall(r"<(.{16})>", text)
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

    got = run(args.machine, PROGRAM, "/tmp/zfld.txt")
    print(f"--- zerobas FIELD/LSET/RSET ---\nresult: <{got}>")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected <{EXPECT}>)")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zfld_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nresult: <{ref}>")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
