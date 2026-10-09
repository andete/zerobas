# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FILESNL (gate: filesnl-acceptance): where the cursor stands after FILES.

The CF-3300 ends a FULL row of the listing at once, so a PRINT straight after
FILES starts on its own row; zerobas wrapped only before the next name and left
the cursor at the end of a full last row (found 2026-10-09 by the DSKO$ keyword
page's example). A partly filled last row keeps the cursor on it, on both.

  full     6 files at WIDTH 40 (two full rows of three), FILES:PRINT "X"
  part     7 files (a last row of one)
  w37      6 files at WIDTH 37 (rows of two)
  midline  PRINT "AB"; then FILES -- the listing starts mid-row

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK, each
on a private copy of disk/test720.dsk (6 files).
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

CASES = {
    "full": ("SCREEN 0:WIDTH 40", ['10 FILES:PRINT "X"', "RUN"]),
    "part": ("SCREEN 0:WIDTH 40", ['10 COPY "HI.TXT" TO "H2.TXT"', '20 FILES:PRINT "X"', "RUN"]),
    "w37": ("SCREEN 0:WIDTH 37", ['10 FILES:PRINT "X"', "RUN"]),
    "midline": ("SCREEN 0:WIDTH 40", ['10 PRINT "AB";:FILES:PRINT "X"', "RUN"]),
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    # .strip(): at WIDTH 37 every row, the prompt included, starts two columns in
    return " | ".join(x for x in r if x and x.strip() not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        reset, lines = CASES[name]
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"filesnl_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False, diska=dsk,
                                                 boot=14.0, reset=("", reset), step=4.5,
                                                 run_gap=20.0)[0])
        if got["CF"] is None:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{got['CF']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the cursor after FILES ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
