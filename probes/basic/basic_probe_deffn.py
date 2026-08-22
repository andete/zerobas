#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""DEF FN / FN — the measured surface of the last missing MSX1 reserved word.

`make kwsweep` reports MISSING=1 and it is `deffn`: on a charter of FAITHFUL
FULL MSX1 BASIC this is the only genuinely missing reserved word. This probe is
the gate that says so in rows instead of in prose, and it is RED BY DESIGN until
the verb ships.

  docs/deffn-scout-2026-08-22.md    what the reference STORES (the crunch)
  docs/deffn-design-2026-08-22.md   what the reference DOES (this row set)

WHERE THE `WANT` COLUMN COMES FROM. Every entry was READ OFF BOTH REFERENCES
(Philips VG-8020 and National CF-3300), boot-per-case, in six rounds recorded in
`scratchpad/deffn_round5.out` .. `deffn_round10.out` plus the scout's own
round 3. 🔴 **THE TABLE WAS GENERATED FROM THOSE LOGS, NOT TRANSCRIBED** — 82
rows retyped by hand is exactly how a PREDICTION ends up in the result column
[[a-prediction-copied-into-the-result-column]] — and the generator refused any
row the two references did not agree on, so `WANT` contains no unscored reading.

⚠️ THREE CLASSES OF ROW, AND THEY ARE NOT INTERCHANGEABLE:

  * `ctl`  POSITIVE CONTROLS — eight rows containing NO `DEF FN` at all
           (`X+1`, `PEEK(VARPTR(X))`, `DEF USR`, a direct-mode `LET`). They are
           green on zerobas TODAY and must stay green: they are what says a red
           subject row is about the verb and not about the apparatus. `--gate`
           fails on a control divergence and only on a control divergence, so
           this probe can be run in CI while the verb is still missing.
  * `addr` OWN-DESIGN, CHARACTERIZATION ONLY — five rows whose value is a RAM
           ADDRESS. The reference's shadow parameter cell reads $F6EB and its
           variables live wherever its own TXTTAB puts them; zerobas's RAM map is
           its own (PROVENANCE.md, the same disposition as USR's calling
           convention). Gating the NUMBER would gate a layout choice, so what is
           gated is the layout-INDEPENDENT claim these rows exist to make:
           `o.sameaddr` must be NON-ZERO (the formal is not the variable) and
           `z.addr2`/`z.addr2i` must be EQUAL (the shadow does not move with
           nesting). See `PREDICATE` below.
  * `gate` everything else — the verb's actual surface, 69 rows.

🔴 TWO SUBJECT ROWS ARE A SILENT WRONG ANSWER TODAY, WHICH IS WHY THEY ARE HERE.
`FNZ(1)` on an undefined name, and a `DEF` on a later unexecuted line, are
`Undefined user function` on both references and read **`0`** on zerobas — parsed
as an ordinary subscripted array reference. This project ranks a silent wrong
answer worse than the refusal beside it, and ERR 18 already ships
(`err_msgtab` entry 18, `sub/errmsg.asm` `em_undef_fn`).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                  # noqa: E402
import probe_report                                               # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

# --- the eight rows with no DEF FN in them ---------------------------------
# 🟢 Each is an ordinary expression driven through the IDENTICAL fixture as the
# subject rows, so a fixture fault reddens a control before it reddens a
# subject. `o.varptr.ctl` / `o.realcell.ctl` in particular exercise the
# VARPTR+PEEK machinery the two sharpest subject rows depend on.
CONTROLS = {"b.ctl", "o.ctl", "o.ctl2", "d.ctl", "o.varptr.ctl",
            "o.realcell.ctl", "d.defusr", "d.let"}

