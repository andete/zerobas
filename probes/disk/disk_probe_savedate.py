#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WRBLKSEEK (b) / Joost 2026-10-01 "Stamp as 3300": a DISK BASIC write stamps
the directory entry exactly as the CF-3300 does (gate: savedate-acceptance).

DOS FMAKE on the CF-3300 stamps date 0821h (1984-01-01), time 0 (the --wseek
FCB dump). Disk BASIC reaches the directory through a different path on ours
(the sub-ROM's fat-prim-body.inc copy), so it is measured on its own: SAVE,
SAVE ,A and OPEN FOR OUTPUT / PRINT# / CLOSE, each a fresh file. The disk image
is read after the run: each entry's +22..25 (time, date) and its index in the
root directory (the value an FCB's +25 carries).

Exit 0 when every file exists on both machines with the same directory index,
+22..25 and size; 1 otherwise. Before the fix ours stamped 00 00 00 00 where
the CF-3300 stamps 00 00 21 08 (scratchpad/savedate_run.out).

Clean room: reads the DISK IMAGE we wrote and the emulator produced -- data.
"""
import os, shutil, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT            # noqa: E402
from disk_probe_bdos import fat12_add               # noqa: E402

# Created by the run: SD1..SD3. MODIFIED, starting from fixtures dated 0 (fat12_add
# writes no date): FIX by APPEND, FIXR by a random PUT; CP is COPY's destination
# from FIXC. FIXI is only OPENed FOR INPUT and closed: the NEGATIVE arm -- a READ
# must not stamp, so it stays 0 on both machines.
FILES = [("SD1", "BAS"), ("SD2", "BAS"), ("SD3", "TXT"), ("FIX", "TXT"),
         ("FIXR", "DAT"), ("CP", "TXT"), ("FIXI", "TXT")]
FIXTURES = {("FIX", "TXT"): b"A\r\n", ("FIXR", "DAT"): bytes(64),
            ("FIXC", "TXT"): b"C\r\n", ("FIXI", "TXT"): b"I\r\n"}
PROG = ["NEW", "10 REM", 'SAVE"SD1.BAS"', 'SAVE"SD2.BAS",A',
        'OPEN"SD3.TXT"FOR OUTPUT AS#1:PRINT#1,"X":CLOSE',
        'OPEN"FIX.TXT"FOR APPEND AS#1:PRINT#1,"B":CLOSE',
        'OPEN"FIXR.DAT"AS#1 LEN=16:FIELD#1,16 AS F$:LSET F$="Z":PUT#1,2:CLOSE',
        'COPY"FIXC.TXT"TO"CP.TXT"',
        'OPEN"FIXI.TXT"FOR INPUT AS#1:CLOSE', 'PRINT"[DONE]"']


def entries(path):
    f = RT.Fat12(path)
    b = f.img
    bps = struct.unpack_from("<H", b, 11)[0]
    root = (struct.unpack_from("<H", b, 14)[0] + b[16] * struct.unpack_from("<H", b, 22)[0]) * bps
    out = {}
    for n, e in FILES:
        d = f.dirent(n, e)
        if d is None:
            out[f"{n}.{e}"] = None
            continue
        raw = bytes(b[root + d["idx"] * 32: root + d["idx"] * 32 + 32])
        out[f"{n}.{e}"] = (d["idx"], raw[22:26].hex(" "), d["size"])
    return out


def main():
    rows = {}
    ours = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
    for tag, machine in (("CF-3300", "National_CF-3300"), ("OURS", ours)):
        dsk = probe_tmp.tmp(f"savedate_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        img = bytearray(open(dsk, "rb").read())
        for (n, e), data in FIXTURES.items():
            fat12_add(img, n, e, data)
        open(dsk, "wb").write(img)
        # reset to SCREEN 0: the CF-3300 boots SCREEN 1 and the capture reads
        # the text plane (this probe's first run forgot it, as fcbblock's did)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=4.0,
                                  diska=dsk)[0] or ""
        rows[tag] = entries(dsk)
        print(f"{tag}: screen {'has' if '[DONE]' in raw else 'LACKS'} [DONE]")
        for k, v in rows[tag].items():
            print(f"  {k:8} " + ("NOT WRITTEN" if v is None else
                                 f"dir index {v[0]:3d}  +22..25 (time, date) = {v[1]}  size {v[2]}"))
    ref, zb = rows["CF-3300"], rows["OURS"]
    if any(v is None for v in ref.values()):
        print("INSTRUMENT FAULT: the CF-3300 wrote nothing -- no reference to compare")
        return 2
    bad = [k for k in ref if zb.get(k) != ref[k]]
    print(f"\n{'PASS' if not bad else 'FAIL'}: disk BASIC directory stamps "
          + ("match the CF-3300" if not bad else f"DIFFER on {bad}"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
