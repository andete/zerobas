#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Black-box characterisation of the STOCK National CF-3300 allocator's
free-then-reallocate ORDER (M30 follow-up investigation).

Context: the M30 round-trip `del_realloc` case found that after
  op1 = DELETE DELFILE.BIN  (frees a low contiguous cluster hole)
  op2 = WRBLK extend WRTEST.BIN
OURS (lowest-free-from-cluster-2 scan) picks the LOWEST freed cluster, but the
real CF-3300 oracle picks a DIFFERENT one. This probe does NOT propose a fix; it
CHARACTERISES what ordering stock actually uses, via differential disk layouts,
reading only stock's OUTPUT disk (never its ROM).

Each experiment: build a fresh /tmp copy of a real MSX-DOS-1 disk with a chosen
free/used layout, boot openMSX (National_CF-3300), let a tiny WRBLK.COM exerciser
(wrblk_rt.asm) DELETE a pre-seeded file then extend WRTEST.BIN by K clusters, then
pure-Python FAT12-parse the mutated image and report the RESULTING CLUSTER CHAIN.
The *sequence* of newly-allocated clusters is the diagnostic.

Models under test (predictions computed per-experiment, see MODELS below):
  lowest    : scan from cluster 2, take first free  (== OURS today)
  highest   : take the numerically-highest free cluster in the hole
  walk_last : reuse in the order the delete FREED them (rover = last cluster the
              delete chain-walk released); == "next-free rover set to last release"
  rover_wrap: a persistent next-free rover set to (last released) then scanning
              UPWARD with wrap-around (classic MS-DOS next-fit)

CLEAN-ROOM: our own exerciser + our own disk layout; the CF-3300 is a black box we
RUN and whose OUTPUT DISK we READ. No stock ROM code is ever read/disassembled.
Test disks are always /tmp copies of the user's disk.
"""
from __future__ import annotations

import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disk_probe_bdos import fat12_add                      # noqa: E402
from disk_probe_wrblk_roundtrip import (                    # noqa: E402
    Fat12, assemble_com, patch_params, run,
    OUR_MACHINE, REF_MACHINE, TARGET,
)

DEFAULT_DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")


# --------------------------------------------------------------------------- #
# low-level FAT12 helpers for CUSTOM (fragmented / reverse-chain) placement
# --------------------------------------------------------------------------- #
def _geom(img):
    bps = struct.unpack_from("<H", img, 11)[0]
    spc = img[13]
    resv = struct.unpack_from("<H", img, 14)[0]
    nfat = img[16]
    rootent = struct.unpack_from("<H", img, 17)[0]
    spf = struct.unpack_from("<H", img, 22)[0]
    first_fat = resv
    first_root = resv + nfat * spf
    root_secs = (rootent * 32 + bps - 1) // bps
    first_data = first_root + root_secs
    return dict(bps=bps, spc=spc, nfat=nfat, rootent=rootent, spf=spf,
                first_fat=first_fat, first_root=first_root, first_data=first_data,
                fat_off=first_fat * bps, clus_bytes=bps * spc)


def _fat_set(img, g, c, v):
    idx = g["fat_off"] + c * 3 // 2
    cur = img[idx] | (img[idx + 1] << 8)
    if c & 1:
        cur = (cur & 0x000F) | ((v & 0xFFF) << 4)
    else:
        cur = (cur & 0xF000) | (v & 0xFFF)
    img[idx] = cur & 0xFF
    img[idx + 1] = (cur >> 8) & 0xFF


def _fat_get(img, g, c):
    idx = g["fat_off"] + c * 3 // 2
    b = img[idx] | (img[idx + 1] << 8)
    return (b >> 4) if (c & 1) else (b & 0xFFF)


def _mirror_fats(img, g):
    fat0 = img[g["fat_off"]:g["fat_off"] + g["spf"] * g["bps"]]
    for k in range(g["nfat"]):
        b = (g["first_fat"] + k * g["spf"]) * g["bps"]
        img[b:b + len(fat0)] = fat0


def add_file_chain(img, name8, ext3, clusters, size):
    """Place a file occupying the EXACT `clusters` (in that CHAIN order): dir
    first-cluster = clusters[0], FAT wires clusters[i] -> clusters[i+1] -> EOC.
    Lets us build a REVERSE / fragmented chain the lowest-first fat12_add can't."""
    g = _geom(img)
    for i, c in enumerate(clusters):
        _fat_set(img, g, c, clusters[i + 1] if i + 1 < len(clusters) else 0xFFF)
    _mirror_fats(img, g)
    # data content is irrelevant to allocation order; leave whatever is there.
    for i in range(g["rootent"]):
        off = g["first_root"] * g["bps"] + i * 32
        if img[off] in (0x00, 0xE5):
            img[off:off + 8] = name8.encode().ljust(8)[:8].upper()
            img[off + 8:off + 11] = ext3.encode().ljust(3)[:3].upper()
            img[off + 11] = 0x20
            for j in range(12, 26):
                img[off + j] = 0
            struct.pack_into("<H", img, off + 26, clusters[0])
            struct.pack_into("<I", img, off + 28, size)
            return
    sys.exit("root directory full")


