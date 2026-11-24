#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of knum_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/knum_controls.py      (exit 1 when a control finds no case against it)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knum  # noqa: E402
import knum_model as M  # noqa: E402


def sn(c):
    return c.src == "SN"


def rx(c):
    return c.src == "RX"


def vl(c):
    return c.src == "VL"


def fx(*whys):
    return lambda c: M.fx_by(c, *whys)


def radix_with(argf):
    def f(c):
        e, u = argf(knum.argval(c))
        return ("err", e) if e else ("str", M.digits_in(u, M.BASES[c.fn]))
    return f


def radix_round(v):
    """CINT-style: rounded half away from zero everywhere, the range tested after rounding"""
    t = int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)
    return (6, None) if t < -32768 or t > 65535 else (0, t & 0xFFFF)


def radix_test_first(v):
    """the range tested on the number itself, before truncation (-32768.5 an error)"""
    return (6, None) if v < -32768 else M.radix_arg(v)


CONTROLS = [
    # (keyword, rule it shadows, what it alters, select, altered model)
    ("STR$", "R-STR-INT/FIXED/EXP", "PRINT's trailing space kept", sn, lambda c: ("str", M.fmt(c, trail=" "))),
    ("STR$", "R-STR-INT/FIXED/EXP", "no leading space for a non-negative number", sn,
     lambda c: ("str", M.fmt(c).lstrip(b" "))),
    ("STR$", "R-STR-FIXED/EXP", "written in full only up to a single's 6 digits (E <= 6)", sn,
     lambda c: ("str", M.fmt(c, hi=6))),
    ("STR$", "R-STR-FIXED/EXP", "written in full down to .001 (E >= -2)", sn, lambda c: ("str", M.fmt(c, lo=-2))),
    ("STR$", "R-STR-EXP", "D as a double's exponent letter", lambda c: sn(c) and c.ty == "D",
     lambda c: ("str", M.fmt(c, sep="D" if c.ty == "D" else "E"))),
    ("HEX$", "R-HEX-HIGH", "truncation toward zero above 32767 too", rx, lambda c: M.m_radix(c, "trunc")),
    ("HEX$", "R-HEX-LOW/HIGH/RANGE", "rounding (CINT) everywhere", rx, radix_with(radix_round)),
    ("HEX$", "R-HEX-LOW/RANGE", "the range tested before truncation", rx, radix_with(radix_test_first)),
    ("OCT$", "R-OCT-HIGH", "truncation toward zero above 32767 too", rx, lambda c: M.m_radix(c, "trunc")),
    ("BIN$", "R-BIN-HIGH", "truncation toward zero above 32767 too", rx, lambda c: M.m_radix(c, "trunc")),
    ("VAL", "R-VAL-SPACE", "only spaces skipped -- zerobas's rule", vl, lambda c: M.m_val(c, ws=b" ")),
    ("VAL", "R-VAL-PREFIX", "nothing allowed between & and its letter -- zerobas's rule", vl,
     lambda c: M.m_val(c, amp_gap=False)),
    ("VAL", "R-VAL-RANGE", "any exponent outside 1..127 an overflow, no wrap -- zerobas's rule", vl,
     lambda c: M.m_val(c, wrap=False)),
    ("VAL", "R-VAL-RANGE", "an exponent of 0 always a clean zero (zerobas: after E / a point, not after D)", vl,
     lambda c: M.m_val(c, keep_digits=False)),
    ("VAL", "R-VAL-RANGE", "the E exponent added inside the 8 bits too (wraps)", vl, lambda c: M.m_val(c, wrap_e=True)),
    ("VAL", "R-VAL-NUMBER", "rounding half to even at the 15th digit", vl, lambda c: M.m_val(c, half="even")),
    ("VAL", "R-VAL-NUMBER", "truncation at the 15th digit", vl, lambda c: M.m_val(c, half="trunc")),
    ("VAL", "R-VAL-NUMBER", "a 16th (guard) digit kept, rounded twice", vl, lambda c: M.m_val(c, guard=True)),
    ("VAL", "R-VAL-NUMBER", "rounding half toward +infinity (not the magnitude half up)", vl,
     lambda c: M.m_val(c, half="ceil")),
    ("VAL", "R-VAL-SUFFIX", "%'s range tested before truncation", vl, lambda c: M.m_val(c, pct_first=True)),
    ("VAL", "R-VAL-SUFFIX", "% an overflow from a magnitude of 32768 (-32768% too) -- zerobas's rule", vl,
     lambda c: ("err", 6) if b"%" in c.s and M.m_val(c) == ("num", M.encode(-32768)) else M.m_val(c)),
    ("VAL", "R-VAL-END", "VAL reads on into the byte after its string", lambda c: vl(c) and c.s and
     M.m_val_bytes(c.s) != M.m_val_bytes(c.s + c.arg[:1]), lambda c: M.m_val_bytes(c.s + c.arg[:1])),
    ("VAL", "R-VAL-ARGERR", "VAL's own error 13 for any bad string argument", fx("an error inside a string argument"),
     lambda c: ("err", 13)),
    ("STR$", "R-STR-ZERO", "an exponent byte 0 with digit bytes written as the digits at 10^-65",
     lambda c: fx("a single with exponent byte 0, digit bytes 10 00 00")(c) or (sn(c) and c.id == "KNM SN S 1E-65"),
     lambda c: ("str", b" 1E-65")),
    ("STR$", "R-STR-SIGNZERO", "an exponent byte 80 taken as zero (the sign bit ignored)",
     fx("a single with exponent byte 80, digit bytes 10 00 00"), lambda c: ("str", b" 0")),
    ("STR$", "R-STR-NOSPACE", "the result made without string space (no error)", fx("string space full"),
     lambda c: ("str", b" 5")),
    ("HEX$", "R-HEX-NOSPACE", "the result made without string space (no error)", fx("string space full"),
     lambda c: ("str", b"FF")),
    ("OCT$", "R-OCT-NOSPACE", "the result made without string space (no error)", fx("string space full"),
     lambda c: ("str", b"377")),
    ("BIN$", "R-BIN-NOSPACE", "the result made without string space (no error)", fx("string space full"),
     lambda c: ("str", b"11111111")),
    ("BIN$", "R-BIN-NAME", "BIN( read as BIN$'s keyword: a syntax error", fx("BIN without $ as an array name"),
     lambda c: ("err", 2)),
    ("VAL", "R-VAL-NUMBER", "6 digits (a single) unless more than 6 are typed without an exponent", vl,
     lambda c: M.m_val(c, nd=6) if any(x in c.s for x in b"EeDd") and not any(x in c.s for x in b"#&")
     else M.m_val(c)),
]


def main():
    bad = 0
    cache = {}
    for fn, rule, what, sel, model in CONTROLS:
        if fn not in cache:
            cache[fn] = M.load(fn)["ref"]
        cs = [c for c in cache[fn] if sel(c)]
        false = [c.id for c in cs if not M.outcome(c, model)]
        print(f"{fn:5} {rule:22} {what:70} FALSE on {len(false):4} of {len(cs)}"
              + (f"  e.g. {false[0]}" if false else "  <- NO CASE SEPARATES IT"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
