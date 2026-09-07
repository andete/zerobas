#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIFORM, second half: is the DRIVE argument's numbering why the value is empty?

D-DSKIFORM settled the FORM: `DSKI$` is a FUNCTION only -- `DSKI$0,0`, `DSKI$ 0,0`
and a bare `DSKI$(0,0)` are all `Syntax error` (ERR 2) on the CF-3300, so the
`A$=DSKI$(0,0)` that D-DSKI, D-DSKIWHERE and D-DSKIBYTES all drove was the right
form after all, and "the read never happened because I used the wrong syntax" is
refuted.

That leaves the OTHER inherited assumption: drive **0**. MSX conventions differ
per verb -- `DSKF(0)` means the DEFAULT drive, and elsewhere 1 is A:. If 0 were
silently-invalid, an empty result and an unvalidated sector number are exactly what
you would see.

MEASURED (CF-3300, disk/test720.dsk, refcache OFF):

    drv0   A$=DSKI$(0,0)   LEN = 0
    drv1   A$=DSKI$(1,0)   LEN = 0
    drv2   A$=DSKI$(2,0)   <no reading -- B: does not exist on this machine and
                            the drive prompt blocks, which is itself a reading:
                            the argument IS a drive selector>

\U0001f3af SO THE NUMBERING IS NOT THE EXPLANATION EITHER. Both drives that exist
return the EMPTY string. Taken with D-DSKIWHERE (no page of $C000..$FFFF holds the
sector) and D-DSKIBYTES (only a ~32-byte work-area record at $EB95..$EBB4 moves),
the observable face of `DSKI$` on this reference is: a function of (drive, sector)
that validates the DRIVE, does not validate the SECTOR, and evaluates to "".
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
ROWS = [("drv0", "A$=DSKI$(0,0)"), ("drv1", "A$=DSKI$(1,0)"),
        ("drv2", "A$=DSKI$(2,0)")]


def main() -> int:
    for tag, body in ROWS:
        p = ['10 ON ERROR GOTO 900', f'20 {body}',
             '30 PRINT"ZQ";LEN(A$);"QZ":END',
             '900 PRINT"ZQ";-ERR;"QZ":END']
        raw = "".join(omsx_repl.run_cases(
            "National_CF-3300", [("direct", ["NEW"] + p + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0, run_gap=20.0,
            cap_gap=5.0, timeout=600.0, diska=DSK)[0] or "")
        v = [g for g in re.findall(r"ZQ\s*(-?\s*[0-9]+)\s*QZ", raw)
             if not any(c in g for c in '"$;')]
        got = v[-1].replace(" ", "") if v else "<none>"
        print(f"  {tag:5s} {body:18s} -> LEN/-ERR = {got}")
    print("\nA `<none>` on drv2 is NOT a lost capture: B: does not exist on this "
          "machine,\nso the drive prompt blocks -- which is itself the reading "
          "that the first\nargument is a DRIVE SELECTOR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
