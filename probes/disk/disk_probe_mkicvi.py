#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC MKI$ / CVI (Phase 2c).

MKI$(n) packs a 16-bit integer into a 2-byte string (little-endian); CVI(s$) is the
inverse (the integer from the first 2 bytes of s$). The HANDLERS live in the disk
ROM, so the runtime oracle is the real National CF-3300 (the diskless VG-8020 only
tokenises them — MKI$ = $FF$AE, CVI = $FF$A8). On a /tmp COPY of test720.dsk:

  A$ = MKI$(258) : OPEN "M.DAT" FOR OUTPUT AS #1 : PRINT #1,A$; : CLOSE #1
  B = CVI(A$) : PRINT "<";B;">"

Two checks, both differential vs the CF-3300:
  1. byte layout — M.DAT holds b"\\x02\\x01\\x1a" (258 = 0x0102 little-endian, then
     the OUTPUT-close Ctrl-Z): pins MKI$'s exact byte order;
  2. round trip — the screen shows CVI(MKI$(258)) = 258.

Strictly black-box: types REPL lines, reads the FAT12 image + VRAM. /tmp copy only.
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

# One line (the CF-3300 garbles a SECOND typed line; one long line types fine).
# a$ = MKI$(258); c$ = MKI$(CVI(a$)) — if CVI inverts MKI$, c$ == a$. Both are
# written to M.DAT, so the file pins BOTH the MKI$ byte order AND the CVI round trip
# entirely on disk (no fragile screen scrape). PRINT# takes string VARS (a$/c$), so
# the intermediate b/c$ are needed (a function can't go straight into PRINT#).
PROGRAM = [
    'a$=mki$(258):b=cvi(a$):c$=mki$(b):'
    'open"m.dat" for output as #1:print#1,a$;:print#1,c$;:close#1',
]
# 258 = 0x0102 LE -> 02 01 ; the CVI round trip reproduces it -> 02 01 ; + close Ctrl-Z
EXPECT_BYTES = b"\x02\x01\x02\x01\x1a"


def read_fat_file(img, name8, ext3):
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
        if not ent or ent[0] in (0x00, 0xE5) or ent[0:11] != want:
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
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zmki_", delete=False).name
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
    cols = 32 if cf3300 else 40
    key = "scr1=" if cf3300 else "scr0="
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    return read_fat_file(img, "M", "DAT")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_BASIC_DISK"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    rc = 0

    mki = run(args.machine, PROGRAM, "/tmp/zmki.txt")
    print("--- zerobas MKI$ / CVI (a$=MKI$(258), c$=MKI$(CVI(a$))) ---")
    print(f"on-disk M.DAT = {mki!r}")
    okf = mki == EXPECT_BYTES
    print("functional:", "PASS" if okf else f"FAIL (want {EXPECT_BYTES!r})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        rmki = run(args.ref_machine, PROGRAM, "/tmp/zmki_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\non-disk M.DAT = {rmki!r}")
        okr = rmki == mki == EXPECT_BYTES
        print("differential:", "PASS — byte-identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
