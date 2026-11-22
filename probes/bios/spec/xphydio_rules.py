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
RUNS = [("xdsk1.asm", "XDSK1_run2.out"), ("xdsk2.asm", "XDSK2_run1.out"), ("xdsk3.asm", "XDSK3_run2.out"),
        ("xdsk4.asm", "XDSK4_run1.out"), ("xdsk5.asm", "XDSK5_run2.out"), ("xdsk6.asm", "XDSK6_run1.out")]
REC = 14
SECTORS = 1440
# THE GEOMETRY the media byte names (sides, sectors per track, tracks) -- the standard 3.5" formats; round 4 (XDSK4)
# pinned it: a sector number maps to TRACK = sector / (sides x sectors per track), side, sector; the call refuses ("past")
# when the track number reaches the media's track count. What wraps is the SIDE-AND-TRACK count, sector / (sectors
# per track), kept in 8 bits (round 6: $F8 sector 1152, track 128 of a one-sided disk, is past; on two-sided $F9 the
# same 8 bits make the track modulo 128 -- round 5: track 128 reads the boot sector, track 210 is past). A transfer
# whose last sector DE + B - 1 does not fit 16 bits is refused before any sector (round 6: 2 from $FFFF, A 2, B 2).
# Before round 6 the model said "the track modulo 128"; before round 5, "modulo 256" -- $F9 sector $1200 (track 256) reads the boot sector,
# $FFFE / $FFFF (track 56) read, $F000 (track 85) and $FF sector 700 (track 43 of 40) are past. The image
# is the 720 KB disk (2 sides x 9 x 80): a read reaches image sector (track x 2 + side) x 9 + sector.
GEOM = {0xF8: (1, 9, 80), 0xF9: (2, 9, 80), 0xFA: (1, 8, 80), 0xFF: (2, 8, 40)}
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
        b += bytes([(0x77 + n) & 0xFF, -n & 0xFF])     # the probe's fill_pat: B counts down from 0 (djnz)
    return b + bytearray([0xE5] * 512)


def sector(n):
    return IMAGE[512 * n: 512 * (n + 1)]


