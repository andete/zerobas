#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kmkcv_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/kmkcv_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kconv_model as C  # noqa: E402
import kmath_model as K  # noqa: E402
import kmkcv_model as M  # noqa: E402


def with_conv(fn, model):
    """MK*$'s rule with another conversion in place of CINT / CSNG / CDBL"""
    def check(c):
        saved = M.CONV[fn]
        M.CONV[fn] = model
        try:
            return M.outcome_ok(c)
        finally:
            M.CONV[fn] = saved
    return check


def cv_with(fn, alt):
    def check(c):
        if c.src != "DCV":
            return M.outcome_ok(c)
        n, src = M.NB[fn], c.bytes
        if alt == "pad":                 # a short string padded with zero bytes instead of an error
            w = M.rec(s=src, vt=n, res=(src + bytes(n))[:n])
        elif alt == "last":              # the LAST n bytes, not the first
            w = M.cv_value(fn, src[-n:] if len(src) >= n else src, src)
        elif alt == "exact":             # a string of exactly n bytes, else error 5
            w = M.cv_value(fn, src, src) if len(src) == n else M.rec(e1=5, s=src, e2=5)
        else:                            # "canon": an exponent-0 single / double made a clean zero
            w = M.cv_value(fn, src, src)
            if w["res"] is not None and n > 2 and w["res"][0] & 0x7F == 0:
                w["res"] = bytes(n)
        return (c.e1, c.sl, c.sb, c.e2, c.vt, c.res) == (w["e1"], w["sl"], w["sb"], w["e2"], w["vt"], w["res"])
    return check


def nodisk_type_first(c):
    """without Disk BASIC a wrong-type argument is error 13 before the 5 -- zerobas's"""
    if c.src == "FX" and c.why in ("a string as the argument", "a number as the argument"):
        return c.e1 == 13
    return M.outcome_ok(c)


def zero_let(c):
    """an exponent-0 single stored in R as 8 zero bytes -- D-ZEROLET"""
    if c.vt == 4 and c.res is not None and c.res[0] & 0x7F == 0 and c.e1 == 0:
        return c.rbytes == bytes(8)
    return M.assigned(c)


CONTROLS = {
    "MKI$": [("R-MKI-BYTES", "the number rounded half away from zero (not CINT's truncation)",
              with_conv("MKI$", lambda ty, b: C.m_cint(ty, b, how="round"))),
             ("R-MKI-NODISK", "without Disk BASIC the argument's type checked first (13) -- zerobas's", nodisk_type_first)],
    "MKS$": [("R-MKS-BYTES", "a double's digits beyond the 6th dropped (not rounded)",
              with_conv("MKS$", lambda ty, b: C.m_csng(ty, b, how="trunc"))),
             ("R-MKS-NODISK", "without Disk BASIC the argument's type checked first (13) -- zerobas's", nodisk_type_first)],
    "MKD$": [("R-MKD-BYTES", "every number's bytes as a double's -- an integer's two bytes widened, not converted",
              with_conv("MKD$", lambda ty, b: ("num", 8, b + bytes(8 - len(b))))),
             ("R-MKD-NODISK", "without Disk BASIC the argument's type checked first (13) -- zerobas's", nodisk_type_first)],
    "CVI": [("R-CVI-BYTES", "a short string padded with zero bytes (no error)", cv_with("CVI", "pad")),
            ("R-CVI-BYTES", "the last 2 bytes, not the first", cv_with("CVI", "last")),
            ("R-CVI-BYTES", "exactly 2 bytes required", cv_with("CVI", "exact")),
            ("R-CVI-NODISK", "without Disk BASIC the argument's type checked first (13) -- zerobas's", nodisk_type_first)],
    "CVS": [("R-CVS-BYTES", "a short string padded with zero bytes (no error)", cv_with("CVS", "pad")),
            ("R-CVS-BYTES", "an exponent-0 single made a clean zero", cv_with("CVS", "canon")),
            ("R-CVS-BYTES", "exactly 4 bytes required", cv_with("CVS", "exact")),
            ("R-CVS-ASSIGN", "an exponent-0 single stored in R as 8 zero bytes -- D-ZEROLET", zero_let)],
    "CVD": [("R-CVD-BYTES", "a short string padded with zero bytes (no error)", cv_with("CVD", "pad")),
            ("R-CVD-BYTES", "exactly 8 bytes required", cv_with("CVD", "exact")),
            ("R-CVD-NODISK", "without Disk BASIC the argument's type checked first (13) -- zerobas's", nodisk_type_first)],
}


def main():
    rc = 0
    for fn, ctl in CONTROLS.items():
        cs = M.load(fn)["ref"]
        rules = {r.id: r for r in M.rules(fn)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:14s} {what[:74]:74s} FALSE on {len(false):4d} of {len(sel):<4d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
