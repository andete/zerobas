#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC OPEN ... FOR APPEND.

On a /tmp COPY of test720.dsk (committed image NEVER mounted):

  OPEN "AP.TXT" FOR OUTPUT AS #1 : PRINT #1,"first"  : CLOSE #1
  OPEN "AP.TXT" FOR APPEND AS #1 : PRINT #1,"second" : CLOSE #1

APPEND opens an existing sequential file and positions the write cursor at its end,
so the second PRINT# extends the file rather than truncating it. Checks:
  1. on-disk ground truth — AP.TXT == b"first\\r\\nsecond\\r\\n\\x1a": APPEND positions
     the cursor ON the original trailing Ctrl-Z and overwrites it (CP/M text append),
     so the file ends with exactly ONE Ctrl-Z (CF-3300-observed, --show-ref);
  2. differential — the real National CF-3300 Disk BASIC, given the identical
     program, produces a byte-identical AP.TXT.

The EXPECTED bytes are PINNED to the CF-3300 observation (run with --show-ref to
print the reference bytes when first establishing the target). "APPEND" is NOT a
reserved word on the MSX main ROM — it crunches to "APP"(ascii) + END ($81), the
same on the diskless VG-8020 and on zerobas — so the tokenisation is already
byte-identical; only the on-disk RESULT is the differential.

Strictly black-box: types REPL lines; the on-disk check parses the FAT12 image
directly. /tmp copy deleted after.
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
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

PROGRAM = [
    'open"ap.txt" for output as #1',
    'print#1,"first"',
    "close#1",
    'open"ap.txt" for append as #1',
    'print#1,"second"',
    "close#1",
]
# Pinned to the CF-3300 observation (--show-ref): APPEND positions the cursor ON
# the original file's trailing Ctrl-Z soft-EOF and overwrites it, then CLOSE re-
# stamps a single Ctrl-Z at the new end — so the original $1A is GONE (CP/M text
# append). Not "first\r\n\x1asecond..." (that would keep the embedded marker).
EXPECT = b"first\r\nsecond\r\n\x1a"


def read_fat_file(img: bytes, name8: str, ext3: str) -> bytes | None:
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
        body.append('after time 11 { type "\\r" }')
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += 6
    body.append(f'after time {t+4} {{ close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n" + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=140.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zapp_", delete=False).name
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
    img = open(dsk, "rb").read()
    os.unlink(dsk)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    ap.add_argument("--show-ref", action="store_true",
                    help="run ONLY the CF-3300 and print its AP.TXT bytes (to pin EXPECT)")
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    if args.show_ref:
        refimg = run(args.ref_machine, PROGRAM, "/tmp/zapp_ref.txt", cf3300=True)
        print(f"CF-3300 AP.TXT = {read_fat_file(refimg, 'AP', 'TXT')!r}")
        return 0

    rc = 0
    img = run(args.machine, PROGRAM, "/tmp/zapp.txt")
    got = read_fat_file(img, "AP", "TXT")
    print("--- zerobas OPEN FOR APPEND ---")
    print(f"on-disk AP.TXT = {got!r}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT!r})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        refimg = run(args.ref_machine, PROGRAM, "/tmp/zapp_ref.txt", cf3300=True)
        ref = read_fat_file(refimg, "AP", "TXT")
        print(f"\n--- CF-3300 differential ---\non-disk AP.TXT = {ref!r}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — byte-identical to zerobas" if okr
              else "FAIL — CF-3300 bytes differ")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
