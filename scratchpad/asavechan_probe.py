#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B design input 3: does `SAVE"x",A` corrupt an OUTPUT channel open beside it?

Main's SAVE ,A streams through the same engine globals (FWR_*) an OUTPUT
channel lives in, and nothing saves the active channel or clears FCH_ACTIVE
around it (read from the code 2026-10-03). The suspicion: PRINT#1 before the
SAVE, PRINT#1 after it, CLOSE -- and the channel's file comes back wrong. Both
files are read back from the IMAGE afterwards (bytes the machine wrote), and
the screen shows whether any statement raised.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT            # noqa: E402

# VERB=asave (default) | bsave | save: the write beside the open channel
VERB = {"asave": 'SAVE"Q.BAS",A', "bsave": 'BSAVE"Q.BAS",&H8000,&H800F',
        "save": 'SAVE"Q.BAS"'}[os.environ.get("VERB", "asave")]
PROG = ["NEW", "10 REM HELLO", 'OPEN"P1.TXT"FOR OUTPUT AS#1', 'PRINT#1,"AAA"',
        VERB, 'PRINT#1,"BBB"', "CLOSE#1", 'PRINT"[E]";ERR']


def content(img, ent):
    if not ent or not ent.get("cluster"):
        return None
    b = img
    off = 14 * 512 + (ent["cluster"] - 2) * 1024
    return b[off:off + min(ent["size"], 64)]


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"asavechan_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=3.0,
                                  diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", raw)
        img = open(dsk, "rb").read()
        f = RT.Fat12(dsk)
        p1, q = f.dirent("P1", "TXT"), f.dirent("Q", "BAS")
        print(f"== {tag}")
        print(f"   P1.TXT {p1} -> {content(img, p1)!r}")
        print(f"   Q.BAS  {q} -> {content(img, q)!r}")
        print(f"   screen tail: {scr[-220:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
