#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC WILDCARD KILL (option-
closure Item 4).

On a /tmp COPY of test720.dsk (5 files: TEST.BIN HI.TXT PROG.BIN PROG.BAS
PROG2.BAS), deletes EVERY file matching an 8.3 wildcard:

  KILL "*.BAS"     ' -> deletes PROG.BAS and PROG2.BAS, leaves the other 3

Checks:
  1. functional — after KILL, both PROG.BAS and PROG2.BAS are gone ($E5 dir
     marker, FAT chains freed to 0) and TEST.BIN / HI.TXT / PROG.BIN are intact;
  2. differential — the real National CF-3300 Disk BASIC, given the same wildcard
     KILL, produces a byte-identical disk image. (This is also the empirical
     check that CF-3300's KILL DOES wildcard the same way -- if it did not, the
     images would diverge and this probe would fail, flagging a real semantic
     mismatch rather than hiding it.)

Strictly black-box: types a REPL line, then reads the FAT12 image directly.
Reuses disk_probe_kill.py's geometry/dir helpers.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from disk_probe_kill import find_entry, fat12_get, geom  # noqa: E402  (reuse)

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

KILL = 'kill"*.bas"'
GONE = [("PROG", "BAS"), ("PROG2", "BAS")]       # must be deleted
KEPT = [("TEST", "BIN"), ("HI", "TXT"), ("PROG", "BIN")]  # must survive


def build_tcl(out_path, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n" + pre +
            f'after time {t} {{ type {{{KILL}}} }}\n'
            f'after time {t+3} {{ type "\\r" }}\n'
            f'after time {t+9} {{ puts $__f "done"; flush $__f; close $__f; exit }}\n')


def run(machine, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zkillw_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, cf3300))
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
    img = open(dsk, "rb").read()
    os.unlink(dsk)
    return img


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

    src = open(SRC_DSK, "rb").read()
    clus = {}
    for n, e in GONE:
        off, ent = find_entry(src, n, e)
        clus[(n, e)] = int.from_bytes(ent[26:28], "little")
        print(f"before: {n}.{e} first cluster {clus[(n,e)]}, FAT={fat12_get(src, clus[(n,e)]):#05x}")

    img = run(args.machine, "/tmp/zkillw.txt")
    ok = True
    for n, e in GONE:
        live, _ = find_entry(img, n, e)
        fat_after = fat12_get(img, clus[(n, e)])
        gone = live is None and fat_after == 0
        print(f"  {n}.{e}: deleted={gone} (live={live}, FAT={fat_after:#05x})")
        ok = ok and gone
    for n, e in KEPT:
        live, _ = find_entry(img, n, e)
        print(f"  {n}.{e}: kept={live is not None}")
        ok = ok and live is not None
    print("functional:", "PASS" if ok else "FAIL")
    rc = rc or (0 if ok else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, "/tmp/zkillw_ref.txt", cf3300=True)
        same = ref == img
        print(f"\ndifferential vs CF-3300: image {'byte-identical' if same else 'DIFFERS'}")
        if not same:
            d = [i for i in range(min(len(img), len(ref))) if img[i] != ref[i]]
            print(f"  {len(d)} differing bytes; first few at {[hex(x) for x in d[:8]]}")
        print("differential:", "PASS" if same else "FAIL")
        rc = rc or (0 if same else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