def _cases():
    out = []
    for asm, run in RUNS:
        src = open(os.path.join(HERE, asm)).read()
        head = src[:src.index("; Drive A is a fresh copy")]
        rows = CASE.findall(head)
        for row, tag, rf in (("nodisk", "N", run), ("disk", "D", run),
                             ("nms8250", "E", f"{asm[:-4].upper()}_nms8250.out")):
            # E: the NMS 8250's built-in drive (D-DISKFORCBIOS (b), 2026-11-22), a reference-only row -- does the
            # rule hold on another interface? (XDSK3's run there needed `@timeout 600`: case 31, sector $F000,
            # outlasts 60 emulated seconds on that drive; the run's header names xdsk3.asm.)
            t = open(os.path.join(ROOT, "scratchpad", rf)).read()
            sec = t[t.index(f" {row}: "):]
            sec = sec[:sec.index("\n=====")] if "\n=====" in sec else sec     # to the next row's header
            for who, key in (("ref", "ref"), ("zb", "ours")):
                b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", sec).group(1))
                b += bytes(max(0, REC * len(rows) - len(b)))
                for i, (num, title, a, f, bb, c, de, hl, ei, kind) in enumerate(rows):
                    r = b[REC * i: REC * (i + 1)]
                    out.append((who, NS(src="XP", id=f"XP {tag}{num}", row=tag, ref_only=(tag == "E"),
                                        num=int(num), title=title,
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
    # measured accepted: $F8 $F9 $FA $FF; refused $00 $32 $80 $F0 $F7. The NMS 8250 (row E) refuses $FF too (cases
    # 12, 22, 41, 49, 63, 70) -- as its GETDPB does (docs/disk/GETDPB.md R-GD-REFUSE)
    return c.cin in GEOM and not (c.row == "E" and c.cin == 0xFF)


def regs(c, good):
    """(C, DE) as returned: row D C $32 after a good transfer, 0 after a failure, DE = the entry A / F; row E (the
    NMS 8250) C $3C / 0 and DE a working value of its own (not compared)"""
    if c.row == "E":
        return ((0x3C if good else 0), c.de)
    return ((0x32 if good else 0), (c.ain << 8) | c.fin)


def place(c, n):
    """sector n under case c's media byte: (track, side, sector), from the side-and-track count kept in 8 bits"""
    sides, spt, _ = GEOM[c.cin]
    n &= 0xFFFF
    q = (n // spt) & 0xFF
    return (q // sides, q % sides, n % spt)


def sec_ok(c, n):
    return place(c, n)[0] < GEOM[c.cin][2]


def image_index(c, n):
    t, side, s = place(c, n)
    return (t * 2 + side) * 9 + s


def nok(c):
    """the sectors transferred before the first one past the disk"""
    if c.dein + count(c) - 1 > 0xFFFF:              # the last sector does not fit 16 bits: refused up front
        return 0
    k = 0
    while k < count(c) and sec_ok(c, c.dein + k):
        k += 1
    return k


def in_range(c):
    return nok(c) == count(c)


def far(c):
    """in range by the track rule, yet past the disk's size: the track number wrapped ($FFFE, $FFFF, $1200)"""
    if not media_ok(c):
        return False
    sides, spt, trk = GEOM[c.cin]
    return in_range(c) and c.dein + count(c) > sides * spt * trk


def disk_sector(c, n):
    """IMAGE sector n as case c finds it: each round starts from a fresh copy and runs its cases in order. Round 1:
    from case 07 on, 1439 holds case 06's write (the pattern's first 512 bytes); round 3: from 24 on, case 23's;
    round 4: image 9 holds case 38's (the pattern), image 8 case 39's (the pattern's bytes 256-767)"""
    if n == SECTORS - 1 and (7 <= c.num <= 10 or 24 <= c.num <= 36):
        return bytes(fill("PAT")[:512])
    if n == 9 and (39 <= c.num <= 53 or 55 <= c.num <= 68):  # case 38 / 54: from $A400
        return bytes(fill("PAT")[:512])
    if n == 8 and (40 <= c.num <= 53 or 56 <= c.num <= 68):  # case 39 / 55: from $A500
        return bytes(fill("PAT")[256:768])
    if n == 18 and (57 <= c.num <= 68 or c.num >= 70):       # case 56 / 69: from $A480
        return bytes(fill("PAT")[128:640])
    if n == 1430 and 67 <= c.num <= 68:                      # case 66
        return bytes(fill("PAT")[:512])
    return sector(n)


def buffer_after(c, nread):
    """the 1 KB buffer after `nread` sectors read into it from DE, each the image sector its place names"""
    buf = fill(c.kind)
    for k in range(min(nread, 2)):
        s = disk_sector(c, image_index(c, c.dein + k))
        buf[512 * k: 512 * (k + 1)] = s
    return buf


def summ(buf):
    return (sum(buf) & 0xFFFF, buf[0], buf[512])


def got(c):
    return (c.sum, c.b0, c.b512)


D = lambda c: c.row in "DE"                                # noqa: E731


def first_e(c):
    """XP E20: round 3's FIRST call on the NMS 8250 (a fresh boot) -- R-PD-FIRSTE"""
    return c.row == "E" and c.num == 20
OK_READ = lambda c: D(c) and not write(c) and media_ok(c) and (in_range(c) or far(c))   # noqa: E731
S1 = "1. PHYDIO ($0144): a physical sector read or write through the disk interface"

RULES = [
    Rule("R-PD-NODISK", S1, "With no disk interface (row N) PHYDIO returns at once: A, F, BC, DE, HL and the interrupt "
         "state as entered; the buffer is not touched.", lambda c: c.row == "N",
         lambda c: (c.a, c.f, c.b, c.c, c.de, c.hl, c.iff) == (c.ain, c.fin, c.bin, c.cin, c.dein, c.hlin, int(c.ein))
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-READ", S1, "A read (carry clear) with an accepted media byte ($F8, $F9, $FA, $FF measured; $FF not on the NMS 8250, R-PD-MEDIA) and the "
         "sectors within the disk its GEOMETRY names ($F9 2 sides x 9 sectors x 80 tracks, $F8 1 x 9 x 80, $FA 1 x 8 x "
         "80, $FF 2 x 8 x 40) puts sectors DE, DE + 1, ... in that order (case 43: the FAT second) into memory from HL "
         "($A400 and $8000 measured), each from the place the geometry gives it ($F8 sector 9 is track 1: the image's "
         "sector 18; $FF sector 8 is side 1: image 9) and returns "
         "A 0, F $42, B 0, C $32, D 0 (the entry A, 0 in every case), E = the entry F, HL as entered. Cases 07 and 24 "
         "read back what cases "
         "06 and 23 wrote. On the NMS 8250 (row E) C is $3C and DE a working value; its one exception is "
         "R-PD-FIRSTE.", lambda c: OK_READ(c) and not far(c) and not first_e(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (0, 0x42, 0, regs(c, True), c.hlin)
         and got(c) == summ(buffer_after(c, count(c)))),
    Rule("R-PD-WRITE", S1, "A write (carry set) of sectors within the disk writes them (cases 07 and 10 read case 06's "
         "pattern back from 1439, 57 case 55's -- taken from HL $A500 -- from 8, 67 case 66's), entered with interrupts "
         "on or off, and returns as a read does: A 0, F $42, B 0, C $32, D / E the entry A / F, HL as "
         "entered; the buffer is not changed.",
         lambda c: D(c) and write(c) and media_ok(c) and in_range(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (0, 0x42, 0, regs(c, True), c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-PAST", S1, "A read that reaches a sector whose TRACK is at or past the media's track count -- the track "
         "from the side-and-track count sector / (sectors per track) kept in 8 BITS (sector 1440 with $F9, 720 with "
         "$F8, 700 and 1439 with $FF; $F000: 6826 = 170, track 85; $F9 3780: 420 = 164, track 82; $F8 1152: 128, "
         "track 128) -- reads the sectors before it, then stops: A 2, F $41, B = the sectors not read, C 0, D / "
         "E the entry A / F (E $5A in case 27), HL as entered ($A400, $8000). B 0 counts as 256 (case 04: one sector "
         "read from 1439, B $FF left: the count runs down from 0 in 8 bits -- how far it can run is not "
         "measured). A transfer whose last sector does not fit 16 bits is refused before any sector: 2 from $FFFF "
         "gives A 2 with B 2 (case 73), where 1 from $FFFF reads.", lambda c: D(c) and not write(c) and media_ok(c) and not in_range(c)
         and not far(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (2, 0x41, (count(c) - nok(c)) & 0xFF, regs(c, False),
                                                           c.hlin)
         and got(c) == summ(buffer_after(c, nok(c)))),
    Rule("R-PD-WPAST", S1, "A write that runs past the last sector writes the sectors before it (case 23: 2 from 1439 "
         "writes 1439 -- case 24 reads it back -- and stops at 1440; case 64, 3 from 1439, leaves B 2), then stops: A 8, F $11, B = the sectors not written, C 0, D / E the entry A / F "
         "(E $FF in case 29), HL as entered; the buffer is not changed.",
         lambda c: D(c) and write(c) and media_ok(c) and not in_range(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (8, 0x11, count(c) - nok(c), regs(c, False), c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-FFFF", S1, "A sector number past the disk whose side-and-track count WRAPS (8 bits) back onto it is NOT "
         "refused: it returns as a good read (A 0, F $42, B 0, C $32, D / E the entry A / F, HL as entered). $F9 "
         "sector $1200 (count 512 = 0) and $0900 (256 = 0) read the BOOT sector; $FFFE / $FFFF (7281 = 113: track 56, "
         "side 1) read a zero sector (which one is not separated).", lambda c: OK_READ(c) and far(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (0, 0x42, 0, regs(c, True), c.hlin)
         and got(c) == summ(buffer_after(c, 1))),
    Rule("R-PD-MEDIA", S1, "A media byte the interface does not take ($00, $32, $80, $F0, $F7 measured; on the NMS 8250 $FF too) refuses the "
         "call before any transfer -- before the sector check too (case 36 reading, 72 writing: $00 and sector 1440 "
         "give 12), entered "
         "with interrupts on (case 25), and for a WRITE (case 44: nothing written, case 45 reads the sector unchanged): A 12, F $89, "
         "B as entered (1, 2, 0), C 0, D / E the entry A / F (E $A4 in case 28), HL as entered; the "
         "buffer is not touched.",
         lambda c: D(c) and not media_ok(c),
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (12, 0x89, c.bin, regs(c, False), c.hlin)
         and got(c) == summ(fill(c.kind))),
    Rule("R-PD-FIRSTE", S1, "On the NMS 8250, round 3's FIRST call after start-up -- sector 9 with C $F8, which that "
         "media byte puts on TRACK 1 -- returns A 0, F $42, B 0 as a good read, but the bytes are the disk's BOOT "
         "sector (track 0), measured twice (scratchpad/XDSK3_nms8250.out, and XDSK3_nms8250_b.out byte for byte the same); the "
         "same read later (cases 40, 58) gets track 1's sector, as on the NMS 1200. Whether every first call that "
         "needs a seek reads the wrong track is not separated (round 1 starts on track 0).", first_e,
         lambda c: (c.a, c.f, c.b, (c.c, c.de), c.hl) == (0, 0x42, 0, regs(c, True), c.hlin)
         and got(c) == summ(bytearray(sector(0)) + fill(c.kind)[512:])),
    Rule("R-PD-DI", S1, "With a disk interface, the interrupt state after the call is the INTERFACE's, whether they "
         "were on or off before it: OFF on the VG-8020's NMS 1200, ON on the NMS 8250 (row E) -- a caller cannot "
         "count on either.", D, lambda c: c.iff == (1 if c.row == "E" else 0)),
]
