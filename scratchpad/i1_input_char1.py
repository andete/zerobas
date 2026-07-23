#!/usr/bin/env python3
"""I1 characterization: STICK / STRIG / PAD / PDL on the VG-8020 reference.

Round 1 -- crunch tokens (stored_line capture).
Round 2 -- values + error domain, unplugged (tagged prints, ON ERROR trap).
"""
from __future__ import annotations
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676

TOKEN_CASES = [
    ("stick",  ["10 A=STICK(0)"]),
    ("strig",  ["10 A=STRIG(0)"]),
    ("pdl",    ["10 A=PDL(1)"]),
    ("pad",    ["10 A=PAD(0)"]),
    ("mixed",  ['10 A=STICK(0)+STRIG(1)']),
]

def tokens() -> None:
    print("=== ROUND 1: crunch tokens (VG-8020) ===")
    specs = [("direct", ls) for _, ls in TOKEN_CASES]
    raws = omsx_repl.run_cases(REF, specs, batch=False,
                               capture=("stored_line", TXTTAB))
    for (label, lines), raw in zip(TOKEN_CASES, raws):
        print(f"  {label:8} {lines[0]:28} -> {raw}")


def _tag(raw, tag):
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(re.escape(tag) + r"[ \d\-\.]*", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def case(body, tag):
    # omsx_repl numbers stored lines itself (10,20,30,40) -- bodies only.
    return ["ON ERROR GOTO 40", body, "END", f'PRINT"{tag}";"E";ERR:END']


VALUE_CASES = [
    # label, statement printing tag+values, tag
    ("stick_0_8",  'PRINT"A";STICK(0);STICK(1);STICK(2)', "A"),
    ("stick_neg",  'PRINT"B";STICK(-1)', "B"),
    ("stick_3",    'PRINT"C";STICK(3)', "C"),
    ("stick_frac", 'PRINT"D";STICK(.9);STICK(1.4);STICK(2.6)', "D"),
    ("strig_all",  'PRINT"F";STRIG(0);STRIG(1);STRIG(2);STRIG(3);STRIG(4)', "F"),
    ("strig_5",    'PRINT"G";STRIG(5)', "G"),
    ("strig_neg",  'PRINT"H";STRIG(-1)', "H"),
    ("pdl_1_4",    'PRINT"I";PDL(1);PDL(2);PDL(3);PDL(4)', "I"),
    ("pdl_0",      'PRINT"J";PDL(0)', "J"),
    ("pdl_12_13",  'PRINT"K";PDL(12)', "K"),
    ("pdl_13",     'PRINT"L";PDL(13)', "L"),
    ("pad_0_3",    'PRINT"M";PAD(0);PAD(1);PAD(2);PAD(3)', "M"),
    ("pad_4_7",    'PRINT"N";PAD(4);PAD(5);PAD(6);PAD(7)', "N"),
    ("pad_8",      'PRINT"O";PAD(8)', "O"),
    ("pad_neg",    'PRINT"P";PAD(-1)', "P"),
    ("bare_stick", 'PRINT"Q";STICK', "Q"),
    ("stick_noparen", 'PRINT"R";STICK 0', "R"),
    ("stick_str",  'PRINT"S";STICK("X")', "S"),
    ("stick_expr", 'A=1:PRINT"T";STICK(A*2)', "T"),
    ("stick_big",  'PRINT"U";STICK(40000)', "U"),
]

ROUND3_CASES = [
    # the arg-coercion discriminators: round-half-up vs truncate-toward-zero
    ("pdl_0p6",    'PRINT"A";PDL(0.6)', "A"),      # round->1 (255) | trunc->0 (ERR5)
    ("pdl_12p6",   'PRINT"B";PDL(12.6)', "B"),     # round->13 (ERR5) | trunc->12 (255)
    ("strig_4p9",  'PRINT"C";STRIG(4.9)', "C"),    # round->5 (ERR5) | trunc->4 (0)
    ("stick_m0p4", 'PRINT"D";STICK(-0.4)', "D"),   # trunc->0 (0) | floor->-1 (ERR5)
    ("stick_m0p6", 'PRINT"E";STICK(-0.6)', "E"),   # round->-1 (ERR5) | trunc->0 (0)
    ("pad_7p5",    'PRINT"F";PAD(7.5)', "F"),      # round->8 (ERR5) | trunc->7 (0)
    # int boundaries
    ("stick_32767",'PRINT"G";STICK(32767)', "G"),
    ("stick_32768",'PRINT"H";STICK(32768)', "H"),
    ("stick_m32768",'PRINT"I";STICK(-32768)', "I"),
    # grammar
    ("unclosed",   'PRINT"J";STICK(0', "J"),
    ("empty_arg",  'PRINT"K";STICK()', "K"),
    ("stmt_pos",   'STICK(0):PRINT"L";1', "L"),
    ("let_bare",   'A=STICK:PRINT"M";A', "M"),
    ("two_args",   'PRINT"N";STICK(0,1)', "N"),
    ("strig_on",   'STRIG(1)ON:PRINT"O";1', "O"),
    ("nested",     'PRINT"P";STICK(STRIG(0)+1)', "P"),
]


def values(cases=None, title="ROUND 2: values + errors, UNPLUGGED") -> None:
    cases = cases or VALUE_CASES
    print(f"=== {title} (VG-8020) ===")
    specs = [("stored", case(body, tag)) for _, body, tag in cases]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    for (label, body, tag), raw in zip(cases, raws):
        flat = " ".join("".join(raw or "").split())
        print(f"  {label:14} {body:44} -> {_tag(raw, tag)!r}   | {flat[-90:]!r}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "tokens"):
        tokens()
    if which in ("all", "round3"):
        values(ROUND3_CASES, "ROUND 3: arg coercion + grammar")
    if which in ("all", "values"):
        values()
