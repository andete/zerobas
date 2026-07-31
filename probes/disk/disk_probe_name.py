#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC NAME…AS… (rename).

On a /tmp COPY of test720.dsk (committed image never mounted):

  NAME "HI.TXT" AS "BYE.TXT"

Checks:
  1. functional — after rename, HI.TXT is gone, BYE.TXT exists with the SAME first
     cluster (4) and size (26) as HI.TXT had, and BYE.TXT's data is unchanged
     ("Hello from zerobas-disk!\\r\\n");
  2. differential — the real National CF-3300 Disk BASIC, given the same NAME,
     produces a byte-identical disk image (rename rewrites only the 8.3 name field
     of one directory entry).

Strictly black-box: types a REPL line, parses the FAT12 image directly. /tmp copy
deleted after extraction.
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

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

NAME = 'name"hi.txt" as "bye.txt"'
EXPECT_DATA = b"Hello from zerobas-disk!\r\n"


def geom(img):
    rsvd = int.from_bytes(img[14:16], "little")
    nfat = img[16]
    spf = int.from_bytes(img[22:24], "little")
    rootents = int.from_bytes(img[17:19], "little")
    spc = img[13]
    firstroot = rsvd + nfat * spf
    rootsecs = (rootents * 32 + 511) // 512
    firstdata = firstroot + rootsecs
    return rsvd, spc, firstroot, rootents, firstdata


def find_entry(img, name8, ext3):
    _, _, firstroot, rootents, _ = geom(img)
    want = name8.ljust(8).upper().encode() + ext3.ljust(3).upper().encode()
    base = firstroot * 512
    for e in range(rootents):
        ent = img[base + e*32: base + e*32 + 32]
        if ent[0:11] == want and ent[0] not in (0x00, 0xE5):
            return ent
    return None


def cluster_data(img, clus, size):
    _, spc, _, _, firstdata = geom(img)
    sec = firstdata + (clus - 2) * spc
    return img[sec*512: sec*512 + size]


def build_tcl(out_path, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n" + pre +
            f'after time {t} {{ type {{{NAME}}} }}\n'
            f'after time {t+3} {{ type "\\r" }}\n'
            f'after time {t+9} {{ puts $__f done; flush $__f; close $__f; exit }}\n')


def run(machine, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zname_", delete=False).name
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

    img = run(args.machine, "/tmp/zname.txt")
    old = find_entry(img, "HI", "TXT")
    new = find_entry(img, "BYE", "TXT")
    print("zerobas after NAME:")
    print(f"  HI.TXT  present: {old is not None}")
    print(f"  BYE.TXT present: {new is not None}")
    ok = old is None and new is not None
    if new is not None:
        clus = int.from_bytes(new[26:28], "little")
        size = int.from_bytes(new[28:32], "little")
        data = cluster_data(img, clus, size)
        print(f"  BYE.TXT cluster={clus} size={size} data={data!r}")
        ok = ok and clus == 4 and size == 26 and data == EXPECT_DATA
    print("functional:", "PASS" if ok else "FAIL")
    rc = rc or (0 if ok else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, "/tmp/zname_ref.txt", cf3300=True)
        same = ref == img
        print(f"\ndifferential vs CF-3300: image "
              f"{'byte-identical' if same else 'DIFFERS'}")
        if not same:
            d = [i for i in range(min(len(img), len(ref))) if img[i] != ref[i]]
            print(f"  {len(d)} differing bytes; first at {[hex(x) for x in d[:8]]}")
        print("differential:", "PASS" if same else "FAIL")
        rc = rc or (0 if same else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
