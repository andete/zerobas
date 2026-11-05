"""pustype-acceptance (D-PUSTYPE + D-RESNEXTEOL): PRINT USING with a value of the wrong type.

A string field (`!`, `&`, `\..\`) given a number was Syntax error here and Type
mismatch (13) on both references, which also evaluate the value first (`1/0` is
11); and a numeric field given a string left its Type mismatch PENDING, so at a
line's end it surfaced inside the next line -- ERL named the wrong line and RESUME
NEXT skipped that line's first statement. Three programs, both zerobas targets
against the VG-8020: the value kinds (scratchpad/pustype2_measure.bas), the field
kinds (pustype_measure.bas) and RESUME NEXT after end-of-line errors
(resnexteol_measure.bas, PRINT USING among six other error kinds as controls).

Clean-room: a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROGS = [("scratchpad/pustype2_measure.bas", 19), ("scratchpad/pustype_measure.bas", 7),
         ("scratchpad/resnexteol_measure.bas", 25)]


def main():
    bad = 0
    for prog, rows in PROGS:
        text = open(os.path.join(REPO, prog)).read()
        ref = run_programs.run(run_programs.REF, "pustype", text)
        rl = ref[1].replace("\r", "").splitlines()
        print(f"{prog}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
        for m in run_programs.ZB:
            zb = run_programs.run(m, "pustype", text)
            zl = zb[1].replace("\r", "").splitlines()
            ok = len(rl) == rows and zl == rl
            bad += not ok
            print(f"  {m:30} {zb[0]}  {'SAME' if ok else 'DIVERGES'}")
            for a, b in zip(rl, zl):
                if a != b:
                    print(f"      ref {a!r}  zb {b!r}")
            if len(zl) != len(rl):
                print(f"      rows: ref {len(rl)} zb {len(zl)}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: PRINT USING raises the references' type errors, at once")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
