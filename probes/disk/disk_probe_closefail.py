#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""closefail-acceptance -- a Disk BASIC CLOSE that FAILS, then a second CLOSE (D-COPYSLOW step 1, 2026-11-28).

Measured on the National CF-3300 (scratchpad/AE_bfiles_u2.out): a failing CLOSE of an OUTPUT channel leaves it OPEN
in RANDOM mode -- the channel block's +0 mode goes 02 -> 04 -- so the SECOND CLOSE is a random-mode close, the
directory entry only. On a FULL disk that succeeds (the channel is freed: D-DISKFULL's face); on a WRITE-PROTECTED
disk it fails again. zerobas's old DOUT_DEAD bit freed the channel silently on BOTH (the wp row was red before).
Two cases, each on both machines, from MSX-DOS's `BASIC`:
    wp     OPEN / PRINT# on a writable disk, the disk swapped (openMSX `diska`) for a READ-ONLY copy -- openMSX mounts
           it write-protected -- then CLOSE, CLOSE
    full   every free cluster marked used, OPEN / PRINT# / CLOSE / CLOSE / OPEN / CLOSE
Compared per case: the message after each typed line, and channel #1's block +0 after each CLOSE (BASIC's own data at
$DD6E with MAXFILES=1 -- a work-area read, not code). Exit 0 when both cases agree, 1 on a divergence, 2 when the
CF-3300 itself did not answer.
"""
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_dossession as D                   # noqa: E402
import disk_probe_diskfull                          # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
OURS = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = {
    "wp": [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("p1", 'PRINT #1,"B"'),
           ("c1", "CLOSE"), ("c2", "CLOSE")],
    "full": [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("p1", 'PRINT #1,"HELLO"'),
             ("c1", "CLOSE"), ("c2", "CLOSE"), ("o2", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("c3", "CLOSE")],
}
BLK0 = 0xDD6E   # channel #1's block +0 at MAXFILES=1, the same address on both (measured)


def run(machine, case):
    steps = CASES[case]
    D.SESSION = [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 8)] + [(t, x, 30) for t, x in steps]
    dsk = probe_tmp.tmp(f"closefail_{case}_{machine}.dsk")
    shutil.copyfile(SRC, dsk)
    if case == "full":
        disk_probe_diskfull.full_disk(dsk)
    ro = probe_tmp.tmp(f"closefail_{case}_{machine}_ro.dsk")
    if os.path.exists(ro):
        os.chmod(ro, 0o644)
    shutil.copyfile(SRC, ro)
    os.chmod(ro, 0o444)
    out = probe_tmp.tmp(f"closefail_{case}_{machine}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = D.tcl(out)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = f"  puts $f \"B0 $tag [rd {BLK0}]\"\n"
    if case == "wp":
        hook += f"  if {{$tag eq \"p1\"}} {{diska {{{ro}}}}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    b = "{boot datecmd basic basicmem}"
    assert tcl.count(b) == 1
    tcl = tcl.replace(b, "{boot datecmd basic basicmem " + " ".join(t for t, _ in steps) + "}")
    sf = probe_tmp.tmp(f"closefail_{case}_{machine}.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", machine, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    if not os.path.exists(out):
        return None
    lines = open(out).read().splitlines()
    b0 = {ln.split()[1]: int(ln.split()[2]) for ln in lines if ln.startswith("B0 ")}
    snap = next((ln for ln in reversed(lines) if ln.startswith(steps[-1][0] + " ")), None)
    if snap is None:
        return None
    p = snap.split()
    w = int(p[1][2:])
    raw = bytes.fromhex(p[3])
    rows = [raw[k * w:(k + 1) * w].decode("latin1").rstrip() for k in range(24)]
    # the message after each typed line: the screen as ONE flat string (a long line WRAPS -- the CF-3300's OPEN line
    # does at 32 / 40 columns), each typed line searched AFTER the previous one (every CLOSE is the same text), and
    # the first non-blank row after the row the line ends on
    # -- matched with SPACES REMOVED, each kept character remembering its row (the CF's BASIC screen here is SCREEN 1
    # at WIDTH 29 inside 32-column rows, so a wrapped line is not rejoined by padding the rows: 2026-11-28)
    chars = [(c, ri) for ri, r in enumerate(rows) for c in r if c != " "]
    flat = "".join(c for c, _ in chars)
    msgs, cur = [], 0
    for t, x in steps:
        xs = x.replace(" ", "")
        i = flat.find(xs, cur)
        if i < 0:
            msgs.append("<line not seen>")
            continue
        cur = i + len(xs)
        nxt = chars[cur - 1][1] + 1
        msg = next((r.strip() for r in rows[nxt:] if r.strip()), "")
        msgs.append("ok" if msg in ("Ok", "ZB") else msg)
    return {"msgs": msgs, "b0": [b0.get(t) for t, _ in steps if t.startswith("c")]}


def main():
    bad = blind = 0
    for case in CASES:
        ref, ours = run("National_CF-3300", case), run(OURS, case)
        if ref is None:
            print(f"  NO-REFERENCE {case}")
            blind += 1
            continue
        same = ours == ref
        print(f"  {'ok  ' if same else 'DIFF'} {case:5s} CF {ref}\n{'':13s}ZB {ours}")
        bad += not same
    print(f"{len(CASES)} cases, {bad} diverge, {blind} without a reference")
    return 2 if blind else 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
