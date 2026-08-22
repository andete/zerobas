#!/usr/bin/env python3
"""D-DEFFN control: no kwtable entry is a prefix of another, in EITHER direction.

`match_kw` takes the FIRST matching entry and does no longest-match and no word
boundary, so adding a row is safe exactly when no existing entry is a prefix of
the new one and the new one is a prefix of no existing entry -- the constraint
`kwtable.inc`'s own DEFINT/DEF comment records. This walks the table instead of
eyeballing the F-words.

🔴 IT IS NOT A CLEAN-TABLE CHECK. The table ALREADY contains deliberate prefix
pairs (DEFSTR/DEFSNG/DEFDBL before DEF, MAXFILES/MAX, LLIST/LIST): those are
correct BECAUSE of their ORDER. So the rule this enforces is the ordered one --
if X is a prefix of Y, then Y must come FIRST -- and the check's value is that
it fails when a new row lands on the wrong side of one.
"""
import re, sys

ROW = re.compile(r'^\s*db\s+(\d+)\s*,\s*"([^"]*)"\s*,\s*1\s*,\s*([A-Z_0-9]+)', re.M)

def main() -> int:
    src = open("basic/kwtable.inc").read()
    rows = [(int(n), w, t) for n, w, t in ROW.findall(src)]
    bad = []
    for n, w, t in rows:
        if n != len(w):
            bad.append(f"length field {n} != len({w!r})")
    print(f"  denominator: {len(rows)} keyword rows walked")
    if not rows:
        print("  REFUSING: 0 rows parsed -- the regex has gone blind, not the table")
        return 2
    viol = []
    for i, (_, w, t) in enumerate(rows):
        for j, (_, w2, t2) in enumerate(rows):
            if i == j or w == w2:
                continue
            if w2.startswith(w) and i < j:
                # w is a prefix of w2 and is tried FIRST -> w2 unreachable
                viol.append(f"{w!r} (row {i}) shadows {w2!r} (row {j})")
    for v in viol:
        print("  SHADOWED: " + v)
    for b in bad:
        print("  LENGTH:   " + b)
    fn = [r for r in rows if r[1] == "FN"]
    print(f"  FN row present: {bool(fn)}  {fn}")
    ok = not viol and not bad
    print("  OK -- no row is shadowed by an earlier prefix" if ok else "  FAILED")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
