#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kconv_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/kconv_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kconv_model as M  # noqa: E402
import kmath_model as K  # noqa: E402


def is_(fn, **alt):
    model = lambda ty, b: M.MODELS[fn](ty, b, **alt)    # noqa: E731
    return lambda c: M.outcome(c, M.want(c, model))


def csng_by_value(ty, b):
    """a double shortened to 6 digits by its VALUE rounded half to even, an exact float conversion's way"""
    if ty != "D" or b[0] & 0x7F == 0:
        return M.m_csng(ty, b)
    return M.m_csng(ty, b, how="even")


def cdbl_binary(ty, b):
    """a single widened through binary floating point (the digits a binary single would add)"""
    if ty != "S" or b[0] & 0x7F == 0:
        return M.m_cdbl(ty, b)
    import struct
    try:
        v = struct.unpack("f", struct.pack("f", float(K.value(b))))[0]
    except OverflowError:                       # beyond a binary single's range: no such widening
        return M.m_cdbl(ty, b)
    if v == 0:
        return M.m_cdbl(ty, b)
    s = f"{abs(v):.14e}"
    d, e = s.split("e")
    ds = (d.replace(".", "") + "0" * 14)[:14]
    return "num", 8, K._pack((b[0] & 0x80) | (64 + int(e) + 1), ds)


def assign_zero_let(c):
    """R after an exponent-0 single result is 8 zero bytes (zerobas's D-ZEROLET), not the single's own bytes"""
    if c.vt == 4 and c.res is not None and c.res[0] & 0x7F == 0:
        return c.rbytes == bytes(8)
    return K.assigned(c)


def assign_short(c):
    """R holds the result cut to a single's 6 digits, then widened"""
    if c.vt == 8 and c.res is not None and c.res[0] & 0x7F:
        return c.rbytes == c.res[:4] + bytes(4)
    return K.assigned(c)


CONTROLS = {
    "CINT": [("R-CINT-TRUNC", "rounded half away from zero", is_("CINT", how="round")),
             ("R-CINT-TRUNC", "floor (as INT)", is_("CINT", how="floor")),
             ("R-CINT-TRUNC+R-CINT-RANGE", "the range tested on the value BEFORE truncation (32767.4 an Overflow)",
              is_("CINT", how="precheck"))],
    "CSNG": [("R-CSNG-ROUND", "the 7th digit and beyond dropped (truncation)", is_("CSNG", how="trunc")),
             ("R-CSNG-ROUND", "rounded half to even", lambda c: M.outcome(c, M.want(c, csng_by_value))),
             ("R-CSNG-OVER", "no carry into the exponent (truncation)", is_("CSNG", how="trunc")),
             ("R-CSNG-ODD", "an exponent-0 single made a clean zero -- zerobas's", is_("CSNG", odd="zero"))],
    "CDBL": [("R-CDBL-WIDEN", "a single widened through binary floating point", lambda c: M.outcome(c, M.want(c, cdbl_binary))),
             ("R-CDBL-ODD", "an exponent-0 single made a clean zero -- zerobas's", is_("CDBL", odd="zero")),
             ("R-CDBL-ASSIGN", "R given only the result's first 6 digits (stored through a single)", assign_short)],
}
CONTROLS["CSNG"].append(("R-CSNG-ASSIGN", "an exponent-0 single stored in R as 8 zero bytes -- D-ZEROLET",
                         assign_zero_let))


def main():
    rc = 0
    for fn, ctl in CONTROLS.items():
        cs = M.load(fn)["ref"]
        rules = {r.id: r for r in M.rules(fn)}
        for rid, what, check in ctl:
            sel = [c for c in cs if any(rules[r].select(c) for r in rid.split("+"))]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:16s} {what[:70]:70s} FALSE on {len(false):4d} of {len(sel):<4d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
