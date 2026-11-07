# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: a DEF FN call evaluates EVERY actual before it binds any formal
(D-FNALIAS, docs/spec-deffn-alias.md §7), no emulator.

Programs run through run_prog (each statement via exec -> exec_stmt -> the
handler), the DEF FN tenant reached through the harness's sub-ROM bridge, CHPUT
captured. The expected faces are the VG-8020 / CF-3300 readings banked in
probes/basic/basic_probe_deffn.py (both references agree on every row here):

  o.alias       `FNA(5,P)` with P=3 at top level           503 (zb was 505)
  o.aliasnest   `FNA(9,X)` from inside FNB(X), X=3          903 (zb was 909)
  o.dupformal   `DEF FNA(X,X)=X : FNA(1,2)`                 2   (the last actual wins)
  o.dupformal3  `DEF FNA(X,Y,X)=X*10+Y : FNA(1,2,3)`        32
  o.str9        nine string temporaries as actuals          19  (D-FNSTR9: zb was ERR 16)
  o.tempend     three such calls of five in one expression  111 (zb was ERR 16)

plus the controls (no shared name) and a DEFINT row: an INT actual is DE, not
FAC, and the park must not clobber it (the first build of the park did:
o.alias read 2048003).
"""

import os
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402
import test_statements as T  # noqa: E402  (its build + run_prog_cap)

S9 = ",".join(f'"{i}"+""' for i in range(1, 10))
S5 = ",".join(f'"{i}"+""' for i in range(1, 6))

ROWS = [
    ("o.alias",        [(10, "DEF FNA(P,Q)=P*100+Q"), (20, "P=3"), (30, "PRINT FNA(5,P)")],
     b" 503 \r\n"),
    ("o.alias.ctl",    [(10, "DEF FNA(P,Q)=P*100+Q"), (30, "PRINT FNA(5,7)")],
     b" 507 \r\n"),
    ("o.aliasnest",    [(10, "DEF FNA(X,Q)=X*100+Q"), (20, "DEF FNB(X)=FNA(9,X)"),
                        (30, "PRINT FNB(3)")],
     b" 903 \r\n"),
    ("o.aliasnest.ctl", [(10, "DEF FNA(X,Q)=X*100+Q"), (20, "DEF FNB(X)=FNA(9,7)"),
                         (30, "PRINT FNB(3)")],
     b" 907 \r\n"),
    ("o.dupformal",    [(10, "DEF FNA(X,X)=X"), (30, "PRINT FNA(1,2)")], b" 2 \r\n"),
    ("o.dupformal3",   [(10, "DEF FNA(X,Y,X)=X*10+Y"), (30, "PRINT FNA(1,2,3)")],
     b" 32 \r\n"),
    ("defint alias",   [(5, "DEFINT A-Z"), (10, "DEF FNA(P,Q)=P*100+Q"), (20, "P=3"),
                        (30, "PRINT FNA(5,P)")],
     b" 503 \r\n"),
    ("o.str9",         [(10, "DEF FNA$(A$,B$,C$,D$,E$,F$,G$,H$,I$)=A$+I$"),
                        (30, f"X$=FNA$({S9}):PRINT X$")],
     b"19\r\n"),
    ("o.tempend",      [(10, "DEF FNA$(A$,B$,C$,D$,E$)=A$"),
                        (30, f"PRINT FNA$({S5})+FNA$({S5})+FNA$({S5})")],
     b"111\r\n"),
]


def machine():
    m = Machine(T.ROM, T.SYM, rom_base=T.BASIC_BASE)
    # an FN call slides the stack inside the tenant (fnf_save): the bridge must
    # hand back the tenant's SP, as CALSLT does (tests/msxtest.py)
    m.bridge_keeps_tenant_sp = True
    # FN_FEND as cold boot's clear_usrtab leaves it (tests/test_forfast.py F4)
    m.poke(m.sym["FN_FEND"], m.sym["FN_PAREA"] & 0xFF)
    # the string pool's cold-boot size (tests/test_str_compare.py's D-CLP stand-in:
    # run_prog's clear_vars does not set it, and a zero pool is Out of string space)
    m.poke_w(m.sym["POOLSIZE"], 4096)
    return m


def run():
    T.build()
    fails = 0
    for label, lines, want in ROWS:
        got = T.run_prog_cap(machine(), lines)
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r}"
              + ("" if ok else f"  want {want!r}"))
    return fails


if __name__ == "__main__":
    f = run()
    print("FAIL" if f else "PASS")
    sys.exit(1 if f else 0)
