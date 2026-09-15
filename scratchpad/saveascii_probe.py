#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWSAVE: `SAVE"x",A` reads 49 here and NOTHING on the reference — which?

The kwsweep row `save_b` came back DIVERGENT with the reference side EMPTY, and
an empty capture is not a verdict: it is either the reference refusing the ASCII
save or the apparatus losing the screen. This probe separates them, against the
same National CF-3300 and the same disk fixture the sweep uses, and DUMPS THE RAW
SCREEN rather than scraping for a marker.

  c0  CONTROL: the sweep's own tokenised `save` row, known to read `[ 68 ]` on
      both machines. If it is empty here, the apparatus is what is wrong.
  c1  the ASCII save, exactly as the row has it.
  c2  the ASCII save and nothing else -- does the SAVE itself end the program?
  c3  the ASCII save, then `FILES` -- is the file on the disk at all?
"""
import sys, os, shutil, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACH = "National_CF-3300"
DSK = os.path.join(REPO, "disk", "test720.dsk")

CASES = [
    ("c0_tokenised", ['A=1:SAVE"S.BAS"', 'OPEN"S.BAS"FOR INPUT AS#1',
                      'A=LOF(1):CLOSE#1', 'PRINT"<";A;">"']),
    ("c1_ascii",     ['A=1:SAVE"SA.BAS",A', 'OPEN"SA.BAS"FOR INPUT AS#1',
                      'B$=INPUT$(1,#1):CLOSE#1', 'PRINT"<";ASC(B$);">"']),
    ("c2_bare",      ['A=1:SAVE"SB.BAS",A', 'PRINT"<OK>"']),
    ("c3_files",     ['A=1:SAVE"SC.BAS",A', 'FILES']),
]


def main() -> int:
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(DSK, fh.name)
    specs = [("stored", lines) for _, lines in CASES]
    raws = omsx_repl.run_cases(MACH, specs, batch=False, boot=14.0,
                               reset=("", "SCREEN 0", "CLS"), diska=fh.name,
                               # 🔴 THE SWEEP'S OWN DISK_TIMING, NOT A GUESS. The
                               # first cut used step=3/cap_gap=6 and the CONTROL
                               # came back EMPTY TOO -- the capture was taken
                               # while the CF-3300 was still writing, which is an
                               # apparatus fault and not a reference behaviour.
                               step=5.0, cap_gap=20.0, timeout=900.0)
    for (name, _), raw in zip(CASES, raws):
        s = "".join(raw or "")
        print("===", name)
        for r in range(0, len(s), 40):
            line = s[r:r + 40].rstrip()
            if line:
                print("   %2d |%s|" % (r // 40, line))
    os.unlink(fh.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
