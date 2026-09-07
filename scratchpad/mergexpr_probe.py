#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MERGEXPR — is `MERGE`'s filename a string EXPRESSION, or must it be a literal?

Found by READING, in the standing review tier. D-FNEXPR2/D-FILESIDE established
that a file verb's filename is a string EXPRESSION and that a `cp '"'` test is
"answering the wrong question" -- `FILES A$` listed the whole directory and only
then derailed. Nine verbs were converted and call `fname_expr`: BLOAD, LOAD,
FILES, OPEN, KILL, NAME (both halves), SAVE, BSAVE.

\U0001f3af `MERGE` WAS NOT. [`basic/files.asm:1913`](basic/files.asm:1913) still opens
with `cp '"' / jp nz,stmt_error` and goes straight to `parse_disk_fcb`, with no
`fname_expr` anywhere in `ex_merge`. So `MERGE A$` should be a Syntax error here.

## The rows separate PARSING from I/O by error code, so no fixture content is needed

Every row names a file that does NOT exist. That makes the two outcomes distinct:

    ERR 53  File not found   -> the filename was EVALUATED, then looked up
    ERR  2  Syntax error     -> the filename was never evaluated at all

  m.lit     MERGE"A:NOSUCH.BAS"          CONTROL: the literal form both sides support
  m.var     A$=...:MERGE A$              the variable form -- the subject
  m.concat  MERGE "A:"+"NOSUCH.BAS"      an expression that is not a bare variable
  k.var     A$=...:KILL A$               CONTROL on ZEROBAS's OWN expression path:
                                         KILL was converted, so this must read 53
                                         on both -- if it does not, `fname_expr` is
                                         broken generally and m.var says nothing
                                         about MERGE

\U0001f534 `m.lit` IS LOAD-BEARING TWICE. It pins that the file really is absent (so
53 is the right answer and not an accident of a stale fixture), and that MERGE's
literal path reaches the disk at all on both machines.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SRC = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
N = '"A:NOSUCH.BAS"'

CASES = [
    ("m.lit",    [f'20 MERGE{N}'],
     "CONTROL: the literal form -- must be ERR 53 (File not found) on both"),
    ("m.var",    [f'15 A$={N}', '20 MERGE A$'],
     "THE SUBJECT: a variable. 53 = evaluated; 2 = the quote test refused it"),
    ("m.concat", ['20 MERGE "A:"+"NOSUCH.BAS"'],
     "an expression that is not a bare variable -- same question"),
    # 🎯 THE TWO FACES A FIX MUST NOT BREAK. Converting MERGE to `fname_expr`
    # deletes its `cp '"'` gate, so whatever that gate was producing for a bare
    # verb and for a NON-STRING argument has to be reproduced by the expression
    # path instead. D-FILESIDE measured exactly these for FILES (`FILES 5` is
    # Type mismatch with ZERO entries listed) and they are the rows that told it
    # the conversion was complete rather than merely different.
    ("m.bare",   ['20 MERGE'],
     "bare MERGE, no argument at all -- the face the quote gate produces today"),
    ("m.colon",  ['20 MERGE:PRINT"x"'],
     "MERGE with a COLON, not end-of-line -- the second no-operand shape, and a "
     "fix that tests only for $00 would answer this one differently"),
    ("m.num",    ['20 MERGE 5'],
     "a NUMBER, not a string -- Type mismatch (13) if evaluated, Syntax (2) if refused"),
    ("k.var",    [f'15 A$={N}', '20 KILL A$'],
     "CONTROL on zerobas's OWN expression path: KILL was converted by D-FNEXPR, "
     "so 53 on both, or fname_expr is broken generally"),
]


def main() -> int:
    out = {}
    for label, body, note in CASES:
        row = {}
        for side, c in SIDES.items():
            dsk = os.path.join(tempfile.gettempdir(), f"zb_mrg_{label}_{side}.dsk")
            shutil.copy(SRC, dsk)
            p = ['10 ON ERROR GOTO 900'] + body + [
                '30 PRINT"ZQ";0;"QZ":END',
                '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", ["NEW"] + p + ["RUN"])], batch=False,
                reset=c["reset"], boot=c["boot"], step=5.0, run_gap=25.0,
                cap_gap=5.0, timeout=600.0, diska=dsk)[0] or "")
            v = [g for g in re.findall(r"ZQ\s*([0-9]+)\s*QZ", raw)
                 if not any(ch in g for ch in '"$;')]
            row[side] = int(v[-1]) if v else None
        out[label] = row
        f = {s: ("<none>" if row[s] is None else
                 ("no error" if row[s] == 0 else f"ERR {row[s]}")) for s in SIDES}
        print(f"  {label:9s} cf3300={f['cf3300']:>12s}  zb={f['zb']:>12s}   {note}",
              flush=True)

    lit, kv = out.get("m.lit", {}), out.get("k.var", {})
    if lit.get("cf3300") != 53 or lit.get("zb") != 53:
        print(f"\n\U0001f534 m.lit DID NOT READ 53 ON BOTH ({lit}) -- either the file "
              f"exists or MERGE's literal path does not reach the disk. No row "
              f"below it is a reading.")
        return 2
    if kv.get("cf3300") != 53 or kv.get("zb") != 53:
        print(f"\n\U0001f534 THE k.var CONTROL FAILED ({kv}) -- zerobas's fname_expr "
              f"path is broken for KILL too, so m.var says nothing about MERGE "
              f"specifically.")
        return 2
    dis = [k for k, v in out.items() if v["cf3300"] != v["zb"]]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
