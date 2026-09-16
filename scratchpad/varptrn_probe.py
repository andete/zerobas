#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-VARPTRN -- what does `VARPTR(#n)` answer, and can a row ever AGREE on it?

`VARPTR(#n)` is the last of Joost's ruling-2 four. It is recorded as DEFERRED in
docs/TODO-done.md with NO REASON GIVEN -- weaker than the two blockers this
session already found stale -- but it has a real question behind it that the
others did not: the answer is an ADDRESS, and an address is implementation
specific. The reference's FCB does not live where ours does, so a row that
compares the VALUE can never agree and should never be written.

🎯 SO ASK WHAT *CAN* AGREE, BEFORE IMPLEMENTING ANYTHING:
  err     does it ERROR? A verb that raises where the reference answers is a
          divergence a row CAN score, whatever the number is.
  stride  VARPTR(#2) - VARPTR(#1). A STRUCTURAL property: if the references lay
          channels out at a fixed pitch, that pitch is a fact about MSX's channel
          table and is comparable across machines in a way the base is not.
  order   is #2 above #1? Also structural, and weaker than the stride.
⚠️ A row is only worth writing on an axis that CAN agree. Measuring first is what
decides whether this form is implementable-and-scorable or implementable-and-
unscorable -- and those are different answers to Joost's question.
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 14.0),
    "cf3300": ("National_CF-3300", 14.0),
    "zb":     ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0),
}
CASES = [
    ("closed.1", ['10 ON ERROR GOTO 90', '20 PRINT"[";VARPTR(#1);"]"',
                  "30 END", '90 PRINT"[E";ERR;"]"', "RUN"]),
    ("closed.2", ['10 ON ERROR GOTO 90', '20 PRINT"[";VARPTR(#2);"]"',
                  "30 END", '90 PRINT"[E";ERR;"]"', "RUN"]),
    ("open.1",   ['10 ON ERROR GOTO 90', '20 MAXFILES=2',
                  '30 OPEN"VP.TXT"FOR OUTPUT AS#1',
                  '40 PRINT"[";VARPTR(#1);"]"',
                  "50 END", '90 PRINT"[E";ERR;"]"', "RUN"]),
    # 🎯 THE DELTA, WHICH IS THE ONLY AXIS THAT CAN AGREE. varptr_b already does
    # this for the variable form -- it reads the ARRAY STRIDE so "the
    # machine-dependent base cancels". VARPTR(#2)-VARPTR(#1) is the per-channel
    # block stride, a structural fact about the channel table rather than an
    # address. MAXFILES=2 first, because with the default of 1 channel #2 does
    # not exist and the reference answers ERR 52 (measured).
    ("stride",   ['10 ON ERROR GOTO 90', '20 MAXFILES=2',
                  '30 A=VARPTR(#1):B=VARPTR(#2)',
                  '40 PRINT"[";B-A;"]"',
                  "50 END", '90 PRINT"[E";ERR;"]"', "RUN"]),
]


def main() -> int:
    for _, lines in CASES:
        for ln in lines:
            if len(ln) > 38:
                print(f"INSTRUMENT FAULT: {len(ln)} cols: {ln!r}")
                return 2
    out = {}
    for side, (machine, boot) in SIDES.items():
        kw = {}
        if side != "vg8020":                      # the VG-8020 has no disk ROM
            tmp = tempfile.mkstemp(suffix=".dsk")[1]
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), tmp)
            kw["diska"] = tmp
        caps = omsx_repl.run_cases(machine, CASES, batch=False, boot=boot,
                                   reset=("", "SCREEN 0"), cap_gap=45.0,
                                   timeout=1800.0, **kw)
        vals = []
        for cap in caps:
            m = re.search(r"\[\s*(E?)\s*(-?\d+)\s*\]", cap or "")
            vals.append(("ERR " + m.group(2)) if m and m.group(1)
                        else (m.group(2) if m else None))
        out[side] = vals
        print(f"  {side:8s} " + "  ".join(f"{n}={v}" for (n, _), v in zip(CASES, vals)))

    print()
    for side, v in out.items():
        a, b = v[0], v[1]
        if a and b and not a.startswith("ERR") and not b.startswith("ERR"):
            print(f"  {side}: stride VARPTR(#2)-VARPTR(#1) = {int(b) - int(a)}")
        else:
            print(f"  {side}: no stride -- one or both closed reads is {a} / {b}")
    print()
    print("A row can only be written on an axis where the sides CAN agree. The")
    print("ADDRESS cannot: the reference's channel table is not ours. The STRIDE")
    print("and whether it ERRORS both can.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
