#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Clean-room reference capture — observe the Philips VG-8020's crunch bytes for
the Phase-3 string-engine keywords (LEN/LEFT$/RIGHT$/MID$/CHR$/ASC/STR$/VAL).

Reference side only (cart=None): drives the VG-8020's built-in BASIC as a black
box, injecting each keyword as the STORED line `1 <body>` (tokenised into the
program but never executed) and reading its crunch back from TXTTAB ($F676) via
omsx_repl's ("stored_line", …) capture — no disassembly (the reference ROM is
never read as code), no CPU freeze. This is the oracle lock behind the token
equates in basic/sysvars.inc (LEFTD_TOKEN etc.) — the values are ALSO the sourced
MSX2 TH Table 2.20 contiguous function table; this confirms them by observation.
See docs/spec-basic-string-engine.md §4.

The zerobas-SIDE differential (proving zerobas crunches these identically) runs on
the repack build in S5 — the byte-full lean build never tokenises them.

    python3 probes/basic/basic_probe_str_tokens.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # sibling probes
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "lib"))

import basic_probe_crunch as C  # noqa: E402  (reuse MACHINE/TXTTAB/tokens)
import omsx_repl                # noqa: E402  (typing-free stored-line capture)

KEYWORDS = [
    ("LEN",    'a=len("ab")'),
    ("LEFT$",  'a$=left$("hi",1)'),
    ("RIGHT$", 'a$=right$("hi",1)'),
    ("MID$",   'a$=mid$("hi",1,1)'),
    ("CHR$",   'a$=chr$(65)'),
    ("ASC",    'a=asc("a")'),
    ("STR$",   'a$=str$(5)'),
    ("VAL",    'a=val("5")'),
]

# Expected $FF-suffix per keyword (MSX2 TH Table 2.20); the run asserts the
# observed crunch contains PEEK_PREFIX + this suffix.
EXPECT = {"LEN": 0x92, "LEFT$": 0x81, "RIGHT$": 0x82, "MID$": 0x83,
          "CHR$": 0x96, "ASC": 0x95, "STR$": 0x93, "VAL": 0x94}


def main() -> int:
    specs = [("direct", [f"1 {body}"]) for _, body in KEYWORDS]
    raws = omsx_repl.run_cases(C.MACHINE, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", C.TXTTAB))

    ok = True
    for (name, body), raw in zip(KEYWORDS, raws):
        ref = C.tokens(raw)
        got = None
        if ref and 0xFF in ref:
            i = ref.index(0xFF)
            got = ref[i + 1] if i + 1 < len(ref) else None
        want = EXPECT[name]
        good = got == want
        ok = ok and good
        s = " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>"
        tag = "OK" if good else f"FAIL want FF {want:02X}"
        print(f"{tag:14} {name:7} {body:22} -> {s}")

    print("\nALL OK — VG-8020 crunch matches Table 2.20" if ok else "\nMISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
