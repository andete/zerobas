# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECAUTO (gate: recauto-acceptance): GET # / PUT # with NO record number.

The CF-3300 keeps a current record per channel -- the one LOC reports -- and a
GET / PUT without a number takes the NEXT one. zerobas always used record 1, so
a program writing its records in order kept only the last (found 2026-10-09).

  omit     three bare PUT #1 at LEN=8          -> LOF 24, LOC 3
  gomit    PUT #1,1:PUT #1,2, then bare GET #1 twice -> record 3 = Input past
           end (55) both times, LOC stays 2 (a refused GET does not advance it)
  mix      PUT #1,5 then a bare PUT #1          -> record 6
  openget  a 2-record file reopened, two bare GET #1 -> records 1 and 2

Each row prints `ROW <name> CF=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK, each
on a private copy of disk/test720.dsk.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

HEAD = ["MAXFILES=1", "10 ON ERROR GOTO 90"]
TAIL = ["80 CLOSE:END", '90 PRINT "ERR";ERR;"IN";ERL:RESUME NEXT', "RUN"]
O8 = ['20 OPEN "R.DAT" AS #1 LEN=8', "30 FIELD #1,8 AS A$"]
CASES = {
    "omit": O8 + ['40 LSET A$="Q"', "50 PUT #1:PUT #1:PUT #1", "60 PRINT LOF(1);LOC(1)"],
    "gomit": O8 + ['40 LSET A$="ONE":PUT #1,1:LSET A$="TWO":PUT #1,2',
                   "50 GET #1:PRINT A$;LOC(1)", "60 GET #1:PRINT A$;LOC(1)"],
    "mix": O8 + ['40 LSET A$="Q"', "50 PUT #1,5:PUT #1", "60 PRINT LOF(1);LOC(1)"],
    "openget": O8 + ['40 LSET A$="ONE":PUT #1,1:LSET A$="TWO":PUT #1,2',
                     '50 CLOSE:OPEN "R.DAT" AS #1 LEN=8:FIELD #1,8 AS A$',
                     "60 GET #1:PRINT A$;LOC(1):GET #1:PRINT A$;LOC(1)"],
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    only = sys.argv[1:] or list(CASES)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"recauto_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            got[side] = rows(omsx_repl.run_cases(m, [("direct", HEAD + CASES[name] + TAIL)],
                                                 batch=False, diska=dsk, boot=14.0,
                                                 reset=("", "SCREEN 0:WIDTH 40"),
                                                 step=4.5, run_gap=40.0)[0])
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: GET # / PUT # without a record number "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
