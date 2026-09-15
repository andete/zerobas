#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWDRAWX: does `DRAW`'s `X<var>;` or `=<var>;` reach anything, on EITHER machine?

`drawkw_j`/`drawkw_k` were written the way docs/spec-basic-graphics-g6.md §1 names
these -- `DRAW"XA$;"` with `A$="R5"`, and `DRAW"R=A;"` -- and BOTH MACHINES DREW
NOTHING AND NEITHER RAISED. A row agreeing on an absence both sides produce says
nothing about either, so the rows were dropped and the question moved here.

  c0  THE CONTROL: a plain `DRAW"R5"` in the same shape. It must read 15. If it
      does not, the apparatus is what is wrong and nothing else here is a verdict.
  c1  `X<var>;` as the spec spells it.
  c2  the same WITHOUT the `;` -- §147 says that is ERR 5. If it does not raise,
      the family is not being parsed at all and the finding is bigger than a
      spelling.
  c3  a TWO-character variable name, in case the scan takes one letter.
  c4  `=<var>;` as a length operand.
  c5  the same without the `;` -- ERR 5 again per §147.
  c6  `=<var>;` as a COLOUR operand: A=7, so a working substitution reads 7 where
      an ignored one reads 15. A second call site for the same lookup.
  c7  the whole command string from a string EXPRESSION (`DRAW A$`) -- not one of
      the ten forms, but it says whether variable access from DRAW works at all.

Readings: `< n >` is POINT(14,10) -- 15 drawn, 4 background, 7 the c6 colour --
and `<E n >` is a trapped error code.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402


def prog(setup: str, draw: str) -> list[str]:
    """Seven numbered lines; `setup` seeds the variables, `draw` is the statement."""
    return ["ON ERROR GOTO 80",
            "SCREEN2:" + setup,
            "PSET(10,10),15",
            draw,
            "B=POINT(14,10)",
            'SCREEN0:PRINT"<";B;">"',
            "END",
            'B=POINT(14,10):SCREEN0:PRINT"<E";ERR;">":END']


SET = 'A$="R5":AB$="R5":A=7:L=5'
CASES = [
    ("c0_control",  prog(SET, 'DRAW"R5"')),
    ("c1_x_semi",   prog(SET, 'DRAW"XA$;"')),
    ("c2_x_nosemi", prog(SET, 'DRAW"XA$"')),
    ("c3_x_two",    prog(SET, 'DRAW"XAB$;"')),
    ("c4_eq_semi",  prog(SET, 'DRAW"R=L;"')),
    ("c5_eq_nosemi", prog(SET, 'DRAW"R=L"')),
    ("c6_eq_colour", prog(SET, 'DRAW"C=A;R5"')),
    ("c7_str_expr", prog(SET, 'DRAW A$')),
]


def main() -> int:
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        print("===", mach)
        specs = [("stored", lines) for _, lines in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=6.0)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("RUN")
            print(f"  {name:13} {(txt[i:] if i >= 0 else txt)[:70]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
