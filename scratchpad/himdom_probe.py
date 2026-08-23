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
