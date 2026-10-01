#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLOSESTAMP + D-DOSDATE (TODO): two date questions Joost's 2026-10-01 ruling
("Stamp as 3300") left open, measured on our DOS machine and the CF-3300.

The exerciser is probes/disk/dosdate.asm:
  (1) FOPEN FIXD.TXT (a fixture dated 0, 256 B), WRRND record 0 INSIDE its
      size, FCLOSE -- does FCLOSE re-date the entry?
  (2) GDATE, SDATE 1999-12-31, GDATE -- registers kept in page-3 RAM -- then
      FMAKE NEWD.TXT + WRBLK + FCLOSE: does SDATE move GDATE, and the stamp?
Reads its result record from RAM after the run (our own program's data) and
the two directory entries from the disk image.

  ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 probes/disk/disk_probe_dosdate.py
Exit 0 when the two machines agree on every reading; 1 otherwise.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402  -- run_once
import probe_tmp                                    # noqa: E402
import shutil                                       # noqa: E402

ASM = os.path.join(HERE, "dosdate.asm")


def date_of(word: int) -> str:
    return f"{1980 + (word >> 9)}-{(word >> 5) & 15:02d}-{word & 31:02d}" if word else "0"


def main() -> int:
    if not RT.OUR_MACHINE:
        sys.exit("no zerobas machine: set $ZEROBAS_BASIC_MACHINE")
    com = probe_tmp.tmp("dosdate.com")
    subprocess.run(["pasmo", "--bin", ASM, com], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    com_b = open(com, "rb").read()
    got = {}
    for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
        dsk = probe_tmp.tmp(f"dosdate_{tag.lower()}.dsk")
        shutil.copyfile(RT.DEFAULT_DOS, dsk)
        img = bytearray(open(dsk, "rb").read())
        fat12_add(img, "DOSDATE", "COM", com_b)
        fat12_add(img, "AUTOEXEC", "BAT", b"DOSDATE\r\n")
        fat12_add(img, "FIXD", "TXT", bytes(range(256)))   # dated 0 (fat12_add)
        open(dsk, "wb").write(img)
        out = probe_tmp.tmp(f"dosdate_{tag.lower()}.ram")
        cells = " ".join(str(a) for a in [0xC000] + list(range(0xC010, 0xC01B)))
        dump = (f"after time 100 {{ set f [open {{{out}}} w]; foreach a {{{cells}}} "
                f"{{ puts $f [debug read memory $a] }}; close $f }}\n")
        W.run_once(machine, dsk, 14, 110, 180, cmd="DOSDATE", extra_tcl=dump)
        ram = [int(x) for x in open(out).read().split()]
        f = RT.Fat12(dsk)
        b = f.img
        bps = struct.unpack_from("<H", b, 11)[0]
        root = (struct.unpack_from("<H", b, 14)[0] + b[16] * struct.unpack_from("<H", b, 22)[0]) * bps
        ents = {}
        for n, e in (("FIXD", "TXT"), ("NEWD", "TXT")):
            d = f.dirent(n, e)
            ents[n] = None if d is None else struct.unpack_from("<HH", b, root + d["idx"] * 32 + 22)
        r = ram[1:]
        g1 = (r[0] | r[1] << 8, r[3], r[2], r[4])          # year, month, day, dow
        g2 = (r[6] | r[7] << 8, r[9], r[8], r[10])
        got[tag] = {"PHASE": ram[0], "GDATE before": g1, "SDATE A": r[5],
                    "GDATE after": g2, "FIXD after WRRND+FCLOSE": ents["FIXD"],
                    "NEWD (after SDATE)": ents["NEWD"]}
        print(f"{tag}: PHASE={ram[0]} (2 = finished)")
        for k, v in got[tag].items():
            if k == "PHASE":
                continue
            if isinstance(v, tuple) and len(v) == 2:     # (time, date) of an entry
                v = f"time {v[0]:04X} date {v[1]:04X} = {date_of(v[1])}"
            print(f"  {k:26} {v}")
    same = [k for k in got["STOCK"] if got["STOCK"][k] == got["OURS"][k]]
    diff = [k for k in got["STOCK"] if k not in same]
    print(f"\n{'PASS' if not diff else 'FAIL'}: "
          + ("both machines agree" if not diff else f"they DIFFER on {diff}"))
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
