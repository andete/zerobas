#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""GET # / PUT # record-number cases the keyword pages needed (2026-10-09):

  big     LEN=1, PUT #1,32768 -- accepted on both on 09-10 (putdomain_put2.out);
          D-RECLENERR (10-07) made the record an int16-checked parse
  omit    PUT #1 three times with no record, then LOF / LOC -- does the record
          number advance (next record) or stay at 1?
  gomit   two records written, then GET #1 twice with no record
  neg     PUT #1,-1
  frac    PUT #1,2.7 then LOF (truncated? rounded?)

Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK, each
on a private copy of disk/test720.dsk.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

HEAD = ["10 ON ERROR GOTO 90"]
TAIL = ["80 CLOSE:END", '90 PRINT "ERR";ERR;"IN";ERL:RESUME NEXT', "RUN"]
CASES = {
    "big": ['20 OPEN "B.DAT" AS #1 LEN=1', "30 FIELD #1,1 AS A$", '40 LSET A$="Q"',
            "50 PUT #1,32768", "60 PRINT LOF(1);LOC(1)"],
    "omit": ['20 OPEN "O.DAT" AS #1 LEN=8', "30 FIELD #1,8 AS A$", '40 LSET A$="Q"',
             "50 PUT #1:PUT #1:PUT #1", "60 PRINT LOF(1);LOC(1)"],
    "gomit": ['20 OPEN "G.DAT" AS #1 LEN=8', "30 FIELD #1,8 AS A$",
              '40 LSET A$="ONE":PUT #1,1:LSET A$="TWO":PUT #1,2',
              "50 GET #1:PRINT A$;LOC(1)", "60 GET #1:PRINT A$;LOC(1)"],
    "neg": ['20 OPEN "N.DAT" AS #1 LEN=8', "30 FIELD #1,8 AS A$", '40 LSET A$="Q"',
            "50 PUT #1,-1", "60 PRINT LOF(1);LOC(1)"],
    "frac": ['20 OPEN "F.DAT" AS #1 LEN=8', "30 FIELD #1,8 AS A$", '40 LSET A$="Q"',
             "50 PUT #1,2.7", "60 PRINT LOF(1);LOC(1)"],
}


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    bad = 0
    for name, body in CASES.items():
        got = {}
        for side, m in (("CF-3300", "National_CF-3300"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"getput_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [("direct", ["MAXFILES=1"] + HEAD + body + TAIL)], batch=False,
                                      diska=dsk, boot=14.0, reset=("", "SCREEN 0:WIDTH 40"),
                                      step=4.5, run_gap=60.0)[0]
            got[side] = rows(scr)
        same = got["CF-3300"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} {name:5s} CF-3300 [{got['CF-3300']}]  zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
