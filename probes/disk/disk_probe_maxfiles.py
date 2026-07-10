#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC MAXFILES / multi-channel.

Proves the Phase-2 multi-channel table (which retires the single-channel limit):
two sequential OUTPUT files are open AT THE SAME TIME and written INTERLEAVED, so
the per-channel buffering must keep each channel's 512-byte data buffer + write
state independent across repeated channel switches. On a /tmp COPY of test720.dsk
(committed image NEVER mounted — see [[test-disk-mutation-gotcha]]):

  MAXFILES=2
  OPEN "A.TXT" FOR OUTPUT AS #1
  OPEN "B.TXT" FOR OUTPUT AS #2
  PRINT #1,"aaa"
  PRINT #2,"bbb"
  PRINT #1,"ccc"
  PRINT #2,"ddd"
  CLOSE                       (bare CLOSE flushes + closes every open channel)

Each PRINT# switches the active channel, so #1's buffered "aaa\\r\\n" must survive
two saves/restores before "ccc\\r\\n" is appended (and likewise for #2). Checks:
  1. on-disk ground truth — A.TXT == b"aaa\\r\\nccc\\r\\n\\x1a",
                            B.TXT == b"bbb\\r\\nddd\\r\\n\\x1a";
  2. differential — the real National CF-3300 Disk BASIC, given the identical
     program, produces byte-identical A.TXT and B.TXT (Ctrl-Z text-EOF and all).

Strictly black-box: types REPL lines; the on-disk check parses the FAT12 image
directly (our own filesystem read, no ROM involved). /tmp copy deleted after.
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

PROGRAM = [
    "maxfiles=2",
    'open"a.txt" for output as #1',
    'open"b.txt" for output as #2',
    'print#1,"aaa"',
    'print#2,"bbb"',
    'print#1,"ccc"',
    'print#2,"ddd"',
    "close",
]
EXPECT_A = b"aaa\r\nccc\r\n\x1a"
EXPECT_B = b"bbb\r\nddd\r\n\x1a"


def read_fat_file(img: bytes, name8: str, ext3: str) -> bytes | None:
    """Read a file's bytes from a FAT12 image by 8.3 name (no subdirs)."""
    rsvd = int.from_bytes(img[14:16], "little")
    nfat = img[16]
    spf = int.from_bytes(img[22:24], "little")
    rootents = int.from_bytes(img[17:19], "little")
    spc = img[13]
    firstroot = rsvd + nfat * spf
    rootsecs = (rootents * 32 + 511) // 512
    firstdata = firstroot + rootsecs
    want = name8.ljust(8).upper().encode() + ext3.ljust(3).upper().encode()
    for e in range(rootents):
        ent = img[firstroot * 512 + e * 32: firstroot * 512 + e * 32 + 32]
        if not ent or ent[0] in (0x00, 0xE5):
            continue
        if ent[0:11] != want:
            continue
        size = int.from_bytes(ent[28:32], "little")
        clus = int.from_bytes(ent[26:28], "little")
        out = b""
        while 2 <= clus < 0xFF0 and len(out) < size:
            sec = firstdata + (clus - 2) * spc
            out += img[sec * 512: sec * 512 + spc * 512]
            fat_off = rsvd * 512 + clus + (clus // 2)
            pair = int.from_bytes(img[fat_off:fat_off + 2], "little")
            clus = (pair >> 4) if (clus & 1) else (pair & 0x0FFF)
        return out[:size]
    return None


def build_tcl(out_path, lines, cf3300):
    body = []
    t = 12 if cf3300 else 8
    if cf3300:
        body.append('after time 11 { type "\\r" }')   # clear the date prompt
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += 6
    body.append(f'after time {t+4} {{ close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n" + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=150.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zmaxf_", delete=False).name
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
    img = open(dsk, "rb").read()
    os.unlink(dsk)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_BASIC_DISK"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    rc = 0

    img = run(args.machine, PROGRAM, "/tmp/zmaxf.txt")
    a = read_fat_file(img, "A", "TXT")
    b = read_fat_file(img, "B", "TXT")
    print("--- zerobas two-channel interleave ---")
    print(f"on-disk A.TXT = {a!r}")
    print(f"on-disk B.TXT = {b!r}")
    okf = a == EXPECT_A and b == EXPECT_B
    print("functional:", "PASS" if okf
          else f"FAIL (expected A={EXPECT_A!r} B={EXPECT_B!r})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        refimg = run(args.ref_machine, PROGRAM, "/tmp/zmaxf_ref.txt", cf3300=True)
        ra = read_fat_file(refimg, "A", "TXT")
        rb = read_fat_file(refimg, "B", "TXT")
        print("\n--- CF-3300 differential ---")
        print(f"on-disk A.TXT = {ra!r}")
        print(f"on-disk B.TXT = {rb!r}")
        okr = ra == a == EXPECT_A and rb == b == EXPECT_B
        print("differential:", "PASS — byte-identical to zerobas" if okr
              else "FAIL — CF-3300 bytes differ")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
