#!/usr/bin/env python3
r"""D-NGRAM16 — one `fname_dev` for the four "filename expression, then CAS: test".

`call fname_expr / ld de,dev_cas / call dev_cmp` stands at four sites: `LOAD`,
`RUN"name"`, `SAVE` and `BSAVE`. 9 B each.

🔴 THE RISK IS NOT THE Z FLAG, IT IS `fname_expr`'s OUTWARD JUMP. That routine
does `jp nc,els_tc_common` when the filename is not a string, and behind a helper
that jump sits one frame deeper -- the D-NGRAM8 shape, where a `call` moved an
outward jump and a decline stopped declining. Read: both of `els_tc_common`'s
exits (`stmt_error`, `type_mismatch_error`) RAISE and never return, so the extra
frame cannot matter. **That is an argument, so it gets rows**: `*.num` drives a
NON-STRING filename through every one of the four verbs.

The `Z` flag is the other half of the contract -- `dev_cmp` returns it and each
site branches on it -- so the helper ends in a TAIL JUMP, and the round-trip rows
exercise the not-CAS arm at the two verbs that can be observed without a tape.
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
                   reset=("", "SCREEN 0", "NEW"), missmsg="File not found"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",), missmsg="File not found"),
}
MK = ['10 PRINT"ZQ9"', 'SAVE"A:FD.BAS"', "NEW"]

CASES = [
    # 🔴 one NON-STRING filename per site -- the outward-jump rows.
    ("n.load",   ['A=5', 'LOAD A'],                            -1),
    ("n.run",    ['A=5', 'RUN A'],                             -1),
    ("n.save",   ['A=5', 'SAVE A'],                            -1),
    ("n.bsave",  ['A=5', 'BSAVE A,&H8000,&H9000'],             -1),
    # the not-CAS arm, observed end to end.
    ("g.save",   MK,                                           -2),
    ("g.load",   MK + ['LOAD"A:FD.BAS"', 'LIST'],              -1),
    ("g.run",    MK + ['RUN"A:FD.BAS"'],                       -1),
    ("g.miss",   ['LOAD"A:NOSUCH.BAS"'],                       -1),
    # a string EXPRESSION filename (D-FNEXPR2's own row).
    ("g.var",    ['A$="A:NOSUCH.BAS"', 'LOAD A$'],             -1),
    # 🔬 WHAT `RUN A` ACTUALLY DID. `<nothing>` is equally consistent with
    # "refused silently" and "took the BARE-RUN path and ran an empty program",
    # and those are different machines. With a program resident, bare RUN prints
    # it; a refusal prints nothing.
    ("n.runres", ['10 PRINT"ZQ1"', 'A=5', 'RUN A'],            -1),
    ("n.loadres", ['10 PRINT"ZQ1"', 'A=5', 'LOAD A'],          -1),
    # 🔬 WHICH FORMS TAKE THE BARE-RUN PATH. `LOAD` is correct with the same
    # `fname_expr`, so the fault is in `do_run`'s dispatch, not the parse.
    ("n.runstr", ['10 PRINT"ZQ1"', 'A$="A:NOSUCH.BAS"', 'RUN A$'], -1),
    ("n.runexpr", ['10 PRINT"ZQ1"', 'A=5', 'RUN A+0'],          -1),
    ("n.runparen", ['10 PRINT"ZQ1"', 'A=5', 'RUN (A)'],         -1),
    # 🎯 THE CAUSE, AND HOW WIDE IT IS. The REPL's `dl_cmd` matches `RUN` with
    # `is_cmd`, which accepts a SPACE as the delimiter -- so `RUN <anything>`
    # takes the bare-RUN fast path and the argument is discarded entirely. Only
    # `RUN"..."` (no space, so the next byte is `"`) reaches `do_run`.
    # If that is the mechanism, `RUN 20` must also ignore its LINE NUMBER.
    ("n.runline", ['10 PRINT"ZQ1"', '20 PRINT"ZQ2"', 'RUN 20'],  -1),
    ("g.runline", ['10 PRINT"ZQ1"', '20 PRINT"ZQ2"', 'RUN20'],   -1),
    ("g.runquote", ['10 PRINT"ZQ1"', 'RUN"A:NOSUCH.BAS"'],       -1),
    ("n.runspq",  ['10 PRINT"ZQ1"', 'RUN "A:NOSUCH.BAS"'],       -1),
    # 🟢 CONTROLS
    ("ctl.print", ['PRINT "ZQ1"'],                             -1),
    ("ctl.num",   ['PRINT 1+1'],                               -1),
]


def run_side(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_fnamedev_{side}.dsk")
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
