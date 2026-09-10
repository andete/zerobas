#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KEYDEF — the EXACT 160 bytes of the references' function-key defaults.

docs/spec-basic-keystr-scout.md measured the storage (base $F87F, stride 16,
NUL-terminated) and read the HEADS of the defaults through `KEY LIST`, but its
own §"KEY LIST cannot show trailing spaces or a CR" says the exact bytes need a
PEEK read -- "a straight 160-byte image sidesteps the question". This is that
read: every byte of the ten slots on both references after a cold boot, so the
image zerobas ships is copied from a measurement and not typed from memory.

Both references are read; the F6 split (`color 15,4,4` on the VG-8020, `,7` on
the CF-3300) is expected and the VG value ships on both targets by Joost's
standing style ruling (2026-09-04). zerobas is read too, as the control that
says the slots are still zero before the fix.

The program prints the 160 values fenced, 16 per row; the readout keys on the
fence, never on the screen position.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

PROG = ["10 CLS:PRINT\"[KD\";",
        "20 FOR I=0 TO 159:PRINT PEEK(&HF87F+I);:NEXT",
        "30 PRINT\"KD]\"",
        "RUN"]
CASES = [("keydef", PROG)]


def decode(cap):
    c = cap or ""
    i = c.find("[KD"); j = c.find("KD]", i + 3)
    if i < 0 or j < 0:
        return None
    nums = [int(x) for x in re.findall(r"-?\d+", c[i + 3:j])]
    return nums if len(nums) == 160 else nums  # length is checked by the caller


def main() -> int:
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=False,
                                        boot=m["boot"], reset=m["reset"],
                                        run_gap=60.0)
    img = {}
    for s in SIDES:
        v = decode(out[s][0])
        if v is None or len(v) != 160:
            print(f"\U0001f534 {s}: no complete 160-byte fence "
                  f"({'none' if v is None else len(v)} values) -- NOT MEASURED")
            continue
        img[s] = v
        print(f"=== {s}")
        for k in range(10):
            slot = v[16 * k:16 * k + 16]
            txt = "".join(chr(b) if 32 <= b < 127 else f"<{b}>" for b in slot)
            print(f"  F{k + 1:<2} {' '.join(f'{b:3d}' for b in slot)}   |{txt}|")
    if "vg8020" in img and "cf3300" in img:
        diff = [k + 1 for k in range(10)
                if img["vg8020"][16 * k:16 * k + 16] != img["cf3300"][16 * k:16 * k + 16]]
        print(f"\nslots where the two references differ: {diff or 'none'}")
        print("VG8020_IMAGE = " + repr(bytes(img["vg8020"])))
    return 0 if len(img) == 3 else 2


if __name__ == "__main__":
    sys.exit(main())
