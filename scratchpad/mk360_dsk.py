#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW (Joost 2026-11-28 "Measure more"): a 360 KB single-sided MSX disk (media $F8, 2 sectors per FAT) holding
MSXDOS.SYS, COMMAND.COM and one more file from a 720 KB source image, so the FAT-location probe can see whether the
reference's FAT image follows the disk's FAT size. The boot sector is the source's with the 360 KB BPB patched in.
    python3 scratchpad/mk360_dsk.py SRC.dsk OUT.dsk [FILE ...]
"""
import struct
import sys


def files_of(img):
    bps, spc, res, nf, nroot, _tot, _med, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (res + nf * spf) * bps
    data = root + nroot * 32
    out = {}
    for i in range(nroot):
        e = img[root + 32 * i: root + 32 * i + 32]
        if e[0] in (0, 0xE5) or e[11] & 0x18:
            continue
        name = (e[0:8].decode("latin1").rstrip() + "." + e[8:11].decode("latin1").rstrip()).rstrip(".")
        clus, size = struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<I", e, 28)[0]
        buf = bytearray()
        while 2 <= clus < 0xFF8:
            off = data + (clus - 2) * spc * bps
            buf += img[off: off + spc * bps]
            fo = res * bps + clus * 3 // 2
            v = struct.unpack_from("<H", img, fo)[0]
            clus = v >> 4 if clus & 1 else v & 0xFFF
        out[name] = (bytes(e), bytes(buf[:size]))
    return out


def main():
    src, dst, *names = sys.argv[1:]
    names = ["MSXDOS.SYS", "COMMAND.COM"] + (names or ["MSXBUNSE.ROM"])
    s = bytearray(open(src, "rb").read())
    fl = files_of(s)
    bps, spc, res, nf, nroot, tot, med, spf, spt, heads = 512, 2, 1, 2, 112, 720, 0xF8, 2, 9, 1
    img = bytearray(tot * bps)
    img[0:bps] = s[0:bps]
    struct.pack_into("<HBHBHHBHHH", img, 11, bps, spc, res, nf, nroot, tot, med, spf, spt, heads)
    fat = bytearray(spf * bps)
    fat[0:3] = bytes([med, 0xFF, 0xFF])

    def setfat(c, v):
        o = c * 3 // 2
        w = struct.unpack_from("<H", fat, o)[0]
        w = (w & 0x000F) | (v << 4) if c & 1 else (w & 0xF000) | v
        struct.pack_into("<H", fat, o, w)

    root = (res + nf * spf) * bps
    data = root + nroot * 32
    nxt = 2
    for i, n in enumerate(names):
        ent, body = fl[n]
        ncl = max(1, -(-len(body) // (spc * bps)))
        first = nxt
        for k in range(ncl):
            setfat(nxt, nxt + 1 if k < ncl - 1 else 0xFFF)
            nxt += 1
        off = data + (first - 2) * spc * bps
        img[off: off + len(body)] = body
        e = bytearray(ent)
        struct.pack_into("<H", e, 26, first)
        img[root + 32 * i: root + 32 * i + 32] = e
    for k in range(nf):
        img[(res + k * spf) * bps: (res + (k + 1) * spf) * bps] = fat
    open(dst, "wb").write(img)
    print(f"{dst}: 360 KB, {len(names)} files, clusters 2..{nxt - 1} used of {(tot - data // bps) // spc + 1}")


main()
