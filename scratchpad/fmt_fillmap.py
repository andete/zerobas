#!/usr/bin/env python3
"""D-DSKFMT fill map: for a formatted image, the dominant byte of every LOGICAL sector
(mapped through the BPB's sectors/track and heads onto a 2-sided, 9-sector image), as
runs. Usage: fmt_fillmap.py IMAGE [IMAGE...]"""
import collections
import sys


def fillmap(b):
    spt, heads, total = b[0x18] | b[0x19] << 8, b[0x1A] | b[0x1B] << 8, b[0x13] | b[0x14] << 8
    runs, prev, start = [], None, 0
    for lg in range(total):
        t, sd, sc = lg // (spt * heads), (lg // spt) % heads, lg % spt
        off = ((t * 2 + sd) * 9 + sc) * 512
        sec = b[off:off + 512]
        v, n = collections.Counter(sec).most_common(1)[0]
        tag = f"{v:02X}" if n == 512 else "mixed"
        if tag != prev:
            if prev is not None:
                runs.append(f"{start}-{lg - 1}:{prev}")
            prev, start = tag, lg
    runs.append(f"{start}-{total - 1}:{prev}")
    return f"spt {spt} heads {heads} total {total} media {b[0x15]:02X}: " + " ".join(runs)


for p in sys.argv[1:]:
    print(p.rsplit("/", 1)[-1], fillmap(open(p, "rb").read()))
