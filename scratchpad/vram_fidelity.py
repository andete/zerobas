#!/usr/bin/env python3
"""VRAM FIDELITY: does zerobas leave the SAME BYTES as the references?

`POINT` is blind to the representation and every graphics gate reads through it,
so two engines can agree on every visible pixel while writing different VRAM.
That is not cosmetic: **VPEEK is a BASIC statement**, so a program can read those
bytes; and SCREEN 2's colour-clash rules mean the NEXT write to a cell depends on
which nibble currently holds what. Under a faithful-MSX1 charter the bytes are
part of the contract.

Measured 2026-08-24: after `PAINT(128,96),15` on a blank SCREEN 2 both references
leave pattern `0x00` / colour `0x0F` (fill via the BACKGROUND nibble) while
zerobas leaves pattern `0xFF` / colour `0xF4` (fill via the FOREGROUND nibble).
This asks the scope question that finding raises: **is it PAINT only, or does the
whole pixel-write path differ?**

Each case draws, then loops so the capture reads live VRAM, and both SCREEN-2
tables are captured: pattern 0x0000-0x17FF and colour 0x2000-0x37FF.
"""
from __future__ import annotations

import collections
import os
import sys

ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl                                                   # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb":     dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}
BOTH = ("vram_segs", [(0x0000, 0x1800), (0x2000, 0x1800)])

# (label, step, body) -- body's last line must hold the screen.
CASES = [
    ("blank",   20.0, ["SCREEN2", "GOTO20"]),
    ("pset",    20.0, ["SCREEN2", "PSET(100,100),15", "GOTO30"]),
    ("pset.c1", 20.0, ["SCREEN2", "PSET(100,100),1", "GOTO30"]),
    ("line",    20.0, ["SCREEN2", "LINE(20,20)-(200,150),15", "GOTO30"]),
    ("linebf",  20.0, ["SCREEN2", "LINE(20,20)-(200,150),15,BF", "GOTO30"]),
    ("circle",  20.0, ["SCREEN2", "CIRCLE(128,96),60,15", "GOTO30"]),
    ("paint",   90.0, ["SCREEN2", "CIRCLE(128,96),60,15:PAINT(128,96),15",
                       "GOTO30"]),
    ("flood",   90.0, ["SCREEN2", "PAINT(128,96),15", "GOTO30"]),
]


def _prog(body):
    out = [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(body)]
    for i, ln in enumerate(out):
        if ln.split(" ", 1)[1].startswith("GOTO"):
            out[i] = f"{(i + 1) * 10} GOTO{(i + 1) * 10}"
    return out


def grab(side, step, body):
    cfg = SIDES[side]
    spec = ("direct", list(cfg["reset"]) + _prog(body) + ["RUN"])
    cap = omsx_repl.run_batch(cfg["machine"], [spec], reset=(), boot=cfg["boot"],
                              step=step, cap_gap=8.0, capture=BOTH,
                              timeout=600.0, verify_delivery=False)[0]
    return bytes.fromhex(cap) if cap else None


def top(d, n=2):
    return collections.Counter(d).most_common(n)


def main():
    only = sys.argv[1:] or None
    print(f"{'case':<9} {'side':<8} {'pattern (top bytes)':<26} "
          f"{'colour (top bytes)':<26} vs refs")
    ndiff = 0
    for label, step, body in CASES:
        if only and label not in only:
            continue
        got = {}
        for side in ("vg8020", "cf3300", "zb"):
            b = grab(side, step, body)
            if b is None:
                print(f"{label:<9} {side:<8} <NO CAPTURE>")
                continue
            got[side] = b
            pat, col = b[:0x1800], b[0x1800:]
            print(f"{label:<9} {side:<8} {str(top(pat)):<26} {str(top(col)):<26}",
                  end="")
            if side != "zb":
                print()
        if len(got) == 3:
            refs_agree = got["vg8020"] == got["cf3300"]
            same = got["zb"] == got["vg8020"]
            if not refs_agree:
                print("   !! REFERENCES DISAGREE — not a want")
            elif same:
                print("   ✅ IDENTICAL")
            else:
                ndiff += 1
                d = sum(1 for x, y in zip(got["zb"], got["vg8020"]) if x != y)
                print(f"   🔴 DIFFERS ({d} of {len(got['zb'])} bytes)")
        print()
    print(f"=== {ndiff} case(s) where zerobas's VRAM differs from both "
          f"(agreeing) references ===")
    return 1 if ndiff else 0


if __name__ == "__main__":
    raise SystemExit(main())
