#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ASCIIDIGIT — is the ASCII-digit evaluator gap wider than `NAME`?

D-CRUNCHBYTES measured the mechanism on both machines: `AS` is stored as plain
ASCII (`41 53`) because it is not a keyword token, a numeric constant after it
survives the crunch as ASCII (`35` for `5`) on the CF-3300 TOO, and zerobas's
`eval` has no ASCII-digit factor path -- so it answers ERR 2 where the reference
evaluates the operand. `NAME` was simply where a row went looking first.

\U0001f3af THIS ASKS WHETHER THE CLASS IS WIDER, AND THE SOURCE SAYS WHERE TO LOOK.
Three verbs parse `AS` as verbatim ASCII: `FIELD` (basic/field.asm), `OPEN`
(basic/files.asm oo_parse_as_chan) and `NAME`. Of those, `OPEN`'s is the one where
a NUMBER can legally follow, because the `#` is OPTIONAL there -- the source says
so: `cp '#' / jr nz,oopac_num`. So `OPEN"TS.DAT"AS 1` is a supported form whose
channel number lands exactly where the gap is.

`FIELD`'s number comes BEFORE its `AS` (`FIELD #1, 20 AS A$`), so it is not in
this class -- included as a row rather than argued away, because "not in the
class" is a claim.

⚠️ ONE REFERENCE. These are Disk-BASIC verbs; a diskless VG-8020 cannot express
them, so the CF-3300 is the only oracle and the rows say so.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
_SRC = os.path.join(_REPO, "disk", "test720.dsk")
SIDES = {"cf3300": ("National_CF-3300", 14.0), "zb": (ZB, 8.0)}

CASES = [
    # \U0001f3af THE SUBJECT: `#` is optional after OPEN's ASCII `AS`, so the channel
    # number sits exactly where NAME's operand does.
    ("o.as1",   'OPEN"TS.DAT"AS 1',      "THE SUBJECT: a digit after OPEN's ASCII AS"),
    ("o.ashash", 'OPEN"TS.DAT"AS #1',    "CONTROL: the same open with `#` -- restarts the crunch"),
    ("o.asvar", 'C = 1 : OPEN"TS.DAT"AS C',
     "CONTROL: a VARIABLE in the same position, which NAME shows works"),
    # not in the class -- the number precedes the AS. A row, not an argument.
    ("f.field", 'OPEN"TS.DAT"AS #1 : FIELD #1, 20 AS A$',
     "FIELD's number comes BEFORE its AS: predicted NOT in the class"),
    ("n.as5",   'NAME"HI.TXT"AS 5',      "the known member, as the positive control"),
]


def program(stmt):
    return ['10 ON ERROR GOTO 90', f'20 {stmt}', '25 CLOSE',
            '30 PRINT "<0>" : END', '90 PRINT "<"; ERR; ">" : END']


def face(raw):
    m = [g for g in re.findall(r"<([^<>]*)>", "".join(raw or ""))
         if re.match(r"^[-0-9 ]+$", g)]
    return " ".join(m[-1].split()) if m else "<NO OUTPUT>"


def main() -> int:
    dsk = os.path.join(tempfile.mkdtemp(prefix="asciidigit-"), "test720.dsk")
    shutil.copyfile(_SRC, dsk)
    out = {}
    for side, (machine, boot) in SIDES.items():
        out[side] = {}
        for lab, stmt, _why in CASES:
            raw = omsx_repl.run_cases(
                machine, [("direct", ["NEW"] + program(stmt) + ["RUN"])],
                batch=False, reset=("", "SCREEN 0", "NEW"), boot=boot, step=6.0,
                run_gap=25.0, timeout=420.0, diska=dsk)[0] or ""
            out[side][lab] = face(raw)
            print(f"  ran {side:7s} {lab:9s} -> {out[side][lab]!r}", flush=True)

    w = max(len(l) for l, _, _ in CASES)
    print(f"\n  {'row':<{w}}  {'cf3300':>7} {'zb':>5}   statement")
    bad = []
    for lab, stmt, why in CASES:
        a, b = out["cf3300"][lab], out["zb"][lab]
        ok = a == b
        if not ok:
            bad.append(lab)
        print(f"  {lab:<{w}}  {a:>7} {b:>5}   {stmt:<40} {'ok' if ok else '\U0001f534 DIFF'}")
        print(f"  {'':<{w}}          {why}")
    print(f"\n  DIFF {len(bad)}/{len(CASES)}" + ("  " + " ".join(bad) if bad else ""))
    if "o.as1" in bad:
        print("  \U0001f534 THE CLASS IS WIDER THAN NAME. `OPEN ... AS <digit>` is a "
              "supported form (the `#` is optional in our own parser) and it hits "
              "the same ASCII-digit gap -- so the fix belongs in eval, not in a verb.")
    elif out["zb"]["o.as1"] == out["cf3300"]["o.as1"]:
        print("  \U0001f7e2 OPEN is NOT in the class. Something about its path differs "
              "from NAME's, and that difference is the next question -- the gap is "
              "real either way (D-CRUNCHBYTES) but narrower than predicted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
