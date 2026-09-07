#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-COPYVERB — `COPY` characterised: the second of D-KWPIN's eight, and a verb that DOES something.

D-KWPIN pinned eight keywords the reference tokenises and zerobas does not.
`DSKI$` ($EA) was taken first and its surface closed with the verb's usefulness
now a question for Joost — its measured face evaluates to the empty string.
`COPY` ($D6) is the opposite case: a file copy either happens or it does not, and
the CHECK is a separate statement that cannot agree for a subtle reason.

⚠️ EVERY ROW WRITES, SO EVERY ROW GETS A PRIVATE IMAGE. `basic_probe_lptverb.py`
established the reason: boot-per-case reboots the machine but keeps mounting the
SAME file, so one row's copy would be present in the directory for every later row
and for the whole of a second pass. Each case here copies `disk/test720.dsk` to
its own temp path first.

\U0001f3af THE READOUT IS A SECOND STATEMENT, NOT THE COPY'S OWN FACE. After the
`COPY`, the program OPENs the destination for input and prints 55. That separates
"the copy ran without error" from "the file is there" -- a verb that silently did
nothing would pass the first and fail the second.

  c.ctl      no COPY at all, OPEN an existing file        CONTROL, must read 55
  c.basic    COPY"A:PROG.BAS"TO"A:NEW.BAS", OPEN NEW.BAS  the verb working
  c.missing  copy a file that does not exist              the error CODE
  c.self     copy a file onto itself                      the error CODE
  c.nodest   COPY"A:PROG.BAS" with no TO clause           does the 1-arg form exist?

A row reads 55 if the destination opened, or the NEGATED error code if anything
trapped. ERR 2 is Syntax error, so -2 means "this form does not exist".
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SRC = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"

CASES = [
    ("c.ctl",     None,                            'A:PROG.BAS',
     "CONTROL: no COPY -- OPEN an existing file, must read 55"),
    ("c.basic",   'COPY"A:PROG.BAS"TO"A:NEW.BAS"', 'A:NEW.BAS',
     "the verb working: did NEW.BAS appear?"),
    ("c.missing", 'COPY"A:NOSUCH.BAS"TO"A:X.BAS"', 'A:X.BAS',
     "source does not exist -- the error CODE"),
    ("c.self",    'COPY"A:PROG.BAS"TO"A:PROG.BAS"', 'A:PROG.BAS',
     "copy a file onto itself -- the error CODE"),
    ("c.nodest",  'COPY"A:PROG.BAS"',              'A:PROG.BAS',
     "no TO clause -- does the one-argument form exist?"),
]


def rootdir(path):
    """The 8.3 names in the FAT12 root directory, read straight from the image.

    🔴 THE PRECONDITION THIS EXISTS FOR: `c.basic` reads 55 when NEW.BAS can
    be OPENed after the COPY -- which is ALSO what a NEW.BAS that was already on
    the fixture would read [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    Checked once by hand is not checked: a regenerated fixture would rot it
    silently, so main() refuses to score unless the destination is ABSENT first.
    """
    d = open(path, "rb").read()
    out = []
    for sec in range(7, 14):                     # 720K FAT12: boot + 2 FATs x 3
        for off in range(0, 512, 32):
            e = d[sec * 512 + off:sec * 512 + off + 32]
            if not e or e[0] in (0x00, 0xE5):
                continue
            nm = e[0:8].decode("ascii", "replace").rstrip()
            ex = e[8:11].decode("ascii", "replace").rstrip()
            out.append(f"{nm}.{ex}" if ex else nm)
    return out


def main() -> int:
    have = rootdir(SRC)
    if "NEW.BAS" in have:
        print(f"\U0001f534 THE FIXTURE ALREADY CONTAINS NEW.BAS ({have}) -- "
              f"`c.basic` would read 55 whether or not COPY did anything. "
              f"Pick a destination name that is absent, or the row is void.")
        return 2
    print(f"  precondition: {SRC} holds {have}; NEW.BAS absent \u2713\n")
    out = {}
    for label, verb, check, note in CASES:
        dsk = os.path.join(tempfile.gettempdir(), f"zb_copy_{label}.dsk")
        shutil.copy(SRC, dsk)                      # a PRIVATE image per row
        p = ['10 ON ERROR GOTO 900']
        if verb:
            p.append(f'20 {verb}')
        p += [f'30 OPEN"{check}"FOR INPUT AS#1:CLOSE#1',
              '40 PRINT"ZQ";55;"QZ":END',
              '900 PRINT"ZQ";-ERR;"QZ":END']
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + p + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=30.0, cap_gap=5.0, timeout=600.0, diska=dsk)[0] or "")
        v = [g for g in re.findall(r"ZQ\s*(-?\s*[0-9]+)\s*QZ", raw)
             if not any(c in g for c in '"$;')]
        out[label] = int(v[-1].replace(" ", "")) if v else None
        n = out[label]
        face = "<none>" if n is None else ("destination OPENED" if n == 55
                                           else f"ERR {-n}")
        print(f"  {label:10s} {face:20s} {note}", flush=True)

    if out.get("c.ctl") != 55:
        print(f"\n\U0001f534 THE CONTROL DID NOT READ 55 ({out.get('c.ctl')}) -- the "
              f"fixture or the readout is broken and no row above is a reading.")
        return 2
    print(f"\n\U0001f3af COPY WORKS ON THE REFERENCE: c.basic = "
          f"{'YES' if out.get('c.basic') == 55 else 'NO'}. "
          f"zerobas has no COPY keyword at all (D-KWPIN), so every row here is "
          f"the reference's face alone -- this probe CHARACTERISES, it does not "
          f"score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
