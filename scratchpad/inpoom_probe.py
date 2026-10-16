#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14d prep: when does INPUT$ with no string space raise, and are the
keys consumed? S14d makes INPUT$ allocate its result in string space (as INKEY$
does, and as the reference does) instead of staging it in BUF; whether the
allocation comes BEFORE or AFTER reading the keys is observable.
Row: CLEAR 10 (10 bytes of string space), A$=INPUT$(30), 30 Z keys typed. The
handler waits 5 s, then counts the keys still waiting.
PREDICTED, before the run: VG-8020 `[E 14  30]` or `[E 14  31]` (raised before
reading; the typed keys stay queued); zerobas today `[E 14  1]` or `[E 14  0]`
(reads the 30 keys into BUF, then fails at the assignment).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                         # noqa: E402

PROG = ["NEW", "10 CLEAR 10:ON ERROR GOTO 100", '20 A$=INPUT$(30):PRINT"[OK";LEN(A$);"]":END',
        "100 T=TIME", "110 IF TIME-T<300 THEN 110", "120 N=0",
        '130 K$=INKEY$:IF K$<>"" THEN N=N+1:GOTO 130', '140 PRINT"[E";ERR;N;"]":END',
        "RUN", "Z" * 30]

for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
    cap = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("", "SCREEN 0:WIDTH 40"),
                              step=3.0, run_gap=20.0)[0]
    rows = [cap[i:i + 40].strip() for i in range(0, len(cap or ""), 40)]
    print(side, " | ".join(r for r in rows if r.startswith("[") or "rror" in r) or "<NO OUTPUT>", flush=True)
