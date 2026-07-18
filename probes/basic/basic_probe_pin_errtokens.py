#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Black-box token pin for the error-handling (S2) keywords: ERROR, RESUME,
ERR, ERL, ON ERROR GOTO.

Mechanism is identical to basic_probe_crunch.py: store `1 <body>` on the real
VG-8020 MSX-BASIC ROM (a numbered line -> tokenised into the program area but
never executed), read the exact stored line back via omsx_repl's stored_line
capture, and print the body tokens (bytes after the 4-byte link+lineno header).
This READS the reference tokenisation so the S2a keyword table can be pinned to
the observed bytes (cross-checked against the published MSX-BASIC token table,
allowed-source L110). No disassembly — the ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import omsx_repl

MACHINE = "Philips_VG_8020"
TXTTAB = 0xF676

BODIES = [
    "error 5",
    "a=err",
    "a=erl",
    "resume",
    "resume next",
    "resume 0",
    "resume 100",
    "on error goto 100",
    "on error goto 0",
]


def tokens(raw):
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:] if len(b) >= 5 else None


def main() -> int:
    specs = [("direct", [f"1 {body}"]) for body in BODIES]
    raws = omsx_repl.run_cases(MACHINE, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for body, raw in zip(BODIES, raws):
        b = tokens(raw)
        s = " ".join(f"{x:02X}" for x in b) if b else "<not stored>"
        print(f"  {body:22s} -> {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
