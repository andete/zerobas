#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + structural oracle for zerobas-BASIC CALL FORMAT (Phase 2).

CALL FORMAT lays a fresh empty 720 KB FAT12 filesystem onto the disk (drive A, no
prompts — zerobas-disk has a single geometry so there is nothing to choose). The
probe starts from a junk-filled image, formats it, then writes and reads a file back:

  CALL FORMAT
  OPEN "T.DAT" FOR OUTPUT AS #1 : PRINT #1,"hi" : CLOSE   ' -> T.DAT = "hi\\r\\n\\x1a"

Two checks:
  1. STRUCTURAL — the boot sector's BPB geometry (offsets 11..27), the FAT head, and
     an empty root region match a real National CF-3300 "2 sides, double track" (720K)
     format, captured black-box (the values below). The boot-CODE region and OEM name
     are zerobas' own and are NOT compared — reproducing the CF-3300 boot bytes would
     mean copying ROM code (documented divergence; the CF-3300 also writes no $55AA).
  2. FUNCTIONAL — the freshly formatted disk is a working filesystem: the file written
     after CALL FORMAT round-trips (proving the BPB, FAT and dir are all valid).

Strictly black-box: types REPL lines; parses the FAT12 image directly. The disk is a
/tmp junk copy; the committed test720.dsk is never touched.
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

# BPB geometry bytes 11..27 (17 bytes) of real CF-3300 formats — captured black-box
# (call format -> drive A -> CHOICE -> strike key). zerobas's 1=360K menu choice must
# match the CF-3300 "2 - 2 sides" (media $FD, 720 sectors, 2 sec/FAT); 2=720K must match
# "4 - 2 sides, double track" (media $F9, 1440 sectors, 3 sec/FAT).
CF3300_BPB_720 = bytes.fromhex("0002020100027000a005f9030009000200")
CF3300_BPB_360 = bytes.fromhex("0002020100027000d002fd020009000200")
# (geometry key, menu choice key, expected BPB, expected FAT head)
GEOMS = [
    ("720K", "2", CF3300_BPB_720, bytes([0xF9, 0xFF, 0xFF])),
    ("360K", "1", CF3300_BPB_360, bytes([0xFD, 0xFF, 0xFF])),
]
FILE_EXPECT = b"hi\r\n\x1a"


def program(choice):
    # CALL FORMAT now prompts a geometry menu; the choice is read via the REPL line
    # editor, so it is typed as its own line right after `call format`.
    return [
        "call format",
        choice,
        'open"t.dat" for output as #1',
        'print#1,"hi"',
        "close",
    ]


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


def build_tcl(lines):
    body, t = [], 8
    for ln in lines:
        body.append(f'after time {t} {{ type {{{ln}}} }}')
        body.append(f'after time {t+3} {{ type "\\r" }}')
        t += 7
    body.append(f'after time {t+8} {{ exit }}')
    return "set throttle off\n" + "\n".join(body) + "\n"


def run(machine, choice):
    # a junk-filled image: proves CALL FORMAT writes real structures, not leftovers.
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zfmt_", delete=False).name
    open(dsk, "wb").write(b"\xE5" * (720 * 1024))
    tcl = tempfile.NamedTemporaryFile(suffix=".tcl", delete=False).name
    open(tcl, "w").write(build_tcl(program(choice)))
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", tcl],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 120
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk); os.unlink(tcl)
        sys.exit(f"TIMEOUT running {machine}")
    img = open(dsk, "rb").read()
    os.unlink(dsk); os.unlink(tcl)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    # ⚠️ This used to `ap.parse_args()` and DISCARD the result, then boot a hardcoded
    # "C-BIOS_MSX1_EU_BASIC_DISK" below — so CALL FORMAT ran on the LEAN build under
    # `make diskbasic-acceptance-repack` too, and the runner's wiring guard passed it
    # anyway because the env-var NAME appears in this source. Found 2026-07-29 by S1's
    # fallback sweep (docs/spec-lean-retire-s1-explicit-machine.md §1.4).
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    rc = 0

    for name, choice, exp_bpb, exp_fat in GEOMS:
        img = run(args.machine, choice)
        bpb = img[11:28]
        fathead = img[512:515]
        oks = bpb == exp_bpb and fathead == exp_fat
        got = read_fat_file(img, "T", "DAT")
        okf = got == FILE_EXPECT
        print(f"=== {name} (menu choice {choice!r}) ===")
        print(f"  structural: BPB[11:28]={bpb.hex()} FAThead={fathead.hex()}"
              f"  {'PASS' if oks else 'FAIL vs ' + exp_bpb.hex()}")
        print(f"  functional: T.DAT={got!r}  {'PASS' if okf else 'FAIL'}")
        rc = rc or (0 if oks and okf else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
