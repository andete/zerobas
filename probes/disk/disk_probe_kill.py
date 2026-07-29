#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC KILL (Phase 2 Step 2).

On a /tmp COPY of test720.dsk (the committed image is NEVER mounted), deletes an
existing file and checks the on-disk effect:

  KILL "HI.TXT"

Checks:
  1. functional — after KILL, HI.TXT is no longer found in the directory, its
     directory entry's first byte is the $E5 deleted-marker, and its FAT cluster
     (4) is freed back to 0;
  2. differential — the real National CF-3300 Disk BASIC, given the same KILL,
     produces a byte-identical disk image (KILL touches only the dir entry's
     first byte + the FAT chain, so the two images must match exactly).

Strictly black-box: types a REPL line, then parses the FAT12 image directly (our
own filesystem read). The /tmp copy is deleted after extraction.
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

KILL = 'kill"hi.txt"'


def geom(img):
    rsvd = int.from_bytes(img[14:16], "little")
    nfat = img[16]
    spf = int.from_bytes(img[22:24], "little")
    rootents = int.from_bytes(img[17:19], "little")
    spc = img[13]
    firstroot = rsvd + nfat * spf
    rootsecs = (rootents * 32 + 511) // 512
    return rsvd, nfat, spf, rootents, spc, firstroot, rootsecs


def find_entry(img, name8, ext3):
    rsvd, nfat, spf, rootents, spc, firstroot, rootsecs = geom(img)
    want = name8.ljust(8).upper().encode() + ext3.ljust(3).upper().encode()
    base = firstroot * 512
    for e in range(rootents):
        ent = img[base + e*32: base + e*32 + 32]
        if ent[0:11] == want and ent[0] not in (0x00, 0xE5):
            return base + e*32, ent
    return None, None


def fat12_get(img, clus):
    rsvd = int.from_bytes(img[14:16], "little")
    off = rsvd * 512 + clus + clus // 2
    pair = int.from_bytes(img[off:off+2], "little")
    return (pair >> 4) if (clus & 1) else (pair & 0x0FFF)


def build_tcl(out_path, cf3300):
    pre = 'after time 11 { type "\\r" }\n' if cf3300 else ""
    t = 16 if cf3300 else 8
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + pre +
            f'after time {t} {{ type {{{KILL}}} }}\n'
            f'after time {t+3} {{ type "\\r" }}\n'
            f'after time {t+9} {{ puts $__f "done"; flush $__f; close $__f; exit }}\n')


def run(machine, out, cf3300=False, timeout=90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zkill_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, cf3300))
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
    off0, ent0 = find_entry(src, "HI", "TXT")
    clus0 = int.from_bytes(ent0[26:28], "little")
    print(f"before: HI.TXT at dir offset {off0:#x}, first cluster {clus0}, "
          f"FAT[{clus0}]={fat12_get(src, clus0):#05x}")

    img = run(args.machine, "/tmp/zkill.txt")
    # functional checks
    live, _ = find_entry(img, "HI", "TXT")
    marker = img[off0]
    fat_after = fat12_get(img, clus0)
    print(f"\nzerobas after KILL: live entry={live}, dir[{off0:#x}]={marker:#04x}, "
          f"FAT[{clus0}]={fat_after:#05x}")
    ok = live is None and marker == 0xE5 and fat_after == 0
    print("functional:", "PASS" if ok else "FAIL")
    rc = rc or (0 if ok else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, "/tmp/zkill_ref.txt", cf3300=True)
        same = ref == img
        print(f"\ndifferential vs CF-3300: image {'byte-identical' if same else 'DIFFERS'}")
        if not same:
            # narrow to the dir entry + FAT region for diagnostics
            rsvd, nfat, spf, *_ = geom(src)
            d = [i for i in range(len(img)) if i < len(ref) and img[i] != ref[i]]
            print(f"  {len(d)} differing bytes; first few at "
                  f"{[hex(x) for x in d[:8]]}")
        print("differential:", "PASS" if same else "FAIL")
        rc = rc or (0 if same else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
