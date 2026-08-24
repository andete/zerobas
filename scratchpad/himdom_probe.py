#!/usr/bin/env python3
"""D-HIMDOM -- CLEAR's memory-ceiling DOMAIN, and a regression check on D-CLRFIX.

🔴 THE URGENT ROW IS `d.50000`. D-CLRFIX replaced clr_himem's bare `call eval`
with `call eval_int16_checked`, which raises ERR 6 for |x| > 32767. It was
justified by row q.ovf (`CLEAR 200,70000` -> ERR 6 on both references) -- but
70000 is out of range under BOTH candidate rules:

    (a) the value is a SIGNED int16          -> reject anything |x| > 32767
    (b) the value is an UNSIGNED 16-bit ADDRESS -> reject only > 65535

**q.ovf cannot separate them.** A decimal in [32768, 65535] can, and if the
references ACCEPT it then D-CLRFIX introduced a regression for decimal
addresses -- `&HD000` sails through only because MSX BASIC reads a hex literal
>= &H8000 as NEGATIVE (-12288), so |x| <= 32767 by accident.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

🎯 THE OTHER DISCRIMINATOR IS `d.hffff` vs `d.neg1`: `&HFFFF` and `-1` are the
SAME sixteen bits and different surface syntax. If one is accepted and the other
is not, the rule is about the evaluated FLOAT, not about the address.

Readout `<ERR> SAME` or `<ERR> -><himem>` -- the error code AND whether the
ceiling actually moved. Both halves are needed: an ERR alone cannot say whether
a refused value was written anyway, and a delta alone cannot say which error
refused it. See the comment above case() for why the RAW HIMEM must not be in
the face.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

H = 'PRINT"[";PEEK(&HFC4A)+256*PEEK(&HFC4B);"]"'

# 🔴 ROUND 1 PUT THE RAW HIMEM IN THE FACE AND 12 OF 15 ROWS SCORED "THE
# REFERENCES DISAGREE" -- while every ERR code agreed on every row. HIMEM boots
# at 62336 on the VG-8020 and 56951 on the CF-3300, so a row that leaves it
# ALONE reads differently on the two machines for a reason that has nothing to
# do with the question. This is the SAME fault D-CLRFIX §3.1 fixed in
# scratchpad/clrfix_himem.py earlier today, re-introduced in a NEW probe within
# the hour. The delta is the question: HIMEM is read in DIRECT MODE either side
# of the RUN and the face is `<ERR> SAME` or `<ERR> -><value>`.


def case(arg):
    return [H,                              # direct mode, before
            "10 ONERRORGOTO900",
            '20 PRINT"<A>";',
            f"30 CLEAR 200,{arg}",
            '40 PRINT"<E";ERR;">":END',
            '900 PRINT"<E";ERR;">":END',
            "RUN",
            H]                              # direct mode, after


# 🔴 D-HIMRANGE follow-up rows. THREE questions the shipped 15 rows cannot ask:
#   (1) THE MACHINE-SPECIFIC UPPER EDGE. HIMEM boots at 62336 (VG-8020) / 56951
#       (CF-3300), so the ERR-5-above-RAM-top edge should sit at a DIFFERENT
#       value on each reference, and no row in [56951, 62336] existed to prove
#       it. The u.* rows below sweep that window: a row where the two references
#       DISAGREE (one accepts, one refuses) is the finding -- it says the edge is
#       a property of the machine (its RAM top / boot HIMEM), not a constant.
#   (2) CURRENT vs BOOT HIMEM. Does the upper edge read the LIVE HIMEM (so you
#       can only ever LOWER the ceiling) or a fixed boot-time RAM top (so you can
#       raise it back up)? Two CLEARs in one run separate them: lower then raise.
#       If the raise is refused, the check reads a live sysvar; if it succeeds,
#       it reads a fixed top. This decides whether zerobas must boot-init HIMEM.
#   (3) IS THE ERR-7 LOWER EDGE PROGRAM-DEPENDENT? D-HIMDOM ASSUMED it was "a
#       property of the current program and variables" but measured only a BARE
#       program -- which cannot separate "constant floor" from "used-memory +
#       margin". The p.* rows DIM an array first (wiped by CLEAR, but live at the
#       check) to move the high-water mark; if a value accepted bare becomes
#       ERR 7 after the DIM, the edge tracks allocation.


def case2(a1, a2):
    """Two CLEARs: set the ceiling to a1 (a legal value), re-arm the trap, then
    try a2. Re-arm because CLEAR eats the ON ERROR handler (D-CLRTRAP)."""
    return [H,
            "10 ONERRORGOTO900",
            '20 PRINT"<A>";',
            f"30 CLEAR 200,{a1}",
            "32 ONERRORGOTO900",
            f"35 CLEAR 200,{a2}",
            '40 PRINT"<E";ERR;">":END',
            '900 PRINT"<E";ERR;">":END',
            "RUN",
            H]


def casen(n, arg):
    """CLEAR n,arg -- a NON-default string space. If the ERR-7 floor tracks the
    requested string space, a large n raises the floor."""
    return [H,
            "10 ONERRORGOTO900",
            '20 PRINT"<A>";',
            f"30 CLEAR {n},{arg}",
            '40 PRINT"<E";ERR;">":END',
            '900 PRINT"<E";ERR;">":END',
            "RUN",
            H]


def casepad(nlines, arg, remlen=200):
    """Pad the program with nlines of long REM lines (each ~remlen B) to push the
    program high-water up, then CLEAR 200,arg. Few LONG lines rather than many
    short ones -- the 60-short-line version broke injection. If the floor tracks
    program TEXT size, a big program raises the floor."""
    lines = [H, "10 ONERRORGOTO900"]
    for i in range(nlines):
        lines.append(f"{100+i} REM {'X'*remlen}")
    lines += ['20 PRINT"<A>";',
              f"30 CLEAR 200,{arg}",
              '40 PRINT"<E";ERR;">":END',
              '900 PRINT"<E";ERR;">":END',
              "RUN", H]
    return lines


# zerobas PRGEND ($E026) reader -- ONLY meaningful on zb (the sysvar is zerobas's
# own; on the references $E026 is unrelated RAM). Used to set the floor MARGIN
# from a measured PRGEND rather than a guess.
PG = 'PRINT"[";PEEK(&HE026)+256*PEEK(&HE027);"]"'


def caseprgend(nlines):
    """Enter a program of nlines long REMs, then read PRGEND in direct mode."""
    lines = ["10 ONERRORGOTO900"]
    for i in range(nlines):
        lines.append(f"{100+i} REM {'X'*200}")
    lines += ['900 PRINT"<E";ERR;">":END', PG]
    return lines


def casedim(dimspec, arg):
    """DIM an array (raising the used-memory high-water), then CLEAR ,arg. The
    array is live when clr_himem's range check runs (the check precedes the
    variable wipe), so a program-dependent lower edge will refuse a value that a
    bare program accepts."""
    return [H,
            "10 ONERRORGOTO900",
            f"15 DIM {dimspec}",
            '20 PRINT"<A>";',
            f"30 CLEAR 200,{arg}",
            '40 PRINT"<E";ERR;">":END',
            '900 PRINT"<E";ERR;">":END',
            "RUN",
            H]


CASES = {
    # --- 🔴 THE REGRESSION DISCRIMINATOR: decimals in [32768, 65535] --------
    'd.50000':  case("50000"),
    'd.40000':  case("40000"),
    'd.32768':  case("32768"),      # the exact signed-int16 edge, decimal
    'd.32767':  case("32767"),      # one below it -- the in-range twin
    'd.65535':  case("65535"),      # the top of the unsigned address space
    'd.65536':  case("65536"),      # one past it
    'd.70000':  case("70000"),      # CONTROL: measured ERR 6 both refs (D-CLRFIX)
    # --- 🎯 SAME BITS, DIFFERENT SYNTAX ------------------------------------
    'd.hffff':  case("&HFFFF"),     # == -1 as sixteen bits
    'd.neg1':   case("-1"),         # CONTROL: measured ERR 5 both refs
    'd.h8000':  case("&H8000"),     # -32768 signed; the hex edge
    'd.hd000':  case("&HD000"),     # CONTROL: accepted on all three
    # --- the LOW end: where does a ceiling stop being legal? ----------------
    'd.zero':   case("0"),
    'd.one':    case("1"),
    'd.h4000':  case("&H4000"),     # 16384 -- inside ROM, positive int16
    'd.h8050':  case("&H8050"),     # the ceiling the array OOM fixtures use
    # --- (1) THE MACHINE-SPECIFIC UPPER EDGE, [56951, 62336] ----------------
    'u.56000':  case("56000"),      # below BOTH boot HIMEMs -> accept on both
    'u.56951':  case("56951"),      # == CF-3300 boot HIMEM (edge, CF)
    'u.57000':  case("57000"),      # just above CF-3300 top; below VG top
    'u.58000':  case("58000"),      # inside the window: VG accept, CF refuse?
    'u.60000':  case("60000"),      # inside the window
    'u.62000':  case("62000"),      # just below VG top
    'u.62336':  case("62336"),      # == VG-8020 boot HIMEM (edge, VG)
    'u.62337':  case("62337"),      # one past VG top -> refuse on both?
    'u.63000':  case("63000"),      # above both tops -> ERR 5 on both
    # --- (2) CURRENT vs BOOT HIMEM: can you RAISE the ceiling back up? -------
    't.4to6':   case2("40000", "60000"),   # lower to 40000, then raise to 60000
    't.4to5':   case2("40000", "50000"),   # lower to 40000, then raise to 50000
    't.6to4':   case2("60000", "40000"),   # CONTROL: lowering always legal
    't.4to4':   case2("40000", "40000"),   # CONTROL: same value twice
    # --- (3) IS THE ERR-7 LOWER EDGE PROGRAM-DEPENDENT? ---------------------
    # bare-program lower sweep: find where accept begins (D-HIMDOM: >32848, <40000)
    'l.33000':  case("33000"),
    'l.34000':  case("34000"),
    'l.35000':  case("35000"),
    'l.36000':  case("36000"),
    'l.38000':  case("38000"),
    'l.39000':  case("39000"),
    # a double array A#(1000) = 8008 B from $8001 -> top ~ $9F49 (40777).
    'p.dim38k': casedim("A#(1000)", "38000"),   # bare 38000 accepted; dep -> ERR 7
    'p.dim40k': casedim("A#(1000)", "40000"),   # near the array top
    'p.dim44k': casedim("A#(1000)", "44000"),   # above the array top -> accept
    # --- the ERR-5 / ERR-7 boundary at the bottom of RAM --------------------
    'b.7fff':   case("&H7FFF"),     # 32767, ROM side of the $8000 boundary
    'b.8001':   case("&H8001"),     # TXTTAB base, RAM side
    # --- RUN 2: does the floor track STRING SPACE (n)? ----------------------
    # if floor = base + n + margin, then n=10000 raises the floor by ~9800:
    's.n2_42k': casen("200", "42000"),     # CONTROL: n=200 accepts 42000
    's.big33k': casen("10000", "33000"),   # ERR7 either way (below any floor)
    's.big42k': casen("10000", "42000"),   # ERR7 iff floor tracks n (42000<~43k)
    's.big44k': casen("10000", "44000"),   # accept iff floor ~43k < 44000
    's.big52k': casen("10000", "52000"),   # accept (well above any floor, < top)
    # --- RUN 2: does the floor track PROGRAM TEXT size? ---------------------
    # 60 REM lines ~ 2.4 KB of program text above TXTTAB:
    'g.pad34k': casepad(60, "34000"),      # bare 34000 accepts; ERR7 iff prog-dep
    'g.pad38k': casepad(60, "38000"),      # accept iff floor still < 38000
    'g.pad0_34k': casepad(0, "34000"),     # CONTROL: no pad, accepts (== l.34000)
    # --- RUN 3: narrow the n=200 floor (D-HIMDOM window was (32848,40000)) ---
    'f.33200':  case("33200"),
    'f.33400':  case("33400"),
    'f.33600':  case("33600"),
    'f.33800':  case("33800"),
    'f.33900':  case("33900"),
    # --- RUN 3: program-TEXT dependence, working readout (few LONG lines) ----
    # 8 REM lines x ~200 B ~= 1.6 KB of program text above TXTTAB:
    'g3.p34k':  casepad(8, "34000"),       # ERR7 iff floor rose past 34000
    'g3.p36k':  casepad(8, "36000"),       # ERR7 iff floor rose past 36000
    'g3.p38k':  casepad(8, "38000"),       # accept iff floor still < 38000
    'g3.p0_36k': casepad(0, "36000"),      # CONTROL: no pad -> accept
    # --- RUN 3: zerobas PRGEND for a small vs padded program (zb only) -------
    'x.pg0':    caseprgend(0),
    'x.pg8':    caseprgend(8),
    # exact PRGEND for the 5-line case() program (lines 10,20,30,40,900), the
    # one the floor rows f.* / l.* / d.* use -- to set MARGIN precisely.
    'x.pg5':    ["10 ONERRORGOTO900",
                 '20 PRINT"<A>";',
                 "30 CLEAR 200,33700",
                 '40 PRINT"<E";ERR;">":END',
                 '900 PRINT"<E";ERR;">":END',
                 PG],
    # narrow the reference floor to a tighter center
    'f.33650':  case("33650"),
    'f.33700':  case("33700"),
    'f.33750':  case("33750"),
}

BR = re.compile(r"\[([^\]]*)\]")
ERRF = re.compile(r"<E([^>]*)>")
NUM = re.compile(r"^[-0-9. ]*$")
ERRMSG = re.compile(r"(Missing operand|Syntax error|Illegal function call|"
                    r"Type mismatch|Overflow|Out of memory|Undefined line number|"
                    r"Division by zero|Redimensioned array|Subscript out of range|"
                    r"NEXT without FOR|RETURN without GOSUB|Out of DATA|"
                    r"String too long|Bad file mode|File not found)"
                    r"\s+in\s+(\d+)")


def face(cap):
    """`<ERR> SAME` or `<ERR> -><himem>`. BOTH halves are required: an ERR alone
    cannot say whether a refused value was written anyway, and a delta alone
    cannot say which error refused it."""
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    vals = [" ".join(m.group(1).split())
            for m in BR.finditer(txt) if NUM.match(m.group(1))]
    vals = [v for v in vals if v]
    # 🔴 THE FENCE IS ALSO IN THE SOURCE IT ECHOES. Round 2 of this probe read
    # every ERR as the literal '";ERR;"' -- the TYPED LINE `40 PRINT"<E";ERR;">"`
    # contains `<E";ERR;">`, which satisfies `<E([^>]*)>` perfectly. The older
    # probes survive the identical hazard with `[...]` only because they require
    # the captured span to be NUMERIC; I dropped that guard when I added a second
    # fence. Same requirement here, and take the FIRST numeric match, never the
    # first match. [[trapsvc-echo-fence]]
    err = None
    for m in ERRF.finditer(txt):
        if NUM.match(m.group(1)):
            err = " ".join(m.group(1).split()) or "?"
            break
    if err is None:
        m = ERRMSG.search(txt)
        if not m:
            return "<NO OUTPUT>"
        err = f"UNTRAPPED {m.group(1)} in {m.group(2)}"
    if len(vals) < 2:
        return "<NO HIMEM>"
    before, after = vals[0], vals[-1]
    return f"{err} " + ("SAME" if before == after else f"->{after}")


def main():
    only, sides, raw = None, ["vg8020", "cf3300", "zb"], False
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        elif a == "--raw":
            raw = True
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
            if raw and "<NO" in faces[s][l]:
                scr = "".join(caps[0] or [])
                keep = [ln.rstrip() for ln in scr.split("\n") if ln.strip()]
                print(f"      RAW: {keep[-8:]}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
        if len(refs) != 1:
            # ⚠️ NOT automatically an apparatus fault here: if the rule is
            # "<= this machine's RAM top", the two references SHOULD disagree,
            # and that disagreement is the finding.
            print(line + "   !! THE REFERENCES DISAGREE -- read the rule, not the row")
            continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED"); continue
        nmeas += 1
        if vals["zb"] not in refs:
            ndiff += 1; print(line + "   *** DIFF")
        else:
            print(line)
    print(f"\nROWS: {len(labels)} printed, {nmeas} scored -- {ndiff} DIFF")


if __name__ == "__main__":
    main()
