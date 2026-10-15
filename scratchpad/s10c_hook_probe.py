#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROMSIZE S10.C, step C0: which hook cells does the reference's INPUT side enter?

S10.C moves OPEN FOR INPUT, INPUT #, LINE INPUT #, INPUT$(n,#), EOF, LOF, LOC into
disk.rom (TODO D-ROMSIZE; the design brief is in the session scratchpad). Today
zerobas crosses NO hook on that path. D-CHANHOOK's census saw $FE8A entered per
byte read and $FE9E / $FEA3 entered by EOF / LOF without separating them. This
counts, per case, the entries to every published hook slot on the CF-3300
(scratchpad/hookcount_probe.py's counter: never reads a cell, never follows a
target, never steps), each a DELTA against `quiet`.

Disk image: T.TXT = "AB\\r\\nCD", N.TXT = " 1  2 \\r\\n", B.DAT = 600 bytes.
Cases:
  quiet      the baseline
  oin        OPEN"T.TXT" FOR INPUT + CLOSE
  omiss      OPEN"M.TXT" FOR INPUT (a missing file -> 53)
  linput     + LINE INPUT#1,A$ ("AB" + CR LF)
  inum       OPEN N.TXT + INPUT#1,X (" 1 " -- does the numeric peek cross?)
  eof        + one EOF(1)              lof   + one LOF(1)        loc  + one LOC(1)
  in1        OPEN B.DAT + INPUT$(1,#1) in256 + INPUT$(256,#1) (the per-byte scaling)
PREDICTED, before the run: $FE8A is entered once per byte read (linput 4 or 3,
in1 1, in256 256 more than in1); EOF and LOF each enter one of $FE9E / $FEA3; OPEN
enters $FE4E / $FE58 / $FEB2 / $FEB7 as D-CHANHOOK found for OUTPUT; the missing
file's 53 comes after a crossing.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import loadrun_probe as LR                                    # noqa: E402
import hookcount_probe as HC                                  # noqa: E402

MK = "PRINT CHR$(64);"            # `@` built at run time: the echo fence
FILES = {"T       TXT": b"AB\r\nCD", "N       TXT": b" 1  2 \r\n", "B       DAT": bytes(i & 0xFF for i in range(600))}
OT = 'OPEN"T.TXT"FOR INPUT AS#1:'
OB = 'OPEN"B.DAT"FOR INPUT AS#1:'
CASES = {
    "quiet": ['%s"Q"' % MK],
    "oin": [OT + 'CLOSE:%s"K"' % MK],
    "omiss": ['ON ERROR GOTO 0:OPEN"M.TXT"FOR INPUT AS#1:%s"K"' % MK],
    "linput": [OT + 'LINE INPUT#1,A$:CLOSE:%s"K"' % MK],
    "inum": ['OPEN"N.TXT"FOR INPUT AS#1:INPUT#1,X:CLOSE:%s"K"' % MK],
    "eof": [OT + 'E=EOF(1):CLOSE:%s"K"' % MK],
    "lof": [OT + 'E=LOF(1):CLOSE:%s"K"' % MK],
    "loc": [OT + 'E=LOC(1):CLOSE:%s"K"' % MK],
    "in1": [OB + 'A$=INPUT$(1,#1):CLOSE:%s"K"' % MK],
    "in256": [OB + 'A$=INPUT$(1,#1):A$=INPUT$(256,#1):CLOSE:%s"K"' % MK],
}
WATCH = (0xFE4E, 0xFE53, 0xFE58, 0xFE5D, 0xFE62, 0xFE80, 0xFE85, 0xFE8A, 0xFE8F,
         0xFE94, 0xFE99, 0xFE9E, 0xFEA3, 0xFEA8, 0xFEAD, 0xFEB2, 0xFEB7)


def screen(tag):
    cap = HC.CAPTURE.get(tag)
    if not cap:
        return "<NO CAPTURE>"
    rows = [cap[i:i + 40].strip() for i in range(0, len(cap), 40)]
    return " | ".join(r for r in rows if r and r != "Ok" and "PRINT" not in r
                      and "OPEN" not in r and not r.startswith("color ")) or "<blank>"


def main():
    tags = sys.argv[1:] or list(CASES)
    if "quiet" not in tags:
        tags = ["quiet"] + tags
    tmpd = tempfile.mkdtemp(prefix="s10c_")
    got = {}
    for tag in tags:
        dsk = os.path.join(tmpd, f"{tag}.dsk")
        LR.write_files(dsk, FILES)
        got[tag] = HC.run(tag, CASES[tag], dsk)
        print(f"  {tag:7} screen: [{screen(tag)}]", flush=True)
    base = got["quiet"]
    print("\ndelta vs quiet (cells entered by any case):")
    cells = sorted({c for t in tags for c in got[t] if got[t].get(c, 0) != base.get(c, 0) and c in WATCH} |
                   {c for c in WATCH if any(got[t].get(c, 0) != base.get(c, 0) for t in tags)})
    print("  case     " + " ".join(f"{c:04X}" for c in cells))
    for tag in tags[1:]:
        print(f"  {tag:8} " + " ".join(f"{got[tag].get(c, 0) - base.get(c, 0):4d}" for c in cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
