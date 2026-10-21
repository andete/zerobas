#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN triage (facdemo3.di2): WHERE does a disk machine take a disk's geometry
from -- the boot sector's BPB, or the FAT's first byte (the media ID)?

facdemo3's boot sector holds text over BPB bytes 11..13 (bytes per sector reads
$2037, sectors per cluster $20); the rest of its BPB and its FAT ($F9) are a
720 KB disk's. The CF-3300 reads it (its AUTOEXEC.BAS runs); zerobas lists no file.

Every variant is built HERE from the collection's empty.dsk (720 KB, $F9; the
collection's location comes from DISKCORPUS_DIR and is never written here) plus an
AUTOEXEC.BAS of our own (`10 PRINT "AUTOX"`, ASCII) written into cluster 2:
  V0 valid                      the control
  V1 BPB bytes 11..13 = 37 20 20 facdemo3's damage
  V2 BPB bytes 11..29 all zero  no BPB at all
  V3 BPB media byte = $F8       BPB says single-sided, FAT says $F9
  V4 FAT media byte = $F8       BPB says $F9, FAT says single-sided (both copies)
  MF8 .. MFF                    a disk laid out as that media ID's standard MSX-DOS 1
                                format, BPB all zero (MEDIA below is the expectation)
  SF8 .. SFF                    the same, the image cut to that format's size (TOTAL)
  P8                            SF8 with a VALID 360 KB BPB: is a single-sided disk
                                read past its first track (the program is at sector 12)?
Boot, read the screen at T12 (AUTOX printed?), type FILES, read it again. Keys in,
the screen out.
    DISKCORPUS_DIR=... python3 -u scratchpad/bpbrule_probe.py [cf,eu,zb] [V0,V1,...]
"""
import os, subprocess, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diskcorpus_run as D  # noqa: E402

MACHINES = {"cf": ("National_CF-3300", []),
            "eu": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}
PROG = b'10 PRINT "AUTOX"\r\n\x1a'


def base():
    b = bytearray(open(os.path.join(os.environ["DISKCORPUS_DIR"], "empty.dsk"), "rb").read())
    assert len(b) == 737280 and b[21] == 0xF9, "empty.dsk is not the 720 KB $F9 disk"
    fat1, fat2, root, data = 1 * 512, 4 * 512, 7 * 512, 14 * 512
    assert b[fat1] == 0xF9
    b[fat1 + 3] = 0xFF                        # cluster 2 = $FFF, end of chain
    b[fat1 + 4] = (b[fat1 + 4] & 0xF0) | 0x0F
    b[fat2:fat2 + 3 * 512] = b[fat1:fat1 + 3 * 512]   # empty.dsk's 2nd copy is all 0
    e = bytearray(32)
    e[0:11] = b"AUTOEXECBAS"
    e[11] = 0x20
    e[24:26] = (0x0821).to_bytes(2, "little")  # 1984-01-01
    e[26:28] = (2).to_bytes(2, "little")
    e[28:32] = len(PROG).to_bytes(4, "little")
    b[root:root + 32] = e
    b[data:data + len(PROG)] = PROG
    return b


# The standard MSX-DOS 1 formats by media ID (own expectation, under test):
# (sectors per cluster, sectors per FAT, root entries); 1 reserved sector, 2 FATs.
MEDIA = {0xF8: (2, 2, 112), 0xF9: (2, 3, 112), 0xFA: (2, 1, 112), 0xFB: (2, 2, 112),
         0xFC: (1, 2, 64), 0xFD: (2, 2, 112), 0xFE: (1, 1, 64), 0xFF: (2, 1, 112)}


def media_disk(m):
    """A 720 KB image laid out as media ID m's format, BPB ALL ZERO, with our
    AUTOEXEC.BAS in cluster 2 -- only a machine that takes the geometry from the
    FAT's media ID finds it."""
    spc, spf, rootn = MEDIA[m]
    b = bytearray(open(os.path.join(os.environ["DISKCORPUS_DIR"], "empty.dsk"), "rb").read())
    b[11:30] = bytes(19)
    b[512:] = bytes(len(b) - 512)
    root = 1 + 2 * spf
    data = root + rootn * 32 // 512
    for f in (1, 1 + spf):
        o = f * 512
        b[o:o + 5] = bytes([m, 0xFF, 0xFF, 0xFF, 0x0F])   # cluster 2 = $FFF
    e = bytearray(32)
    e[0:11] = b"AUTOEXECBAS"
    e[11] = 0x20
    e[24:26] = (0x0821).to_bytes(2, "little")
    e[26:28] = (2).to_bytes(2, "little")
    e[28:32] = len(PROG).to_bytes(4, "little")
    b[root * 512:root * 512 + 32] = e
    b[data * 512:data * 512 + len(PROG)] = PROG
    return bytes(b)


