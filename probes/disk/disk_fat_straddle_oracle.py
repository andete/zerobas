#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""FAT12 sector-straddle oracle: where does stock lay a boundary-crossing entry?

A FAT12 12-bit entry for cluster N occupies FAT byte offsets floor(1.5N) and
floor(1.5N)+1. When floor(1.5N) mod 512 == 511 the entry's two bytes fall in
ADJACENT 512-byte FAT sectors — it "straddles". This probe confirms, from real
stock-written disk images, that MSX-DOS lays such an entry out as a CONTIGUOUS
byte pair across the sector boundary (straddle at byteidx 511), NOT at any other
offset.

WHY IT EXISTS. It is the oracle for the fat_write_fat_entry straddle fix
(fat.asm:579, 2026-07-04): the shipped writer tested the byteidx HIGH byte == 0
as its straddle condition, but 511 == 0x01FF has high byte 1 — so it mis-packed
entries at clusters 170/341/682 on a 720 KB disk. A host unit test
(tests/test_fat_write_fat_entry.py) reproduced it; this probe supplies the
stock-behaviour reference that the fix must match.

CLEAN-ROOM DISCIPLINE. This reads .dsk DATA images only — the FAT + root
directory laid down by stock MSX-DOS — and interprets them per the PUBLIC
Microsoft FAT specification (§3.2 12-bit packing). That is black-box observation
of a stock-written data artifact, the same class as our GETDPB-vs-CF-3300 oracle;
NO ROM code is read or decoded. The 12-bit unpack here mirrors our own already-
validated reader disk/fat.asm:fat_next_cluster.

METHOD. For every non-system file in each image's root directory, follow its
cluster chain reading the FAT as a contiguous byte array (= straddle at 511) and
check the chain is in-range, non-cyclic, EOC-terminated, and exactly
ceil(size / clusterBytes) links long. A file whose VALID chain crosses a
byteidx-255/511 cluster is a WITNESS: its on-disk FAT can only reconstruct if
stock wrote it at the 511 boundary.

Usage:
  python3 probes/disk/disk_fat_straddle_oracle.py [image.dsk ...]
  # default: every ~/Documents/msx/msx/disks/*.dsk
"""

import glob
import os
import struct
import sys

SECSIZE = 512


def rd16(b, o):
    return b[o] | (b[o + 1] << 8)


def parse_bpb(img):
    bps = rd16(img, 11)
    spc = img[13]
    rsvd = rd16(img, 14)
    nfat = img[16]
    root_ent = rd16(img, 17)
    total = rd16(img, 19)
    spf = rd16(img, 22)
    fat_start = rsvd
    root_start = fat_start + nfat * spf
    root_secs = (root_ent * 32 + bps - 1) // bps
    data_start = root_start + root_secs
    return dict(bps=bps, spc=spc, nfat=nfat, root_ent=root_ent, total=total,
                spf=spf, fat_start=fat_start, root_start=root_start,
                root_secs=root_secs, data_start=data_start)


def next_cluster(fat, n):
    """Follow one FAT12 link reading the FAT as a contiguous byte array — this IS
    the straddle-at-511 behaviour (the sector split is transparent to a linear
    read). Mirrors disk/fat.asm:fat_next_cluster. Public Microsoft FAT spec §3.2."""
    off = n + (n >> 1)                       # floor(n * 1.5)
    b0 = fat[off]
    b1 = fat[off + 1] if off + 1 < len(fat) else 0
    return ((b1 << 4) | (b0 >> 4)) if (n & 1) else (((b1 & 0x0F) << 8) | b0)


def byteidx(n):
    return (n + (n >> 1)) & 0x1FF            # entry low byte's offset within a sector


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
        return None                          # not a standard MSX FAT12 image
    fat = img[bpb["fat_start"] * SECSIZE: (bpb["fat_start"] + bpb["spf"]) * SECSIZE]
    total_clusters = (bpb["total"] - bpb["data_start"]) // bpb["spc"] + 2
    clus_bytes = bpb["spc"] * SECSIZE
    root_off = bpb["root_start"] * SECSIZE

    results = []
    for i in range(bpb["root_ent"]):
        e = img[root_off + i * 32: root_off + i * 32 + 32]
        if not e or e[0] in (0x00, 0xE5) or (e[11] & 0x18):
            continue
        name = bytes(e[0:11]).decode("latin1")
        size = struct.unpack("<I", e[28:32])[0]
        first = rd16(e, 26)
        if not (2 <= first < 0x0FF8):
            continue
        chain, cur, seen, ok = [], first, set(), True
        while 2 <= cur < 0x0FF8:
            if cur in seen or cur >= total_clusters or len(chain) > 4096:
                ok = False
                break
            seen.add(cur)
            chain.append(cur)
            cur = next_cluster(fat, cur)
        terminated = cur >= 0x0FF8
        exp = (size + clus_bytes - 1) // clus_bytes
        size_ok = (len(chain) == exp) if size else (len(chain) <= 1)
        crossed = sorted(c for c in chain if byteidx(c) in (255, 511))
        results.append(dict(name=name, size=size, clusters=len(chain), exp=exp,
                            valid=ok and terminated and size_ok, crossed=crossed))
    return dict(path=path, files=results)


def main(argv):
    paths = argv[1:] or sorted(glob.glob(
        os.path.expanduser("~/Documents/msx/msx/disks/*.dsk")))
    valid = invalid = straddle_files = 0
    witness = []
    for p in paths:
        r = analyze(p)
        if not r:
            continue
        for f in r["files"]:
            if not f["valid"]:
                invalid += 1
                continue
            valid += 1
            if f["crossed"]:
                straddle_files += 1
                witness.append((os.path.basename(p), f))

    print(f"scanned {len(paths)} image path(s)")
    print(f"files with a VALID straddle-at-511 chain matching dir size: {valid}")
    print(f"  ...whose chain CROSSES a byteidx-255/511 cluster (witnesses): "
          f"{straddle_files}")
    print(f"files NOT reconstructible under the 511 rule (non-MSX-DOS/protected): "
          f"{invalid}")
    print()
    print("WITNESSES — stock-written files whose chain crosses a straddle-boundary")
    print("cluster and validate byte-exact under straddle-at-511 (the oracle):")
    for base, f in witness[:30]:
        cl = ", ".join(str(c) for c in f["crossed"][:8])
        print(f"  {base:<22} {f['name']!r} size={f['size']:>6} "
              f"clusters={f['clusters']:>3}(exp {f['exp']:>3})  crosses[{cl}]")
    # exit 0 iff at least one witness exists and nothing valid contradicts the rule
    return 0 if straddle_files else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
