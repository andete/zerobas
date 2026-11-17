#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKCONTRACT gaps 2 / 3 (2026-11-17): BIOS PHYDIO ($0144 -> H.PHYD -> the disk ROM's
DSKIO) on its ERROR paths and a WRITE, called directly -- the National_CF-3300 (stock)
against zerobas's shipped disk machine. The register path a C-BIOS program without BASIC
uses; only a good read of sector 0 was compared (disk_probe_phydio.py).

Each row: our USR stub sets A = drive 0, B = sectors, C = media $F9, DE = the sector,
HL = $D200, Cy = write / read, calls PHYDIO and stores AF / BC; BASIC prints Cy, A
(the error code), B (the sectors not transferred). Write rows also compare the written
sector in both images afterwards.

  read_ok      sector 0, the control
  write_ok     $AA x 512 to sector 13 of a writable image          (gap 3: a direct write)
  write_wp     the same write to a READ-ONLY image file -- openMSX mounts it write-protected
  read_nodisk  sector 0 with NO disk in the drive
  read_far     sector 2000 of a 1440-sector disk

    python3 -u probes/disk/disk_probe_phydioerr.py [ROW ...]   (`make phydioerr-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the CF-3300 gave no reading.
"""
import os
import re
import shutil
import stat
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

REF = "National_CF-3300"
OURS = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
PHYDIO = 0x0144
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
# name -> (write?, sector, disk: "rw" / "ro" / None)
ROWS = {"read_ok": (False, 0, "rw"), "write_ok": (True, 13, "rw"), "write_wp": (True, 13, "ro"),
        "read_nodisk": (False, 0, None), "read_far": (False, 2000, "rw"),
        # the boundary (read_far split CF A=2 / ZB A=8): which rule does the CF-3300 use?
        "read_last": (False, 1439, "rw"), "read_1440": (False, 1440, "rw"),
        "read_1500": (False, 1500, "rw"), "read_ffff": (False, 0xFFFF, "rw")}


# KNOWN, PINNED divergences (filed TODO D-DSKIOCYL, TIER 6): a sector on a cylinder past the
# last (80+ on this 720 KB disk) -- the CF-3300 answers A = 2 (not ready), zerobas A = 8
# (record not found, the FDC's status mapped faithfully). $FFFF wraps back in range on both.
# Both sides' readings are PINNED: a change on either side fails the row.
KNOWN = {n: ("[R F 1  A 2  B 1 ]", "[R F 1  A 8  B 1 ]")
         for n in ("read_far", "read_1440", "read_1500")}


def stub(write, sector):
    # or a | scf / ld bc,$01F9 (B 1, C $F9) / ld de,SECTOR / ld hl,$D200 / ld a,0 /
    # call PHYDIO / push af / ld ($D104),bc / pop hl / ld ($D106),hl / ret
    return [0x37 if write else 0xB7, 0x01, 0xF9, 0x01, 0x11, sector & 255, sector >> 8,
            0x21, 0x00, 0xD2, 0x3E, 0x00, 0xCD, PHYDIO & 255, PHYDIO >> 8, 0xF5,
            0xED, 0x43, 0x04, 0xD1, 0xE1, 0x22, 0x06, 0xD1, 0xC9]


def prog(write, sector):
    s = stub(write, sector)
    fill = "&HAA" if write else "0"
    return ["NEW", f"10 CLEAR 200,&HCFFF:FOR I=0 TO 511:POKE &HD200+I,{fill}:NEXT",
            f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0)",
            '50 PRINT "[R F";PEEK(&HD106) AND 1;" A";PEEK(&HD107);" B";PEEK(&HD105);"]"',
            "60 DATA " + ",".join(str(b) for b in s), "RUN"]


def image(tag, kind):
    if kind is None:
        return None
    path = probe_tmp.tmp(f"phydioerr_{tag}.dsk")
    if os.path.exists(path):
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
    shutil.copy(FIXTURE, path)
    if kind == "ro":
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return path


def read(machine, tag, write, sector, kind):
    dsk = image(tag, kind)
    scr = omsx_repl.run_cases(machine, [("direct", prog(write, sector))], batch=False,
                              diska=dsk, reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              run_gap=25.0)[0] or ""
    rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    reg = next((r for r in rows if r.startswith("[R")), None)
    err = next((r for r in rows if "rror" in r or "ffline" in r or "rotect" in r), None)
    got = reg or (f"<{err}>" if err else None)
    sec = None
    if dsk and write:
        with open(dsk, "rb") as f:
            f.seek(sector * 512)
            sec = f.read(512)
    return got, sec


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = blind = 0
    for name in only:
        write, sector, kind = ROWS[name]
        got = {side: read(m, f"{side}_{name}", write, sector, kind)
               for side, m in (("CF", REF), ("ZB", OURS))}
        if got["CF"][0] is None:
            verdict, blind = "NO-READING", blind + 1
        else:
            same = got["CF"][0] == got["ZB"][0]
            img = ""
            if write:
                img_same = got["CF"][1] == got["ZB"][1]
                fill = got["CF"][1] is not None and got["CF"][1] == b"\xAA" * 512
                img = f" sector {sector}: {'SAME' if img_same else 'DIFFERS'}" \
                      f" (CF {'written' if fill else 'not written'})"
                same = same and img_same
            verdict = "SAME" if same else "DIVERGES"
            if name in KNOWN:
                same = (got["CF"][0], got["ZB"][0]) == KNOWN[name]
                verdict = "KNOWN (D-DSKIOCYL, pinned)" if same else "DIVERGES (the pin moved)"
            bad += not same
            print(f"ROW {name:11} CF={got['CF'][0]} ZB={got['ZB'][0]}{img} {verdict}", flush=True)
            continue
        print(f"ROW {name:11} CF={got['CF'][0]} ZB={got['ZB'][0]} {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: the CF-3300 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: PHYDIO's error paths and a write against the "
          f"CF-3300 ({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
