#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The XDENT probes' cases, shared by docs/disk/GETDPB.md's and docs/disk/DSKCHG.md's rules (xgetdpb_rules.py,
xdskchg_rules.py): probes/bios/spec/xdent1.asm (run 1, scratchpad/XDENT1_run1.out) and xdent2.asm (run 1,
XDENT2_run1.out), xdent3.asm to xdent7.asm (run 1 each; xdent5 and xdent6 with drive A EMPTY), row D -- the VG-8020 + NMS 1200 against zerobas's disk build (the NODISK row has no disk ROM: its
records are skipped, 0). The 30-byte record: A, F, B, C, D, E, H, L, the interrupt state after, the buffer's 21 bytes
from HL ($A400, filled with $E5 before each call)."""
import os
import re
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
HL_IN = 0xA400
# per run: every step in order -- a call (case id, the entry, B in, C in, what) or a wait ("WAIT", timer interrupts)
# / a busy wait with interrupts off ("BUSY", 0 interrupts: none are taken). Only calls record.
W = lambda n: ("WAIT", n)          # noqa: E731
STEPS = {
    "XDENT1_run1.out": [("XE1 0", "MTOFF", 0x00, 0x00, "MTOFF"),
                        ("XE1 1", "GETDPB", 0xF9, 0xF9, ""), ("XE1 2", "GETDPB", 0xF8, 0xF8, ""),
                        ("XE1 3", "GETDPB", 0xFF, 0xFF, ""), ("XE1 4", "GETDPB", 0xFA, 0xFA, ""),
                        ("XE1 5", "GETDPB", 0xF9, 0x00, "C $00"),
                        ("XE1 6", "DSKCHG", 0x00, 0xF9, "first, after the GETDPBs"),
                        ("XE1 7", "DSKCHG", 0x00, 0xF9, "again")],
    "XDENT2_run1.out": [("XE2 0", "DSKCHG", 0x00, 0xF9, "first"), ("XE2 1", "DSKCHG", 0x00, 0xF9, "again"), W(48),
                        ("XE2 2", "DSKCHG", 0x00, 0xF9, "after ~1 s idle"), W(152),
                        ("XE2 3", "DSKCHG", 0x00, 0xF9, "after ~3 s idle"), W(504),
                        ("XE2 4", "DSKCHG", 0x00, 0xF9, "after ~10 s idle"),
                        ("XE2 5", "GETDPB", 0xFE, 0xFE, ""), ("XE2 6", "GETDPB", 0xFC, 0xFC, ""),
                        ("XE2 7", "GETDPB", 0xFD, 0xFD, "")],
    "XDENT3_run1.out": [("XE3 0", "DSKCHG", 0x00, 0xF8, "first, C $F8 (the disk is $F9)"),
                        ("XE3 1", "GETDPB", 0xF9, 0xF8, "C $F8"), W(48),
                        ("XE3 2", "DSKCHG", 0x00, 0xF9, "~1 s"), W(48), ("XE3 3", "DSKCHG", 0x00, 0xF9, "~2 s"), W(48),
                        ("XE3 4", "DSKCHG", 0x00, 0xF9, "~3 s"), W(48), ("XE3 5", "DSKCHG", 0x00, 0xF9, "~4 s"), W(176),
                        ("XE3 6", "GETDPB", 0xF9, 0xF9, "after ~3.5 s idle"),
                        ("XE3 7", "DSKCHG", 0x00, 0xF9, "right after that GETDPB"),
                        ("XE3 8", "MTOFF", 0x00, 0x00, "MTOFF"), ("XE3 9", "DSKCHG", 0x00, 0xF9, "right after MTOFF"),
                        ("BUSY", 0), ("XE3 10", "DSKCHG", 0x00, 0xF9, "after ~3.5 s with interrupts OFF")],
    "XDENT4_run1.out": [("XE4 0", "DSKCHG", 0x00, 0xF9, "first"), ("XE4 1", "DSKCHG", 0x00, 0xF8, "at once, C $F8"),
                        W(96), ("XE4 2", "DSKCHG", 0x00, 0xF8, "at 96, C $F8"), W(96),
                        ("XE4 3", "MTOFF", 0x00, 0x00, "MTOFF at 96"), ("XE4 4", "DSKCHG", 0x00, 0xF9, "after it"),
                        W(304), ("XE4 5", "DSKCHG", 0x00, 0xF9, "at 304")],
    # drive A EMPTY (no @disk): a DSKCHG that would read fails, and the count does not restart
    "XDENT5_run1.out": [("XE5 0", "GETDPB", 0xF9, 0xF9, "drive A empty"),
                        ("XE5 1", "DSKCHG", 0x00, 0xF9, "first, drive A empty")],
    "XDENT6_run1.out": [("XE6 0", "DSKCHG", 0x00, 0xF9, "first, drive A empty"),
                        ("XE6 1", "DSKCHG", 0x00, 0xF9, "at once, still empty")],
    "XDENT7_run1.out": [("XE7 0", "DSKCHG", 0x00, 0xFA, "first, C $FA (above the disk's $F9)")]}
NODISK = {"XDENT5_run1.out", "XDENT6_run1.out"}         # a failed read does not restart the count (XE6 1)


def timeline(run):
    """{case id: timer interrupts since the last DSKCHG that READ the disk (None: no read yet)} -- the model: a
    DSKCHG reads when none has yet, or when 96 interrupts or more have passed since the last read; B 1 answers and
    GETDPB / MTOFF do not read"""
    out, since = {}, None
    for st in STEPS[run]:
        if st[0] in ("WAIT", "BUSY"):
            if since is not None:
                since += st[1]
            continue
        out[st[0]] = since
        if st[1] == "DSKCHG" and (since is None or since >= 96) and run not in NODISK:
            since = 0
    return out


# D-DISKFORCBIOS (b) (2026-11-22): row N, the NMS 8250's built-in drive (MSX2, the Philips-style FDC), the same
# probes' run 3 (XDENTn_run3.out, `--row nms8250`) -- does the model hold on another interface? Its ids carry an N
# ("XE2 N1"); row D's are as they were.
ROWS = [("D", "_run1.out", " disk: "), ("N", "_run3.out", " nms8250: ")]


def cases(entry):
    d = {"ref": [], "zb": []}
    for run1, steps in STEPS.items():
      for row, suffix, head in ROWS:
        run = run1.replace("_run1.out", suffix)
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        sec = t[t.index(head):]
        sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
            b += bytes(max(0, 30 * len(steps) - len(b)))          # (calls only record; this pads enough)
            tl = timeline(run1)
            calls = [st for st in steps if st[0] not in ("WAIT", "BUSY")]
            for i, (cid, ent, bin_, cin, what) in enumerate(calls):
                if ent != entry:
                    continue
                r = b[30 * i: 30 * (i + 1)]
                rid = cid if row == "D" else cid.replace(" ", " N")
                d[who].append(NS(src="XE", id=rid, row=row, ref_only=(row == "N"), entry=ent, bin=bin_, cin=cin, what=what, run=run1,
                                 since=tl[cid], empty=run1 in NODISK,
                                 a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7],
                                 iff=r[8], dpb=list(r[9:30])))
    return d
