#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF step 0 -- CALIBRATE the offline model against a MEASURED artifact.

The whole slice hangs on an offline model of the tenant's octant loop + scale.
Before that model is allowed to predict anything, it has to reproduce a reading
somebody already took on real hardware. D-CIRCDOM measured

    CIRCLE(128,96),700,,,,.137   ->  421 px, sha1 2f6257f6, BYTE-IDENTICAL on
                                     VG-8020 and zerobas

(docs/circdom-msx1-characterization.md §4.1, the control that proved the bound
is the PRODUCT and not the radius). If the model cannot rebuild that sha1 from
arithmetic alone, every prediction it makes later is worth nothing.

⚠️ It must rebuild the whole 6144-byte PATTERN PLANE, not a (popcount, bbox)
summary -- D-CIRCDOM's K-CD3 missed precisely because a prediction was computed
off the bbox while the row compares all 6144 bytes.

    python3 -u scratchpad/circovf_calib.py
"""
from __future__ import annotations

import hashlib

W, H = 256, 192


def octant(r):
    x, y, d = 0, r, 1 - r
    while x <= y:
        yield x, y
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1


def mirrors(x, y):
    return ((x, y), (x, -y), (-x, y), (-x, -y),
            (y, x), (y, -x), (-y, x), (-y, -x))


def scale_trunc(v, asps):
    """zerobas: gfx_mul16u keeps 16 bits, then `ld l,h / ld h,0`."""
    o = ((((abs(v) * asps) & 0xFFFF) + 128) >> 8) & 0xFF
    return -o if v < 0 else o


def scale_exact(v, asps):
    """The hypothesis under test for the reference: full-width product."""
    o = (abs(v) * asps + 128) >> 8
    return -o if v < 0 else o


def pixels(cx, cy, r, asps, aspmaj, scale):
    px, hot = set(), 0
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                v, sx, sy = dx, scale(dx, asps), dy
            else:
                v, sx, sy = dy, dx, scale(dy, asps)
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
                if abs(v) * asps >= 65536:
                    hot += 1
    return px, hot


def plane(px):
    """SCREEN 2 pattern plane: addr = (y>>3)*256 + (x>>3)*8 + (y&7)."""
    b = bytearray(6144)
    for x, y in px:
        b[(y >> 3) * 256 + (x >> 3) * 8 + (y & 7)] |= 0x80 >> (x & 7)
    return bytes(b)


def reduce_plane(b):
    n = x0 = y0 = x1 = y1 = None
    n = 0
    x0 = y0 = 10 ** 6
    x1 = y1 = -1
    for i, v in enumerate(b):
        if not v:
            continue
        row, rest = i // 256, i % 256
        col, y = rest // 8, (i // 256) * 8 + (rest % 8)
        for bit in range(8):
            if v & (0x80 >> bit):
                n += 1
                x = col * 8 + bit
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
    return (n, None if x1 < 0 else (x0, y0, x1, y1),
            hashlib.sha1(b).hexdigest()[:8])


# Every row D-CIRCDOM §4.1 published a READING for. `zb` / `ref` are what the
# table records; the model has to reproduce them from arithmetic alone.
# ⚠️ ASPS for the `a03` rows is 77, not 76: §4.1 was measured on the PRE-FIX
# build, before §5 changed cpt_asp_scale256 from round to truncate.
# label, cx, cy, r, aspect, ASPS, aspmaj, zb=(px,bbox|sha1), ref=(px,...)
CALIB = [
    ("r20_base", 128, 96, 20, "", 256, 0, (112, None), (112, None)),
    ("r200", 128, 96, 200, "", 256, 0, (0, None), (0, None)),
    ("r255", 128, 96, 255, "", 256, 0, (0, None), (0, None)),
    ("r256", 128, 96, 256, "", 256, 0, (31, (113, 96, 143, 96)), (0, None)),
    ("r257", 128, 96, 257, "", 256, 0, (88, (101, 95, 155, 97)), (0, None)),
    ("r300", 128, 96, 300, "", 256, 0, (512, (0, 52, 255, 140)), (0, None)),
    ("r1000", 128, 96, 1000, "", 256, 0, (0, None), (0, None)),
    ("r300_a09", 128, 96, 300, ".9", 230, 0, (376, (33, 82, 223, 110)), (0, None)),
    ("r900_a03", 128, 96, 900, ".3", 77, 0, (512, (0, 81, 255, 111)), (0, None)),
    ("r1900_a0137", 128, 96, 1900, ".137", 35, 0, (512, (0, 92, 255, 100)), (0, None)),
    ("r700_a0137", 128, 96, 700, ".137", 35, 0, (421, "2f6257f6"), (421, "2f6257f6")),
]


def _match(red, want):
    """`want` is (px, bbox) or (px, sha1). A bbox of None is not checked."""
    n, bbox, sha = red
    exp_n, exp = want
    if n != exp_n:
        return False
    if exp is None:
        return True
    return sha == exp if isinstance(exp, str) else bbox == exp


def main():
    print("=== D-CIRCOVF: model calibration against MEASURED artifacts ===")
    print("(D-CIRCDOM docs/circdom-msx1-characterization.md §4.1 -- 11 rows,")
    print(" 22 readings. Nothing here boots an emulator.)\n")
    bad = ok_n = 0
    for lbl, cx, cy, r, asp, asps, maj, w_zb, w_ref in CALIB:
        for name, sc, want in (("zerobas/trunc", scale_trunc, w_zb),
                               ("VG-8020/exact", scale_exact, w_ref)):
            red = reduce_plane(plane(pixels(cx, cy, r, asps, maj, sc)[0]))
            good = _match(red, want)
            bad += not good
            ok_n += good
            print(f"  {'OK  ' if good else 'MISS'} {lbl:12} {name:14} "
                  f"model={red}  measured={want}")
    print()
    print(f"=== {ok_n} exact / {bad} missed, of {ok_n + bad} readings ===")
    print("=== model " + ("CALIBRATED" if not bad else "REFUTED") + " ===")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
