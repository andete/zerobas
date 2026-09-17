#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FNKLINE -- WHAT the reference paints on row 23, so we can paint the same.

Joost ruled option (c) on 2026-09-17: paint the function-key line ourselves, then
move the window bound. D-DSPFNK established THAT the reference paints (20
non-blank cells from offset 2 with `KEY ON`, 21 with a macro assigned) and that
C-BIOS paints nothing. A COUNT is not a layout, so this reads the row as TEXT.

⚠️ BLANKS ARE THE POINT, so code 32 is rendered as `.` -- a dump that shows
spaces as spaces cannot be read back through a screen scrape, and the column
POSITIONS are exactly what has to be reproduced.
⚠️ TWENTY CELLS AT A TIME: a 40-character dump plus its fence does not fit a
40-column line, and a wrapped fence is a lost reading.
🔴 ROW 23 IS `BASE(0)+920` -- 40 bytes a row, not 32; a fixed absolute offset is
the mistake D-KWOSK already made in this exact place.
⚠️ zerobas is the CONTROL here, not a subject: it must come back all dots, which
is what says the dump is reading the right row rather than inventing content.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")


def dump(first: int, *setup: str) -> list[str]:
    """Row 23 cells `first`..`first+19`, code 32 shown as `.`."""
    body = list(setup) + [
        "B=BASE(0)+920+%d" % first,
        'S$=""',
        "FOR I=0 TO 19",
        "V=VPEEK(B+I)",
        'IF V<32 THEN V=46',
        'S$=S$+CHR$(V)',
        "NEXT",
        'PRINT"<F";S$;">"',
    ]
    lines = ["ON ERROR GOTO @T"] + body + ["END", 'PRINT"<Fe";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


CASES = [
    ("on_default_00", dump(0,  "KEY ON")),
    ("on_default_20", dump(20, "KEY ON")),
    ("on_assign_00",  dump(0,  'KEY 1,"ZQZQZQ"', "KEY ON")),
    ("on_assign_20",  dump(20, 'KEY 1,"ZQZQZQ"', "KEY ON")),
    ("off_00",        dump(0,  "KEY OFF")),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = "".join(raw or "")
            i = txt.rfind("<F")
            j = txt.find(">", i + 1)
            cell = txt[i + 2:j] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:14} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
