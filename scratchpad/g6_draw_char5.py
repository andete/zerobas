#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW char round 5: disambiguate V3 -- did RUN or COLOR drop DRAW's C?

Round 4 ran [C6 draw] then [COLOR 11 : plain draw] in two RUNs of one boot and
saw fg 11. Two candidate causes. Here run 2 omits COLOR entirely, so fg 6 =>
C survives a RUN and COLOR is what overrode it; fg 15 => a RUN resets C.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
CTAB = 0x2000
x, y = 100, 140
seg = [((y >> 3)*256 + (x >> 3)*8 + (y & 7), 1), (CTAB + (y >> 3)*256 + (x >> 3)*8 + (y & 7), 1)]
specs = [
    ("stored", ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"C6R8"', 'PRINT"SET"']),
    ("stored", ['SCREEN2', 'PSET(100,140):DRAW"R8"', 'GOTO 30']),
]
raw = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                          capture=("vram_segs", seg), cart=None)
print(f"run1 C6, run2 plain DRAW (no COLOR) -> {raw[-1]}   (x6 => C survives RUN; xf => RUN reset it)")
