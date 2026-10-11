#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""File D-TAPELOAD (Joost's fourth report, 2026-10-11) above D-BLDS.
Anchored on text; refuses on a missing or non-unique anchor."""
import sys

P = "TODO.md"
s = open(P, encoding="utf-8").read()

NEW = """- [ ] 📼 **D-TAPELOAD — MANY `.cas` AND `.wav` TAPES DO NOT LOAD (Joost, 2026-10-11;
      NOT YET MEASURED)**
      🎚️ TIER 1 — happy path: loading existing software from tape.
      🙋 **NEEDS-JOOST** — the failing tapes themselves: which titles / files
      (they stay OUTSIDE the repo; zerobas is public). Everything after that is
      autonomous.
      Joost: *"many .cas and .wav tapes are not loading"*.
      ➡️ Measure first, per tape, on the VG-8020 and both builds: WHERE it
      stops -- no `Found:` (the leader / header / baud detection: TAPION,
      `cas_baud`), a `Device I/O error` mid-file (TAPIN's edge timing against
      a real recording's drift and noise -- `.wav` exercises this, a `.cas`
      does not), or a load that completes and then crashes (a loader that
      calls the BASIC ROM's own entry points, or reads reference RAM state
      zerobas does not keep -- a compatibility question, not a tape one).
      Classify first; the three classes have different fixes and different
      tiers. Synthetic rows (cas_encode, 1200 / 2400 baud, short / long
      leaders, multi-file tapes) can start before the corpus arrives.

"""

A1 = "- [ ] 🔍 **D-BLDS — ON TAPE"
if s.count(A1) != 1:
    sys.exit(f"anchor count {s.count(A1)}")
s = s.replace(A1, NEW + A1)
open(P, "w", encoding="utf-8").write(s)
print("filed D-TAPELOAD")
