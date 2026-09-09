#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NAMESURVIVE — WHICH `Syntax error` is `NAME"HI.TXT"AS 5`'s ERR 2?

THE QUESTION. `basic_probe_namegate.py` has eight operand shapes saying the same
thing: through NAME's SECOND `fname_expr` site a leading crunched numeric
constant answers ERR 2 where the CF-3300 answers 13 (or 11 for `1/0`), while a
variable, a `-`-led constant and a parenthesised one all answer correctly. Every
reading of that so far assumed the 2 comes from `els_tc_common` -- the
"re-drive found no operand" exit.

\U0001f534 BUT ERR 2 HAS A SECOND SUFFICIENT CAUSE ON THIS PATH, AND IT IS NOT THE
OPERAND AT ALL. If `str_eval` ACCEPTED the crunched constant instead of
declining, `do_name` would carry on -- `parse_disk_fcb`, the dirverb stamp, and
then a resume cursor pointing into the middle of the operand, which `exec_stmt`
reports as `Syntax error`. Same code, completely different defect, and the error
code alone cannot separate them [[two-rules-that-coincide-on-every-row-you-have]].

\U0001f3af THE SEPARATOR IS THE DISK, NOT THE SCREEN. If the statement got as far as
the stamp, HI.TXT has been RENAMED and no longer opens. If it faulted on the
operand, HI.TXT is untouched. So: run the statement, trap the error, then ask
whether HI.TXT still exists -- one program, one boot, two facts.

Rows pair each operand with its own survival check:
  * `s.const`  the failing shape (`AS 5`)
  * `s.var`    the WORKING shape (`AS A`) -- the control that says a clean
               operand fault leaves the file alone, so "still there" means
               something
  * `s.ctl`    no NAME at all -- the file is there because nothing touched it

⚠️ A COPY, NOT THE TRACKED IMAGE: this asks the machine to rename a real
directory entry, so it drives its own `tempfile.mkdtemp` copy of test720.dsk.
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

CASES = [
    ("s.const", 'NAME"HI.TXT"AS 5', "THE SUBJECT: the operand shape that answers 2"),
    ("s.var",   'NAME"HI.TXT"AS A', "CONTROL: the shape that answers 13 correctly"),
    ("s.ctl",   'REM',              "CONTROL: no NAME at all -- HI.TXT must survive"),
]


def program(stmt):
    """Run the statement, trap its ERR, then ask whether HI.TXT still opens.

    `E` is the statement's error (0 = none). `F` is 1 if HI.TXT still exists and
    0 if opening it errors -- a SECOND trapped error, which is why line 60 re-arms
    the handler and line 90 keeps its own marker.
    """
    return [
        '10 ON ERROR GOTO 900',
        '20 E = 0 : F = 0',
        f'30 {stmt}',
        '40 GOTO 60',
        '60 ON ERROR GOTO 910',
        '70 OPEN "HI.TXT" FOR INPUT AS #1 : CLOSE : F = 1',
        '90 PRINT "<"; E; F; ">" : END',
        '900 E = ERR : RESUME 60',
        '910 F = 0 : RESUME 90',
    ]


def face(raw):
    m = [g for g in re.findall(r"<([^<>]*)>", "".join(raw or ""))
         if re.match(r"^[-0-9 ]+$", g)]
    return " ".join(m[-1].split()) if m else "<NO OUTPUT>"


def main() -> int:
    dsk = os.path.join(tempfile.mkdtemp(prefix="namesurvive-"), "test720.dsk")
    shutil.copyfile(_SRC, dsk)
    out = {}
    for lab, stmt, _why in CASES:
        raw = omsx_repl.run_cases(
            ZB, [("direct", ["NEW"] + program(stmt) + ["RUN"])],
            batch=False, reset=("", "SCREEN 0", "NEW"), boot=8.0, step=6.0,
            run_gap=30.0, timeout=420.0, diska=dsk)[0] or ""
        out[lab] = face(raw)
        print(f"  ran {lab:8s} -> {out[lab]!r}", flush=True)

    print(f"\n  {'row':<8}  {'E F':>7}   statement")
    for lab, stmt, why in CASES:
        print(f"  {lab:<8}  {out[lab]:>7}   {stmt:<20} {why}")

    if any("<NO" in v for v in out.values()):
        print("\n  \U0001f534 A ROW HAS NO READING -- nothing is concluded.")
        return 2
    if out["s.ctl"].split()[-1] != "1" or out["s.var"].split()[-1] != "1":
        print("\n  \U0001f534 A CONTROL LOST THE FILE. Either the fixture is wrong or a "
              "clean operand fault is already renaming -- the subject row cannot "
              "be read until that is explained.")
        return 2

    survived = out["s.const"].split()[-1] == "1"
    print()
    if survived:
        print("  \U0001f7e2 HI.TXT SURVIVED. The statement never reached the stamp, so the "
              "ERR 2 IS the operand fault -- els_tc_common's 'no operand parsed' "
              "exit, exactly as assumed. The second cause is excluded.")
    else:
        print("  \U0001f534 HI.TXT IS GONE. `str_eval` ACCEPTED the crunched constant and "
              "the rename RAN; the ERR 2 is exec_stmt finding junk at a resume "
              "cursor left inside the operand. That is a different defect from "
              "the one eight rows have been characterising, and it is worse: the "
              "statement performs a disk write it should have refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
