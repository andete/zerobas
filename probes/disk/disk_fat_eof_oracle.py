#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""FAT12 cluster-boundary EOF oracle: how many clusters does stock allocate for a
file whose size is an EXACT multiple of the cluster size?

THE CORNER. When a file's byte size is an exact multiple of the cluster size
(size = k * clusterBytes, k >= 1), the correct allocation is exactly k clusters.
An end-of-file off-by-one — treating "the write filled the last cluster" as "there
must be a next cluster" — would allocate k+1 clusters, the last one empty, and a
reader with the same off-by-one would read one cluster too many past the real end.
That is the read-side twin of the straddle bug: invisible on a small happy-path
disk, latent until a file lands exactly on a cluster boundary.

THE ORACLE. Stock MSX-DOS leaves the answer on disk: every file it wrote has a FAT
chain exactly ceil(size / clusterBytes) links long, and for an exact-multiple file
that is precisely size / clusterBytes with NO trailing empty cluster. We read a
corpus of real stock-written .dsk images, isolate the exact-multiple population
(the boundary cases), and assert each occupies exactly size/clusterBytes clusters.
A stock file that validates under this rule is a WITNESS that CF-3300-family
MSX-DOS stops the chain at the boundary; a file whose valid chain is one link too
long would be a CONTRADICTION (there is none — that is the point).

WHY IT EXISTS. It is the CF-3300 anchor for the cluster-boundary-EOF behaviour that
tests/test_fat_read_file_sector.py checks at the routine level (case 2b: exhausting
a full final cluster advances to the end-of-chain marker and EOFs, reading nothing).
The host test proves OUR routine stops at the boundary; this oracle proves that
boundary is the one stock uses, not merely one we posited. (Tier-C case 1.)

CLEAN-ROOM DISCIPLINE. Reads .dsk DATA images only — the FAT + root directory laid
down by stock — interpreted per the PUBLIC Microsoft FAT specification (§3.2/§3.3).
Black-box observation of a stock-written data artifact, same class as the straddle
oracle and GETDPB-vs-CF-3300; NO ROM code is read or decoded. Shares the already-
validated BPB parse and 12-bit unpack with disk_fat_straddle_oracle (imported, not
duplicated), which mirror disk/fat.asm's own reader.

Usage:
  python3 probes/disk/disk_fat_eof_oracle.py [image.dsk ...]
  # default: every ~/Documents/msx/msx/disks/*.dsk
"""

import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_fat_straddle_oracle import (  # noqa: E402  (reuse, don't duplicate)
    SECSIZE, parse_bpb, next_cluster,
)


def chain_len(fat, first, total_clusters):
    """Follow first..EOC, returning (length, terminated, acyclic_inrange)."""
    cur, seen, ok = first, set(), True
    n = 0
    while 2 <= cur < 0x0FF8:
        if cur in seen or cur >= total_clusters or n > 4096:
            ok = False
            break
        seen.add(cur)
        n += 1
        cur = next_cluster(fat, cur)
    return n, cur >= 0x0FF8, ok


def analyze(path):
    if not os.path.isfile(path):
        return None
    img = open(path, "rb").read()
    if len(img) < SECSIZE:
        return None
    try:
        bpb = parse_bpb(img)
    except Exception:
        return None
    if bpb["bps"] != 512 or bpb["spc"] not in (1, 2) or bpb["nfat"] != 2:
        return None
    fat = img[bpb["fat_start"] * SECSIZE: (bpb["fat_start"] + bpb["spf"]) * SECSIZE]
    total_clusters = (bpb["total"] - bpb["data_start"]) // bpb["spc"] + 2
    clus_bytes = bpb["spc"] * SECSIZE
    root_off = bpb["root_start"] * SECSIZE

    files = []
    for i in range(bpb["root_ent"]):
        e = img[root_off + i * 32: root_off + i * 32 + 32]
        if not e or e[0] in (0x00, 0xE5) or (e[11] & 0x18):
            continue
        size = struct.unpack("<I", e[28:32])[0]
        first = rd16(e, 26)
        if size == 0 or size % clus_bytes != 0:
            continue                              # only the exact-multiple population
        if not (2 <= first < 0x0FF8):
            continue
        n, terminated, ok = chain_len(fat, first, total_clusters)
        exact = size // clus_bytes                # the correct, no-trailing count
        files.append(dict(name=bytes(e[0:11]).decode("latin1"), size=size,
                          clusters=n, exact=exact,
                          witness=(ok and terminated and n == exact),
                          contradiction=(ok and terminated and n != exact)))
    return dict(path=path, files=files, clus_bytes=clus_bytes)


def rd16(b, o):
    return b[o] | (b[o + 1] << 8)


def main(argv):
    paths = argv[1:] or sorted(glob.glob(
        os.path.expanduser("~/Documents/msx/msx/disks/*.dsk")))
    witnesses = contradictions = 0
    shown = []
    contra = []
    for p in paths:
        r = analyze(p)
        if not r:
            continue
        for f in r["files"]:
            if f["witness"]:
                witnesses += 1
                shown.append((os.path.basename(p), f))
            elif f["contradiction"]:
                contradictions += 1
                contra.append((os.path.basename(p), f))

    print(f"scanned {len(paths)} image path(s)")
    print(f"exact-multiple files stopping at exactly size/clusterBytes clusters "
          f"(witnesses): {witnesses}")
    print(f"exact-multiple files with a trailing extra cluster (contradictions): "
          f"{contradictions}")
    print()
    print("WITNESSES — stock files sized to an exact cluster multiple, chain stops")
    print("at the boundary (no trailing empty cluster) — the CF-3300 EOF anchor:")
    for base, f in shown[:30]:
        print(f"  {base:<22} {f['name']!r} size={f['size']:>6} "
              f"clusters={f['clusters']:>3} (exact {f['exact']:>3})")
    if contra:
        print()
        print("CONTRADICTIONS — should be empty; a stock file with a trailing cluster:")
        for base, f in contra[:30]:
            print(f"  {base:<22} {f['name']!r} size={f['size']:>6} "
                  f"clusters={f['clusters']:>3} (exact {f['exact']:>3})")

    # exit 0 iff the corner population exists AND stock never contradicts the rule
    return 0 if (witnesses and not contradictions) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
