#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIWHERE — does `DSKI$` read a sector at all, and if so, WHERE does it land?

D-DSKI measured the reference's value-face and refuted the obvious reading: on the
CF-3300 `A$=DSKI$(0,0)` yields the EMPTY string, `ASC` of it is ERR 5, the DRIVE is
validated (ERR 62) and the SECTOR NUMBER is not (sector 9999 on a 720 KB disk
raises nothing). It closed by saying where the data goes is NOT established and
was deliberately not guessed at. This answers that, black-box.

## The instrument: the machine checksums its OWN memory

One program, one boot. It reads a sector, checksums every 256-byte page of
$C000..$FFFF into an array, reads a DIFFERENT sector, checksums again, and prints
the pages whose checksum MOVED. If a sector read happens and lands in RAM, the
page holding it must change between two different sectors.

🔴 THE CONTROL IS THE WHOLE INSTRUMENT. Running the checksum loop CHANGES memory
by itself — BASIC variables, the string heap, the FOR stack — so a bare
"these pages differ" list is mostly the probe's own footprint. `s.same` runs the
IDENTICAL program with BOTH reads on the SAME sector. Pages differing there are
noise by construction; only pages that differ in `s.diff` and NOT in `s.same` are
evidence about the sector [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ AND A NEGATIVE HERE IS A REAL READING, NOT A FAILURE. If no page separates the
two, then either no read happened, or it landed outside $C000..$FFFF, or it went
somewhere PEEK cannot see (the disk ROM's own slot). The rows say which of those
is excluded, not which is true.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"


def program(second_sector: int):
    """Checksum $C000..$FFFF page by page around two DSKI$ reads.

    The two reads differ only in the SECTOR, so anything the sector controls must
    show up as a moved page. `D$` accumulates the page numbers in hex.
    """
    return [
        '10 ON ERROR GOTO 900',
        '20 DIM C(63):D$=""',
        '30 A$=DSKI$(0,0)',
        # 🎯 STAGE MARKERS. The first cut printed NOTHING and I could not tell
        # a hung DSKI$ from a checksum loop too slow to finish inside the capture
        # window -- the screen showed RUN and an empty page for both. Each marker
        # is one more thing that must be on the screen for the next stage to be
        # the suspect [[an-unnamed-outcome-reads-as-no-outcome]].
        '35 PRINT"ZP";1;"PZ"',
        '40 FORP=0TO63:S=0:FORI=0TO255STEP16:S=S+PEEK(&HC000+P*256+I):NEXT',
        '50 C(P)=S:NEXT',
        '55 PRINT"ZP";2;"PZ"',
        f'60 A$=DSKI$(0,{second_sector})',
        '65 PRINT"ZP";3;"PZ"',
        '70 FORP=0TO63:S=0:FORI=0TO255STEP16:S=S+PEEK(&HC000+P*256+I):NEXT',
        '80 IF S<>C(P) THEN D$=D$+HEX$(P)+" "',
        '90 NEXT',
        '100 PRINT"ZQ";D$;"QZ":END',
        '900 PRINT"ZQ";"E";ERR;"QZ":END',
    ]


CASES = [
    ("s.diff", program(1),
     "read sector 0, checksum, read sector 1, checksum -- pages that MOVED"),
    ("s.same", program(0),
     "CONTROL: the IDENTICAL program with BOTH reads on sector 0. Every page "
     "listed here is the probe's own footprint and means nothing"),
]


def pages(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9A-FE ]*?)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return g.strip()
    return None


def main() -> int:
    got = {}
    for label, prog, _ in CASES:
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + prog + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            # 🔴 `run_gap`, NOT `cap_gap`. The window a case gets between RUN
            # and capture is exactly `step`; `cap_gap` is the gap AFTER the
            # capture and "buys this case nothing" (omsx_repl.py:684, which says
            # so in as many words). A first cut passed cap_gap=240 and captured
            # 5 emulated seconds after RUN -- the stage-1 marker was on screen
            # and nothing else, which reads exactly like a hang.
            run_gap=150.0, cap_gap=5.0, timeout=900.0, diska=DSK)[0] or "")
        got[label] = pages(raw)
        print(f"  {label:8s} {got[label]!r}", flush=True)
        if got[label] is None:
            # 🔴 AN ABSENT FENCE MUST NOT PRINT AS AN ABSENT OUTCOME. Show
            # the screen: a typing failure, a Syntax error and a program still
            # running all read as `None` and need different fixes
            # [[an-unnamed-outcome-reads-as-no-outcome]].
            st = [m for m in re.findall(r"ZP\s*([0-9]+)\s*PZ", raw)]
            print(f"    STAGE MARKERS REACHED: {st or 'NONE'} "
                  f"(1=DSKI$ returned, 2=first checksum pass, 3=second DSKI$)")
            print(f"    RAW SCREEN ({len(raw)} chars):")
            for r in range(24):
                row = raw[r * 40:(r + 1) * 40].rstrip()
                if row.strip():
                    print(f"      r{r:02d}|{row}")

    d, sm = got.get("s.diff"), got.get("s.same")
    print(f"\n  s.diff pages: {d!r}\n  s.same pages (NOISE): {sm!r}")
    if d is None or sm is None:
        print("\n\U0001f534 NO READING on one side -- nothing is concluded.")
        return 2
    if d.startswith("E") or sm.startswith("E"):
        print(f"\n\U0001f534 A ROW TRAPPED AN ERROR ({d!r} / {sm!r}) -- the program "
              f"did not complete, so the page lists say nothing.")
        return 2
    dset, nset = set(d.split()), set(sm.split())
    signal = sorted(dset - nset)
    print(f"\n\U0001f3af PAGES THAT MOVE WITH THE SECTOR (s.diff minus noise): "
          f"{signal or 'NONE'}")
    print("\n\U0001f534 A MOVED PAGE IS NOT A LANDING SPOT, AND THIS PROBE'S OWN "
          "RESULT PROVED IT.\n    Page $2B ($EB00) moves, and D-DSKIBYTES then "
          "read the bytes there: they are\n    NOT the sector's, and only 25 "
          "bytes in the span $EB95..$EBB4 differ at all --\n    a work-area "
          "record that records the REQUEST, not a 512-byte transfer. A page\n"
          "    checksum answers 'something here depends on the sector', which is "
          "one step\n    short of 'the sector is here'.")
    if not signal:
        print("  A NEGATIVE, and a real reading: no page of $C000..$FFFF tracks "
              "the sector number. That EXCLUDES a landing spot in this window; it "
              "does not establish that no read happened -- the disk ROM's own "
              "slot is not PEEK-visible from BASIC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
