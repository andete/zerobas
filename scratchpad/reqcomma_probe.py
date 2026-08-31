#!/usr/bin/env python3
r"""D-NGRAM17 — one `req_comma` for the four MANDATORY-comma sites.

`call skip_spaces / cp ',' / jp nz,stmt_error / inc hl` -- *a comma is required
here* -- stands at four sites, one per verb:

  exf_havech    basic/field.asm     FIELD #n , width AS var
  inp_readvar   basic/files.asm     INPUT #n , var
  ex_swap       basic/missing.asm   SWAP a , b
  ex_sound      basic/sound.asm     SOUND reg , value

🔴 THE FAMILY IS BIGGER THAN THE COLLAPSIBLE SET, AND THAT IS THE POINT. There
are 72 `cp ','` sites in `basic/`. Enumerated at instruction level they fall into
groups by WHERE THEY JUMP: 4 to `stmt_error` (a required comma -- these), 3 to
`exec_stmt` (an OPTIONAL comma that ends the statement), and a tail of 2-site
groups each branching to its own local label. Only the first group shares a
destination, so only the first group can share a body -- the D-NGRAM11 rule that
a caller's own decline target is what keeps it at the call site.

BOTH HALVES, ONE ROW PER SITE: `g.*` supplies the comma (it must be CONSUMED --
the `inc hl` -- or the verb misreads its next argument), `b.*` omits it (it must
RAISE). A row set with only the good half cannot see a lost `inc hl`.
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

CASES = [
    # ex_swap -- the comma must be consumed, so A must come back as 2.
    ("g.swap",  ['A=1:B=2:SWAP A,B', 'PRINT A'],                     -1),
    ("b.swap",  ['A=1:B=2:SWAP A B'],                                -1),
    # ex_sound
    # 🔴 ONE LINE, NOT TWO, AND A KNIFE SAID SO. As two typed lines the row read
    # the PRINT and was BLIND to whatever SOUND did -- K-C1 broke the comma and
    # this row did not move. Joined by `:`, a SOUND that misparses aborts the
    # statement and the PRINT never runs, so the row can finally see it.
    ("g.sound", ['SOUND 0,0:PRINT "ZQ1"'],                           -1),
    ("b.sound", ['SOUND 0 0'],                                       -1),
    # inp_readvar
    ("g.input", ['OPEN"A:PROG.BAS"FOR INPUT AS#1', 'INPUT#1,A$',
                 'CLOSE#1', 'PRINT LEN(A$)>0'],                      -1),
    ("b.input", ['OPEN"A:PROG.BAS"FOR INPUT AS#1', 'INPUT#1 A$'],    -1),
    # exf_havech
    ("g.field", ['OPEN"A:T.DAT"AS#1', 'FIELD#1,10 AS A$',
                 'CLOSE#1', 'PRINT LEN(A$)'],                        -1),
    ("b.field", ['OPEN"A:T.DAT"AS#1', 'FIELD#1 10 AS A$'],           -1),
    # 🔬 `g.field` diverges (10 vs 0). Is that FIELD, or CLOSE releasing the
    # buffer the field variable points into? Reading it BEFORE the CLOSE says.
    ("g.field2", ['OPEN"A:T.DAT"AS#1', 'FIELD#1,10 AS A$',
                  'PRINT LEN(A$)'],                                  -1),
    # 🔬 WHY `b.swap` IS BLIND TO K-C2. If the crunch ignores spaces inside a
    # variable NAME, `SWAP A B` never presents a missing comma at all -- it
    # presents ONE variable called `AB`, and the error comes from SWAP's
    # second-argument check, before `req_comma` is reached.
    ("x.spacename", ['AB=9', 'PRINT A B'],                           -1),
    # 🟢 CONTROLS: statements with no mandatory comma at all.
    ("ctl.print", ['PRINT "ZQ2"'],                                   -1),
    ("ctl.let",   ['A=7', 'PRINT A'],                                -1),
]


def run_side(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_reqcomma_{side}.dsk")
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
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
