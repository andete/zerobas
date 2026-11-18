#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The XSCR supplement's cases and the reference's behaviour as a MODEL (docs/spec-method.md §3a): shared by
docs/bios/DSPFNK.md's rules (xkey_rules.py, the key-line calls) and docs/bios/CLS.md's (xcls_rules.py, CLS / POSIT).
Each case's expected outputs are computed from its inputs alone -- the name table as an image built from the probe's
address-dependent garbage, then changed as the rules' sentences say -- never from the other machine or from another
case. Run: scratchpad/XSCR_run2.out (run 1, scratchpad/XSCR_run1.out, recorded LINTTB only as a sum; its 50 cases
are run 2's first 50)."""
import os
import re

import xscr_cases as X
import xscr3_cases as X3
import xscr4_cases as X4
import xscr5_cases as X5

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SP = 32
LT_MARK = 175               # the value the reference writes into a LINTTB entry it marks (two garbage sets: 175 both)
# A / F on return (not published): the reference's literal values per XSCR case
REF_AF = {"XS 00": (0x00, 0x44), "XS 01": (0x00, 0x44), "XS 02": (0x28, 0xBB), "XS 03": (0x28, 0xBB),
          "XS 04": (0x00, 0x44), "XS 05": (0x00, 0x44), "XS 06": (0x00, 0x44), "XS 07": (0x28, 0xBB),
          "XS 08": (0x00, 0x44), "XS 09": (0x28, 0xBB), "XS 10": (0x00, 0x44), "XS 11": (0x00, 0x44),
          "XS 12": (0x00, 0x44), "XS 13": (0x00, 0x44), "XS 14": (0x00, 0x44), "XS 15": (0x00, 0x44),
          "XS 16": (0x00, 0x44), "XS 17": (0x00, 0x44), "XS 18": (0x00, 0x44), "XS 19": (0x1D, 0x9B),
          "XS 20": (0x00, 0x44), "XS 21": (0x00, 0x44), "XS 22": (0x00, 0x44), "XS 23": (0x00, 0x44),
          "XS 24": (0x28, 0xBB), "XS 25": (0x02, 0x42), "XS 26": (0x02, 0x42), "XS 27": (0x00, 0x54),
          "XS 28": (0x01, 0x00), "XS 29": (0x00, 0x54), "XS 30": (0x00, 0x00), "XS 31": (0x00, 0x44),
          "XS 32": (0x00, 0x44), "XS 33": (0x00, 0x44), "XS 34": (0x00, 0x54), "XS 35": (0x01, 0x00),
          "XS 36": (0x00, 0x44), "XS 37": (0x00, 0x44), "XS 38": (0x00, 0x54), "XS 39": (0x00, 0x54),
          "XS 40": (0x00, 0x54), "XS 41": (0x00, 0x44), "XS 42": (0x00, 0x44), "XS 43": (0x66, 0x24),
          "XS 44": (0x48, 0x18), "XS 45": (0x24, 0x30), "XS 46": (0x24, 0x30), "XS 47": (0x22, 0x30),
          "XS 48": (0x22, 0x30), "XS 49": (0x24, 0x30), "XS 50": (0x24, 0x30), "XS 51": (0x24, 0x30),
          "XS 52": (0x24, 0x30), "XS 53": (0x24, 0x30), "XS 54": (0x00, 0x44)}
REF_AF.update({"XS3 00": (0x00, 0x54), "XS3 01": (0x00, 0x54), "XS3 02": (0x25, 0xB3), "XS3 03": (0x20, 0xB3),
               "XS3 04": (0x28, 0xBB), "XS3 05": (0x00, 0x44), "XS3 06": (0x00, 0x44), "XS3 07": (0x00, 0x44),
               "XS3 08": (0x00, 0x44), "XS3 09": (0x24, 0x30), "XS3 10": (0x24, 0x30), "XS3 11": (0x24, 0x30),
               "XS3 12": (0x24, 0x30), "XS3 13": (0x24, 0x30), "XS3 14": (0x24, 0x30), "XS3 15": (0x24, 0x30),
               "XS3 16": (0x00, 0x54), "XS3 17": (0x00, 0x54), "XS3 18": (0x00, 0x44)})
REF_AF.update({"XS4 00": (0x00, 0x44), "XS4 01": (0x00, 0x44), "XS4 02": (0x00, 0x44), "XS4 03": (0x00, 0x44)})
REF_AF.update({"XS5 00": (0x00, 0x44), "XS5 01": (0x25, 0xB3), "XS5 02": (0x00, 0x44), "XS5 03": (0x1D, 0x9B), "XS5 04": (0x28, 0xBB), "XS5 05": (0x00, 0x44), "XS5 06": (0x00, 0x44), "XS5 07": (0x02, 0x42)})
REF_AF.update({"XS5 08": (0x00, 0x44), "XS5 09": (0x00, 0x44), "XS5 10": (0x00, 0x44)})
OUTPUTS = ["a", "f", "cnsdfg", "crtcnt", "csrx_out", "csry_out", "linlen", "scrmod", "linl40", "linl32", "lt",
           "namesum", "row1", "rowc", "row24", "vsum", "win"]


def load(who, calls):
    """XSCR run 2 (group XS) and XSCR3 run 1 (group XS3: LINTTB's garbage address-dependent, TXTNAM changed late)."""
    out = []
    for mod, run, src in ((X, "XSCR_fix2.out", "XS"), (X3, "XSCR3_fix2.out", "XS3"), (X4, "XSCR4_fix2.out", "XS4"),
                             (X5, "XSCR5_fix2.out", "XS5")):
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        key = "ref" if who == "ref" else "ours"
        for c in mod.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))):
            if c.name in calls:
                c.src, c.id = src, f"{src} {c.idx:02}"
                c.ltpat = src in ("XS3", "XS4", "XS5")
                c.lw = getattr(c, "lw", 0)
                c.late = getattr(c, "late", 0)
                out.append(c)
    return out


