#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKI — what does `DSKI$` actually DO? The first of D-KWPIN's eight, characterised.

D-KWPIN pinned eight keywords the reference tokenises and zerobas does not, with
their oracle-measured tokens. `DSKI$` ($EA) is the tractable one to take first:
it READS a sector, so no fixture is destroyed, and zerobas already owns the
sector I/O (DSKIO/FAT12) that would implement it.

⚠️ NOTHING ABOUT ITS SEMANTICS IS ASSUMED HERE, INCLUDING THE OBVIOUS PART. A
sector is 512 bytes and an MSX BASIC string cannot exceed 255, so "it returns the
sector as a string" cannot be right as stated — and rather than pick one of the
plausible resolutions, this probe MEASURES `LEN`. Writing the implementation
against a guess is how `TAB(` got recorded as "already faithful".

The rows, all against the CF-3300 (the disk-equipped reference) with
`disk/test720.dsk` mounted, and against zerobas on the same image:

  d.ctl     the fence with no DSKI$ at all -- if this is not 7 the readout is
            broken and nothing below it is a measurement
  d.len     LEN of the result
  d.byte0   ASC of its first character -- sector 0 is the boot sector, whose
            first byte is the x86 jump the FAT12 format opens with, so a
            PLAUSIBLE-looking number here is checkable against the image on disk
  d.err9    a sector number past the end of a 720 KB disk -- the error CODE
  d.drv9    a drive letter that does not exist -- the error CODE

🔴 THE ERROR ROWS ARE THE ONES THAT SAY WHAT ZEROBAS MUST DO. zerobas has no
`DSKI$` keyword, so `A$=DSKI$(0,0)` parses as a subscripted string ARRAY there and
cannot raise the reference's error; whatever it prints is the silent-variable
shape, not an answer.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
# Every row traps, so an error is a READING and not a lost capture.
# 🔴 AND LINE 40 IS NOT DECORATION -- WITHOUT IT THE PROGRAM FALLS INTO ITS
# OWN HANDLER. BASIC sorts by line number, so the handler at 900 runs after the
# body whether or not anything went wrong; the first cut of this probe had no
# END, every row's LAST fence was the handler's `-ERR` with ERR still 0, and the
# CONTROL read 0 instead of 7. It refused to score, which is the only reason the
# other four rows were not published as readings
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
HEAD = '10 ON ERROR GOTO 900'
TAIL = ['40 END', '900 PRINT"ZQ";-ERR;"QZ":END']

CASES = [
    ("d.ctl",   [HEAD, '20 PRINT"ZQ";7;"QZ"'] + TAIL,
     "CONTROL: no DSKI$ anywhere -- must read 7"),
    # 🎯 THE MOUNT CONTROL. `d.len` reading 0 is what an EMPTY RESULT looks
    # like and equally what a DISK THAT IS NOT THERE looks like. This row opens a
    # file that exists on test720.dsk: 55 means the image is mounted and readable,
    # anything negative means the fixture never arrived and no DSKI$ row below is
    # a reading at all [[an-unnamed-outcome-reads-as-no-outcome]].
    ("d.mount", [HEAD, '20 OPEN"A:PROG.BAS"FOR INPUT AS#1:CLOSE#1',
                 '30 PRINT"ZQ";55;"QZ"'] + TAIL,
     "CONTROL: the fixture is mounted and readable -- must read 55"),
    ("d.len",   [HEAD, '20 A$=DSKI$(0,0)', '30 PRINT"ZQ";LEN(A$);"QZ"'] + TAIL,
     "LEN of one sector read -- 512 is impossible in an MSX string"),
    ("d.byte0", [HEAD, '20 A$=DSKI$(0,0)', '30 PRINT"ZQ";ASC(A$);"QZ"'] + TAIL,
     "first byte of sector 0, checkable against the image on disk"),
    ("d.err9",  [HEAD, '20 A$=DSKI$(0,9999)', '30 PRINT"ZQ";0;"QZ"'] + TAIL,
     "sector past the end of a 720 KB disk -- negative = the trapped ERR"),
    ("d.drv9",  [HEAD, '20 A$=DSKI$(9,0)', '30 PRINT"ZQ";0;"QZ"'] + TAIL,
     "a drive that does not exist -- negative = the trapped ERR"),
]


def value(scr):
    if scr is None:
        return None
    # the fence is in the source the screen still echoes: LAST match, and refuse
    # any carrying source punctuation [[trapsvc-echo-fence]]
    for g in reversed(re.findall(r"ZQ\s*(-?\s*[0-9]*)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        try:
            return int(g.replace(" ", ""))
        except ValueError:
            continue
    return None


def main() -> int:
    res = {}
    for s, c in SIDES.items():
        # 🔴 NOT `as_stored`: it takes ONE line, and handing it a LIST
        # concatenated the whole program into a single typed line -- the harness
        # caught it as a mis-delivery rather than letting it read as a result.
        # Each line is TYPED, then RUN, which is what the other multi-line
        # probes do.
        res[s] = omsx_repl.run_cases(
            c["machine"], [("direct", list(l) + ["RUN"]) for _, l, _ in CASES],
            batch=False, reset=c["reset"], boot=c["boot"], step=5.0,
            cap_gap=25.0, timeout=420.0, diska=DSK)
        print(f"  {s} captured", flush=True)

    print(f"\n{'row':9s} {'cf3300':>10s} {'zb':>10s}   (negative = trapped ERR)")
    out = {}
    for i, (label, _, note) in enumerate(CASES):
        v = {s: value(res[s][i]) for s in SIDES}
        out[label] = v
        cell = {s: ("<none>" if v[s] is None else str(v[s])) for s in SIDES}
        print(f"{label:9s} {cell['cf3300']:>10s} {cell['zb']:>10s}")
        print(f"    {note}")

    if out.get("d.ctl", {}).get("cf3300") != 7:
        print("\n\U0001f534 THE FENCE CONTROL DID NOT READ 7 -- the readout or the "
              "typing is broken and every row above is void.")
        return 2
    if out.get("d.mount", {}).get("cf3300") != 55:
        print("\n\U0001f534 THE MOUNT CONTROL DID NOT READ 55 ON THE REFERENCE "
              f"({out.get('d.mount')}) -- the fixture is not there, so `d.len` "
              "reading 0 means 'no disk', not 'an empty result'.")
        return 2
    print("\nThis probe CHARACTERISES the reference; it does not score zerobas. "
          "zerobas has no DSKI$ keyword (D-KWPIN), so its column is the "
          "silent-variable face, recorded for the record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
