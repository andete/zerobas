#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MATHACC — `ATN` and `EXP` scored against TRUTH, not against each other.

TODO.md filed `ATN(1)`, `EXP(-100)` and `EXP(100)` as differing "in the LAST
DIGIT only ... a mathpack rounding question". Two points do not say which
implementation is better, and "last digit" is a description of the PRINTOUT, not
of the error.

🎯 SO THIS SCORES EVERY ROW AGAINST A 60-DIGIT ORACLE and reports the signed
error in UNITS OF THE LAST PLACE of the 14-significant-digit result MSX BASIC
prints. A differential says the two disagree; only a truth column says who is
wrong [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

The oracle is `decimal` at prec 60: Euler's arctangent series (verified against
a 50-digit pi/4 literal) and Decimal.exp(). No third-party module.
"""
import os, sys
from decimal import Decimal, getcontext, Context, ROUND_HALF_UP
getcontext().prec = 60
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402


PI = Decimal("3.141592653589793238462643383279502884197169399375105820974945")


def _atan_series(x: Decimal) -> Decimal:
    """Euler's series. Converges fast only while x is SMALL -- see atan()."""
    one = Decimal(1)
    z = x*x/(one + x*x)
    term = s = one
    for n in range(1, 20000):
        term *= Decimal(2*n) / Decimal(2*n + 1) * z
        s += term
        if abs(term) < Decimal(10) ** -55:
            return x/(one + x*x) * s
    # 🔴 REFUSE, NEVER RETURN THE TRUNCATED SUM. The first cut looped to 5000 and
    # returned whatever it had: for ATN(100) that is z = 0.9999, nowhere near
    # converged, and it produced 1.0623664808539 -- a PLAUSIBLE arctangent, which
    # the table then printed in a column headed "correctly rounded" while all
    # three machines agreed on the true 1.5607966601082. The oracle was the only
    # wrong party and it was the one grading
    # [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
    raise ArithmeticError(f"atan series did not converge for x={x}")


def atan(x: Decimal) -> Decimal:
    """Range-reduced: |x| > 1 goes through atan(x) = sign*pi/2 - atan(1/x), so
    the series is only ever asked for |x| <= 1 where it converges quickly."""
    if x < 0:
        return -atan(-x)
    if x > 1:
        return PI/2 - _atan_series(Decimal(1)/x)
    return _atan_series(x)


def sig14(d: Decimal) -> Decimal:
    return Context(prec=14, rounding=ROUND_HALF_UP).create_decimal(d)


# 🔬 WIDE ENOUGH TO TEST ONE-SIDEDNESS. On the first 12 arguments zerobas was
# never LOWER than the references -- on 4 it was exactly +1 ulp in MAGNITUDE and
# on 8 identical. A one-sided error points at the FINAL ROUNDING, not at the
# polynomial, so it is worth more arguments than a differential needs.
ATN_ARGS = ["0.05", "0.1", "0.2", "0.25", "0.3", "0.4", "0.5", "0.6", "0.7",
            "0.75", "0.8", "0.9", "1", "1.25", "1.5", "1.75", "2", "3", "5",
            "10", "50", "100", "-1", "-0.5", "-0.75", "-2"]
EXP_ARGS = ["1", "2", "0.5", "-1", "10", "-10", "50", "-50", "100", "-100"]

CASES, ORDER, TRUTH = {}, [], {}
def add(lab, expr, truth):
    CASES[lab] = ([], expr); ORDER.append(lab); TRUTH[lab] = truth

for a in ATN_ARGS:
    add(f"atn({a})", f"ATN({a})", atan(Decimal(a)))
for a in EXP_ARGS:
    add(f"exp({a})", f"EXP({a})", Decimal(a).exp())
# 🟢 CONTROLS: values every implementation gets exactly right. If these show a
# non-zero ulp error the PARSER is wrong, not the mathpack.
add("ctl.atn0", "ATN(0)", Decimal(0))
add("ctl.exp0", "EXP(0)", Decimal(1))


def parse(s: str) -> Decimal | None:
    t = (s or "").strip().replace("E", "e")
    if not t or "ERR" in t or "<" in t:
        return None
    if t.startswith("."):
        t = "0" + t
    if t.startswith("-."):
        t = "-0" + t[1:]
    try:
        return Decimal(t)
    except Exception:
        return None


def ulps(got: Decimal | None, truth: Decimal) -> str:
    """Signed error in units of the last printed place. `None` -> '-'."""
    if got is None:
        return "-"
    if truth == 0:
        return "0" if got == 0 else "!=0"
    exact = sig14(truth)
    # the last place of a 14-significant-digit decimal
    ulp = Decimal(10) ** (exact.adjusted() - 13)
    return f"{(got - truth) / ulp:+.1f}"


def main() -> int:
    sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
    D.CASES.update(CASES)
    res = {s: D.run_side(s, ORDER) for s in sides}
    w = max(len(l) for l in ORDER)
    print(f"{'row':<{w}}  {'correctly rounded':>21}  "
          + "  ".join(f"{s + ' (ulp)':>28}" for s in sides))
    worse = {s: 0 for s in sides}
    exact = {s: 0 for s in sides}
    for lab in ORDER:
        t = TRUTH[lab]
        cells = []
        for s in sides:
            g = parse(str(res[s].get(lab)))
            u = ulps(g, t)
            cells.append(f"{str(res[s].get(lab))[:20]:>20} {u:>7}")
            if u not in ("-", "+0.0", "0"):
                try:
                    if abs(float(u)) >= 0.5:
                        worse[s] += 1
                    else:
                        exact[s] += 1
                except ValueError:
                    pass
            else:
                exact[s] += 1
        print(f"{lab:<{w}}  {str(sig14(t)):>21}  " + "  ".join(cells))
    print()
    for s in sides:
        print(f"  {s:<8} rows >= 0.5 ulp from truth: {worse[s]} / {len(ORDER)}")
    print("\nA differential says the two disagree; the ulp column says WHO IS "
          "WRONG. Read that column, not the DIFF count.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
