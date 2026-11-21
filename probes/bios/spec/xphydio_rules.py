#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/PHYDIO.md's EXECUTABLE RULES (docs/spec-method.md §3a): PHYDIO ($0144) -- probes/bios/spec/xdsk1.asm
(round 1, cases 00-10, scratchpad/XDSK1_run2.out) and xdsk2.asm (round 2, cases 11-19, scratchpad/XDSK2_run1.out),
both rows: N (no disk interface: H.PHYD a bare RET) and D (the VG-8020 + NMS 1200 against zerobas's disk build).
Each probe's header lists its cases (read here); the 14-byte record is A, F, B, C, D, E, H, L, the interrupt state
after, the 16-bit sum of the 1 KB buffer, the buffer's bytes +0 and +512, a pad.

The model is the probe's own set-up, then the disk IMAGE (disk/empty720.dsk, the same file on both machines): the
buffer after a read holds the image's sectors, never another machine's or another case's reading."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/PHYDIO.md"
RUNS = [("xdsk1.asm", "XDSK1_run2.out"), ("xdsk2.asm", "XDSK2_run1.out")]
REC = 14
SECTORS = 1440
IMAGE = open(os.path.join(ROOT, "disk", "empty720.dsk"), "rb").read()
CASE = re.compile(r";\s+(\d\d): (.*?): A (\d), F \$([0-9A-F]{2}), B (\d+), C \$([0-9A-F]{2}), DE (\d+), "
                  r"HL \$([0-9A-F]{4}), (di|ei), fill (E5|PAT)")
OUTS = ["a", "f", "b", "c", "de", "hl", "iff", "sum", "b0", "b512"]
OUTPUTS = {"XP": OUTS}


def fill(kind):
    if kind == "E5":
        return bytearray([0xE5] * 1024)
    b = bytearray()
    for n in range(256):
        b += bytes([(0x77 + n) & 0xFF, n])
    return b + bytearray([0xE5] * 512)


def sector(n):
    return IMAGE[512 * n: 512 * (n + 1)]


def _cases():
    out = []
    for asm, run in RUNS:
        src = open(os.path.join(HERE, asm)).read()
        head = src[:src.index("; Drive A is a fresh copy")]
        rows = CASE.findall(head)
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for row, tag in (("nodisk", "N"), ("disk", "D")):
            sec = t[t.index(f" {row}: "):]
            sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec     # to the next row's header
            for who, key in (("ref", "ref"), ("zb", "ours")):
                b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
                b += bytes(max(0, REC * len(rows) - len(b)))
                for i, (num, title, a, f, bb, c, de, hl, ei, kind) in enumerate(rows):
                    r = b[REC * i: REC * (i + 1)]
                    out.append((who, NS(src="XP", id=f"XP {tag}{num}", row=tag, num=int(num), title=title,
                                        ain=int(a), fin=int(f, 16), bin=int(bb), cin=int(c, 16), dein=int(de),
                                        hlin=int(hl, 16), ein=ei == "ei", kind=kind,
                                        a=r[0], f=r[1], b=r[2], c=r[3], de=(r[4] << 8) | r[5], hl=(r[6] << 8) | r[7],
                                        iff=r[8], sum=r[9] | (r[10] << 8), b0=r[11], b512=r[12])))
    return out


def cases():
    d = {"ref": [], "zb": []}
    for who, c in _cases():
        d[who].append(c)
    return d


def write(c):
    return c.fin & 1


def count(c):
    return c.bin or 256


def media_ok(c):
    return c.cin in (0xF8, 0xF9, 0xFF)          # the media bytes measured accepted ($00 and $32 refused)


def in_range(c):
    return c.dein + count(c) <= SECTORS


def disk_sector(c, n):
    """sector n as case c finds it: round 1 runs its cases in order on ONE disk, so from case 07 on sector 1439 holds
    what case 06 wrote (the pattern's first 512 bytes); round 2 (cases 11-19) starts from a fresh copy of the image"""
    if n == SECTORS - 1 and 7 <= c.num <= 10:
        return bytes(fill("PAT")[:512])
    return sector(n)


def buffer_after(c, nread):
    """the 1 KB buffer after `nread` sectors read into it from DE (sector $FFFF: 512 zero bytes, measured)"""
    buf = fill(c.kind)
    for k in range(min(nread, 2)):
        s = bytes(512) if c.dein == 0xFFFF else disk_sector(c, c.dein + k)
        buf[512 * k: 512 * (k + 1)] = s
    return buf


def summ(buf):
    return (sum(buf) & 0xFFFF, buf[0], buf[512])


def got(c):
    return (c.sum, c.b0, c.b512)


D = lambda c: c.row == "D"                                  # noqa: E731
OK_READ = lambda c: D(c) and not write(c) and media_ok(c) and (in_range(c) or c.dein == 0xFFFF)   # noqa: E731
S1 = "1. PHYDIO ($0144): a physical sector read or write through the disk interface"

RULES = [
    Rule("R-PD-NODISK", S1, "With no disk interface (row N) PHYDIO returns at once: A, F, BC, DE, HL and the interrupt "
         "state as entered; the buffer is not touched.", lambda c: c.row == "N",
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl, c.iff) == (c.ain, c.fin, c.bin, c.cin, c.dein, c.hlin, int(c.ein))
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-READ", S1, "A read (carry clear) with an accepted media byte ($F8, $F9, $FF measured) and the sectors "
         "within the disk (DE + B <= 1440) puts sectors DE, DE + 1, ... into memory from HL ($A400 and $8000 "
         "measured) and returns A 0, F $42, B 0, C $32, D = the entry A, E = the entry F, HL as entered. Case 07 "
         "reads back what case 06 wrote.", lambda c: OK_READ(c) and c.dein != 0xFFFF,
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (0, 0x42, 0, 0x32, (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(buffer_after(c, count(c)))),
    Rule("R-PD-WRITE", S1, "A write (carry set) of sectors within the disk writes them, and returns as a read does: A 0, "
         "F $42, B 0, C $32, D / E the entry A / F, HL as entered; the buffer is not changed.",
         lambda c: D(c) and write(c) and in_range(c),
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (0, 0x42, 0, 0x32, (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-PAST", S1, "A read that runs past the last sector (1439) reads the sectors before it, then stops: A 2, F "
         "$41, B = the sectors not read, C 0, D / E the entry A / F, HL as entered. B 0 counts as 256 (case 04: one "
         "sector read from 1439, B $FF left).", lambda c: D(c) and not write(c) and media_ok(c) and not in_range(c)
         and c.dein != 0xFFFF,
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (2, 0x41, (count(c) - max(0, SECTORS - c.dein)) & 0xFF, 0,
                                                         (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(buffer_after(c, max(0, SECTORS - c.dein)))),
    Rule("R-PD-WPAST", S1, "A write past the last sector returns A 8, F $11, B = the sectors not written, C 0, D / E the "
         "entry A / F, HL as entered; the buffer is not changed.", lambda c: D(c) and write(c) and not in_range(c),
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (8, 0x11, count(c), 0, (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-FFFF", S1, "Sector $FFFF is NOT refused: a 1-sector read there returns as a good read (A 0, F $42, B 0, "
         "C $32, D / E the entry A / F, HL as entered) and the 512 bytes read are all 0. Which sector it reads is not "
         "measured.", lambda c: OK_READ(c) and c.dein == 0xFFFF,
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (0, 0x42, 0, 0x32, (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(buffer_after(c, 1))),
    Rule("R-PD-MEDIA", S1, "A media byte the interface does not take ($00 and $32 measured) refuses the call before any "
         "transfer: A 12, F $89, B as entered, C 0, D / E the entry A / F, HL as entered; the buffer is not touched.",
         lambda c: D(c) and not media_ok(c),
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl) == (12, 0x89, c.bin, 0, (c.ain << 8) | c.fin, c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-DI", S1, "With a disk interface, interrupts are OFF after the call, whether they were on or off before it.",
         D, lambda c: c.iff == 0),
]
