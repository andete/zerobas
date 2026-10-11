#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""File D-OPENGRP (Joost, 2026-10-11) above D-BLDS.
Anchored on text; refuses on a missing or non-unique anchor."""
import sys

P = "TODO.md"
s = open(P, encoding="utf-8").read()

NEW = """- [ ] 🎨 **D-OPENGRP — `OPEN "GRP:"` IS NOT SUPPORTED: TEXT ON THE GRAPHICS SCREEN
      (Joost, 2026-10-11; NOT YET MEASURED)**
      🎚️ TIER 1 — happy path: `OPEN "GRP:" FOR OUTPUT AS #1` then `PRINT #1`
      is how a BASIC program puts text on SCREEN 2.
      🤖 **AUTONOMOUS** — the VG-8020 settles it.
      Today: the OPEN dispatch (basic/files.asm, `do_open`) knows `LPT:`,
      `CRT:` and `CAS:` only; its comment says an unknown `xxx:` "stays a disk
      name", so `GRP:` never reaches the graphics screen (on the diskless build
      it probably reaches the tape -- unmeasured). D-NODISKOPEN listed `GRP:`
      as unmeasured on either target.
      ➡️ Measure first, VG-8020 against both builds, reading VRAM back: what
      `PRINT #1` draws in SCREEN 2 and 3 (glyph, colour, the position it starts
      from -- PSET / PRESET / DRAW's last point), how the position advances,
      the right and bottom edges, CR / LF and other control codes; `OPEN
      "GRP:"` in SCREEN 0 / 1 (which error, at OPEN or at PRINT #); `INPUT #`
      and the other read verbs on it; `CLOSE`, `MAXFILES`, `EOF` / `LOC` /
      `LOF` on the channel.
      🔧 Price before building: the drawing belongs in the graphics tenant
      (sub ROM); main needs a fourth device name in the dispatch and the
      channel's output arm -- against main page 1 10 B, low 19 B
      (2026-10-11), so a carve may come first.

"""

A1 = "- [ ] 🔍 **D-BLDS — ON TAPE"
if s.count(A1) != 1:
    sys.exit(f"anchor count {s.count(A1)}")
s = s.replace(A1, NEW + A1)
open(P, "w", encoding="utf-8").write(s)
print("filed D-OPENGRP")
