#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KGOSUB -- the measured cases behind docs/keywords/GOTO.md, GOSUB.md and RETURN.md: the flow region's second keyword
probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 5; docs/spec-method.md §3a). The run file is the shared RAM-record
harness's (probes/basic/spec/ramrec.py); the frame is kfor.py's.

Clean room: typed BASIC in, RAM out. No reference ROM byte is read; the record area ends below $F380 (asserted).

EACH CASE IS A BLOCK OF 30 LINES from its base n: line n starts from nothing (`CLEAR`, `ON ERROR` set again), runs
the statement(s) under test and ends `GOTO n+25`; the case's own target lines sit at n+5 .. n+20 (written `{L5}` ..
`{L20}` in the cases below, `{R}` for the record line n+25); n+25 records. Each line a case reaches ORs its own bit
into WP% (`WP%=WP% OR k`), so the record says WHICH lines ran, not only how many; WN% counts a repeated body. RESUME
NEXT carries on after an error, so the FIRST and the LAST error are both kept (kfor.py's lesson). A case that could run
for ever carries kfor.py's guard, `ON -(WN%>20) GOTO {R}`. The probe's own variables all start with W.

THE RECORD (6 bytes per case, from $C001):
  0     E   the FIRST error (0: none)
  1     F   the LAST error
  2-3   N   WN% (low, high)
  4-5   P   WP%, the bits of the lines reached (low, high)

THE GROUPS (case ids "KGS FX <i>", "KGS FY <i>"): FX, the first run's cases of GOTO, GOSUB and RETURN; FY, goldfish
pass 1's separating cases (a second typed program).

THE FRAME USES GOTO (`GOTO n+25` ends each case line; the guard is `ON ... GOTO`), which spec-plan §1 would keep out
of a GOTO probe. Kept on purpose (goldfish pass 1): a frame GOTO that went wrong lands outside its case, and the
record frame's own check (the done flag and the end byte, ramrec.frame) refuses the run -- it cannot produce a
PLAUSIBLE wrong record. The cases under test never depend on the frame's GOTO to reach their own lines.

    python3 probes/basic/spec/kgosub.py [--out scratchpad/KGS_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 6
RUN = "KGS_run1.out"
GAPS = {"FX": 4000.0, "FY": 4000.0}
G = "ON -(WN%>20) GOTO {R}"

# (keyword, line n's statements, {offset: the line's statements}, what it separates)
FX = [
    ("GOTO", "WP%=1:GOTO {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4"}, "a forward GOTO skips the rest of the line"),
    ("GOTO", "GOTO {L10}", {5: "WP%=WP% OR 4", 10: "WP%=WP% OR 8"}, "GOTO skips the lines between"),
    ("GOTO", "WN%=0:GOTO {L5}", {5: "WN%=WN%+1:WP%=WP% OR 4:" + G + ":GOTO {L5}"}, "a GOTO loop (the guard ends it)"),
    ("GOTO", "GOTO 65000", {}, "a line that does not exist"),
    ("GOTO", "GOTO 65530", {}, "a line number past 65529"),
    ("GOTO", "GOTO", {}, "no line number"),
    ("GOTO", "WK=1:GOTO WK", {}, "a variable as the line"),
    ("GOTO", "GO TO {L5}", {5: "WP%=WP% OR 4"}, "GO TO with a space"),
    ("GOTO", "GOTO {L5} 7", {5: "WP%=WP% OR 4"}, "something after the line number"),
    ("GOSUB", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN"}, "GOSUB / RETURN comes back after the GOSUB"),
    ("GOSUB", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:GOSUB {L10}:WP%=WP% OR 16:RETURN", 10: "WP%=WP% OR 8:RETURN"},
     "nested GOSUBs"),
    ("GOSUB", "WN%=0:GOSUB {L5}", {5: "WN%=WN%+1:IF WN%<5 THEN GOSUB {L5}", 10: "RETURN"},
     "recursion five deep, each level falling through to RETURN"),
    ("GOSUB", "GOSUB 65000", {}, "a line that does not exist"),
    ("GOSUB", "GOSUB", {}, "no line number"),
    ("GOSUB", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4"}, "a subroutine without RETURN (runs on into the record)"),
    ("GOSUB", "WN%=0:GOSUB {L5}", {5: "WN%=WN%+1:" + G + ":GOSUB {L5}"}, "unbounded recursion (the guard ends it)"),
    ("RETURN", "RETURN", {}, "RETURN without GOSUB"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN {L10}", 10: "WP%=WP% OR 8"},
     "RETURN with a line number"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN 65000"}, "RETURN to a line that does not exist"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN:WP%=WP% OR 8"}, "statements after RETURN"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2:RETURN", {5: "RETURN"}, "a second RETURN once the GOSUB came back"),
    ("RETURN", "FOR I=1 TO 2:GOSUB {L5}:WN%=WN%+1:NEXT", {5: "RETURN"}, "GOSUB inside FOR"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2:NEXT", {5: "FOR I=1 TO 3:WN%=WN%+1:RETURN"},
     "RETURN from inside a FOR in the subroutine, then NEXT"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "FOR I=1 TO 3:WN%=WN%+1:" + G + ":NEXT:RETURN"},
     "a whole FOR inside the subroutine"),
    ("RETURN", "FOR I=1 TO 2:GOSUB {L5}:WP%=WP% OR 2", {5: "WN%=WN%+1:" + G + ":NEXT"},
     "NEXT inside the subroutine for a FOR outside it"),
    ("GOTO", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:GOTO {L10}", 10: "WP%=WP% OR 8:RETURN"},
     "a GOTO inside a subroutine, RETURN from elsewhere"),
    # added after the first run (GO TO with a space: the reference jumps, zerobas says Syntax error)
    ("GOSUB", "GO SUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN"}, "GO SUB with a space"),
    ("GOTO", "GO  TO {L5}", {5: "WP%=WP% OR 4"}, "GO TO with two spaces"),
    ("GOTO", "IF 1 THEN GO TO {L5}", {5: "WP%=WP% OR 4"}, "GO TO after THEN"),
    ("GOTO", "GO", {}, "GO alone"),
]

# GROUP FY -- goldfish pass 1 (scratchpad/REVIEW-m2-gkwgosub.md): the cases that separate the rules' rivals. `{L5a}
# {L5b}` is line n+5's number split before its last digit (`GOTO 200 5`); a key "@k" is an ABSOLUTE line k (the
# program's last case line is far below it, so only its own case reaches it).
FY = [
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN {L10}", 10: "WP%=WP% OR 8:RETURN"},
     "RETURN n closes the subroutine"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN 65000:WN%=WN%+1:RETURN"},
     "RETURN n to a missing line closes the subroutine first"),
    ("RETURN", "RETURN 65000", {}, "RETURN n with nothing open"),
    ("RETURN", "WK=1:RETURN WK", {}, "RETURN and a variable with nothing open"),
    ("RETURN", "GOSUB {L5}:WP%=WP% OR 2:NEXT I", {5: "FOR I=1 TO 3:FOR J=1 TO 2:RETURN"},
     "RETURN drops every FOR opened in the subroutine"),
    ("RETURN", "FOR I=1 TO 2:GOSUB {L5}:WP%=WP% OR 2", {5: "WN%=WN%+1:" + G + ":NEXT I"},
     "NEXT I in the subroutine for a FOR outside it"),
    ("RETURN", 'GOSUB {L5}:WP%=WP% OR 2', {5: 'WP%=WP% OR 4:RETURN "A"'}, "RETURN and a string"),
    ("GOSUB", "WN%=0:GOSUB {L5}:WP%=WP% OR 2", {5: "WN%=WN%+1:IF WN%<3 THEN GOSUB {L5}", 10: "WN%=WN%+10:RETURN"},
     "recursion three deep, the returns counted"),
    ("GOSUB", "GOSUB 65000:WN%=WN%+1:RETURN", {}, "GOSUB to a missing line pushes no frame"),
    ("GOSUB", "IF 1 THEN GOSUB {L5}:WP%=WP% OR 2", {5: "RETURN"}, "GOSUB in a THEN clause comes back to it"),
    ("GOSUB", "GOSUB {L5a} {L5b}:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN"}, "GOSUB: digits joined across a space"),
    ("GOSUB", "GOSUB {L5} ZZ:WP%=WP% OR 2", {5: "WP%=WP% OR 4:RETURN"}, "GOSUB: letters after the line number"),
    ("GOTO", "GOTO {L5a} {L5b}", {5: "WP%=WP% OR 4"}, "GOTO: digits joined across a space"),
    ("GOTO", "GOTO {L5} ZZ", {5: "WP%=WP% OR 4"}, "GOTO: letters after the line number"),
    ("GOTO", "GOTO 65530", {"@6553": "WP%=WP% OR 4:GOTO {R}"}, "GOTO 65530 with a line 6553"),
    ("GOTO", "GOTO 70000", {"@7000": "WP%=WP% OR 8:GOTO {R}"}, "GOTO 70000 with a line 7000"),
    ("GOTO", "IF 1 GO TO {L5}", {5: "WP%=WP% OR 4"}, "GO TO after IF without THEN"),
    ("GOTO", "ON 1 GO TO {L5}", {5: "WP%=WP% OR 4"}, "ON 1 GO TO"),
    ("GOTO", "GO=1:FOR I=GO TO 3:WN%=WN%+1:NEXT", {}, "a variable GO before TO"),
    ("GOTO", "GOTO -1", {}, "a negative line"),
    ("GOTO", 'GOTO "A"', {}, "a string as the line"),
]
GROUPS = {"FX": FX, "FY": FY}


