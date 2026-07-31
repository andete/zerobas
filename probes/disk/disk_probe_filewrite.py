#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC sequential file WRITE.

Exercises the write path on a /tmp COPY of test720.dsk (the committed image is
NEVER mounted — Disk BASIC writes would mutate it; see [[test-disk-mutation-
gotcha]]):

  OPEN "OUT.TXT" FOR OUTPUT AS #1 : PRINT #1,"hello world" : CLOSE #1
  OPEN "OUT.TXT" FOR INPUT  AS #1 : LINE INPUT #1,A$ : CLOSE #1 : PRINT A$

Three checks:
  1. self round-trip — the second statement prints "hello world" on screen;
  2. on-disk ground truth — OUT.TXT in the image reads back as b"hello world\\r\\n";
  3. differential — the real National CF-3300 Disk BASIC, given the same write,
     produces a byte-identical OUT.TXT data stream.

Strictly black-box: types REPL lines + reads VRAM; the on-disk check parses the
FAT12 image directly (our own filesystem read, no ROM involved). The /tmp copy is
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

TEXT = "hello world"
# MSX Disk BASIC stamps the CP/M text-EOF marker (Ctrl-Z, $1A) when CLOSEing a
# sequential OUTPUT file — confirmed against the real CF-3300 by this probe.
EXPECT_BYTES = b"hello world\r\n\x1a"
WRITE = 'open"out.txt" for output as #1:print#1,"hello world":close#1'
READBACK = 'open"out.txt" for input as #1:line input#1,a$:close#1:print a$'


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
        # follow the FAT12 chain
        while 2 <= clus < 0xFF0 and len(out) < size:
            sec = firstdata + (clus - 2) * spc
            out += img[sec * 512: sec * 512 + spc * 512]
            # next cluster (FAT12 12-bit entry)
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
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    body.append(f'after time {t+4} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n" + "\n".join(body) + "\n")


def run(machine, lines, out, keep_dsk=False, cf3300=False, timeout=110.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zwrite_", delete=False).name
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
    if not os.path.exists(out):
        os.unlink(dsk)
        sys.exit(f"no capture from {machine}")
    cols = 32 if cf3300 else 40
    key = "scr1=" if cf3300 else "scr0="
    rows = []
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            rows = ["".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*cols:(r+1)*cols]).rstrip()
                    for r in range(len(d)//cols)]
    img = open(dsk, "rb").read() if keep_dsk else None
    os.unlink(dsk)
    return rows, img


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

    # zerobas: write + read-back round trip, and keep the image for the byte check.
    rows, img = run(args.machine, [WRITE, READBACK], "/tmp/zwrite.txt", keep_dsk=True)
    print("--- zerobas write -> read-back ---")
    for i, r in enumerate(rows):
        if r.strip():
            print(f"{i:2}|{r}")
    ok1 = any(r.strip() == TEXT for r in rows)
    print("round-trip:", "PASS" if ok1 else "FAIL (screen != 'hello world')")
    got = read_fat_file(img, "OUT", "TXT")
    ok2 = got == EXPECT_BYTES
    print(f"on-disk OUT.TXT = {got!r}")
    print("on-disk bytes:", "PASS" if ok2 else f"FAIL (expected {EXPECT_BYTES!r})")
    rc = rc or (0 if ok1 and ok2 else 1)

    if not args.no_ref:
        _, refimg = run(args.ref_machine, [WRITE], "/tmp/zwrite_ref.txt",
                        keep_dsk=True, cf3300=True)
        refbytes = read_fat_file(refimg, "OUT", "TXT")
        print(f"\n--- CF-3300 differential ---\non-disk OUT.TXT = {refbytes!r}")
        ok3 = refbytes == got == EXPECT_BYTES
        print("differential:", "PASS — byte-identical to zerobas" if ok3
              else "FAIL — CF-3300 bytes differ")
        rc = rc or (0 if ok3 else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
