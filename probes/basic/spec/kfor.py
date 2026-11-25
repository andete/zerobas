#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KFOR -- the measured cases behind docs/keywords/FOR.md and NEXT.md: the flow region's first keyword probe
(D-KWSPEC; docs/keywords/spec-plan.md §2 region 5; docs/spec-method.md §3a). The run file is the shared RAM-record
harness's (probes/basic/spec/ramrec.py); the frame is klet.py's.

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it runs every case and POKEs a record of
the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read; the
record area ends below $F380 (asserted).

THE SETUP SEPARATES (spec-method §3a): every case is its own line and starts from NOTHING -- `CLEAR` (no variable,
no FOR frame; `ON ERROR` set again) -- with the loop under test after it on the same line; the body counts its runs
in WN%. RESUME NEXT after an error continues on that line, and the next line records ERR, WN% and the loop variable
through VARPTR. A case that could run forever (STEP 0, a STEP that an integer variable truncates to 0) carries a
guard in its body, `ON -(WN%>20) GOTO <the record line>`, so a count of 21 reads "it did not stop". EVERY counting
body has it since the first run (2026-11-25): there a FOR that FAILED left a half-built frame on zerobas, and the
NEXT that RESUME NEXT reached then looped for ever (STEP missing: step 0). The probe's own
variables all start with W.

THE RECORD (14 bytes per case, from $C001):
  0     E   the FIRST error of the case (0: none) -- the statement's own
  1     F   the LAST error (RESUME NEXT carries on along the line: after a failed FOR the body and its NEXT still
            run, and their error -- typically NEXT without FOR, 1 -- would otherwise overwrite the FOR's; the first
            run, 2026-11-25, recorded only this one and read 1 for `FOR A$=...`, a Type mismatch)
  2-3   N   WN%, the body's runs (low, high)
  4     T   the loop variable's type: 2 / 4 / 8 (its VARPTR bytes follow); 0: none read; $EE: VARPTR refused it
            (error 5 -- the variable does not exist)
  5-12      its bytes
  13    C   how many errors the case raised (line 800 counts them; goldfish pass 1: a middle error was invisible)

THE READOUT USES NO FOR / NEXT (spec-plan §1: not the keyword under test): since goldfish pass 1 it is two
subroutines of unrolled POKEs (950 zeroes, 960 copies); unrolled inline, the program outgrew the RAM below HIMEM.

