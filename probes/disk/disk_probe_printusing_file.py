#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""On-disk + differential oracle for zerobas-BASIC PRINT# USING (Phase 2).

PRINT# USING is the file form of PRINT USING: formatted text is written to a
sequential output channel instead of the screen. Because the formatter emits through
the same `pchar`/`print_crlf` sink that PRINT# uses, the same template machinery
applies. The probe writes three formatted lines to a file and CLOSEs it:

  OPEN "U.DAT" FOR OUTPUT AS #1 : A$="cat"
  PRINT #1, USING "###";5          ' "  5"  + CRLF
  PRINT #1, USING "[!]";A$          ' "[c]"  + CRLF   (first-char field)
  PRINT #1, USING "## ";1;2;3       ' " 1  2  3 " + CRLF   (format reuse)
  CLOSE                              ' appends the Ctrl-Z soft-EOF

The on-disk U.DAT is then read straight out of the FAT12 image (ground truth) and
must equal `b"  5\\r\\n[c]\\r\\n 1  2  3 \\r\\n\\x1a"`. The real National CF-3300 writes the
byte-identical file. zerobas is integer-only, so every value is an integer.

Strictly black-box: types REPL lines; the check parses the FAT12 image directly.
The disk is a /tmp copy; the committed test720.dsk is never mutated.
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

# The CF-3300 (National / Japanese ROM) supports only the '#' numeric and '!' first-
# char fields in PRINT USING; the '\..\' fixed field and '&' whole-string field are
# NOT supported on it (it emits the template literally / errors "Illegal function
# call"). The Philips VG-8020 supports the full set, and zerobas matches THAT (see
# basic_probe_printusing.py). So this on-disk differential — for which the CF-3300 is
# the only disk oracle — uses the common subset both ROMs share.
PROGRAM = [
    'open"u.dat" for output as #1',
    'a$="cat"',
    'print#1,using"###";5',
    'print#1,using"[!]";a$',
    'print#1,using"## ";1;2;3',
    "close",
]
EXPECT = b"  5\r\n[c]\r\n 1  2  3 \r\n\x1a"


def read_fat_file(img: bytes, name8: str, ext3: str):
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
        t += 8 if cf3300 else 5
    body.append(f'after time {t+5} {{ exit }}')
    return "set throttle off\n" + "\n".join(body) + "\n"


def run(machine, out, cf3300=False, timeout=150.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zpuf_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, PROGRAM, cf3300))
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
    return read_fat_file(img, "U", "DAT")


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

    got = run(args.machine, "/tmp/zpuf.txt")
    print(f"--- zerobas PRINT# USING ---\non-disk U.DAT = {got!r}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT!r})")
    rc = 0 if okf else 1

    if not args.no_ref:
        ref = run(args.ref_machine, "/tmp/zpuf_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\non-disk U.DAT = {ref!r}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
