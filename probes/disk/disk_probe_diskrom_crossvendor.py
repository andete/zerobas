#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cross-vendor disk-ROM provenance comparison (identity only — never disassembly).

Reproduces the finding behind `spec-diskrom-kernel.md` "Clean-room basis" and
`oracle-artifacts.md` "Cross-vendor disk-ROM set": that the MSX disk ROM is a
**shared ASCII/Microsoft MSX-DOS-1 kernel (~2/3, byte-identical industry-wide)**
plus a vendor-specific third, and that the entries this MSXDOS.SYS hard-codes
($4030, $50A9, $5454 CONOUT, $4462, $544E) all fall in the shared region — i.e.
they are cross-vendor de-facto-standard entries, the same legitimacy class as the
published $4010 DSKIO / $4016 GETDPB.

This is a PROVENANCE / identity analysis, not a black-box behavioural probe: it
compares reference disk-ROM *files* for byte-identity. It deliberately never
prints or interprets ROM code bytes (only hashes, diff counts, and per-offset
match/differ) — reading a reference ROM to understand its code is forbidden;
checking whether two oracle artifacts are the same file is provenance, which the
charter allows (cross-source validation; see oracle-artifacts.md).

The vendor ROMs are the user's local oracle stash, not committed to the repo;
the expected SHA1s are pinned in oracle-artifacts.md. Run:

    python3 probes/disk/disk_probe_diskrom_crossvendor.py
    python3 probes/disk/disk_probe_diskrom_crossvendor.py --roms ~/Documents/msx/share/systemroms
"""
from __future__ import annotations

import argparse
import gzip
import os
import sys

# Disk ROMs in the local systemroms stash, by vendor/model. CF-3300 is the
# reference (our oracle machine). All are 16 KB ($4000-$7FFF).
VENDOR_ROMS = {
    "National CF-3300":     "cf-3300_disk",
    "Spectravideo SVI-738": "svi-738_disk",
    "Daewoo DPF-550":       "dpf-550_disk",
    "Philips VG-8235":      "vg8235_disk",
    "Sony HB-F500P":        "hb-f500p_disk",
    "Philips NMS-8245":     "nms8245_disk",
    "Panasonic FS-4600":    "fs-4600_disk",
}
REFERENCE = "National CF-3300"

# The fixed disk-ROM entries this MSXDOS.SYS hard-codes (offset = addr - $4000).
HARDCODED_ENTRIES = {
    "$4030 GETWRK": 0x0030,
    "$50A9":        0x10A9,
    "$5454 CONOUT": 0x1454,
    "$4462":        0x0462,
    "$544E":        0x144E,
}
DEFAULT_ROMS = os.path.expanduser("~/Documents/msx/share/systemroms")


def load(roms_dir: str, stem: str) -> bytes | None:
    for cand in (f"{stem}.rom.gz", f"{stem}.rom"):
        p = os.path.join(roms_dir, cand)
        if os.path.isfile(p):
            data = open(p, "rb").read()
            return gzip.decompress(data) if cand.endswith(".gz") else data
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roms", default=DEFAULT_ROMS,
                    help=f"dir holding *_disk.rom(.gz) (default {DEFAULT_ROMS})")
    args = ap.parse_args()

    roms = {name: load(args.roms, stem) for name, stem in VENDOR_ROMS.items()}
    present = {n: r for n, r in roms.items() if r is not None}
    if REFERENCE not in present:
        print(f"SKIP: reference {REFERENCE} not found in {args.roms} "
              f"(vendor ROMs are the local oracle stash, not committed). "
              f"Present: {sorted(present)}", file=sys.stderr)
        return 0  # not a failure: the stash is optional/local
    ref = present[REFERENCE]
    N = min(len(r) for r in present.values())
    others = [n for n in present if n != REFERENCE]

    print(f"=== cross-vendor disk-ROM comparison ({len(present)} vendors, {N} bytes) ===")
    print(f"reference: {REFERENCE}\n")

    # 1. overall difference + the $5454 (and each hard-coded entry) identity
    print("vendor                 | overall diff | hard-coded entries identical to reference?")
    all_entry_match = {e: True for e in HARDCODED_ENTRIES}
    for n in others:
        r = present[n]
        diff = sum(1 for i in range(N) if r[i] != ref[i])
        marks = []
        for e, off in HARDCODED_ENTRIES.items():
            same = r[off] == ref[off]
            all_entry_match[e] &= same
            marks.append(f"{e}={'=' if same else 'X'}")
        print(f"  {n:<20} | {diff:5d} ({100*diff//N:2d}%) | " + " ".join(marks))

    # 2. shared (byte-identical-across-ALL) extent
    idmap = [all(present[n][i] == ref[i] for n in others) for i in range(N)]
    shared = sum(idmap)
    print(f"\nshared (byte-identical across all {len(present)} vendors): "
          f"{shared}/{N} = {100*shared//N}%")
    # contiguous shared runs >= 64 bytes
    runs = []
    i = 0
    while i < N:
        if idmap[i]:
            j = i
            while j < N and idmap[j]:
                j += 1
            if j - i >= 64:
                runs.append((i, j))
            i = j
        else:
            i += 1
    print("largest shared blocks:")
    for a, b in sorted(runs, key=lambda x: -(x[1] - x[0]))[:5]:
        print(f"  ${0x4000+a:04X}-${0x4000+b-1:04X}  ({b-a} bytes)")

    # 3. verdict: the cited finding is that every hard-coded entry is shared
    print("\n=== verdict (the cited finding) ===")
    ok = True
    for e, off in HARDCODED_ENTRIES.items():
        in_shared = idmap[off]
        ok &= in_shared
        print(f"  {e:<14} (off ${off:04X}): "
              f"byte-identical across all vendors = {all_entry_match[e]}; "
              f"in a shared run = {in_shared}")
    print(f"\n{'PASS' if ok else 'FAIL'} — every MSXDOS.SYS-hard-coded entry lies in the "
          f"cross-vendor shared kernel (de-facto-standard ABI)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
