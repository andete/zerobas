#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""dskfmt-acceptance: DSKFMT ($401C) formats as the National CF-3300 does, and the
disk it makes WORKS (D-DSKFMT; D-SIDEWRITE).

For each choice it builds probes/disk/dskfmt.asm's throwaway boot disk
(build_dskfmt_disk.py) and captures both machines at the program's `done` loop
(disk_probe_diff.py capture, armed on the program's own $A5 marker). The program
calls CHOICE, DSKFMT, reads sectors 0..7 back through DSKIO, then -- through MSX-DOS's
own BDOS -- resets the disk, FMAKEs T.DAT, writes a record, closes, reopens and reads it
back. A choice PASSES when:
  * every differing byte is CHOICE's HL (a pointer into each ROM: $0400-$0401) or in
    sector 0 from offset $1E on (the boot CODE: ours is our own loader, by design --
    the BPB at offsets 0..$1D, both FATs and the root are compared and must match);
  * DSKFMT answered A = 0, Cy = 0, B = 0 on both;
  * the record came back (codes+26 = 1) on both, after five BDOS answers of 0.
The values are printed, not only their agreement: a case that agrees can agree on a
failure.

Usage: python3 probes/disk/dskfmt_acceptance.py [--choices 1,4] [--dos-disk D]
Choice 4 takes the CF-3300 ~3 minutes.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from disk_bdos_acceptance import DEFAULT_DOS_DISK  # noqa: E402
import probe_tmp  # noqa: E402

CODES = 0x0400
SECTOR0 = 0x04C0
MARK = CODES + 27
BOOTCODE = (SECTOR0 + 0x1E, SECTOR0 + 0x200)      # sector 0's code area


def run_choice(c: int, dos_disk: str, work: str) -> bool:
    dsk = os.path.join(work, f"dskfmt_c{c}.dsk")
    out = subprocess.run(["python3", os.path.join(HERE, "build_dskfmt_disk.py"),
                          "--dos-disk", dos_disk, "--choice", str(c), "--out", dsk],
                         capture_output=True, text=True)
    m = re.search(r"done = (0x[0-9a-fA-F]+)", out.stdout)
    if out.returncode or not m:
        print(f"  FAIL  choice {c}: the probe disk did not build\n{out.stdout}{out.stderr}")
        return False
    done = m.group(1)
    cap = subprocess.run(["python3", "-u", os.path.join(HERE, "disk_probe_diff.py"), "capture",
                          "--at", done, "--arm-addr", done, "--arm-check-addr", hex(MARK),
                          "--arm-check-val", "0xA5", "--settle", "300", "--machine", "both",
                          "--mem", f"{CODES:#06x}:0x10C0", "--diska", dsk],
                         capture_output=True, text=True)
    txt = cap.stdout + cap.stderr
    if "ALIGNED: both hit" not in txt:
        print(f"  FAIL  choice {c}: a side never reached `done` -- NOTHING WAS MEASURED\n{txt[-1500:]}")
        return False
    hs = re.search(r"head stock: ([0-9A-F ]+)", txt)
    ho = re.search(r"head ours : ([0-9A-F ]+)", txt)
    runs = re.search(r"diff runs: (.*)", txt)
    if not hs or not ho:
        print(f"  FAIL  choice {c}: no block head in the capture (the tool changed?)")
        return False
    s = [int(x, 16) for x in hs.group(1).split()]
    o = [int(x, 16) for x in ho.group(1).split()]
    ok = True
    for side, v in (("stock", s), ("ours", o)):
        fmt, use, back = v[2:5], v[21:26], v[26]
        print(f"  choice {c} {side:5s}: DSKFMT A/Cy/B {fmt}  BDOS {use}  record back {back}")
        if fmt != [0, 0, 0] or use != [0, 0, 0, 0, 0] or back != 1:
            ok = False
    stray = []
    if runs:
        for r in runs.group(1).split(", "):
            a, _, b = r.partition("-")
            a = int(a, 16)
            b = int(b, 16) if b else a
            if (a, b) == (CODES, CODES + 1) or (BOOTCODE[0] <= a and b < BOOTCODE[1]):
                continue
            stray.append(r)
    if stray:
        print(f"  choice {c}: DIFFERS outside CHOICE's pointer and the boot code: {', '.join(stray)}")
        ok = False
    print(f"  {'PASS' if ok else 'FAIL'}  choice {c}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--choices", default="1,2,3,4")
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK)
    args = ap.parse_args()
    if not os.path.isfile(args.dos_disk):
        print(f"DOS source disk not found: {args.dos_disk}", file=sys.stderr)
        return 2
    work = probe_tmp.tmp("dskfmt_acc")
    os.makedirs(work, exist_ok=True)
    res = [run_choice(int(c), args.dos_disk, work) for c in args.choices.split(",")]
    print(f"===== dskfmt-acceptance: {sum(res)}/{len(res)} choices PASS =====")
    return 0 if all(res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
