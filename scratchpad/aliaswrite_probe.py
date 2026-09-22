#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALIASWRITE -- does a disk verb between two PRINT# corrupt the FILE?

The read side is settled (D-ALIASBITE): `KILL`/`NAME`/`DSKF` between two reads
of an open channel make the next read serve whatever the verb left in
`FSECTOR_BUF` -- 4 bytes of the wrong data, no error. The WRITE stream (`FWR_*`)
buffers through THAT SAME BUFFER until a sector fills, so a verb between two
`PRINT#`s may make `CLOSE` commit the verb's leftovers TO DISK.

🔴 THAT WOULD BE STRICTLY WORSE THAN THE READ SIDE. A bad read is transient and
lives in one variable; a bad write is on the medium, survives the session, and
is what the next program reads back.

📏 THE READOUT IS THE HOST-PARSED IMAGE, NOT THE SCREEN. This investigation
produced three wrong headlines off a screen scrape, because a NUL is invisible
to `CHPUT` and "nothing appeared" and "zero bytes were delivered" paint
identically [[readout-blind-to-its-own-subject]]. Here the emulator writes a
scratch `.dsk`, the run ends, and the host walks the FAT chain and compares the
file BYTE FOR BYTE against what the program printed. Nothing is inferred from
pixels.

⚠️ THE CONTROL IS THE SAME PROGRAM WITH A NON-DISK STATEMENT between the two
`PRINT#`s. Without it, a file that differs from the ideal proves nothing -- the
BASIC writer's own record format (CR/LF, padding) is not this probe's subject.

    python3 -u scratchpad/aliaswrite_probe.py [--selftest]