def fill(c):
    return 0xA5 if c.gset else 0x5A


def lt_garbage(c):
    """LINTTB's garbage: one byte for all 24 entries (XS), or entry k := $40 + k (+ $20, garbage set 1) (XS3)."""
    if getattr(c, "ltpat", False):
        return [0x40 + k + (0x20 if c.gset else 0) for k in range(24)]
    return [0xAA if c.gset else 0x55] * 24


def cols(c):
    return 40 if c.mode == 0 else 32


def count(c):
    return 960 if c.mode == 0 else 768


def pat(c, i):
    return 0x80 | ((i + 64 * c.gset) & 0x7F)


def label_cells(lab):
    """A label as the key line shows it, up to its terminating 0 (or 16 bytes): $01 + a character from $40 to $5F
    gives that character − $40 (a graphic character); $01 + any other character gives the character; a $01 at the
    end gives nothing; a control character below $20 a space; anything else itself."""
    lab = lab.split(b"\0")[0]
    out, i = [], 0
    while i < len(lab):
        b = lab[i]
        if b == 1:
            if i + 1 < len(lab):
                n = lab[i + 1]
                out.append(n - 0x40 if 0x40 <= n <= 0x5F else n)
            i += 2
            continue
        out.append(SP if b < 0x20 else b)
        i += 1
    return out


def width(c):
    """The width the key-line calls use: LINLEN as found (XSCR5's `lw` sets it after the mode's call) -- the rule under
    test."""
    return c.lw or c.width


def key_cells(c, found):
    """Row CRTCNT's cells after the key line is drawn (show) over `found`: the width's span spaced, then the FIRST five
    labels from margin + k x slot, cut to slot - 1 cells."""
    n, w = cols(c), width(c)
    m, slot = (n - w + 1) // 2, (w + 1) // 5
    row = list(found)
    for i in range(max(0, m), min(n, m + w)):
        row[i] = SP
    for k in range(5):
        for j, ch in enumerate(label_cells(X.LABELS[c.lab][k])[:max(0, slot - 1)]):
            row[m + k * slot + j] = ch
    return row


