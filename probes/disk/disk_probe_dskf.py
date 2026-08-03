#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC DSKF() (free disk space).

On a /tmp COPY of test720.dsk (committed image never mounted):

  PRINT DSKF(0)

DSKF(d) returns the number of free clusters on drive d (= free KB on this
1 KB/cluster 720 KB volume). Checks that zerobas prints the same value as the
real National CF-3300 Disk BASIC (707 free clusters on test720.dsk), and that the
value is independently consistent with a direct FAT12 free-cluster count.

Strictly black-box: types a REPL line, reads VRAM; the cross-check counts free
FAT entries in the image directly. /tmp copy deleted after.
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

LINE = "print dskf(0)"


def count_free(img):
    rsvd = int.from_bytes(img[14:16], "little")
    nfat = img[16]
    spf = int.from_bytes(img[22:24], "little")
    rootents = int.from_bytes(img[17:19], "little")
    spc = img[13]
    total_sec = int.from_bytes(img[19:21], "little")
    firstroot = rsvd + nfat * spf
    rootsecs = (rootents * 32 + 511) // 512
    firstdata = firstroot + rootsecs
    total_clusters = (total_sec - firstdata) // spc + 2
    free = 0
    for c in range(2, total_clusters):
        off = rsvd * 512 + c + c // 2
        pair = int.from_bytes(img[off:off+2], "little")
        val = (pair >> 4) if (c & 1) else (pair & 0x0FFF)
        if val == 0:
            free += 1
    return free


def build_tcl(out_path, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + pre +
            f'after time {t} {{ type {{{LINE}}} }}\n'
            f'after time {t+3} {{ type "\\r" }}\n'
            f'after time {t+9} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
            f' flush $__f; close $__f; exit }}\n')


def run(machine, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zdskf_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, cf3300))
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
    nums = []
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            rows = ["".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*cols:(r+1)*cols]) for r in range(len(d)//cols)]
            grab = False
            for r in rows:
                if "dskf(0)" in r.replace(" ", ""):
                    grab = True
                    continue
                if grab and re.search(r"\d", r):
                    nums = re.findall(r"\d+", r)
                    break
    return nums


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

    expect = count_free(open(SRC_DSK, "rb").read())
    print(f"direct FAT12 free-cluster count: {expect}")

    nums = run(args.machine, "/tmp/zdskf.txt")
    got = int(nums[0]) if nums else None
    print(f"zerobas DSKF(0) = {got}")
    okf = got == expect
    print("functional:", "PASS" if okf else f"FAIL (expected {expect})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        refnums = run(args.ref_machine, "/tmp/zdskf_ref.txt", cf3300=True)
        ref = int(refnums[0]) if refnums else None
        print(f"\nCF-3300 DSKF(0) = {ref}")
        okr = ref == got == expect
        print("differential:", "PASS" if okr else "FAIL")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