"""
from __future__ import annotations

import os
import shutil
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import probe_tmp  # noqa: E402,F401  -- module level, sets tempfile.tempdir
import omsx_repl  # noqa: E402
import fatbuf_probe as FB  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
TARGET = "W       DAT"          # 8.3, space-padded -- the file under test

# Two records, distinct and self-describing, so a diff names WHICH half moved.
REC1 = "AAAABBBBCCCCDDDD"
REC2 = "EEEEFFFFGGGGHHHH"

BODY = [
    "5 MAXFILES=2",
    '10 OPEN"Y.DAT"FOR OUTPUT AS#2',    # a victim for KILL/NAME to act on
    '15 PRINT#2,"V"',
    "17 CLOSE#2",
    '20 OPEN"W.DAT"FOR OUTPUT AS#1',
    f'25 PRINT#1,"{REC1}"',
    "30 ON ERROR GOTO 99",
]
TAIL = [
    f'40 PRINT#1,"{REC2}"',
    "45 CLOSE#1",
    "95 END",
    '99 PRINTCHR$(91);"E";ERR;CHR$(93)',
    "RUN",
]
ARMS = [("no-disk", ["35 X=1"]),            # negative control -- MUST be clean
        ("KILL", ['35 KILL"Y.DAT"']),
        ("NAME", ['35 NAME"Y.DAT"AS"V.DAT"']),
        ("DSKF", ["35 X=DSKF(0)"])]


def geom(d):
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    root_sec = rsv + nf * spf
    return dict(bps=bps, spc=spc, rsv=rsv, nf=nf, spf=spf, nroot=nroot,
                root_sec=root_sec,
                data_sec=root_sec + (nroot * 32 + bps - 1) // bps)


def read_file(img, name8):
    """The bytes of `name8` off the image, by walking its FAT chain.

    Returns None when the entry is absent -- which is DATA ("the file was never
    created"), a different outcome from an empty file, and the two must not be
    collapsed [[an-unnamed-outcome-reads-as-no-outcome]]."""
    g = geom(img)
    fat = bytearray(img[g["rsv"] * g["bps"]:(g["rsv"] + g["spf"]) * g["bps"]])
    for i in range(g["nroot"]):
        e = g["root_sec"] * g["bps"] + i * 32
        if img[e:e + 11] != name8.encode():
            continue
        clus = struct.unpack("<H", img[e + 26:e + 28])[0]
        size = struct.unpack("<I", img[e + 28:e + 32])[0]
        out, csz, seen = bytearray(), g["bps"] * g["spc"], set()
        while 2 <= clus < 0xFF0:
            if clus in seen:
                return b"<CHAIN LOOPS>"
            seen.add(clus)
            off = (g["data_sec"] + (clus - 2) * g["spc"]) * g["bps"]
            out += img[off:off + csz]
            clus = FB.fat12_get(fat, clus)
        return bytes(out[:size])
    return None


def verdict(ctl, sub):
    """Named before the run, so the outcome cannot be chosen after it."""
    if ctl is None:
        return ("INSTRUMENT FAULT: the CONTROL never created the file, so no "
                "row can be attributed to a verb")
    if REC1.encode() not in ctl or REC2.encode() not in ctl:
        return (f"INSTRUMENT FAULT: the CONTROL file is missing a record "
                f"({ctl!r}) -- the probe is measuring its own file handling")
    if sub is None:
        return "GONE — the verb left no directory entry for the file at all"
    if sub == ctl:
        return "CLEAN — the file on disk is byte-identical to the control"
    miss = [r for r in (REC1, REC2) if r.encode() not in sub]
    if miss:
        return (f"DATA LOST ON THE MEDIUM — record(s) {', '.join(miss)} are "
                f"absent from the committed file; got {sub!r}")
    return f"DIFFERS but both records survive: {sub!r} vs {ctl!r}"


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    good = (REC1 + "\r\n" + REC2 + "\r\n").encode()
    arm("identical file -> CLEAN", verdict(good, good).startswith("CLEAN"))
    lost = (("\x00" * 16) + "\r\n" + REC2 + "\r\n").encode()
    arm("first record replaced by NULs -> DATA LOST",
        verdict(good, lost).startswith("DATA LOST"))
    arm("a missing entry -> GONE", verdict(good, None).startswith("GONE"))
    # 🔴 THE ARM THAT KEEPS A BROKEN PROBE FROM BLAMING THE ROM: if the CONTROL
    # is already wrong, no verdict about a verb may be issued at all.
    arm("NEGATIVE: a control missing a record is an INSTRUMENT FAULT",
        verdict(b"short", good).startswith("INSTRUMENT FAULT"))
    arm("NEGATIVE: a control that is None is an INSTRUMENT FAULT",
        verdict(None, good).startswith("INSTRUMENT FAULT"))
    # and the reader: it must find a real file in a real image, and report None
    # for one that is absent -- without this the sweep could return None for
    # every arm and read as "GONE" everywhere.
    img = bytearray(open(SRC_DSK, "rb").read()) if os.path.exists(SRC_DSK) else None
    if img is not None:
        arm("NEGATIVE: an absent name reads None, not b''",
            read_file(bytes(img), "NOSUCH  XYZ") is None)
        g = geom(bytes(img))
        arm("the geometry parses (512 B sectors)", g["bps"] == 512)
    else:
        print("  selftest: SKIPPED the image arms (no test720.dsk)")
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def run(label, lines):
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)      # never write the tracked fixture
    omsx_repl.run_cases(ZB, [(label, BODY + lines + TAIL)], batch=False,
                        reset=(), boot=8.0, step=3.0, cap_gap=2.5,
                        run_gap=60.0, timeout=900.0, diska=tmp)
    got = read_file(open(tmp, "rb").read(), TARGET)
    print(f"  {label:9} {got!r}")
    return got


def main(argv):
    print("D-ALIASWRITE: does a disk verb between two PRINT# corrupt the "
          "FILE?\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    out = {n: run(n, l) for n, l in ARMS}
    ctl = out["no-disk"]
    print()
    for name, _ in ARMS[1:]:
        print(f"  {name}: {verdict(ctl, out[name])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