def expect(c):
    """Every output of an XSCR case as the reference's rules say, from the case's inputs."""
    n, N = cols(c), count(c)
    img = [pat(c, i) for i in range(N)]
    lt = lt_garbage(c)
    e = dict(cnsdfg=c.cns, crtcnt=c.crt, csrx_out=c.csrx, csry_out=c.csry, linl40=77, linl32=77,
             scrmod=c.mode, win=[0xEE] * 32)
    extra = 0                           # VRAM outside the name table: its change from the fill
    text = c.mode in (0, 1)
    r = c.crt                           # the key line's row (all XSCR cases have it on screen)
    row = lambda k: img[(k - 1) * n:k * n]                                    # noqa: E731

    def put(k, cells):
        img[(k - 1) * n:k * n] = cells
    if c.name in ("DSPFNK", "ERAFNK", "FNKSB"):
        on = c.name == "DSPFNK" or (c.name == "FNKSB" and c.cns)
        e["cnsdfg"] = 255 if on else (0 if c.name == "ERAFNK" else c.cns)
        acts = text and (c.name != "FNKSB" or c.cns)
        if acts and on:
            if c.csry == r:             # the cursor on the key line's row: scroll the text rows up, cursor up
                for k in range(1, r - 1):
                    put(k, row(k + 1))
                lt[0:r - 2] = lt[1:r - 1]   # LINTTB scrolls with the rows (XS3: address-dependent entries)
                put(r - 1, [SP] * n)    # the new last text row comes in blank (width 40 only measured)
                e["csry_out"] = r - 1
                lt[r - 2] = LT_MARK
            put(r, key_cells(c, row(r)))
        elif acts:                      # ERAFNK: the span spaced, the row's LINTTB entry marked
            m = (n - width(c) + 1) // 2
            cells = row(r)
            for i in range(max(0, m), min(n, m + width(c))):
                cells[i] = SP
            put(r, cells)
            lt[r - 1] = LT_MARK
    elif c.name == "CLS":
        if c.ef & 0x40:                 # the Z flag set: it acts
            if text:
                img = [SP] * N
                if c.cns:
                    put(r, key_cells(c, row(r)))
                    e["cnsdfg"] = 255
                e["csrx_out"], e["csry_out"] = 1, 1
                lt = [24 - k for k in range(24)]
            elif c.mode == 2:           # pattern table 0, colour table BAKCLR as it is (6 KB each)
                extra = 6144 * (0 - fill(c)) + 6144 * (c.bg - fill(c))
            elif c.mode == 3:           # the multicolour pattern table (1.5 KB): BAKCLR in both nibbles (BAKCLR 6)
                extra = 1536 * (((c.bg & 15) * 17) - fill(c))
    elif c.name == "POSIT":
        if text:
            top = (c.crt + c.cns) & 0xFF
            e["csrx_out"] = c.h if 1 <= c.h <= c.width else c.width
            e["csry_out"] = c.l if 1 <= c.l <= top else top
    e["lt"] = lt
    e["namesum"] = sum(img) & 0xFFFF
    after = lambda k: (img[k * n:k * n + 40 - n] if k * n + 40 - n <= N else                  # noqa: E731
                       img[k * n:] + [fill(c)] * (40 - n - len(img[k * n:]))) if n < 40 else []
    e["row1"] = row(1) + after(1)
    e["rowc"] = row(r) + after(r)
    e["row24"] = row(24) + after(24)
    e["row12"] = row(12) + after(12)            # XSCR4 only
    e["rowcm1"] = row(r - 1) + after(r - 1)
    e["vsum"] = (fill(c) * (16384 - N) + sum(img) + extra) & 0xFFFF
    if c.mode >= 2:
        w = []
        for base in (0x0000, 0x1000, 0x2000, 0x3000):
            v = fill(c)
            if c.name == "CLS" and c.ef & 0x40:
                if c.mode == 2:
                    v = 0 if base < 0x1800 else (c.bg if base < 0x3800 else v)
                elif c.mode == 3 and base < 0x0600:
                    v = (c.bg & 15) * 17
            w += [v] * 8
        e["win"] = w
    if text:
        e["linlen"] = width(c)
    return e


def matches(c, fields):
    e = expect(c)
    return all(getattr(c, f) == e[f] for f in fields)