def _lines(n, main, subs):
    m = {f"L{k}": n + k for k in (5, 10, 15, 20)}
    m["L5a"], m["L5b"] = (n + 5) // 10, (n + 5) % 10
    m["R"] = n + 25
    m["g"] = ""
    fmt = lambda t: t.format(**m)    # noqa: E731
    out = [(n, fmt(main) + f":GOTO {n + 25}")]
    for k, t in sorted(subs.items(), key=lambda kv: str(kv[0])):
        out.append((int(k[1:]) if isinstance(k, str) else n + k, fmt(t)))
    return out


def program(group="FX"):
    lines = ["10 CLEAR 300,&HBF00:POKE &HC000,0:GOTO 2000", "800 IF WE=0 THEN WE=ERR", "810 WF=ERR:RESUME NEXT"]
    cases = []
    n = 2000
    for i, (kw, main, subs, why) in enumerate(GROUPS[group]):
        base = 0xC001 + REC * i
        body = _lines(n, main, subs)
        body[0] = (n, "CLEAR 300,&HBF00:ON ERROR GOTO 800:WE=0:WF=0:WN%=0:WP%=0:WK=0:I=0:" + body[0][1])
        lines += [f"{k} {t}" for k, t in body]
        lines.append(f"{n + 25} ON ERROR GOTO 0:POKE {base},WE:POKE {base + 1},WF:POKE {base + 2},WN% AND 255:"
                     f"POKE {base + 3},WN%\\256 AND 255:POKE {base + 4},WP% AND 255:POKE {base + 5},WP%\\256 AND 255")
        cases.append((f"KGS {group} {i}", dict(kw=kw, stmt=main, subs=subs, why=why, base=n)))
        n += 30
    lines.append(f"{n} POKE &HC001+{REC * len(cases)},&HC3:POKE &HC000,&H5A:END")
    lines = sorted(lines, key=lambda t: int(t.split()[0]))
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    return [dict(e=r[0], f=r[1], n=r[2] | r[3] << 8, p=r[4] | r[5] << 8) for r in rs], None


def load(group=None, run=RUN):
    """the cases of one group, or (group None) of every group, in GROUPS' order"""
    if group is None:
        parts = [load(g, run) for g in GROUPS]
        return {who: [c for p in parts for c in p[who]] for who in ("ref", "zb")}
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
    groups = [g for g in GROUPS if g in argv] or list(GROUPS)
    if "--lines" in argv:
        print("\n".join(program(groups[0])[0]))
        return 0
    for group in groups:
        lines, cases = program(group)
        cap = ramrec.measure(lines, len(cases), REC, GAPS[group])
        bad = []
        for who in ("ref", "zb"):
            recs, why = decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, group, cap, len(cases), bad))
        print(f"{group}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