# --- the five address-valued rows, and the claim each really makes ---------
ADDR = {"z.addr", "z.addr2", "z.addr2i", "z.addr.ctl", "o.sameaddr"}
CASES = {
    'b.ctl'             : (['X=5'], 'X+1'),
    'b.forward'         : (['GOTO 60', 'DEF FNA(X)=X+1'], 'FNA(2)'),
    'b.nested'          : (['DEF FNA(X)=X+1', 'DEF FNB(X)=FNA(X)*2'], 'FNB(3)'),
    'b.noarg'           : (['DEF FNA=7'], 'FNA'),
    'b.param'           : (['X=5:DEF FNA(X)=X+1', 'Y=FNA(2)'], 'Y;X'),
    'b.paramnew'        : (['DEF FNA(Q)=Q+1', 'Y=FNA(7)'], 'Y;Q'),
    'b.recurse'         : (['DEF FNA(X)=FNA(X)'], 'FNA(1)'),
    'b.redef'           : (['DEF FNA(X)=X+1', 'DEF FNA(X)=X+2'], 'FNA(1)'),
    'b.str'             : (['DEF FNA$(X$)=X$+"!"'], 'FNA$("hi")'),
    'b.two'             : (['DEF FNA(X,Y)=X+Y'], 'FNA(2,3)'),
    'b.undef'           : ([], 'FNZ(1)'),
    'o.actualfirst'     : (['X=5:DEF FNA(X)=X*10'], 'FNA(X+1)'),
    'o.argnoarg'        : (['DEF FNA=7'], 'FNA(1)'),
    'o.aryformal'       : (['DIM B(5)', 'DEF FNA(B(1))=B(1)+1'], 'FNA(2)'),
    'o.badname'         : (['DEF FN1(X)'], '"OK"'),
    'o.barecall'        : (['DEF FNA(X)=X+1'], 'FNA'),
    'o.clearwipe.ctl'   : (['DEF FNA(X)=X+1'], 'FNA(2)'),
    'o.clearwipe3'      : (['DEF FNA(X)=X+1', 'CLEAR'], 'FNA(2)'),
    'o.ctl'             : (['X=5'], 'X+1'),
    'o.ctl2'            : (['X=5'], 'X+1'),
    'o.defint'          : (['DEFINT A-Z', 'DEF FNA(X)=X/2'], 'FNA(5)'),
    'o.defint.ctl'      : (['DEF FNA(X)=X/2'], 'FNA(5)'),
    'o.defintbang'      : (['DEFINT A-Z', 'DEF FNA!(X)=X/2'], 'FNA!(5)'),
    'o.defstr'          : (['DEFSTR A-Z', 'DEF FNA(X)=X+"!"'], 'FNA("hi")'),
    'o.dynaddr'         : (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNB(Y)=PEEK(P)', 'DEF FNA(X)=FNB(0)'], 'FNA(2)'),
    'o.dynorder'        : (['X=5', 'DEF FNA(X)=FNB(0)', 'DEF FNB(Y)=X'], 'FNA(2)'),
    'o.dynscope'        : (['X=5', 'DEF FNB(Y)=X', 'DEF FNA(X)=FNB(0)'], 'FNA(2)'),
    'o.dynself'         : (['X=5', 'DEF FNB(Y)=X', 'DEF FNA(X)=FNB(0)+X*100'], 'FNA(2)'),
    'o.errrestore'      : (['X=5:DEF FNA(X)=X/0', 'ON ERROR GOTO 800', 'Y=FNA(2)'], 'X;E', ['800 E=ERR:RESUME 60']),
    'o.fnbang'          : (['DEF FNA!(X)=X/2'], 'FNA!(5)'),
    'o.fnpct'           : (['DEF FNA%(X)=X/2'], 'FNA%(5)'),
    'o.global'          : (['Y=3:DEF FNA(X)=X+Y'], 'FNA(2)'),
    'o.ifnot'           : (['IF 0 THEN DEF FNA(X)=X+1'], 'FNA(2)'),
    'o.ifthen'          : (['IF 1 THEN DEF FNA(X)=X+1'], 'FNA(2)'),
    'o.lazybody'        : (['DEF FNA(X)=X+*2'], '"OK"'),
    'o.lazydiv'         : (['DEF FNA(X)=X/0'], '"OK"'),
    'o.namespace'       : (['A=9:DEF FNA(X)=X+1', 'Y=FNA(2)'], 'A;Y'),
    'o.nestsame'        : (['DEF FNA(X)=X', 'DEF FNB(X)=FNA(X+1)+X'], 'FNB(3)'),
    'o.noeq'            : (['DEF FNA(X) X+1'], '"OK"'),
    'o.numstr'          : (['DEF FNA$(X$)=X$+"!"'], 'FNA$(1)'),
    'o.outer.ctl'       : (['X=5', 'DEF FNA(X)=0+X'], 'FNA(2)'),
    'o.outerabs'        : (['X=5', 'DEF FNA(X)=ABS(0)+X'], 'FNA(2)'),
    'o.outerafter'      : (['X=5', 'DEF FNB(Y)=Y', 'DEF FNA(X)=FNB(0)+X'], 'FNA(2)'),
    'o.outerbefore'     : (['X=5', 'DEF FNB(Y)=Y', 'DEF FNA(X)=X+FNB(0)'], 'FNA(2)'),
    'o.outernoarg'      : (['X=5', 'DEF FNB=1', 'DEF FNA(X)=FNB+X'], 'FNA(2)'),
    'o.p10'             : (['DEF FNA(A,B,C,D,E,F,G,H,I,J)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1)'),
    'o.p11'             : (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1,2)'),
    'o.p12'             : (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K,L)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1,2,3)'),
    'o.p16'             : (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1,2,3,4,5,6,7)'),
    'o.p3'              : (['DEF FNA(A,B,C)=A'], 'FNA(1,2,3)'),
    'o.p5'              : (['DEF FNA(A,B,C,D,E)=A'], 'FNA(1,2,3,4,5)'),
    'o.p8'              : (['DEF FNA(A,B,C,D,E,F,G,H)=A'], 'FNA(1,2,3,4,5,6,7,8)'),
    'o.p9'              : (['DEF FNA(A,B,C,D,E,F,G,H,I)=A'], 'FNA(1,2,3,4,5,6,7,8,9)'),
    'o.quotedcolon'     : (['DEF FNA$(X$)=X$+":Q"'], 'FNA$("a")'),
    'o.realcell'        : (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNA(X)=PEEK(P)'], 'FNA(2)'),
    'o.realcell.ctl'    : (['DEFINT A-Z', 'X=5:P=VARPTR(X)'], 'PEEK(P)'),
    'o.runtwice'        : (['DEF FNA(X)=X+1', 'Y=FNA(2)'], 'Y'),
    'o.sameaddr'        : (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNA(X)=VARPTR(X)-P'], 'FNA(2)'),
    'o.stmtcolon'       : (['DEF FNA(X)=X+1:B=9'], 'FNA(2);B'),
    'o.strnum'          : (['X=5:DEF FNA(X)=X+1'], 'FNA("hi")'),
    'o.strnumx'         : (['X=5:DEF FNA(X)=X+1', 'ON ERROR GOTO 800', 'Y=FNA("hi")'], 'X;E', ['800 E=ERR:RESUME 60']),
    'o.suffn'           : (['DEF FNA%(X)=X+1'], 'FNA%(2)'),
    'o.sufformal'       : (['DEF FNA(X%)=X%+1'], 'FNA(2)'),
    'o.toofew'          : (['DEF FNA(X,Y)=X+Y'], 'FNA(1)'),
    'o.toomany'         : (['DEF FNA(X)=X+1'], 'FNA(1,2)'),
    'o.twocalls'        : (['DEF FNA(X)=X+1', 'Y=FNA(2)+FNA(3)'], 'Y'),
    'o.twofault'        : (['DEF FN(X'], '"OK"'),
    'o.undefarg'        : ([], 'FNZ(1,2)'),
    'o.varptr'          : (['DEFINT A-Z', 'X=5:DEF FNA(X)=PEEK(VARPTR(X))'], 'FNA(2)'),
    'o.varptr.ctl'      : (['DEFINT A-Z', 'X=5'], 'PEEK(VARPTR(X))'),
    'z.addr'            : (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)'], 'FNA(2)'),
    'z.addr.ctl'        : (['DEFINT A-Z', 'X=5'], 'VARPTR(X)'),
    'z.addr2'           : (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)', 'DEF FNB(X)=FNA(0)*0+VARPTR(X)'], 'FNB(2)'),
    'z.addr2i'          : (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)', 'DEF FNB(X)=FNA(0)'], 'FNB(2)'),
    'z.p10def'          : (['DEF FNA(A,B,C,D,E,F,G,H,I,J)=A'], '"OK"'),
}

DIRECT = {
    'd.ctl'             : ['X=5', 'CLS:PRINT"[";X+1;"]"'],
    'd.def'             : ['DEF FNA(X)=X+1', 'CLS:PRINT"[";FNA(2);"]"'],
    'd.defonly'         : ['CLS:DEF FNA(X)=X+1:PRINT"[OK]"'],
    'd.defrun'          : ['DEF FNA(X)=X+1', '10 CLS:PRINT"[";FNA(2);"]"', 'RUN'],
    'd.defusr'          : ['CLS:DEF USR=&HC000:PRINT"[OK]"'],
    'd.let'             : ['CLS:A=1:PRINT"[OK]"'],
    'd.sameline'        : ['CLS:DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"'],
}

WANT = {
    'b.ctl'             : '6',   # scout-round3
    'b.forward'         : 'ERR 18 AT 60',   # scout-round3
    'b.nested'          : '8',   # scout-round3
    'b.noarg'           : '7',   # scout-round3
    'b.param'           : '3 5',   # scout-round3
    'b.paramnew'        : '8 0',   # scout-round3
    'b.recurse'         : 'ERR 7 AT 60',   # scout-round3
    'b.redef'           : '3',   # scout-round3
    'b.str'             : 'hi!',   # scout-round3
    'b.two'             : '5',   # scout-round3
    'b.undef'           : 'ERR 18 AT 60',   # scout-round3
    'd.ctl'             : '6',   # round9
    'd.def'             : '<Undefined user function>',   # round8
    'd.defonly'         : '<Illegal direct>',   # round8
    'd.defrun'          : '<Undefined user function>',   # round8
    'd.defusr'          : 'OK',   # round9
    'd.let'             : 'OK',   # round9
    'd.sameline'        : '<Illegal direct>',   # round8
    'o.actualfirst'     : '60',   # round5
    'o.argnoarg'        : '7 1',   # round5
    'o.aryformal'       : 'ERR 2 AT 60',   # round5
    'o.badname'         : 'ERR 2 AT 20',   # round5
    'o.barecall'        : 'ERR 2 AT 60',   # round5
    'o.clearwipe.ctl'   : '3',   # round6
    'o.clearwipe3'      : '<Undefined user function>',   # round8
    'o.ctl'             : '6',   # round10
    'o.ctl2'            : '6',   # round9
    'o.defint'          : '2',   # round5
    'o.defint.ctl'      : '2.5',   # round5
    'o.defintbang'      : '2.5',   # round6
    'o.defstr'          : 'hi!',   # round5
    'o.dynaddr'         : '5',   # round9
    'o.dynorder'        : '5',   # round8
    'o.dynscope'        : '5',   # round6
    'o.dynself'         : '205',   # round8
    'o.errrestore'      : '5 11',   # round5
    'o.fnbang'          : '2.5',   # round6
    'o.fnpct'           : '2',   # round6
    'o.global'          : '5',   # round6
    'o.ifnot'           : 'ERR 18 AT 60',   # round5
    'o.ifthen'          : '3',   # round5
    'o.lazybody'        : 'OK',   # round5
    'o.lazydiv'         : 'OK',   # round5
    'o.namespace'       : '9 3',   # round6
    'o.nestsame'        : '7',   # round5
    'o.noeq'            : 'OK',   # round5
    'o.numstr'          : 'ERR 13 AT 60',   # round5
    'o.outer.ctl'       : '2',   # round7
    'o.outerabs'        : '2',   # round7
    'o.outerafter'      : '2',   # round7
    'o.outerbefore'     : '2',   # round7
    'o.outernoarg'      : '3',   # round7
    'o.p10'             : 'ERR 5 AT 60',   # round6
    'o.p11'             : 'ERR 5 AT 60',   # round6
    'o.p12'             : 'ERR 5 AT 60',   # round5
    'o.p16'             : 'ERR 5 AT 60',   # round5
    'o.p3'              : '1',   # round5
    'o.p5'              : '1',   # round5
    'o.p8'              : '1',   # round5
    'o.p9'              : '1',   # round6
    'o.quotedcolon'     : 'a:Q',   # round7
    'o.realcell'        : '5',   # round9
    'o.realcell.ctl'    : '5',   # round9
    'o.runtwice'        : '3',   # round7
    'o.sameaddr'        : '30327',   # round9
    'o.stmtcolon'       : '3 9',   # round7
    'o.strnum'          : 'ERR 13 AT 60',   # round5
    'o.strnumx'         : '5 13',   # round5
    'o.suffn'           : '3',   # round5
    'o.sufformal'       : '3',   # round5
    'o.toofew'          : 'ERR 2 AT 60',   # round5
    'o.toomany'         : 'ERR 2 AT 60',   # round5
    'o.twocalls'        : '7',   # round8
    'o.twofault'        : 'ERR 2 AT 20',   # round5
    'o.undefarg'        : 'ERR 18 AT 60',   # round5
    'o.varptr'          : '2',   # round8
    'o.varptr.ctl'      : '5',   # round8
    'z.addr'            : '-2325',   # round10
    'z.addr.ctl'        : '-32679',   # round10
    'z.addr2'           : '-2325',   # round10
    'z.addr2i'          : '-2325',   # round10
    'z.p10def'          : 'OK',   # round10
}

# --- what an `addr` row actually claims, independent of any RAM map --------
# 🎯 A NUMBER THAT IS A LAYOUT CHOICE CANNOT BE A GATE, BUT THE FACT IT WAS
# MEASURED TO ESTABLISH STILL CAN. Each entry is (readable claim, predicate over
# the side's own faces), evaluated on ONE side at a time -- so it holds on
# zerobas for zerobas's addresses and on a reference for its own.
# 🔴 EACH ENTRY NAMES THE ROWS ITS PREDICATE READS, AND EVERY ONE OF THEM MUST
# BE A NUMBER BEFORE THE PREDICATE IS SCORED AT ALL. The first version did not,
# and on today's tree -- where every DEF FN row reads `ERR 2 AT 30` -- two of the
# three came back **PASS**: `'ERR 2 AT 30' == 'ERR 2 AT 30'` satisfies "the
# shadow does not move with nesting", and `!=` satisfies the other. A gate that
# is GREEN WHILE MEASURING NOTHING is the exact shape this tree keeps finding
# [[gate-can-be-green-while-measuring-nothing]], and here it would have signed
# off the two sharpest claims in the whole design against a machine that cannot
# express either. Unreadable inputs now score `....`, never PASS.
PREDICATE = {
    # the formal is NOT the program's variable: taking VARPTR of the name inside
    # the body and subtracting the address taken outside must not be 0
    "o.sameaddr": ("VARPTR(formal) differs from VARPTR(variable)",
                   ("o.sameaddr",),
                   lambda f: _num(f["o.sameaddr"]) != 0.0),
    # the shadow does not move with nesting: the address read one level deeper
    # is the SAME address
    "z.addr2":    ("the shadow cell does not move with nesting",
                   ("z.addr2", "z.addr2i"),
                   lambda f: _num(f["z.addr2"]) == _num(f["z.addr2i"])),
    # ...and it is not where the ordinary variable lives
    "z.addr":     ("the shadow is not the variable's own cell",
                   ("z.addr", "z.addr.ctl"),
                   lambda f: _num(f["z.addr"]) != _num(f["z.addr.ctl"])),
}


def _num(face):
    try:
        return float(face)
    except (TypeError, ValueError):
        return None


BR = re.compile(r"\[([^\]]*)\]")
# 🔴 NO `^` ANCHOR, AND THAT IS A FIX, NOT A STYLE CHOICE. omsx_repl returns the
# 24 screen rows CONCATENATED WITH NO NEWLINE, so an `^`-anchored, re.M message
# regex can only ever match at offset 0 -- an UNTRAPPED error message is never in
# row 0 and was therefore INVISIBLE. Three rows across the design rounds read
# `<NO OUTPUT>` on BOTH references while the raw screen plainly said `Undefined
# user function in 60`, and two of them were within one step of being written up
# as "DEF FN in direct mode produces nothing"
# [[readout-blind-to-its-own-subject]]. The set below is what err_msgtab prints.
ERRRE = re.compile(r"(Undefined user function|Illegal function call|"
                   r"Subscript out of range|Redimensioned array|Illegal direct|"
                   r"Out of memory|Type mismatch|Out of string space|"
                   r"String too long|Division by zero|Overflow|"
                   r"[A-Z][A-Za-z' ]{2,25} error)")


def face(cap):
    """One reading. `<NO OUTPUT>` is a MISSING MEASUREMENT, not a value."""
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    m = BR.search(txt)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERRRE.search(txt)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def build(label):
    """The delivered lines for one row: a stored program, or direct commands."""
    if label in DIRECT:
        return list(DIRECT[label]), False
    spec = CASES[label]
    lines, expr = spec[0], spec[1]
    extra = spec[2] if len(spec) > 2 else []
    if len(lines) > 4:
        raise SystemExit(f"{label}: {len(lines)} setup lines collide with line 60")
    body = ["10 ON ERROR GOTO 900"]
    body += [f"{20 + 10 * k} {ln}" for k, ln in enumerate(lines)]
    # 🔴 THE EXPRESSION GOES STRAIGHT INTO THE PRINT, and the CLS in front of it
    # is load-bearing twice over. Without the CLS the line's own ECHO carries the
    # `[...]` fence and every row returns its own SOURCE TEXT -- eleven rows
    # "agreed" that way in the scout's round 2. And an earlier shape assigned
    # `60 V=<expr>` first, which made the HARNESS LINE a syntax error on any
    # multi-value expression (`Y;X`), so both references reported ERR 2 AT 60 and
    # the row read as a DEF FN divergence.
    body += [f'60 CLS:PRINT"[";{expr};"]":END']
    body += list(extra)
    body += ['900 CLS:PRINT"[ERR";ERR;"AT";ERL;"]":END']
    return body + ["RUN"], True


def run_side(side, labels):
    cfg = SIDES[side]
    out = {}
    for label in labels:
        lines, _stored = build(label)
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + lines)],
            batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
        out[label] = face(caps[0])
    return out


def klass(label):
    if label in CONTROLS:
        return "ctl"
    if label in ADDR:
        return "addr"
    return "gate"



# ===========================================================================
def _score(faces_zb):
    """The report's three classifiers, over a PLANTED zb face table.

    Factored out of main() so `--selftest` exercises the SAME code the real run
    does, rather than a re-implementation that could agree with a broken one.
    """
    labels = sorted(WANT)
    blanket, seen = set(), {}
    for l in labels:
        if klass(l) == "gate":
            seen.setdefault(faces_zb[l], []).append(l)
    blanket = {f for f, ls in seen.items()
               if sum(1 for l in ls if faces_zb[l] != WANT[l]) >= 5}
    out = dict(ctl=[], gate=[], silent=[], vacuous=[], blank=[])
    for l in labels:
        k, z, r = klass(l), faces_zb[l], WANT[l]
        if z in ("<NO OUTPUT>", "<NO CAPTURE>"):
            out["blank"].append(l)
        elif z == r:
            if k == "gate" and z in blanket:
                out["vacuous"].append(l)
        else:
            out[("ctl" if k == "ctl" else "gate")].append(l)
            if (k == "gate" and _num(z) is not None
                    and (r.startswith("<") or r.startswith("ERR "))):
                out["silent"].append(l)
    return out


def selftest() -> int:
    """🔬 MUTATION-TEST THE GATE ITSELF, because a battery is the DENOMINATOR.

    This probe's whole subject is missing, so 67 of 69 rows are red no matter
    what the instrument does -- which means a REAL RUN CANNOT DEMONSTRATE THAT
    IT WOULD DETECT ANYTHING. The classifiers and the address claims are
    therefore exercised against PLANTED face tables here: an implementation
    that is right, several that are subtly wrong, and the state the tree is
    actually in. Every case names what it must produce, so a classifier that
    stops working fails a case instead of quietly agreeing.
    """
    labels = sorted(WANT)
    perfect = dict(WANT)                                   # the verb, correct
    today = {l: ("0" if l in ("b.undef", "b.forward", "o.undefarg", "o.ifnot",
                              "d.def", "d.defrun")
                 else "ERR 2 AT 20") for l in labels}
    for l in CONTROLS:                                     # controls pass today
        today[l] = WANT[l]
    cases = []
    cases.append(("a correct implementation", perfect,
                  lambda r: not r["gate"] and not r["ctl"] and not r["vacuous"]))
    cases.append(("today's tree", today,
                  lambda r: (not r["ctl"] and len(r["silent"]) == 6
                             and set(r["vacuous"]) == {"o.twofault", "o.badname"})))
    # one wrong rule at a time, each on top of a correct implementation
    muts = {
        "binds through the variable table": {"o.realcell": "2", "o.dynself": "202",
                                             "o.dynscope": "2", "o.dynaddr": "2"},
        "10 formals accepted":              {"o.p10": "1"},
        "DEF FN parses its body":           {"o.lazybody": "ERR 2 AT 20"},
        "direct mode allowed":              {"d.defonly": "OK", "d.sameline": "3"},
        "CLEAR does not erase":             {"o.clearwipe3": "3"},
        "undefined name reads 0":           {"b.undef": "0"},
        "result not coerced to FN type":    {"o.fnpct": "2.5"},
        "shadow moves with nesting":        {"z.addr2": "-99"},
    }
    for name, delta in muts.items():
        f = dict(perfect); f.update(delta)
        cases.append((f"MUTANT: {name}", f,
                      lambda r, d=delta: bool(set(r["gate"]) & set(d))
                                         or bool(set(r["vacuous"]) & set(d))))
    # 🎯 THE CASE THAT PINS THE BLANKET RULE. A mostly-correct tree with ONE
    # wrong row must report NO vacuous rows -- the first rule reported 4 to 11.
    near = dict(perfect); near["o.toomany"] = "ERR 5 AT 60"
    cases.append(("one wrong row, nothing vacuous", near,
                  lambda r: r["gate"] == ["o.toomany"] and not r["vacuous"]))
    # a blank must never be scored as a divergence
    blankf = dict(perfect); blankf["o.global"] = "<NO OUTPUT>"
    cases.append(("a blank reading", blankf,
                  lambda r: r["blank"] == ["o.global"] and "o.global" not in r["gate"]))
    # ...and a broken CONTROL must be caught even when every subject row is right
    ctlf = dict(perfect); ctlf["o.ctl"] = "99"
    cases.append(("a broken positive control", ctlf, lambda r: r["ctl"] == ["o.ctl"]))

    W = max(len(n) for n, _, _ in cases)
    bad = 0
    for name, faces_zb, ok in cases:
        r = _score(faces_zb)
        held = ok(r)
        bad += 0 if held else 1
        print(probe_report.row("PASS" if held else "FAIL", name, W,
                               {"gate": len(r["gate"]), "ctl": len(r["ctl"]),
                                "silent": len(r["silent"]),
                                "vacuous": len(r["vacuous"]),
                                "blank": len(r["blank"])}))
    # the address claims, on the three planted sets the design doc records
    pf = {"o.sameaddr": "30327", "z.addr2": "-2325", "z.addr2i": "-2325",
          "z.addr": "-2325", "z.addr.ctl": "-32679"}
    wf = {"o.sameaddr": "0", "z.addr2": "-2325", "z.addr2i": "-99",
          "z.addr": "-2325", "z.addr.ctl": "-2325"}
    ef = {k: "ERR 2 AT 30" for k in pf}
    for nm, f, want in (("claims: reference-like", pf, "PASS"),
                        ("claims: planted-wrong", wf, "FAIL"),
                        ("claims: error faces", ef, "....")):
        got = set()
        for lbl, (_claim, reads, fn) in PREDICATE.items():
            if any(_num(f.get(r)) is None for r in reads):
                got.add("....")
            else:
                got.add("PASS" if fn(f) else "FAIL")
        held = got == {want}
        bad += 0 if held else 1
        print(probe_report.row("PASS" if held else "FAIL", nm, W,
                               {"verdicts": sorted(got), "want": want}))
    n = len(cases) + 3
    print(probe_report.footer(n, n,
                              f"{n - bad} of {n} instrument cases held"))
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero if a POSITIVE CONTROL diverges (the "
                         "subject rows are a recorded baseline until DEF FN "
                         "ships; see --strict)")
    ap.add_argument("--strict", action="store_true",
                    help="also require every `gate` row to match the reference "
                         "-- the switch that flips when the verb lands")
    ap.add_argument("--sides", default="zb",
                    help="comma list of vg8020,cf3300,zb (default zb: the WANT "
                         "column is already measured, re-measure only to "
                         "re-verify it)")
    ap.add_argument("--only", default="")
    ap.add_argument("--selftest", action="store_true",
                    help="MUTATION-TEST THE INSTRUMENT on planted face tables "
                         "instead of booting anything -- see selftest()")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    labels = sorted(WANT)
    if args.only:
        pats = args.only.split(",")
        labels = [l for l in labels if any(p in l for p in pats)]
    sides = [s for s in args.sides.split(",") if s in SIDES]
    if not sides:
        raise SystemExit("no known side selected")

    # 🔴 FLOOR THE DENOMINATOR. An emptied row set prints a clean 0/0 and exits 0
    # -- the shape that has fooled this tree's own self-tests
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    # ⚠️ THE REFUSAL PATH PRINTS ROWS, DELIBERATELY. `check_report_shape.py`
    # only calls a probe IN CONTRACT -- and therefore only CHECKS its grammar --
    # when it prints report rows on the exit-2 path AND on another one. A
    # refusal that prints prose instead is a probe whose layout nothing gates.
    W0 = max((len(l) for l in labels), default=12)
    bad = None
    # 🔴 AN EMPTY SELECTION IS A REFUSAL, NOT A CRASH -- and this arm exists
    # because the calibration run found it: `--only nosuchrow` reached the
    # `max()` below over an empty sequence and died with a traceback and NO
    # REPORT AT ALL, which a runner reads as a probe that printed nothing.
    if not labels:
        bad = f"--only {args.only!r} selected no row"
    elif not args.only and len(labels) < 60:
        bad = f"{len(labels)} rows, expected the full measured set"
    elif not args.only and not (CONTROLS <= set(labels)):
        bad = "a positive control is missing from the row set"
    if bad:
        print(probe_report.row("....", "denominator", W0,
                               {"rows": len(labels),
                                "controls": len(CONTROLS & set(labels))},
                               f"  REFUSING: {bad}"))
        print(probe_report.footer(1, 0, "row set unusable -- NOT MEASURED"))
        return 2

    faces = {s: run_side(s, labels) for s in sides}
    W = max(len(l) for l in labels)

    # 🔴 THE BLANKET FACE. zerobas answers `Syntax error` to EVERY `DEF FN`
    # line, so any subject row whose WANT happens to be a syntax error at the
    # DEF's own line agrees today WITHOUT the tree knowing anything about DEF FN
    # -- and would keep agreeing through an implementation that got the rule
    # wrong. Two rows (`o.twofault`, `o.badname`, both wanting `ERR 2 AT 20`)
    # are in exactly that position. Rather than leave it to the reader to
    # notice, the report says which greens are worthless
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. A face shared with
    # 5+ rows that DIVERGE is a blanket, not an answer.
    blanket = set()
    if "zb" in faces:
        seen = {}
        for l in labels:
            if klass(l) == "gate":
                seen.setdefault(faces["zb"][l], []).append(l)
        # 🔴 IT IS THE DIVERGING ROWS THAT HAVE TO BE ≥5, NOT THE SHARING ONES,
        # AND THE SELFTEST IS WHAT SAID SO. The first rule was "≥5 rows share
        # this face AND at least one of them diverges", which is right for
        # today's tree and WRONG for a mostly-working one: five rows may
        # legitimately share `ERR 2 AT 60`, and one of them going red then
        # branded the other four vacuous. Every planted mutant reported 4-11
        # bogus vacuous rows before this line changed.
        blanket = {f for f, ls in seen.items()
                   if sum(1 for l in ls if faces["zb"][l] != WANT[l]) >= 5}

    def _silent(label):
        """zb hands back a VALUE where the reference REFUSES -- the class this
        project ranks worse than the refusal beside it."""
        if "zb" not in faces or klass(label) != "gate":
            return False
        z, r = faces["zb"][label], WANT[label]
        return (_num(z) is not None
                and (r.startswith("<") or r.startswith("ERR ")))
    printed = scored = 0
    ctl_bad, gate_bad, blank, silent, vacuous = [], [], [], [], []
    for label in labels:
        k = klass(label)
        vals = {"ref": WANT[label]}
        vals.update({s: faces[s][label] for s in sides})
        note = ""
        if any(v in ("<NO OUTPUT>", "<NO CAPTURE>") for v in vals.values()):
            # 🔴 A BLANK IS NOT A DIVERGENCE. Scoring one as `DIFF` would
            # report a missing measurement as a finding.
            tag, note = "....", "  (NOT MEASURED -- blank reading)"
            blank.append(label)
        elif k == "addr":
            tag, note = "--", "  (own-design RAM layout; see PREDICATE)"
        elif "zb" in faces and faces["zb"][label] == WANT[label]:
            tag = "PASS" if k == "ctl" else "ok"
            if faces["zb"][label] in blanket:
                note = ("  🔴 AGREES WITH THE BLANKET " 
                        f"{faces['zb'][label]!r} this tree gives every DEF FN "
                        "line -- NOT EVIDENCE")
                vacuous.append(label)
            scored += 1
        else:
            tag = "FAIL" if k == "ctl" else "DIFF"
            if _silent(label):
                note = "  🔴 SILENT WRONG ANSWER (a value where the reference refuses)"
                silent.append(label)
            scored += 1
            (ctl_bad if k == "ctl" else gate_bad).append(label)
        print(probe_report.row(tag, label, W, vals, note))
        printed += 1

    # the address rows are scored on their CLAIM, one side at a time
    pred_bad = []
    if not args.only:
        for s in sides:
            for lbl, (claim, reads, fn) in PREDICATE.items():
                vals = {f"{s}:{r}": faces[s].get(r, "<absent>") for r in reads}
                unreadable = [r for r in reads if _num(faces[s].get(r)) is None]
                if unreadable:
                    # NOT a failure and emphatically NOT a pass: the rows this
                    # claim is made of did not produce numbers on this side.
                    print(probe_report.row(
                        "....", f"claim:{lbl}", W, vals,
                        f"  NOT MEASURED -- {','.join(unreadable)} is not a "
                        f"number here ({claim})"))
                    printed += 1
                    continue
                held = fn(faces[s])
                if not held:
                    pred_bad.append(f"{s}:{lbl}")
                print(probe_report.row("PASS" if held else "FAIL",
                                       f"claim:{lbl}", W, vals, f"  {claim}"))
                printed += 1
                scored += 1

    why = (f"{len(gate_bad)} of {sum(1 for l in labels if klass(l)=='gate')} "
           f"DEF FN rows still divergent; "
           f"{len(ctl_bad)} of {len(CONTROLS)} controls failed")
    print(probe_report.footer(printed, scored, why))
    if blank:
        print(f"NOT MEASURED: {', '.join(blank)}")
    if silent:
        print(f"SILENT WRONG ANSWERS ({len(silent)}): {', '.join(silent)}")
    if vacuous:
        print(f"GREEN BUT VACUOUS ({len(vacuous)}): {', '.join(vacuous)} "
              f"-- these agree with the blanket syntax error, not with a rule")
    if gate_bad:
        print("DEF FN not implemented (expected until the verb ships): "
              + ", ".join(gate_bad))

    if args.gate and (ctl_bad or pred_bad):
        print("CONTROL FAILURE — the apparatus is not measuring; "
              "a red subject row above proves nothing")
        return 1
    if args.strict and gate_bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
