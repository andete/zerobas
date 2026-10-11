#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AUTORUN: does a disk ROM CLAIM H.READ ($FF07) or H.MAIN ($FF0C)?
A claimed hook cell starts with $F7 (RST $30, an inter-slot call); an
unclaimed one is a bare RET ($C9 = 201). One typed PRINT of the FIRST byte of
each cell at the prompt, on the CF-3300, the VG-8020 and both zerobas builds.
Clean room: a PEEK of two documented work-area cells; the target of a claimed
hook is NOT followed.

Prediction: 201 201 everywhere (no ROM here claims them at the prompt).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

ROWS = (("National_CF-3300", dict(boot=14.0)), ("Philips_VG_8020", {}),
        ("C-BIOS_MSX1_EU_REPACK_DISK", {}), ("C-BIOS_MSX1_EU_REPACK_NODISK", {}))
LINE = 'PRINT"<";PEEK(&HFF07);PEEK(&HFF0C);">"'
RX = re.compile(r"<\s*(\d+)\s+(\d+)\s*>")


def main():
    for m, kw in ROWS:
        raw = omsx_repl.run_cases(m, [("direct", [LINE])], batch=False,
                                  reset=("", "SCREEN 0"), **kw)[0] or ""
        hit = RX.findall("".join(raw.splitlines()))
        print(f"{m:32s} H.READ H.MAIN first bytes: {hit[-1] if hit else None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