# --------------------------------------------------------------------------- #
# experiments
# --------------------------------------------------------------------------- #
def build_order(dos, out, com, del_clusters_desc=False):
    """DELFILE.BIN (4 clusters) + WRTEST.BIN (1 cluster) just above it.
    del_clusters_desc=False -> ascending chain (fat12_add, 336->337->338->339).
    del_clusters_desc=True  -> reverse chain (339->338->337->336) over the SAME
    physical clusters, so the delete frees them in the opposite walk order."""
    shutil.copyfile(dos, out)
    img = bytearray(open(out, "rb").read())
    if del_clusters_desc:
        # reserve the 4 low clusters first (so WRTEST lands at 340) by wiring a
        # reverse chain over exactly what fat12_add WOULD have used.
        g = _geom(img)
        tot = (len(img) // g["bps"] - g["first_data"]) // g["spc"] + 2
        free = [c for c in range(2, tot) if _fat_get(img, g, c) == 0][:4]
        add_file_chain(img, "DELFILE", "BIN", list(reversed(free)), 4096)
    else:
        fat12_add(img, "DELFILE", "BIN", bytes([0x99]) * 4096)
    fat12_add(img, TARGET[0], TARGET[1], bytes([0x66]) * 512)
    fat12_add(img, "WRBLK", "COM", com)
    fat12_add(img, "AUTOEXEC", "BAT", b"WRBLK\r\n")
    open(out, "wb").write(img)


EXPERIMENTS = {
    # extend WRTEST by 4 clusters after deleting the ascending-chain hole.
    # DECISIVE sequence test (lowest vs highest vs walk_last vs rover_wrap).
    "order4":   dict(recnum=32, desc=False,
                     note="ascending-chain hole {336-339}, +4-cluster extend"),
    # single-cluster extend after deleting a REVERSE-chain hole. Distinguishes
    # numeric-highest (->339) from walk-last-released (->336).
    "descend1": dict(recnum=8, desc=True,
                     note="reverse-chain hole (339->...->336), +1-cluster extend"),
    # extend by 4 after the reverse-chain delete: full order under reverse walk.
    "descend4": dict(recnum=32, desc=True,
                     note="reverse-chain hole, +4-cluster extend"),
}


def analyse(chain_before_first, chain, hole, note):
    """chain = WRTEST's full chain after the op; chain[0] is its original cluster
    (340). newly-allocated = chain[1:]. Report + compare to model predictions."""
    new = chain[1:]
    print(f"    note: {note}")
    print(f"    hole (freed clusters): {hole}")
    print(f"    WRTEST full chain: {chain}")
    print(f"    >>> newly allocated (in order): {new}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", default=DEFAULT_DOS)
    ap.add_argument("--exp", choices=list(EXPERIMENTS) + ["all"], default="order4")
    ap.add_argument("--machines", default="stock",
                    choices=["stock", "ours", "both"],
                    help="which side(s) to run (default stock: ours is known lowest-first)")
    ap.add_argument("--boot", type=int, default=14)
    ap.add_argument("--end", type=int, default=40)
    ap.add_argument("--timeout", type=float, default=110)
    args = ap.parse_args()

    com0 = assemble_com()
    exps = list(EXPERIMENTS) if args.exp == "all" else [args.exp]
    sides = {"stock": [("STOCK", REF_MACHINE)], "ours": [("OURS", OUR_MACHINE)],
             "both": [("OURS", OUR_MACHINE), ("STOCK", REF_MACHINE)]}[args.machines]

    for name in exps:
        e = EXPERIMENTS[name]
        print(f"\n===== EXPERIMENT {name}  ({e['note']}) =====")
        # recnum forces the extend length; cnt=1 single record far past EOF.
        com = patch_params(com0, e["recnum"], 128, 1, 0x77, delflag=1)
        for tag, machine in sides:
            out = f"/tmp/alloc_order_{name}_{tag.lower()}.dsk"
            build_order(args.dos_disk, out, com, del_clusters_desc=e["desc"])
            pre = Fat12(out)
            dd = pre.dirent("DELFILE", "BIN")
            hole, _ = pre.chain(dd["cluster"])
            wt = pre.dirent(*TARGET)
            print(f"  [{tag}] pre: DELFILE chain={hole}  WRTEST cl={wt['cluster']}")
            try:
                run(machine, out, args.boot, args.end, args.timeout)
            except TimeoutError as ex:
                print(f"  [{tag}] {ex}")
            post = Fat12(out)
            d = post.dirent(*TARGET)
            if not d:
                print(f"  [{tag}] WRTEST.BIN VANISHED"); continue
            ch, term = post.chain(d["cluster"])
            print(f"  [{tag}] post: size={d['size']} term={term:#05x}")
            analyse(wt["cluster"], ch, hole, e["note"])


if __name__ == "__main__":
    main()
