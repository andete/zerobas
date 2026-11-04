# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECBIG (gate: recbig-acceptance): the domain of GET # / PUT #'s record number.

Measured on the National CF-3300 (2026-11-04), for PUT and GET alike: the value
is TRUNCATED toward zero (1.99 -> 1, 2.5 -> 2); 1 and up is that record;
-32767..-1 WRAP to n + 65536 (-1 -> 65535, -32767 -> 32769); -32768 and below
are Overflow (6); 0 is Illegal function call (5). LOC reads the record back
UNSIGNED (65535, not -1). zerobas made 32768..65535 Overflow after D-RECLENERR
moved the parse to the int16 converter, and printed LOC 65535 as -1.

  PUT rows  OPEN "R.DAT" AS #1 LEN=1, FIELD 1 byte, PUT #1,n; print LOF;LOC
  GET rows  the same file extended to 65535 records first (PUT #1,-1), then
            GET #1,n; print LOF;LOC
  p1 is the control (record 1 has always agreed).

WIDENED 2026-11-04 (Joost: "Widen"): the record is 32 bits on the CF-3300 --
65536 and up are records, 1E9 is one (Disk full), 4294967296 is Overflow -- and
LOC after a FAILED GET / PUT is n - 1 (f1e9: LOC 999999999 after `PUT 1`;
f5get9: GET past EOF, LOC 8). Rows p65536 .. f5get9.
⚠️ KEPT, NOT ROWS: `PUT #1,4294967295#` SUCCEEDS on the CF-3300 (LOF 4294967295
-- its free-space check wraps); zerobas says Disk full. And a record whose byte
offset is under 2^24 but past the disk (PUT #1,1000000 at LEN=1) is Disk full on
both, but zerobas extends the chain until the disk is full first (D-RECSLOW).

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`, a fresh copy of
disk/test720.dsk per case and side.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

OPEN = '20 OPEN "R.DAT" AS #1 LEN=1:FIELD #1,1 AS A$:LSET A$="X"'
PUTS = {"p1": "1", "p1.99": "1.99", "p2.5": "2.5", "p32768": "32768",
        "p65535": "65535", "p40000!": "40000!", "p65536": "65536", "p1e9": "1E9",
        "p1e10": "1E10", "p2p32": "4294967296#", "f1e9": "1:PUT #1,1E9",
        "f5get9": "5:GET #1,9", "m1": "-1", "m2": "-2",
        "m32767": "-32767", "m32768": "-32768", "m32769": "-32769", "p0": "0",
        "pstr": '"A"'}
GETS = {"g2.5": "2.5", "g40000": "40000", "gm2": "-2", "gm32767": "-32767",
        "gm32768": "-32768", "g0": "0"}


def program(name):
    if name in PUTS:
        body = [OPEN, f"40 PUT #1,{PUTS[name]}"]
    else:
        body = [OPEN + ":PUT #1,-1", f"40 GET #1,{GETS[name]}"]
    return (["10 ON ERROR GOTO 90"] + body +
            ['50 PRINT "[";LOF(1);LOC(1);"]":CLOSE:END',
             '90 PRINT "[ERR";ERR;LOC(1);"]":END', "RUN"])


def reading(scr):
    if scr is None:
        return None
    flat = " ".join(str(scr).split())
    k = flat.rfind("RUN")
    if k < 0:
        return None
    t = flat[k + 3:]
    i, j = t.find("["), t.find("]")
    return t[i:j + 1] if 0 <= i < j else None


def main():
    names = list(PUTS) + list(GETS)
    only = sys.argv[1:] or names
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"recbig_{name.replace('.', 'p')}_{m}.dsk".replace("!", "s"))
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            # 150 s of emulated time: extending a fresh file to 65535 one-byte
            # records takes zerobas ~3550 frames (~71 s; the CF-3300: 3 frames,
            # measured 2026-11-04 with TIME). A speed item, not this gate's.
            got[side] = reading(omsx_repl.run_cases(
                m, [("direct", ["SCREEN 0", "NEW"] + program(name))],
                batch=False, diska=dsk, run_gap=150.0)[0])
        if got["CF"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF={got['CF']} ZB={got['ZB']} {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: GET # / PUT # record-number domain "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
