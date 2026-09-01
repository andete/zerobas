#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""batchcheck — a suite's rows must be IDENTICAL batched and boot-per-case.

🔴 WHY (D-BATCH1/D-BATCH2, 2026-09-01). `run_cases` defaults to `batch=True` --
one boot per matrix -- and `batch=False`, "the historical default", is passed by
**35 of the tree's 60 emulator probes**. It dominates the battery:
`strparen-acceptance` went **35 s -> 5 s** on the flip, 16/16 rows unchanged.

🔴 BUT THE SPEEDUP IS NOT THE POINT. D-EDITVERB records what a wrongly batched
suite does: one case's capture becomes a whole log and every later delta is
silently wrong *"in the direction of a plausible-looking divergence"*. A suite
with accumulated state (D-LPTVERB's `LPOS`, D-EDITVERB's printer log) MUST stay
boot-per-case. This is the control that says which is which.

🔴 AND THE FIRST VERSION OF THIS TOOL WAS WITHDRAWN AS UNSOUND. `reset` used to
mean something in the batched path and NOTHING boot-per-case (`reset=()`), so
every boot-per-case probe prepended its own -- and forcing the other mode from
outside produced a THIRD behaviour, not the old one. Its first run said
`rc 0 vs 2` and that was the instrument, not the suite. D-BATCH2 made `reset`
apply in both modes and made all 69 implicit sites explicit; only then is
flipping a mode from outside faithful.

    python3 scratchpad/batchcheck.py <make-target>

Exit: 0 rows identical (convertible), 1 they differ (must stay boot-per-case),
2 the INSTRUMENT could not measure.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOISE = re.compile(r"refcache:|wall |elapsed|seconds|make\[|^python3 |^\s*wrote |"
                   r"^\s*/Users/|install-repack-machine")


def rows(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines()
            if l.strip() and not NOISE.search(l)]


def run(target: str, mode: str) -> tuple[list[str], float, int]:
    env = dict(os.environ, ZEROBAS_REFCACHE="0", ZB_BATCH=mode)
    t = time.time()
    p = subprocess.run(["make", target], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    return rows(p.stdout + p.stderr), time.time() - t, p.returncode


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    target = argv[0]
    a_rows, a_t, a_rc = run(target, "1")      # forced BATCHED
    b_rows, b_t, b_rc = run(target, "0")      # forced BOOT-PER-CASE
    if not a_rows or not b_rows:
        print(f"INSTRUMENT: {target} printed no row lines in one or both modes "
              f"({len(a_rows)} / {len(b_rows)}) — nothing was compared.")
        return 2
    print(f"{target}")
    print(f"  batched       : {a_t:6.1f}s  rc={a_rc}  {len(a_rows)} rows")
    print(f"  boot-per-case : {b_t:6.1f}s  rc={b_rc}  {len(b_rows)} rows")
    if a_t:
        print(f"  batching is {b_t / a_t:.1f}x faster")
    if a_rc != b_rc:
        print(f"🔴 EXIT STATUS DIFFERS ({a_rc} vs {b_rc}) — the two modes do not "
              f"agree on pass/fail. Must stay boot-per-case.")
        return 1
    diff = [(x, y) for x, y in zip(a_rows, b_rows) if x != y]
    if len(a_rows) != len(b_rows) or diff:
        print(f"🔴 {len(diff)} ROW(S) DIFFER ({len(a_rows)} vs {len(b_rows)} row "
              f"lines) — this suite carries state across cases. It must stay "
              f"boot-per-case, and its `batch=False` should SAY SO.")
        for x, y in diff[:8]:
            print(f"     batched : {x}\n     per-case: {y}")
        return 1
    print("  ✅ every row identical in both modes — CONVERTIBLE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
