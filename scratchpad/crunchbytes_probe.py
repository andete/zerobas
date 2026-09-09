#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CRUNCHBYTES — is the constant in `AS 5` stored the same way as the one in
`NAME 5 AS...`?

WHY. Eight rows say NAME's SECOND `fname_expr` site answers ERR 2 for a leading
crunched numeric constant and 13 for a variable, a `-`-led constant or a
parenthesised one. D-NAMESURVIVE excluded the alternative cause (the file
survives, so the statement really does fault on the operand). What is left is
either the crunch or `eval`'s first-factor path — and the crunch is the cheaper
of the two to ask, because the machine will simply show us the bytes.

🎯 THE COMPARISON IS THE POINT. `NAME 5 AS"X.DAT"` answers **13**, correctly,
through the SAME `fname_expr` — so if the `5` after `AS` is stored differently
from the `5` after `NAME`, the whole first-byte signature falls out of the
tokeniser and no evaluator reading is needed. If the bytes are identical, that is
what finally forces the difference into `eval`.

INSTRUMENT. Type the statement as line 10 but never run it: `RUN 20` starts at
the dumper, which walks the stored program from `TXTTAB` ($F676) and prints the
first 24 bytes of the line record — `[link:2][lineno:2][crunched tokens][00]`.

⚠️ THREE FENCES OF EIGHT BYTES, NOT ONE OF TWENTY-FOUR. A 48-character group
wraps the 40-column screen and a wrapped token splits — which is exactly how
`fcbname_scan` first reported `F866` as `'F8'` and `'66'`. Each group fits on one
row by construction [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
⚠️ And each byte is padded to two hex digits, so a group is fixed-width and a
missing byte cannot masquerade as a shorter number.
"""
from __future__ import annotations

import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
# \U0001f3af THE REFERENCE SIDE IS THE WHOLE POINT ONCE THE BYTES DIFFER. A dump of
# OUR crunch says what we do; only the CF-3300's own dump says whether it is
# wrong. Same program, same TXTTAB read -- PEEK is on both machines.
SIDES = {
    "zb":     (ZB, 8.0),
    "cf3300": ("National_CF-3300", 14.0),
}

CASES = [
    ("c.as5",  'NAME"HI.TXT"AS 5',  "THE SUBJECT: the constant that answers ERR 2"),
    ("c.old5", 'NAME 5 AS"X.DAT"',  "the SAME constant at the FIRST site, which answers 13"),
    ("c.asa",  'NAME"HI.TXT"AS A',  "the variable that answers 13 at the SECOND site"),
    ("c.asneg", 'NAME"HI.TXT"AS -5', "the `-`-led constant, which also answers 13"),
    # \U0001f3af PREDICTIONS, WRITTEN BEFORE THE RUN. If the model is "the tokeniser
    # stops crunching numeric constants after the string literal, and a TOKEN
    # restarts it", then:
    #   c.asparen  ->  `(` is ASCII 28, and the 5 behind it is CRUNCHED (16)
    #   c.printlit ->  the same thing happens with no NAME anywhere, so this is
    #                  about the LITERAL, not about NAME
    # A miss on either is worth more than the hits.
    ("c.asparen", 'NAME"HI.TXT"AS (5)', "PREDICTION: 28 16 29 -- a token restarts the crunch"),
    ("c.printlit", 'PRINT"X";5', "PREDICTION: is it the LITERAL, not NAME? 5 should be ASCII 35"),
]


def program(stmt):
    return [
        f'10 {stmt}',
        '20 T = PEEK(&HF676) + 256 * PEEK(&HF677)',
        '30 FOR G = 0 TO 2',
        '40 D$ = ""',
        '50 FOR I = 0 TO 7 : P = PEEK(T + G * 8 + I)',
        '60 D$ = D$ + RIGHT$("0" + HEX$(P), 2) : NEXT',
        '70 PRINT "<"; D$; ">"',
        '80 NEXT',
        '90 END',
    ]


def groups(raw):
    """Every 16-hex-digit fence, in order. A short one is a wrap and is dropped
    rather than silently concatenated."""
    return [g for g in re.findall(r"<([0-9A-F]{16})>", "".join(raw or ""))]


def main() -> int:
    out = {}
    side = sys.argv[1] if len(sys.argv) > 1 else "zb"
    machine, boot = SIDES[side]
    print(f"  side: {side} ({machine})")
    for lab, stmt, _why in CASES:
        raw = omsx_repl.run_cases(
            machine, [("direct", ["NEW"] + program(stmt) + ["RUN 20"])],
            batch=False, reset=("", "SCREEN 0", "NEW"), boot=boot, step=6.0,
            run_gap=25.0, timeout=420.0)[0] or ""
        g = groups(raw)
        out[lab] = "".join(g[:3]) if len(g) >= 3 else None
        print(f"  ran {lab:8s} -> {out[lab]!r}  ({len(g)} group(s))", flush=True)

    if any(v is None for v in out.values()):
        print("\n  \U0001f534 A ROW DID NOT PRODUCE THREE FULL GROUPS -- the dump wrapped "
              "or the program did not finish. Nothing is concluded.")
        return 2

    print()
    for lab, stmt, why in CASES:
        b = out[lab]
        pretty = " ".join(b[i:i + 2] for i in range(0, len(b), 2))
        print(f"  {lab:<8}  {stmt:<20}\n            {pretty}\n            {why}")

    print("\n  The record is [link:2][lineno:2][crunched tokens...][00].")
    print(f"  c.as5 vs c.old5 identical tail? "
          f"{'YES' if out['c.as5'][8:] == out['c.old5'][8:] else 'NO -- they differ'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
