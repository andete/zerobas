#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KIF -- the measured cases behind docs/keywords/IF.md: the flow region's third keyword probe (D-KWSPEC;
docs/keywords/spec-plan.md §2 region 5; docs/spec-method.md §3a). The frame, the record and the 30-line case blocks
are kgosub.py's: line n runs the IF under test and ends `GOTO n+25`; the case's target lines sit at n+5 .. n+20; WP%'s
bits say WHICH lines and statements ran (1 is set first on line n, the cases OR in 2 / 4 / 8 / 16 for the parts that
ran), WN% counts, and the first and last errors are kept.

THE RECORD (6 bytes per case, from $C001): E, F, N (2), P (2) -- kgosub.py's.

THE GROUP (case ids "KIF FX <i>"): FX, every case of IF.

    python3 probes/basic/spec/kif.py [--out scratchpad/KIF_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 6
RUN = "KIF_run1.out"
GAPS = {"FX": 4000.0}
G = "ON -(WN%>20) GOTO {R}"
O = "WP%=WP% OR "

# (keyword, line n's statements, {offset: the line's statements}, what it separates)
FX = [
    ("IF", "WP%=1:IF 1 THEN " + O + "2:" + O + "4", {}, "a true IF runs THEN and the rest of the line"),
    ("IF", "WP%=1:IF 0 THEN " + O + "2:" + O + "4", {}, "a false IF skips THEN and the rest of the line"),
    ("IF", "WP%=1:IF -1 THEN " + O + "2", {}, "-1 is true"),
    ("IF", "WP%=1:IF .5 THEN " + O + "2", {}, "a fraction is true"),
    ("IF", "WP%=1:IF 1E-30 THEN " + O + "2", {}, "a tiny number is true"),
    ("IF", "WP%=1:WK=0:IF WK THEN " + O + "2", {}, "a variable holding 0 is false"),
    ("IF", "WP%=1:IF 1 THEN {L5}", {5: O + "4"}, "THEN a line number"),
    ("IF", "WP%=1:IF 0 THEN {L5}", {5: O + "4"}, "THEN a line number, false"),
    ("IF", "WP%=1:IF 1 GOTO {L5}", {5: O + "4"}, "IF ... GOTO"),
    ("IF", "WP%=1:IF 0 GOTO {L5}:" + O + "2", {5: O + "4"}, "IF ... GOTO, false (the rest of the line too)"),
    ("IF", "WP%=1:IF 1 THEN " + O + "2 ELSE " + O + "4", {}, "ELSE, true"),
    ("IF", "WP%=1:IF 0 THEN " + O + "2 ELSE " + O + "4", {}, "ELSE, false"),
    ("IF", "WP%=1:IF 0 THEN " + O + "2 ELSE {L5}", {5: O + "8"}, "ELSE a line number"),
    ("IF", "WP%=1:IF 0 THEN " + O + "2 ELSE " + O + "4:" + O + "8", {}, "statements after ELSE's own"),
    ("IF", "WP%=1:IF 1 THEN " + O + "2 ELSE " + O + "4:" + O + "8", {}, "statements after ELSE, true"),
    ("IF", "WP%=1:IF 1 THEN IF 0 THEN " + O + "2 ELSE " + O + "4", {}, "ELSE after a nested IF (true, false)"),
    ("IF", "WP%=1:IF 0 THEN IF 1 THEN " + O + "2 ELSE " + O + "4", {}, "ELSE after a nested IF (false outside)"),
    ("IF", "WP%=1:IF 0 THEN IF 1 THEN " + O + "2 ELSE " + O + "4 ELSE " + O + "8", {},
     "two ELSEs: the second belongs to the outer IF"),
    ("IF", "WP%=1:IF 1 THEN IF 1 THEN " + O + "2 ELSE " + O + "4 ELSE " + O + "8", {}, "two ELSEs, both true"),
    ("IF", 'WP%=1:IF "A"<"B" THEN ' + O + "2", {}, "a string comparison"),
    ("IF", 'WP%=1:WK$="A":IF WK$ THEN ' + O + "2", {}, "a string as the condition"),
    ("IF", "WP%=1:IF 1 THEN", {}, "THEN followed by nothing"),
    ("IF", "WP%=1:IF 1 " + O + "2", {}, "no THEN"),
    ("IF", "WP%=1:IF THEN " + O + "2", {}, "no condition"),
    ("IF", "WP%=1:IF 1/0 THEN " + O + "2:" + O + "4", {}, "the condition's own error"),
    ("IF", "WP%=1:IF 1 THEN 65000", {}, "THEN a line that does not exist"),
    ("IF", "WP%=1:IF 0 THEN 65000:" + O + "2", {}, "THEN a missing line, false"),
    ("IF", "WP%=1:GOTO {L5}", {5: "WN%=WN%+1:IF WN%<3 THEN {L5}"}, "THEN back to its own line"),
    ("IF", "WP%=1:FOR I=1 TO 3:IF I=2 THEN " + O + "2:NEXT", {}, "NEXT after a true IF on the same line"),
    ("IF", "WP%=1:FOR I=1 TO 3:WN%=WN%+1:IF I=9 THEN " + O + "2:NEXT", {}, "a false IF skips the NEXT behind it"),
    ("IF", "WP%=1:IF 1 THEN " + O + "2 ELSE 65000", {}, "ELSE to a missing line, not taken"),
    ("IF", "WP%=1:IF 1 THEN:" + O + "2", {}, "THEN followed by a colon"),
]


def _lines(n, main, subs):
    m = {f"L{k}": n + k for k in (5, 10, 15, 20)}
    m["R"] = n + 25
    m["L0"] = n
    m["g"] = ""
    fmt = lambda t: t.format(**m)    # noqa: E731
    # line n+1: reached only by FALLING THROUGH line n (a false IF skips the rest of its line, the GOTO n+25 included),
    # so it goes straight to the record -- a fall-through must not run the case's target lines
    out = [(n, fmt(main) + f":GOTO {n + 25}"), (n + 1, f"GOTO {n + 25}")]
    for k, t in sorted(subs.items()):
        out.append((n + k, fmt(t)))
    return out


def program(group="FX"):
    lines = ["10 CLEAR 300,&HBF00:POKE &HC000,0:GOTO 2000", "800 IF WE=0 THEN WE=ERR", "810 WF=ERR:RESUME NEXT"]
    cases = []
    n = 2000
    for i, (kw, main, subs, why) in enumerate(FX):
        base = 0xC001 + REC * i
        body = _lines(n, main, subs)
        body[0] = (n, "CLEAR 300,&HBF00:ON ERROR GOTO 800:WE=0:WF=0:WN%=0:WP%=0:WK=0:I=0:" + body[0][1])
        lines += [f"{k} {t}" for k, t in body]
        lines.append(f"{n + 25} ON ERROR GOTO 0:POKE {base},WE:POKE {base + 1},WF:POKE {base + 2},WN% AND 255:"
                     f"POKE {base + 3},WN%\\256 AND 255:POKE {base + 4},WP% AND 255:POKE {base + 5},WP%\\256 AND 255")
        cases.append((f"KIF FX {i}", dict(kw=kw, stmt=main, subs=subs, why=why)))
        n += 30
    lines.append(f"{n} POKE &HC001+{REC * len(FX)},&HC3:POKE &HC000,&H5A:END")
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    return [dict(e=r[0], f=r[1], n=r[2] | r[3] << 8, p=r[4] | r[5] << 8) for r in rs], None


def load(group="FX", run=RUN):
    sec = ramrec.read_section(os.path.join(ROOT, "scratchpad", run), group)
    _, cases = program(group)
    out = {}
    for who, h in sec.items():
        recs, why = decode(h, len(cases))
        if recs is None:
            sys.exit(f"FAIL: {run} {group} {who}: {why}")
        out[who] = [NS(src=group, id=cid, **meta, **r) for (cid, meta), r in zip(cases, recs)]
    return out


def main(argv):
    path = os.path.join(ROOT, "scratchpad", RUN)
    if "--out" in argv:
        path = os.path.join(ROOT, argv[argv.index("--out") + 1])
    lines, cases = program()
    if "--lines" in argv:
        print("\n".join(lines))
        return 0
    cap = ramrec.measure(lines, len(cases), REC, GAPS["FX"])
    bad = []
    for who in ("ref", "zb"):
        recs, why = decode(cap[who], len(cases))
        if recs is None:
            bad.append(f"{who}: {why}")
    text = open(path).read() if os.path.exists(path) else ""
    open(path, "w").write(ramrec.write_section(text, "FX", cap, len(cases), bad))
    print(f"FX: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
    if not bad:
        ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
        diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
        print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
