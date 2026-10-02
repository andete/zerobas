#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKFULLRETRY, measured: a BSAVE of 16 KB onto a disk with ONE free
cluster fills the disk mid-write. Does it answer 66, and how long does each
machine take? The sub-ROM SAVE tenant resumes its loop after a failure, so
the suspicion (from the code) is that ours retries a FAT scan per byte.

The program times itself with TIME (the VDP-interrupt counter: 60 Hz on the
Japanese CF-3300, 50 Hz on our EU target), so the reading is one summary line: `B <err> <ticks> #`.
"""
import os, re, shutil, struct, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_diskfull as DF                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

LEAVE = int(os.environ.get("LEAVE", "1"))          # free clusters to leave
PROG = ["NEW", "10 ON ERROR GOTO 90", "20 TIME=0",
        '30 BSAVE"BF.BIN",&H8000,&HBFFF', '40 PRINT"B";0;TIME;"#":END',
        '90 PRINT"B";ERR;TIME;"#":END', "RUN"]


def leave_free(path, n):
    """full_disk, then free the LAST n data clusters again."""
    DF.full_disk(path)
    b = bytearray(open(path, "rb").read())
    bps = struct.unpack_from("<H", b, 11)[0]
    resv = struct.unpack_from("<H", b, 14)[0]
    nfat = b[16]
    spf = struct.unpack_from("<H", b, 22)[0]
    rootent = struct.unpack_from("<H", b, 17)[0]
    spc = b[13]
    total = struct.unpack_from("<H", b, 19)[0]
    first_data = resv + nfat * spf + (rootent * 32 + bps - 1) // bps
    nclus = (total - first_data) // spc + 2
    fat = resv * bps
    for c in range(nclus - n, nclus):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        v = (v & 0x000F) if c & 1 else (v & 0xF000)
        b[i], b[i + 1] = v & 0xFF, v >> 8
    for k in range(1, nfat):
        b[(resv + k * spf) * bps:(resv + (k + 1) * spf) * bps] = b[fat:fat + spf * bps]
    open(path, "wb").write(b)


def main():
    for tag, machine, hz in (("CF-3300", "National_CF-3300", 60), ("OURS", "C-BIOS_MSX1_EU_REPACK_DISK", 50)):
        dsk = probe_tmp.tmp(f"bsvfull_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        leave_free(dsk, LEAVE)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=4.0,
                                  run_gap=float(os.environ.get("GAP", "120")),
                                  diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
        m = re.findall(r"\bB ?(-?\d+) ?(\d+) ?#", scr)
        print(f"== {tag}: {('ERR %s, %s ticks (%.1f s)' % (m[-1][0], m[-1][1], int(m[-1][1]) / hz)) if m else 'NO READING'}")
        print(f"   screen tail: {scr[-200:]}")
        print(f"   BF.BIN entry: {RT.Fat12(dsk).dirent('BF', 'BIN')}")
        img = open(dsk, "rb").read()
        c = 714                                     # the one cluster left free
        i = 512 + c * 3 // 2
        v = img[i] | img[i + 1] << 8
        print(f"   FAT[{c}] = {(v >> 4) if c & 1 else (v & 0xFFF):03X} (000 = free)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
