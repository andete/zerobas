#!/usr/bin/env python3
"""D-TPAPTAIL (c): what does a machine-code routine called from BASIC get from
$F368+3, before any MSX-DOS session and after one (A>BASIC)?

The test is a FILE, T.BAS, run with one typed line (`RUN"T.BAS"`): typing the
USR program line by line was unreliable (scratchpad/f368bas_nodos.out). T.BAS
pokes our own 33-byte routine at &HC000 and calls it through USR:

  in a,($A8) / ld ($C030),a        the primary slots before
  ld a,($FFFF) / cpl / ld ($C031),a  page 3's subslot register before
  call $F36B (or $F368)            the entry under test (RAM-resident on the
                                   reference: CALLED, never read -- §8.5)
  in a,($A8) / ld ($C032),a        ... and after
  ld a,($FFFF) / cpl / ld ($C033),a
  ld a,$5A / ld ($C034),a          "it came back"
  ret

then prints `F:` and the five bytes. A line without `F:` is "never came back"
(or the screen said why). Black box: typed keys in, the text screen out.

  nodos  a data disk (a copy of disk/test720.dsk) + T.BAS, at the BASIC prompt
  dos    the MSX-DOS 1 system disk (a copy) + T.BAS: DOS boots, `BASIC`, then RUN

    python3 -u scratchpad/f368use_probe.py [--dos-disk PATH]
"""
import argparse
import os
import shutil
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl   # noqa: E402
import probe_tmp   # noqa: E402

DEFAULT_DOS_DISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
def code(target):
    return [0xDB, 0xA8, 0x32, 0x30, 0xC0, 0x3A, 0xFF, 0xFF, 0x2F, 0x32, 0x31, 0xC0,
        0xCD, target & 0xFF, target >> 8,
        0xDB, 0xA8, 0x32, 0x32, 0xC0, 0x3A, 0xFF, 0xFF, 0x2F, 0x32, 0x33, 0xC0,
        0x3E, 0x5A, 0x32, 0x34, 0xC0, 0xC9]


PEEKS = ";\" \";".join(f"HEX$(PEEK(&HC03{i}))" for i in range(5))
def tbas(target):
    CODE = code(target)
    return "\r\n".join([
    "10 CLEAR 200,&HBFFF",
    f"20 FOR I=0 TO {len(CODE) - 1}:READ A$:POKE &HC000+I,VAL(\"&H\"+A$):NEXT",
    "30 POKE &HC034,0:DEFUSR=&HC000:X=USR(0)",
    f"40 PRINT \"F:\";{PEEKS}",
    "50 DATA " + ",".join(f"{b:02X}" for b in CODE[:17]),
    "60 DATA " + ",".join(f"{b:02X}" for b in CODE[17:]),
]) + "\r\n\x1a"


TO_BASIC = ["", "", "BASIC", "SCREEN 0:WIDTH 40"]   # DOS: date, time, BASIC; text readable


def fat12_add(img: bytearray, name8: str, ext3: str, content: bytes):
    """Add a root-directory file to a FAT12 image in place, using its own BPB."""
    bps, spc = struct.unpack_from("<H", img, 11)[0], img[13]
    rsvd, nfat = struct.unpack_from("<H", img, 14)[0], img[16]
    roots, spf = struct.unpack_from("<H", img, 17)[0], struct.unpack_from("<H", img, 22)[0]
    fat0 = rsvd * bps
    root0 = fat0 + nfat * spf * bps
    data0 = root0 + roots * 32
    csz = spc * bps
    nclus = (len(img) - data0) // csz + 2

    def get(c):
        o = fat0 + c * 3 // 2
        v = img[o] | img[o + 1] << 8
        return v >> 4 if c & 1 else v & 0xFFF

    def put(c, v):
        for f in range(nfat):
            o = fat0 + f * spf * bps + c * 3 // 2
            if c & 1:
                img[o] = (img[o] & 0x0F) | (v << 4 & 0xF0)
                img[o + 1] = v >> 4 & 0xFF
            else:
                img[o] = v & 0xFF
                img[o + 1] = (img[o + 1] & 0xF0) | (v >> 8 & 0x0F)

    need = max(1, -(-len(content) // csz))
    free = [c for c in range(2, nclus) if get(c) == 0][:need]
    if len(free) < need:
        sys.exit("INSTRUMENT FAULT: the image is full")
    for i, c in enumerate(free):
        put(c, free[i + 1] if i + 1 < len(free) else 0xFFF)
        chunk = content[i * csz:(i + 1) * csz]
        img[data0 + (c - 2) * csz:data0 + (c - 2) * csz + len(chunk)] = chunk
    for e in range(roots):
        o = root0 + e * 32
        if img[o] in (0x00, 0xE5):
            img[o:o + 32] = bytes(32)
            img[o:o + 11] = (name8.ljust(8) + ext3.ljust(3)).upper().encode("ascii")
            img[o + 11] = 0x20
            struct.pack_into("<HI", img, o + 26, free[0], len(content))
            return
    sys.exit("INSTRUMENT FAULT: the root directory is full")


def screen(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK)
    a = ap.parse_args()
    if not os.path.isfile(a.dos_disk):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {a.dos_disk}")
        return 2
    for case, target in (("nodos", 0xF36B), ("dos", 0xF36B), ("nodos", 0xF368), ("dos", 0xF368)):
        for m in ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"):
            src = a.dos_disk if case == "dos" else os.path.join(REPO, "disk", "test720.dsk")
            img = bytearray(open(src, "rb").read())
            fat12_add(img, "T", "BAS", tbas(target).encode("ascii"))
            dsk = probe_tmp.tmp(f"f368use_{case}_{m}.dsk")
            open(dsk, "wb").write(img)
            lines = (TO_BASIC if case == "dos" else []) + ['RUN"T.BAS"']
            reset = ("",) if case == "dos" else ("", "SCREEN 0:WIDTH 40")
            try:
                got = screen(omsx_repl.run_cases(m, [("direct", lines)], batch=False, diska=dsk,
                                                 boot=14.0, reset=reset, step=5.0,
                                                 run_gap=20.0)[0])
            except SystemExit as e:
                got = "<APPARATUS: " + str(e).splitlines()[0][:70] + ">"
            fline = next((p.strip() for p in (got or "").split(" | ") if p.strip().startswith("F:")),
                         "NO F: LINE")
            print(f"ROW ${target:04X} {case:5s} {m:28s} {fline}")
            print(f"    screen: {got}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