THE GROUPS (case ids "KFR FX <i>", "KFR FY <i>"): FX, the first run's cases of FOR and NEXT; FY, goldfish pass 1's
separating cases (a second typed program: one program with both outgrew the RAM below HIMEM).

    python3 probes/basic/spec/kfor.py [--out scratchpad/KFR_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 14
RUN = "KFR_run1.out"
GAPS = {"FX": 4000.0, "FY": 4000.0}
# The guard: leave a loop that does not stop. NOT `IF ... THEN n`: a false IF skips the REST OF THE LINE -- the
# NEXT after it included -- so every guarded body would run once (the second run, 2026-11-25, read N=1 everywhere).
# `ON 0 GOTO` falls through to the next statement; -(WN%>20) is 1 only when the guard trips.
G = "ON -(WN%>20) GOTO {rec}"

# (keyword, the case -- `{g}` is the guard --, what it separates, the loop variable to read or None)
FX = [
    ("FOR", "FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT", "three runs", "I"),
    ("FOR", "FOR I=1 TO 1:WN%=WN%+1:{g}:NEXT", "start = limit", "I"),
    ("FOR", "FOR I=3 TO 1:WN%=WN%+1:{g}:NEXT", "start past the limit", "I"),
    ("FOR", "FOR I=3 TO 1 STEP -1:WN%=WN%+1:{g}:NEXT", "a negative step", "I"),
    ("FOR", "FOR I=1 TO 3 STEP -1:WN%=WN%+1:{g}:NEXT", "a negative step, start below", "I"),
    ("FOR", "FOR I=1 TO 3 STEP 0:WN%=WN%+1:{g}:NEXT", "STEP 0", "I"),
    ("FOR", "FOR I=3 TO 1 STEP 0:WN%=WN%+1:{g}:NEXT", "STEP 0, start past the limit", "I"),
    ("FOR", "FOR I=0 TO 1 STEP .1:WN%=WN%+1:{g}:NEXT", "a fractional step (double)", "I"),
    ("FOR", "FOR I!=0 TO 1 STEP .1:WN%=WN%+1:{g}:NEXT", "a fractional step (single)", "I!"),
    ("FOR", "FOR I#=0 TO 1 STEP .1#:WN%=WN%+1:{g}:NEXT", "a fractional step (double literal)", "I#"),
    ("FOR", "FOR I%=1 TO 3:WN%=WN%+1:{g}:NEXT", "an integer variable", "I%"),
    ("FOR", "FOR I%=32765 TO 32767:WN%=WN%+1:{g}:NEXT", "an integer variable up to 32767", "I%"),
    ("FOR", "FOR I%=-32766 TO -32768 STEP -1:WN%=WN%+1:{g}:NEXT", "an integer variable down to -32768", "I%"),
    ("FOR", "FOR I%=1 TO 3 STEP .5:WN%=WN%+1:{g}:NEXT", "an integer variable, STEP .5", "I%"),
    ("FOR", "FOR I%=1 TO 3.7:WN%=WN%+1:{g}:NEXT", "an integer variable, a fractional limit", "I%"),
    ("FOR", "FOR I%=1.6 TO 3:WN%=WN%+1:{g}:NEXT", "an integer variable, a fractional start", "I%"),
    ("FOR", "FOR I%=1 TO 40000:WN%=WN%+1:{g}:NEXT", "an integer variable, a limit past 32767", "I%"),
    ("FOR", "FOR I=1 TO 3:WN%=WN%+1:{g}:I=5:NEXT", "the variable changed in the body", "I"),
    ("FOR", "WL=3:FOR I=1 TO WL:WN%=WN%+1:{g}:WL=1:NEXT", "the limit changed in the body", "I"),
    ("FOR", "WS=1:FOR I=1 TO 5 STEP WS:WN%=WN%+1:{g}:WS=2:NEXT", "the step changed in the body", "I"),
    ("FOR", "FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT J,I", "nested, NEXT J,I", "J"),
    ("FOR", "FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT:NEXT", "nested, two bare NEXTs", "I"),
    ("NEXT", "FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT I", "NEXT I inside FOR J", "I"),
    ("FOR", "FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT I", "the same variable twice", "I"),
    ("FOR", "FOR I=1 TO 2", "no NEXT", "I"),
    ("FOR", 'FOR A$="A" TO "B":WN%=WN%+1:{g}:NEXT', "a string variable", None),
    ("FOR", 'FOR I=1 TO "A":WN%=WN%+1:{g}:NEXT', "a string limit", "I"),
    ("FOR", "FOR I=1", "no TO", "I"),
    ("FOR", "FOR I=1 TO", "nothing after TO", "I"),
    ("FOR", "FOR I TO 3", "no `=`", "I"),
    ("FOR", "FOR 1=1 TO 3", "a number as the variable", None),
    ("FOR", "FOR Q(1)=1 TO 3:WN%=WN%+1:{g}:NEXT", "an array element as the variable", None),
    ("FOR", "FOR I=1 TO 3 STEP:WN%=WN%+1:{g}:NEXT", "STEP with nothing", "I"),
    ("FOR", "FOR I=1/0 TO 3:WN%=WN%+1:{g}:NEXT", "the start's own error", "I"),
    ("FOR", "FOR I=1 TO 1/0:WN%=WN%+1:{g}:NEXT", "the limit's own error", "I"),
    ("NEXT", "NEXT", "NEXT without FOR", None),
    ("NEXT", "NEXT I", "NEXT I without FOR", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT J", "NEXT J inside FOR I", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT I,", "a trailing comma", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT 5", "a number after NEXT", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT I J", "two names without a comma", "I"),
    ("NEXT", "FOR I=1 TO 2:FOR J=1 TO 2:WN%=WN%+1:{g}:NEXT J,I,K", "a third name past the frames", "I"),
    # LAST: on zerobas the first run never got past this case (every later record unwritten)
    ("FOR", 'FOR I=1 TO 2 STEP "A":WN%=WN%+1:{g}:NEXT', "a string step", "I"),
]

# GROUP FY -- goldfish pass 1 (scratchpad/REVIEW-m2-gkwfor.md): the cases that separate the rules' rivals. A group of
# its own: with them, ONE typed program outgrew the RAM below HIMEM (both machines stopped while it was typed).
FY = [
    ("FOR", "FOR I=1:WN%=WN%+1:{g}:NEXT", "no TO, a body after it", "I"),
    ("FOR", "FOR I TO 3:WN%=WN%+1:{g}:NEXT", "no `=`, a body after it", "I"),
    ("FOR", "FOR I=1 TO:WN%=WN%+1:{g}:NEXT", "nothing after TO, a body after it", "I"),
    ("FOR", "FOR 1=1 TO 3:WN%=WN%+1:{g}:NEXT", "a number as the variable, a body after it", "I"),
    ("FOR", "FOR I=1 TO 1 STEP 0:WN%=WN%+1:{g}:NEXT", "STEP 0, start = limit", "I"),
    ("FOR", "FOR I%=-1.6 TO 0:WN%=WN%+1:{g}:NEXT", "an integer variable, a negative fractional start", "I%"),
    ("FOR", "FOR I%=1 TO 5 STEP 1.5:WN%=WN%+1:{g}:NEXT", "an integer variable, STEP 1.5", "I%"),
    ("FOR", "FOR I%=3 TO 1 STEP -.5:WN%=WN%+1:{g}:NEXT", "an integer variable, STEP -.5", "I%"),
    ("FOR", "FOR I%=1 TO -40000 STEP -1:WN%=WN%+1:{g}:NEXT", "an integer variable, a limit below -32768", "I%"),
    ("FOR", "FOR I%=40000 TO 1:WN%=WN%+1:{g}:NEXT", "an integer variable, a start past 32767", "I%"),
    ("FOR", "FOR I%=1 TO 3 STEP 40000:WN%=WN%+1:{g}:NEXT", "an integer variable, a step past 32767", "I%"),
    ("FOR", "FOR I%=32766 TO 32767.9:WN%=WN%+1:{g}:NEXT", "an integer variable, a limit of 32767.9", "I%"),
    ("FOR", "FOR I!=0 TO 1 STEP 1/3:WN%=WN%+1:{g}:NEXT", "a step inexact in single (single)", "I!"),
    ("FOR", "FOR I#=0 TO 1 STEP 1/3:WN%=WN%+1:{g}:NEXT", "a step inexact in single (double)", "I#"),
    ("FOR", "FOR I=1 TO 3 STEP 1/0:WN%=WN%+1:{g}:NEXT", "the step's own error", "I"),
    ("FOR", 'FOR I="A" TO 3:WN%=WN%+1:{g}:NEXT', "a string start", "I"),
    ("FOR", "FOR I=1 TO 2 STEP 1,2:WN%=WN%+1:{g}:NEXT", "a comma after STEP's value", "I"),
    ("FOR", "WL=1:FOR I=1 TO WL:WN%=WN%+1:{g}:WL=3:NEXT", "the limit raised in the body", "I"),
    ("FOR", "FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT I", "the same variable twice, two NEXT I", "I"),
    ("FOR", "FOR I=1 TO 2:FOR J=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT J", "FOR I again above FOR J", "J"),
    ("FOR", "I=7:FOR I=1/0 TO 3:WN%=WN%+1:{g}:NEXT", "the start's own error, I preset", "I"),
    ("FOR", "I=7:FOR I TO 3:WN%=WN%+1:{g}:NEXT", "no `=`, I preset", "I"),
    ("FOR", "I=7:FOR I=1 TO 40000:WN%=WN%+1:{g}:NEXT", "a double variable, a large limit", "I"),
    ("NEXT", "FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT I:NEXT J", "is J's frame dropped by NEXT I", "J"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT J:NEXT", "does I's frame survive a failed NEXT J", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT I,5", "a number later in the list", "I"),
    ("NEXT", "FOR IJ=1 TO 2:WN%=WN%+1:{g}:NEXT I J", "a space inside the name", "IJ"),
    ("NEXT", "FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:{g}:NEXT J,I", "NEXT J,I: the outer variable", "I"),
    ("NEXT", "FOR I=1 TO 2:FOR J=1 TO 2:WN%=WN%+1:{g}:NEXT J,K", "NEXT J,K with K not open", "I"),
    ("NEXT", "FOR A%=1 TO 2:WN%=WN%+1:{g}:NEXT A", "NEXT A after FOR A%", "A%"),
    ("NEXT", "FOR AB=1 TO 2:WN%=WN%+1:{g}:NEXT A", "NEXT A after FOR AB", "AB"),
    ("NEXT", "NEXT", "a bare NEXT without FOR: VARPTR(I) refuses", "I"),
    ("NEXT", "FOR I=1 TO 2:WN%=WN%+1:{g}:NEXT J", "a failed NEXT J: does it create J", "J"),
]


def _read(name, base):
    o = base + 4
    nb = {"%": 2, "!": 4, "#": 8}.get(name[-1], 8)
    # T := $EE first: VARPTR of a variable that does not exist is error 5 on BOTH machines, and a failing NEXT I
    # creates I on the VG-8020 but not on zerobas (the third run stopped there). The record line's own handler (900)
    # sets WX; a false IF then skips the rest of the line, so the $EE stays.
    return f"WX=0:POKE {o},238:WV=VARPTR({name}):IF WX=0 THEN POKE {o},{nb}:WO={o + 1}:GOSUB 960"


GROUPS = {"FX": FX, "FY": FY}


def program(group="FX"):
    lines = ["10 CLEAR 300,&HBF00:POKE &HC000,0:GOTO 2000", "800 WC=WC+1:IF WE=0 THEN WE=ERR", "810 WF=ERR:RESUME NEXT", "900 WX=1:RESUME NEXT",
             # the readout's two subroutines (no FOR / NEXT: spec-plan §1; unrolled inline, the program outgrew RAM)
             "950 " + ":".join(f"POKE WO+{k},0" for k in range(9)) + ":RETURN",
             "960 " + ":".join(f"POKE WO+{k},PEEK(WV+{k})" for k in range(8)) + ":RETURN"]
    cases = []
    n = 2000
    for i, (kw, stmt, why, var) in enumerate(GROUPS[group]):
        base = 0xC001 + REC * i
        rec = n + 1
        # every W variable exists before the case (klet.py's lesson: a later variable moves the arrays)
        lines.append(f"{n} CLEAR 300,&HBF00:ON ERROR GOTO 800:WE=0:WF=0:WC=0:WN%=0:WV=0:WK=0:WL=0:WS=0:WX=0:WO=0:"
                     + stmt.format(g=G.format(rec=rec)))
        lines.append(f"{rec} ON ERROR GOTO 900:POKE {base},WE:POKE {base + 1},WF:POKE {base + 2},WN% AND 255:"
                     f"POKE {base + 3},WN%\\256 AND 255:WO={base + 4}:GOSUB 950:POKE {base + 13},WC")
        n = rec + 1
        if var:
            lines.append(f"{n} {_read(var, base)}")
            n += 1
        cases.append((f"KFR {group} {i}", dict(kw=kw, stmt=stmt, why=why, var=var)))
    lines.append(f"{n} POKE &HC001+{REC * len(cases)},&HC3:POKE &HC000,&H5A:END")
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        t = r[4]
        v = ({2: "%", 4: "!", 8: "#"}[t], bytes(r[5:5 + t])) if t in (2, 4, 8) else ("none" if t == 0xEE else None)
        out.append(dict(e=r[0], f=r[1], n=r[2] | r[3] << 8, v=v, c=r[13]))
    return out, None


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
