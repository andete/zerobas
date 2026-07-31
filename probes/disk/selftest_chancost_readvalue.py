#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""K4 -- falsify the NOREAD guard on SYNTHETIC screens, both directions.

Run from the repo root:  python3 probes/disk/selftest_chancost_readvalue.py

Boots no machine and needs no reference ROMs, so it is runnable anywhere and in
seconds -- which is the point: this probe's OTHER guards (the echo guard's K1/K2,
the NOCAPTURE K3) were run ad hoc and are now only claims in a document. This one
can be re-run. See docs/chancost-cf3300-characterization.md 0.2.

RED  = the guard must fire (the screen carries no reading).
GREEN= the guard must NOT fire (the screen carries a real reading).

The point of the RED rows: before this guard, each returned None, and None on
BOTH machines compares equal and prints `agree`.
"""
import sys
sys.path.insert(0, "probes/disk")
import diskbasic_probe_chancost as P

CASES = [
    # --- RED: no number, no known class -> must be NOREAD -------------------
    ("red_overflow_unclassified", ["Ok", "MAXFILES=65536", "Zzzz error", "Ok"],
     "NOREAD"),
    ("red_empty",                 [], "NOREAD"),
    ("red_only_ok",               ["Ok", "MAXFILES=8", "Ok"], "NOREAD"),
    ("red_text_only",             ["Ok", "Undefined line number", "Ok"], "NOREAD"),

    # --- GREEN: a real reading -> must NOT be NOREAD ------------------------
    ("grn_number",   ["Ok", "MAXFILES=2", "PRINT FRE(0)", "23163", "Ok"], 23163),
    ("grn_negative", ["Ok", "PRINT LOF(1)", "-1", "Ok"], -1),
    ("grn_ifc",      ["Ok", "MAXFILES=16", "Illegal function call", "Ok"], "IFC"),
    ("grn_syntax",   ["Ok", "MAXFILEZ=2", "Syntax error", "Ok"], "SYNTAX"),
    # the two classes D-MFDOM ADDED -- each was NOREAD before, i.e. each was a
    # real reference answer this probe could not read.
    ("grn_overflow", ["Ok", "MAXFILES=70000", "Overflow", "Ok"], "OVF"),
    ("grn_tmismatch", ["Ok", 'MAXFILES="X"', "Type mismatch", "Ok"], "TM"),
    # lowercase: zerobas prints its own lowercase strings (PROVENANCE 851) and
    # the class comparison is what makes that NOT a divergence.
    ("grn_overflow_lc", ["Ok", "MAXFILES=70000", "overflow", "Ok"], "OVF"),
    # an error OUTRANKS a later number -- unchanged behaviour, pinned so the
    # refactor into read_value() is shown not to have moved it.
    ("grn_err_outranks", ["Ok", "MAXFILES=16", "Illegal function call",
                          "PRINT FRE(0)", "14849", "Ok"], "IFC"),
]

bad = 0
for label, rows, want in CASES:
    got = P.read_value(rows)
    ok = got == want
    bad += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label:<26} got={got!r:<10} want={want!r}")
print(f"\nK4: {len(CASES)-bad}/{len(CASES)}")

# --- K4b: the CUT. What the PRE-CHANGE rule did with the same screens. -------
# This replicates the old derivation (error class, else last number, else None)
# on purpose: it is a demonstration of the old rule, not a test of the new code.
import re
def old_read_value(rows):
    value = None
    for r in rows:
        cls = P.err_class(r)
        if cls:
            value = cls
    if value is None:
        nums = [int(r) for r in rows if re.fullmatch(r"-?\d+", r)]
        value = nums[-1] if nums else None
    return value

print("\nK4b -- the CUT: the same unreadable screens under the PRE-CHANGE rule.")
# a REFERENCE screen carrying an unclassified `Overflow`, and a ZEROBAS screen
# carrying nothing at all. Two DIFFERENT failures, on two different machines.
ref_rows = ["Ok", "MAXFILES=65536", "Overflow", "Ok"]
zb_rows  = ["Ok", "MAXFILES=65536", "Ok"]
# ...but the old ERR_CLASSES had no `overflow`, so strip it to model the old map.
old_classes = {k: v for k, v in P.ERR_CLASSES.items() if k not in ("OVF", "TM")}
saved, P.ERR_CLASSES = P.ERR_CLASSES, old_classes
o_ref, o_zb = old_read_value(ref_rows), old_read_value(zb_rows)
P.ERR_CLASSES = saved
n_ref, n_zb = P.read_value(ref_rows), P.read_value(zb_rows)
print(f"  OLD rule: ref={o_ref!r} zb={o_zb!r} -> compare equal? "
      f"{o_ref == o_zb}  => verdict would be {'agree' if o_ref == o_zb else 'DIVERGES'}")
print(f"  NEW rule: ref={n_ref!r} zb={n_zb!r} -> "
      f"ref is a READING ({n_ref!r}), zb is fatal ({n_zb!r})")
cut_ok = (o_ref == o_zb is None) and n_ref == "OVF" and n_zb == "NOREAD"
print(f"  K4b {'CUT CONFIRMED' if cut_ok else 'DID NOT CUT'}: the old rule scored a "
      f"silent-accept defect as `agree`.")
sys.exit(1 if (bad or not cut_ok) else 0)
