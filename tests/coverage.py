# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Code-coverage measurement for the host-side unit tests — no core changes.

Coverage is a pure test-harness concern, so we monkeypatch Z80.step here to log
every executed opcode address; the production core (z80.py) is untouched. We run
each test group in-process, accumulate the executed addresses, then bucket them
against the pasmo symbol table to report, per labelled region, whether it was
ENTERED by any test. That automates the "what's covered?" audit.

Metric: symbol-delimited *region entry* — region [label_i, label_{i+1}) counts
as covered iff some executed opcode address fell inside it. (A finer byte metric
would need a full disassembly pass to know which bytes are opcode starts; region
entry is the pragmatic, honest measure and maps straight onto "is this routine
tested?". Data tables in the code image — kwtable, the dispatch table — never
execute, so they legitimately show as not-entered.)

Run: `python3 tests/coverage.py`  (or `make coverage`).
"""

import bisect
import contextlib
import importlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import z80                              # noqa: E402
from msxtest import load_symbols        # noqa: E402

# --- instrument: log each executed opcode address (no z80.py change) ---------
_PCS = set()
_orig_step = z80.Z80.step


def _traced_step(self):
    _PCS.add(self.pc)                   # PC here = the opcode about to run
    return _orig_step(self)


z80.Z80.step = _traced_step

# --- test groups: (label, modules, source, load-base) ------------------------
GROUPS = [
    ("BASIC", [
        "test_tokenise", "test_expr", "test_vars", "test_strvar", "test_print",
        "test_list", "test_screen", "test_vdpio", "test_poke", "test_usr",
        "test_program",
    ], "basic/main.asm", 0x4000),
    ("tape", ["test_tape"], "tape/tape.asm", 0x00E1),
    ("disk", ["test_getdpb"], "disk/disk.asm", 0x4000),
]

# Data tables that live in the code image (lowercase, so not caught by the
# constant filter) and legitimately never execute as code.
DATA_LABELS = {"kwtable", "dispatch", "disptab", "verbtab", "banner_text",
               "prompt_text"}


def is_code_label(name):
    """A code label, not an EQU constant. Convention in this codebase: code
    labels are lowercase, constants (CHPUT, CAS_FLATMAX, DSKIO_ENTRY) are
    UPPERCASE. A constant whose *value* happens to land in the code range would
    otherwise masquerade as an un-executed routine."""
    if name in DATA_LABELS:
        return False
    return any(c.islower() for c in name)


def code_extent(rom_path, base):
    """[lo, hi) of real content: trim the trailing $00 padding."""
    data = open(rom_path, "rb").read()
    hi = len(data)
    while hi > 0 and data[hi - 1] == 0:
        hi -= 1
    return base, base + hi


def regions(sym_path, lo, hi):
    """Code regions [label_i, label_{i+1}) — boundaries from code labels only,
    so constants/data don't split or inflate the routine map."""
    syms = load_symbols(sym_path)
    code = sorted((a, n) for n, a in syms.items()
                  if lo <= a < hi and is_code_label(n))
    out = []
    for i, (a, n) in enumerate(code):
        end = code[i + 1][0] if i + 1 < len(code) else hi
        if end > a:
            out.append((n, a, end))
    return out


def measure(label, mods, src, base):
    _PCS.clear()
    for mname in mods:
        mod = importlib.import_module(mname)
        with contextlib.redirect_stdout(io.StringIO()):
            fails = mod.run()
        if fails:
            print(f"  !! {mname} reported {fails} failing check(s)")

    rom, sym = "/tmp/cov_group.rom", "/tmp/cov_group.sym"
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, src), rom, sym],
                   check=True, capture_output=True)
    lo, hi = code_extent(rom, base)
    regs = regions(sym, lo, hi)

    starts = [a for _, a, _ in regs]
    entered = [False] * len(regs)
    for pc in _PCS:
        if lo <= pc < hi:
            i = bisect.bisect_right(starts, pc) - 1
            if 0 <= i < len(regs) and regs[i][1] <= pc < regs[i][2]:
                entered[i] = True

    n_total = len(regs)
    n_cov = sum(entered)
    pct = 100.0 * n_cov / n_total if n_total else 0.0

    print(f"\n=== {label}: {n_cov}/{n_total} routines entered ({pct:.0f}%) "
          f"[code {lo:#06x}..{hi:#06x}] ===")
    missed = [n for (n, _, _), ent in zip(regs, entered) if not ent]
    if missed:
        print(f"  not entered ({len(missed)}):")
        line = "    "
        for name in missed:
            if len(line) + len(name) + 2 > 78:
                print(line)
                line = "    "
            line += name + "  "
        if line.strip():
            print(line)
    return n_cov, n_total


def main():
    print("Host unit-test coverage (region-entry; data tables excluded)")
    total_cov = total_all = 0
    for label, mods, src, base in GROUPS:
        c, t = measure(label, mods, src, base)
        total_cov += c
        total_all += t
    pct = 100.0 * total_cov / total_all if total_all else 0.0
    print(f"\nOVERALL: {total_cov}/{total_all} code regions entered ({pct:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
