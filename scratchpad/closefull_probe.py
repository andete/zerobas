#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLOSEFULL: is a disk-full at CLOSE an error, on the CF-3300 and on ours?

A disk with NO free cluster: OPEN FOR OUTPUT only creates the directory entry,
`PRINT #1,"HELLO"` stays in the buffer, so the first cluster is allocated at
CLOSE -- the only statement that can fail. Ours' fdcc_disk discards the carry of
fat_io_putbyte/fat_io_close (basic/files.asm), though chan_gate's comment says
CLOSE re-raises it. The screen after each line, and the directory entry the run
leaves, are read.
"""
import os, re, shutil, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT            # noqa: E402

PROG = ['ON ERROR GOTO 0', 'OPEN"CF.TXT"FOR OUTPUT AS#1:PRINT"[O]"',
        'PRINT#1,"HELLO":PRINT"[P]"', 'CLOSE#1:PRINT"[C]"', 'PRINT"E=";ERR',
        # still open after the failed CLOSE? (File already open = 54) -- then a
        # second CLOSE, and the channel's mode via a fresh OPEN
        'OPEN"CG.TXT"FOR OUTPUT AS#1:PRINT"[R]"', 'PRINT"E2=";ERR',
        'CLOSE#1:PRINT"[C2]"', 'PRINT"E3=";ERR',
        # D-DISKFULL's SAVE face, on the same full disk. (The PRINT# face is
        # scratchpad/printfull_probe.py: on ours it HANGS, and would swallow this.)
        '10 REM', 'SAVE"SF.BAS":PRINT"[S]"', 'PRINT"E5=";ERR', 'PRINT"[END]"']


def full_disk(path):
    """Mark every free FAT12 cluster used (EOC), in every FAT copy."""
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

    def get(c):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        return v >> 4 if c & 1 else v & 0xFFF

    def put(c, val):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        v = (v & 0x000F) | (val << 4) if c & 1 else (v & 0xF000) | val
        b[i], b[i + 1] = v & 0xFF, v >> 8

    freed = 0
    for c in range(2, nclus):
        if get(c) == 0:
            put(c, 0xFFF)
            freed += 1
    for k in range(1, nfat):
        b[(resv + k * spf) * bps:(resv + (k + 1) * spf) * bps] = b[fat:fat + spf * bps]
    open(path, "wb").write(b)
    return freed


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"closefull_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        n = full_disk(dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=4.0,
                                  diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", raw)
        print(f"== {tag}: {n} free clusters marked used")
        print(f"  screen: {scr[-400:]}")
        d = RT.Fat12(dsk).dirent("CF", "TXT")
        print(f"  CF.TXT entry: {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
