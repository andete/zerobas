"""concat3-acceptance (D-CONCAT3): how much free string space a `+` chain needs.

The references allocate each later step's whole body while the previous one is
still live; zerobas extended the first step's body in place for every step, so
`T$=T$+L$+" "` needed 100 free bytes here and 199 on the VG-8020 and the CF-3300 --
a program that runs out of string space on a real MSX ran on here. Two programs,
both zerobas targets against the VG-8020: the 3-term threshold
(scratchpad/concat3_measure.bas) and six chain shapes (scratchpad/concat_chain.bas:
4 terms, a function first, a function in the middle, a literal first, an unassigned
chain inside LEN(), and the 2-term control D-CONCATPEAK already matched).

Clean-room: a tape in; the printer port out; FRE("") is the only reading.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROGS = [("scratchpad/concat3_measure.bas", 2), ("scratchpad/concat_chain.bas", 6)]


def main():
    bad = 0
    for prog, rows in PROGS:
        text = open(os.path.join(REPO, prog)).read()
        ref = run_programs.run(run_programs.REF, "concat3", text)
        rl = ref[1].replace("\r", "").splitlines()
        print(f"{prog}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
        for m in run_programs.ZB:
            zb = run_programs.run(m, "concat3", text)
            zl = zb[1].replace("\r", "").splitlines()
            ok = len(rl) == rows and zl == rl
            bad += not ok
            print(f"  {m:30} {zb[0]}  {'SAME' if ok else 'DIVERGES'}")
            for a, b in zip(rl, zl):
                if a != b:
                    print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a `+` chain needs the references' free string space")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
