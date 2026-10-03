#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SAVEFULLSTAMP, measured: what do tokenised SAVE, SAVE ,A and
PRINT#+CLOSE leave on a disk with ONE free cluster when the file is bigger than
a cluster? D-DISKFULLSTAMP measured BSAVE: the CF-3300 refuses the block WHOLE
and closes (header + Ctrl-Z, size 8). These writers may not.

Each case is boot-per-case on a fresh test720 copy with every free cluster but
the last marked used (bsvfull_probe.leave_free). A ~2 KB program is typed first
(30 lines of REM). Read back: ERR, then the file's directory entry, its first
16 bytes and the FAT entry of the one free cluster. These are file bytes the
machine WROTE, not ROM.

    CASE=save|asave|print  ONLY=CF-3300|OURS  python3 -u scratchpad/savefull_probe.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT            # noqa: E402
import bsvfull_probe as B                          # noqa: E402

BIG = [f"{100 + i} REM " + "X" * 60 for i in range(30)]
CASES = {
    "save": ("SF", "BAS", BIG + ["10 ON ERROR GOTO 90", "20 SAVE\"SF.BAS\"",
                                 '30 PRINT"Q";0;"#":END', '90 PRINT"Q";ERR;"#":END', "RUN"]),
    "asave": ("SA", "BAS", BIG + ["10 ON ERROR GOTO 90", "20 SAVE\"SA.BAS\",A",
                                  '30 PRINT"Q";0;"#":END', '90 PRINT"Q";ERR;"#":END', "RUN"]),
    # PRINT# past one cluster, then CLOSE; the error lands in the loop or at CLOSE
    "print": ("PF", "TXT", ["NEW", "10 ON ERROR GOTO 90", '20 OPEN"PF.TXT"FOR OUTPUT AS#1',
                            "30 FOR I=1 TO 80:PRINT#1,STRING$(20,65):NEXT", "40 CLOSE#1",
                            '50 PRINT"Q";0;I;"#":END', '90 PRINT"Q";ERR;I;ERL;"#":CLOSE:END', "RUN"]),
}


def main():
    name = os.environ.get("CASE", "save")
    stem, ext, lines = CASES[name]
    sides = (("CF-3300", "National_CF-3300"), ("OURS", "C-BIOS_MSX1_EU_REPACK_DISK"))
    only = os.environ.get("ONLY")
    for tag, machine in (x for x in sides if not only or x[0] == only):
        dsk = probe_tmp.tmp(f"savefull_{name}_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        B.leave_free(dsk, 1)
        raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=1.5,
                                  run_gap=60.0, diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
        m = re.findall(r"\bQ ?((?:-?\d+ ?)+)#", scr)
        print(f"== {name} {tag}: {m[-1] if m else 'NO READING'}")
        ent = RT.Fat12(dsk).dirent(stem, ext)
        print(f"   {stem}.{ext} entry: {ent}")
        img = open(dsk, "rb").read()
        if ent and ent.get("cluster"):
            off = 14 * 512 + (ent["cluster"] - 2) * 1024
            print(f"   first 16 B: {img[off:off + 16].hex(' ')}")
            last = img[off:off + 1024]
            print(f"   cluster's last 8 B: {last[-8:].hex(' ')}")
        i = 512 + 714 * 3 // 2
        v = img[i] | img[i + 1] << 8
        print(f"   FAT[714] = {v & 0xFFF:03X} (000 = free)")
        print(f"   screen tail: {scr[-160:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
