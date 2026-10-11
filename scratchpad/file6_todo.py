#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""File D-LISTFLT (Joost's screenshot, 2026-10-11; measured the same day)
above D-AUTORUN. Anchored on text; refuses on a missing or non-unique anchor."""
import sys

P = "TODO.md"
s = open(P, encoding="utf-8").read()

NEW = """- [ ] 🧾 **D-LISTFLT — LIST (AND ASCII SAVE) GARBLE EVERY FLOAT LITERAL: `detok` HAS NO
      ARM FOR `$1D` / `$1F` (Joost's screenshot, 2026-10-11; measured the same day)**
      🎚️ TIER 1 — happy path, and worse than cosmetic: `list_walk` is also
      ASCII SAVE's writer, so `SAVE "X",A` of a program with a float literal
      writes garbage to tape or disk.
      🤖 **AUTONOMOUS** — the VG-8020 settles the spelling.
      Joost's screen: `321 i=0.123456789` LISTs as `321 I=@14VxSTOP` -- the
      double literal's value bytes printed as themselves ($40 `@`, $12 the
      digit-1 token, ..., $90 the STOP token). The tokeniser (sub/tkfloat.asm)
      emits SNG_TOKEN $1D + 4 and DBL_TOKEN $1F + 8 bytes; the evaluator and
      tok_skip read them; basic/detok.inc never does.
      📏 [`listflt_probe.py`](scratchpad/listflt_probe.py) →
      [`.out`](scratchpad/listflt_probe.out), 12 literals: zerobas garbles
      ALL of them, singles too (`101 AA4`). 🔮 Predicted: HIT. The VG-8020's
      spelling, which is the spec: `0.123456789` → `.123456789#`; `1.5` →
      `1.5`; `0.5` → `.5`; `1E10` → `10000000000!`; `1.5#` → `1.5#`;
      `1.5!` → `1.5`; `123456789` → `123456789#`; `3.14159265358979` →
      `3.1415926535898#` (14 digits); `1.5D3` → `1500#`; `2E-5` → `2E-05`;
      `12345678` → `12345678#`; `40000` → `40000!`. Read: PRINT's number
      text without the sign space, plus `#` on every double, and `!` on a
      single whose text has no `.` and no `E` (it would re-read as an
      integer). Check that rule against more rows before building (a double
      with an exponent, a negative literal -- `-` is an operator token --, a
      single that prints with `E`).
      🔧 detok lives in the sub ROM (sub/detok.asm includes the shared body);
      the arm loads the value, calls the number formatter and appends the
      suffix. Price it: where PRINT's formatter lives relative to the tenant.
      ✅ Proof: the probe's rows identical on both builds, LIST and an ASCII
      SAVE / LOAD round trip (the program must RUN the same after it).

"""

A1 = "- [ ] 📼 **D-AUTORUN — "
if s.count(A1) != 1:
    sys.exit(f"anchor count {s.count(A1)}")
s = s.replace(A1, NEW + A1)
open(P, "w", encoding="utf-8").write(s)
print("filed D-LISTFLT")