# Each format's total sectors: an image of THAT size, because openMSX takes a .dsk's
# physical geometry from its size -- on a 720 KB image a single-sided or 8-sector
# format's logical sectors past track 0 land elsewhere in the file (measured: on the
# 720 KB images only F9 / FD / FE ran; their data sits in track 0 or matches).
TOTAL = {0xF8: 720, 0xF9: 1440, 0xFA: 640, 0xFB: 1280, 0xFC: 360, 0xFD: 720,
         0xFE: 320, 0xFF: 640}


def variant(v):
    if v == "P8":                             # a VALID 360 KB $F8 disk (BPB filled in)
        b = bytearray(media_disk(0xF8)[:720 * 512])
        b[11:30] = bytes.fromhex("0002" "02" "0100" "02" "7000" "d002" "f8" "0200"
                                 "0900" "0100" "0000")
        return bytes(b)
    if v.startswith("S"):                     # S<m>: media_disk, sized to its format
        m = int(v[1:], 16)
        return media_disk(m)[:TOTAL[m] * 512]
    if v.startswith("M"):
        return media_disk(int(v[1:], 16))
    b = base()
    if v == "V1":
        b[11:14] = b"\x37\x20\x20"
    elif v == "V2":
        b[11:30] = bytes(19)
    elif v == "V3":
        b[21] = 0xF8
    elif v == "V4":
        b[1 * 512] = b[4 * 512] = 0xF8
    return bytes(b)


def run(mkey, img):
    machine, extra = MACHINES[mkey]
    td = tempfile.mkdtemp(prefix="bpbrule_")
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "c.txt")
        cap = ("proc __cap {tag} {\n"
               f"  set f [open {{{out}}} a]\n"
               "  binary scan [debug read_block VRAM 0 16384] H* v\n"
               "  set r {}\n"
               "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }\n"
               "  binary scan [debug read_block memory 0xF41C 2] H* cl\n"
               '  puts $f "$tag [reg pc] $r $cl $v"\n'
               "  close $f\n}\n")
        tcl = ("set throttle off\n" + cap +
               "after time 12 { __cap T12 }\n"
               'after time 12.5 { type "FILES\\r" }\n'
               "after time 16 { __cap F }\n"
               "after time 16.5 { exit }\n")
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                       ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                        "-script", os.path.join(td, "s.tcl")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        caps = {}
        if os.path.exists(out):
            for ln in open(out):
                p = ln.split()
                caps[p[0]] = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
                              "curlin": 0, "vram": bytes.fromhex(p[11])}
        return caps
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    mk = (sys.argv[1] if len(sys.argv) > 1 else "cf,eu,zb").split(",")
    vs = (sys.argv[2] if len(sys.argv) > 2 else "V0,V1,V2,V3,V4").split(",")
    for v in vs:
        img = variant(v)
        for m in mk:
            caps = run(m, img)
            t12 = D.screen_text(caps["T12"]) if "T12" in caps else ["<none>"]
            f = D.screen_text(caps["F"]) if "F" in caps else ["<none>"]
            ran = any("AUTOX" in r for r in t12)
            asked = any("date" in r for r in t12)
            # what FILES added: the rows after the last "FILES" echo
            idx = max((i for i, r in enumerate(f) if r.strip() == "FILES"), default=None)
            listing = f[idx + 1:] if idx is not None else f[-3:]
            print(f"{v} {m}: AUTOX={'yes' if ran else 'no'} date-question={'yes' if asked else 'no'}"
                  f"  FILES -> {' | '.join(r.strip() for r in listing)}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
