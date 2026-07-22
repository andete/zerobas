#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G7 impl step 1 (spec §11.1 / D-G7-3): does OUR runtime's mode set do the
reference's sprite-table init?

The reference initialises all 32 attribute entries on a mode set to
`y=209, pattern=plane, colour=FORCLR`, leaving the x byte untouched, and keeps
the sprite size in RG1SAV bits 1..0 across later SCREEN statements. Our mode set
is C-BIOS `CHGMOD`, a different implementation -- so this is measured, not
assumed. Runs the same cases on the reference and on the merged repack build.
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SATR = 0x1B00

CASES = [
    ("init_p0_3",   "COLOR15,1,1:SCREEN2", f"&H{SATR:04X}", 12),
    ("init_col4",   "COLOR4,1,1:SCREEN2",  f"&H{SATR:04X}", 8),
    ("init_p31",    "COLOR15,1,1:SCREEN2", f"&H{SATR:04X}+4*31", 4),
    ("dirty_then",  "COLOR15,1,1:SCREEN2:VPOKE&H1B00,7:VPOKE&H1B01,60:"
                    "VPOKE&H1B02,9:VPOKE&H1B03,3:SCREEN2", f"&H{SATR:04X}", 4),
    ("cls_keeps",   "COLOR15,1,1:SCREEN2:VPOKE&H1B00,7:CLS", f"&H{SATR:04X}", 4),
]


def dump(base, n, tag):
    return [f'A$="":FOR I=0 TO {n-1}:A$=A$+STR$(VPEEK({base}+I)):NEXT',
            f'SCREEN0:PRINT"Q{tag}Q";A$;"|";PEEK(&HF3E0);PEEK(&HF3E9)']


def pick(txt, tag):
    m = re.search(rf"Q{tag}Q([^\r\n]*)", txt or "")
    return " ".join(m.group(1).split()) if m else f"<none> raw={(txt or '')[:60]!r}"


def main():
    specs = [("stored", [f"CLEAR 2000:{head}"] + dump(base, n, i))
             for i, (lab, head, base, n) in enumerate(CASES)]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW",))
    bad = 0
    for i, (c, r, z) in enumerate(zip(CASES, ref, zb)):
        rr, zz = pick(r, i), pick(z, i)
        same = "SAME" if rr == zz else "DIFF"
        bad += same == "DIFF"
        print(f"  {c[0]:12s} {same}\n      ref: {rr}\n      zb : {zz}")
    print(f"\n  {len(CASES)-bad}/{len(CASES)} identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
