#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC (tr6): decode the xtrdsk* run files, FS-A1GT beside FS-A1ST.

    python3 scratchpad/xtrdsk_decode.py RUNFILE ...     # one block per file; AE_xtrdsk_decoded.out is all of them

xtrdsk2a/b/c, xtrdsk3a: probes/bios/spec/xtrdsk_body.inc's 17-byte records. xtrdsk2d / 2e: xbsys2.asm's 23-byte
records (+8 = its own IFF sample), plus 2d's early LD A,I sample at $A300 + case and 2e's debugger IFF at the
instruction after CALL BDOS ($A300 + 5n: IFF, time). xtrdsk4*: the phase sweep's counters.
"""
import re
import sys

NAMES = {0x0D: "DSKRST", 0x0E: "SELDSK", 0x18: "LOGIN", 0x19: "CURDRV", 0x1B: "ALLOC", 0x2A: "GDATE", 0x2B: "SDATE",
         0x2C: "GTIME", 0x2D: "STIME", 0xF0: "CHGCPU", 0xF1: "WAIT"}


def recs(h):
    b = bytes.fromhex(h) + bytes(17)       # the run file trims trailing zero bytes
    out = []
    for i in range(0, len(b) - 16, 17):
        r = b[i:i + 17]
        if r[0] == 0:
            break
        out.append(r)
    return out


def fmt(r, t0):
    if r[0] == 0xFE:
        return f"-- group {r[1]}"
    t = int.from_bytes(r[13:17], "little")
    return (f"{NAMES.get(r[0], '%02X' % r[0]):6} A{r[1]:02X} F{r[2]:02X} BC{r[3]:02X}{r[4]:02X} DE{r[5]:02X}{r[6]:02X} "
            f"HL{r[7]:02X}{r[8]:02X} IX{r[9]:02X}{r[10]:02X} {'EI' if r[11] else 'DI'} {'R800' if r[12] else 'Z80 '} "
            f"t={t / 1e6:9.6f}")


def cap(t, side):
    return bytes.fromhex(re.search(r"CAP %s\s*: ([0-9a-f]+)" % side, t).group(1)) + bytes(0x800)


XS2 = ["SDATE", "GDATE", "SDATE", "GDATE", "SDATE", "SDATE", "SDATE", "STIME", "STIME", "STIME", "ALLOC", "ALLOC",
       "SELDSK", "CURDRV", "DSKRST", "CURDRV", "LOGIN"]


def xbsys2_like(t, early):
    print("case  call    | A1GT: xbsys2's sample, " + early + " | A1ST: the same")
    for i in range(17):
        row = []
        for side in ("ref", "ours"):
            b = cap(t, side)
            if early == "early LD A,I":
                e = str(b[0x2FF + i])
            else:                           # 2e: the debugger's IFF at the instruction after CALL BDOS
                r = b[0x2FF + 5 * i:0x2FF + 5 * i + 5]
                e = f"IFF={r[0]} t={int.from_bytes(r[1:], 'little') / 1e6:.6f}"
            row.append(f"{b[i * 23 + 8]}  {e:24}")
        print(f"{i:4}  {XS2[i]:7} | {row[0]} | {row[1]}")


def main():
    for fn in sys.argv[1:]:
        print(f"===== {fn}")
        one(fn)
        print()


def one(fn):
    t = open(fn).read()
    if "xtrdsk2d" in fn:
        return xbsys2_like(t, "early LD A,I")
    if "xtrdsk2e" in fn:
        return xbsys2_like(t, "debugger IFF")
    if "xtrdsk4" in fn:
        for side, name in (("ref", "FS-A1GT"), ("ours", "FS-A1ST")):
            b = cap(t, side)
            n, k = int.from_bytes(b[0:2], "little"), int.from_bytes(b[2:4], "little")
            print(f"{name}: {k} trials, {n} scored DI" + "".join(
                f" k={int.from_bytes(b[4 + 4 * i:6 + 4 * i], 'little')}" for i in range(min(n, 60))))
        return
    ref = recs(re.search(r"CAP ref\s*: ([0-9a-f]+)", t).group(1))
    ours = recs(re.search(r"CAP ours\s*: ([0-9a-f]+)", t).group(1))
    print(f"{'FS-A1GT':66}| FS-A1ST")
    for i in range(max(len(ref), len(ours))):
        a = fmt(ref[i], 0) if i < len(ref) else ""
        b = fmt(ours[i], 0) if i < len(ours) else ""
        mark = "  " if (i < len(ref) and i < len(ours) and ref[i][:12] == ours[i][:12]) else "* "
        print(f"{mark}{i:2} {a:62}| {b}")


if __name__ == "__main__":
    main()
