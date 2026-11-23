#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC: decode the turbo R readings of the tape probes xtap1 / xtap5 (scratchpad/AE_trall/xtap1.out, xtap5.out --
run with biosl_run.py's `@tape` on a machine WITHOUT a cassette port: nothing recorded or played, TAPEREADY
acknowledged with 2) step by step, beside the VG-8020's reading (the page's baseline, XTAP1_run2.out / XTAP5_run1.out,
nodisk row) and the FS-A1WSX's (scratchpad/AE_m1on2/, msx2p row). The step lists are xtap1_model's (STEPS1 / STEPS5).
Records: A F BC DE HL IFF portC (10 bytes); TAPOUT / TAPIN: A F; PORTC: port C once.

    python3 scratchpad/trtap_decode.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "bios", "spec"))
import xtap1_model as G  # noqa: E402


def cap(path, row, who="ref"):
    t = open(os.path.join(ROOT, "scratchpad", path)).read()
    m = re.search(r"===== \S+ " + row + r": .*?CAP " + who + r"\s*: (\w+)", t, re.S)
    return bytes.fromhex(m.group(1)) if m else None


def records(b, steps):
    out, off = [], 0
    for st in steps:
        if st[0] == "PORTC":
            out.append(("PORTC", "", f"portC {b[off]:02X}"))
            off += 1
            continue
        name, ca, cf, ei, pc, de = st
        n = 2 if name in ("TAPOUT", "TAPIN") else 10
        r = b[off:off + n]
        off += n
        entry = f"A{ca:02X}" + (f" F{cf:02X}" if cf is not None else "") + (f" EI{ei}" if ei is not None else "") + \
            (f" pc{pc:02X}" if pc is not None else "")
        if n == 2:
            out.append((name, entry, f"A {r[0]:02X} F {r[1]:02X}"))
        else:
            out.append((name, entry, f"A {r[0]:02X} F {r[1]:02X} BC {r[2]:02X}{r[3]:02X} DE {r[4]:02X}{r[5]:02X} "
                                     f"HL {r[6]:02X}{r[7]:02X} IFF {r[8]} portC {r[9]:02X}"))
    return out


def main():
    for probe, base, steps in (("xtap1", "XTAP1_run2.out", G.STEPS1), ("xtap5", "XTAP5_run1.out", G.STEPS5)):
        gt = cap(f"AE_trall/{probe}.out", "turbor", "ref")
        st = cap(f"AE_trall/{probe}.out", "turbor", "ours")
        vg = cap(base, "nodisk", "ref")
        wsx = cap(f"AE_m1on2/{probe}.out", "msx2p", "ref")
        print(f"===== {probe}: A1GT {'==' if gt == st else '!='} A1ST")
        cols = [("A1GT", gt), ("VG-8020", vg), ("A1WSX", wsx)]
        rec = {n: records(b, steps) for n, b in cols if b}
        for i, (name, entry, r) in enumerate(rec["A1GT"]):
            print(f"{i:2} {name:6} {entry:22} A1GT : {r}")
            for n in ("VG-8020", "A1WSX"):
                if n in rec and rec[n][i][2] != r:
                    print(f"{'':31} {n:5}: {rec[n][i][2]}")
    gt, st = cap("AE_trall/b7tape.out", "turbor", "ref"), cap("AE_trall/b7tape.out", "turbor", "ours")
    print(f"===== b7tape: A1GT {'==' if gt == st else '!='} A1ST")
    print(f"TAPOON CF {gt[0]:02X}  TAPOUT CF-or {gt[1]:02X}  TAPION CF {gt[2]:02X}  TAPIN CF-or {gt[3]:02X}  "
          f"bytes as written {gt[4]:02X}  bytes read {gt[16:32].hex()}")
    vg = cap("AE_cbios_review_d23.out", "nodisk", "ref")
    if vg is not None:
        print(f"VG-8020 (AE_cbios_review_d23.out, b7tape nodisk): {vg[:5].hex()} bytes {vg[16:32].hex()}")


if __name__ == "__main__":
    main()
