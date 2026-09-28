"""D-CASSAYPROG: which tape verbs print the `Skip :`/`Found:` search rows
while a PROGRAM runs?

`10 CLOAD"ZR"` RUN printed no search rows on the VG-8020 and both on zerobas
(scratchpad/cload_ta_probe6.out). Two rules fit that one row: "silent while a
program runs" and "silent for CLOAD's in-program form". The rows below separate
them: the other four verbs that reach the shared search engine, each run from a
program, plus a DIRECT control that must print them. Every subject is read
UNFILTERED (the search rows ARE the subject), with castail's own machinery,
sides and fixtures (`two` = ASCII SK then RT, `twot` = tokenised twin).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "probes", "lib"),
                os.path.join(HERE, "..", "probes", "basic")]
import basic_probe_castail as ct  # noqa: E402

N = ct.CAS_NAME
W = ct.W_LOAD2
TWO = [
    ("d-load",  [f'LOAD"CAS:{N}"', W],                                   0, None),
    ("p-load",  [f'10 LOAD"CAS:{N}"', "RUN", W, "LIST"],                 1,
     ((3, "listing", False),)),
    ("p-merge", [f'10 MERGE"CAS:{N}"', "RUN", W, "LIST"],                1,
     ((3, "listing", False),)),
    ("p-run",   [f'10 RUN"CAS:{N}"', "RUN", W],                          1, None),
    ("p-open",  ["MAXFILES=1", f'10 OPEN"CAS:{N}" FOR INPUT AS #1',
                 '20 CLOSE:PRINT CHR$(91)+"OK]"', "RUN", W],             3, None),
]
TWOT = [
    ("p-cload", [f'10 CLOAD"{N}"', "RUN", W, "LIST"],                    1,
     ((3, "listing", False),)),
]
ct.UNFILTERED_SUBJECTS |= {r[0] for r in TWO + TWOT}


def main():
    sides = sys.argv[1:] or ["vg8020", "cf3300", "zb"]
    res = {}
    for side in sides:
        out: dict = {}
        ct.run_group(side, None, "two", TWO, out)
        ct.run_group(side, None, "twot", TWOT, out)
        res[side] = out
    labels = sorted({k for o in res.values() for k in o})
    for lab in labels:
        print(f"{lab:16} " + "  ".join(f"{s}={res[s].get(lab)!r}" for s in sides))


if __name__ == "__main__":
    main()
