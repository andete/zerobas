#!/usr/bin/env python3
r"""D-FLDCLOSE — what does a FIELDed variable hold AFTER `CLOSE`, and does it stay?

D-NGRAM17 §5 found the divergence: after `CLOSE#1`, `LEN(A$)` reads 10 on the
CF-3300 and 0 here. Reading BEFORE the close agrees, so `FIELD` is right and
`CLOSE` is the difference -- the reference leaves the descriptor pointing into
the released buffer; zerobas resets it.

🎯 JOOST ASKED THE DECIDING QUESTION BEFORE CHOOSING: does the reference's
CONTENT survive, or does it turn to garbage once something reuses that memory?
Matching a stale-but-stable value is a very different promise from matching a
live dangling pointer, and the error code cannot tell them apart.

  b.*  BEFORE the close -- the control: both machines must agree here.
  c.*  immediately after `CLOSE`.
  d.*  after the close AND a burst of string allocation that should reuse the
       released buffer.
  e.*  after the close AND re-opening + re-FIELDing another channel.
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                 # noqa: E402
import probe_tmp                                                 # noqa: E402
import basic_probe_runtail as R                                  # noqa: E402

TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), missmsg="Syntax error"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",), missmsg="Syntax error"),
}
SETUP = ['OPEN"A:T.DAT"AS#1', 'FIELD#1,10 AS A$', 'LSET A$="ABCDEFGHIJ"']
CHURN = 'FOR I=1 TO 8:B$=STRING$(10,CHR$(65+I)):NEXT'

CASES = [
    ("b.len",    SETUP + ['PRINT LEN(A$)'],                            -1),
    ("b.val",    SETUP + ['PRINT A$'],                                 -1),
    ("c.len",    SETUP + ['CLOSE#1', 'PRINT LEN(A$)'],                 -1),
    ("c.val",    SETUP + ['CLOSE#1', 'PRINT A$'],                      -1),
    ("d.len",    SETUP + ['CLOSE#1', CHURN, 'PRINT LEN(A$)'],          -1),
    ("d.val",    SETUP + ['CLOSE#1', CHURN, 'PRINT A$'],               -1),
    ("e.val",    SETUP + ['CLOSE#1', 'OPEN"A:T2.DAT"AS#1',
                          'FIELD#1,10 AS C$', 'LSET C$="ZZZZZZZZZZ"',
                          'PRINT A$'],                                 -1),
    # 🟢 CONTROLS: an ordinary string is untouched by any of this.
    ("ctl.str",  ['X$="HELLO"', 'PRINT X$'],                           -1),
    ("ctl.churn", ['X$="HELLO"', CHURN, 'PRINT X$'],                    -1),
]


def run_side(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_fldclose_{side}.dsk")
    shutil.copy(TEST_DSK, dsk)
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _ in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"], diska=dsk)
    return {label: R.tail_after(raw, lines[subj], cfg["missmsg"])
            for (label, lines, subj), raw in zip(CASES, caps)}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    res = {s: run_side(s) for s in sides}
    w = max(len(l) for l, _, _ in CASES)
    diff = []
    for label, _, _ in CASES:
        vals = [str(res[s].get(label)) for s in sides]
        same = len(set(vals)) == 1
        if len(sides) > 1 and not same:
            diff.append(label)
        tag = "--" if len(sides) < 2 else ("ok" if same else "DIFF")
        print(f"{tag:<4} {label:<{w}}  "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides))
    print(f"\nDIFF vs the CF-3300: {len(diff)}/{len(CASES)}"
          + ("  " + " ".join(diff) if diff else ""))
    print("READ c.val vs d.val vs e.val ON THE REFERENCE: if the content is the "
          "same in all three, matching it means inheriting a STALE BUT STABLE "
          "value; if it changes, it means inheriting a LIVE DANGLING POINTER.")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
