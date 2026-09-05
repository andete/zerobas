#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUTCUT -- a machine reset BETWEEN a RANDOM `PUT` and its `CLOSE`, MEASURED.

TODO (filed 2026-07-31 by D-RNDDIR, re-examined 2026-08-09 and recorded NOT
MEASURABLE): in that window the two disks are believed to differ -- the reference
has stamped nothing and loses the write, while zerobas's root-directory entry is
already stamped and points at a chain whose FAT state at that instant NOTHING HAS
EXAMINED. Both re-examinations said the same thing: *"it needs power cut
mid-program, and the harness reads the image after the machine exits normally."*

🎯 THE POWER CUT IS ONE TCL LINE. openMSX backs a `-diska` image with the host
file and writes sectors through as the guest issues them, so **killing the
emulator IS the power cut** and the `.dsk` left on disk is the artifact. The only
real requirement is that the cut land at a chosen INSTANT rather than a guessed
one, and the guest can say when: the program POKEs a sentinel after `PUT` and
then spins, and the script polls that byte and exits the moment it appears. No
race, no sleep-and-hope.

⚠️ THE CONTROL IS NOT OPTIONAL HERE. "zerobas's entry is stamped" means nothing
without the same machine's CLEAN-CLOSE image beside it -- an entry present after
a cut is only interesting if it differs from what a normal `CLOSE` produces, and
an entry ABSENT after a cut is only interesting if a clean run would have made
one. So every machine runs both arms and the four images are compared as a
matrix, not as two readings.

WHAT IS READ, straight out of the FAT12 image (layout from tools/make_test_dsk.py:
FAT at sector 1, root dir at sector 7, data from sector 14):
  * the root-directory entry for the file -- present? size? first cluster?
  * that cluster's FAT12 value -- free, a chain, or EOC?
  * the data sector itself -- did the record's bytes land?

    python3 scratchpad/putcut_probe.py
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_preflight                                              # noqa: E402
from make_test_dsk import (Fat12Image, SECTOR, FIRST_FAT, FIRST_ROOT,  # noqa: E402
                           FIRST_DATA, SEC_PER_CLUS, ROOT_ENTRIES)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MARK = 0xD005
REC = "ZEROBAS-RECORD1"          # exactly 15 chars + the LSET pad = 16
MACHINES = [("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK"),
            ("CF-3300", "National_CF-3300")]


def program(close: bool):
    """The cut arm spins after PUT; the control arm CLOSEs first. Everything
    else is identical, so the only difference between the two images is the
    CLOSE."""
    return ["10 OPEN\"R.DAT\"AS#1 LEN=16",
            "20 FIELD#1,16 AS A$",
            f"30 LSET A$=\"{REC}\"",
            "40 PUT#1,1"] + \
           (["45 CLOSE#1"] if close else []) + \
           [f"50 POKE&H{MARK:04X},&HA5",
            "60 GOTO 60"]


def run(machine, close, timeout=150.0):
    subprocess.run(["pkill", "-9", "openmsx"], capture_output=True)
    time.sleep(1.0)
    tmp = tempfile.mkdtemp(prefix="putcut_")
    d = Fat12Image()
    d.add_file("AUTOEXEC", "BAS",
               ("\r\n".join(program(close)) + "\r\n").encode())
    dk = os.path.join(tmp, "d.dsk")
    open(dk, "wb").write(d.finish())
    # Poll the guest's own sentinel and exit the INSTANT it appears -- that is
    # the power cut, placed by the guest rather than by a guessed delay.
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"proc chk {{}} {{\n"
           f"  if {{[debug read memory 0x{MARK:04X}] == 165}} {{ exit }}\n"
           f"  after time 0.2 chk\n"
           f"}}\n"
           f"after time 6 chk\n"
           f"after time 100 {{ exit }}\n")
    tp = os.path.join(tmp, "s.tcl")
    open(tp, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dk, "-script", tp]
    p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    return open(dk, "rb").read()


def fat12_get(img, n):
    off = FIRST_FAT * SECTOR + (n * 3) // 2
    w = img[off] | (img[off + 1] << 8)
    return (w >> 4) if (n & 1) else (w & 0x0FFF)


def inspect(img):
    """The root entry, its cluster's FAT value, and whether the record landed."""
    out = {"entry": None, "size": None, "clus": None, "fat": None, "data": False}
    for i in range(ROOT_ENTRIES):
        e = img[FIRST_ROOT * SECTOR + i * 32: FIRST_ROOT * SECTOR + i * 32 + 32]
        if e[0] in (0x00, 0xE5):
            continue
        if e[:11] == b"R       DAT":
            out["entry"] = True
            out["clus"] = e[26] | (e[27] << 8)
            out["size"] = int.from_bytes(e[28:32], "little")
            break
    if out["entry"] and out["clus"]:
        out["fat"] = fat12_get(img, out["clus"])
        sec = FIRST_DATA + (out["clus"] - 2) * SEC_PER_CLUS
        out["data"] = REC.encode() in img[sec * SECTOR:(sec + 1) * SECTOR]
    return out


def fmt(r):
    if not r["entry"]:
        return "no directory entry"
    # 🔴 clus == 0 IS A REAL STATE, not a missing reading, and the first cut of
    # this formatter crashed on it -- `if entry and clus` skipped the FAT lookup
    # and left fat=None. A directory entry that names a file and points at
    # cluster 0 points at NOTHING; it has to be reported, not fallen over.
    if not r["clus"]:
        return (f"entry PRESENT but clus=0 (points at NOTHING)  "
                f"size={r['size']}  no chain, no data")
    f = r["fat"]
    fat = ("free" if f == 0 else "EOC" if f >= 0xFF8 else f"-> {f}")
    return (f"entry PRESENT  size={r['size']}  clus={r['clus']}  "
            f"FAT={fat}  record bytes on disk: {'YES' if r['data'] else 'no'}")


def main():
    print("=== D-PUTCUT: power cut between a RANDOM PUT and its CLOSE ===\n")
    print("program (the two arms differ only by line 45):")
    for l in program(False):
        print("   ", l)
    print("    45 CLOSE#1                <- present in the CONTROL arm only\n")
    results = {}
    for label, mach in MACHINES:
        for close in (True, False):
            arm = "clean CLOSE" if close else "CUT after PUT"
            img = run(mach, close)
            results[(label, arm)] = inspect(img)
            print(f"  {label:8} {arm:14}  {fmt(results[(label, arm)])}")
    print("\n=== the matrix, read as the filing asks")
    for label, _m in MACHINES:
        c = results[(label, "clean CLOSE")]
        k = results[(label, "CUT after PUT")]
        same = fmt(c) == fmt(k)
        print(f"  {label:8} cut vs clean: "
              f"{'IDENTICAL — the CLOSE changes nothing on disk' if same else 'DIFFER'}")
    zb = results[("zerobas", "CUT after PUT")]
    rf = results[("CF-3300", "CUT after PUT")]
    print(f"\n  after the cut, zerobas vs CF-3300: "
          f"{'AGREE' if fmt(zb) == fmt(rf) else '🔴 DIFFER'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
