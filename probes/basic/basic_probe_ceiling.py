#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMFLD gate: the text ceiling BOOT CHOSE, on both builds. `make ceiling-acceptance`.

Since RAM lever (2) (TODO.md, the RAM-usage item) the main ROM -- one binary for
both builds -- picks its text ceiling at boot: TXTMAX (the disk build's) when a
disk ROM lowered HIMEM, TXTMAX_NODISK (higher: the disk-only tenants sit between
the two) otherwise. That choice is invisible to every other gate: FRE(0) is
never gated as an absolute (a property of each machine's map), so a boot that
fell back to the disk ceiling on the diskless build would cost it bytes and go
unnoticed. This reads the choice back.

zerobas only: it is a claim about zerobas's own map. The expected values come
from build/basic-reloc.sym, never copied (the workspace keeps moving).

  nodisk  TXTCEIL == TXTMAX_NODISK and HIMEM == TXTMAX_NODISK
  disk    TXTCEIL == TXTMAX        and HIMEM <  TXTMAX (the disk ROM lowered it)

Prediction (2026-10-13): both rows PASS; with the boot's `jr nc,bh_store` cut
(the diskless branch never taken) the nodisk row FAILS.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
import omsx_repl  # noqa: E402

HIMEM = 0xFC4A


def sym(name):
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(rf"^{name}\s+EQU\s+([0-9A-Fa-f]+)H", ln)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"{name} is not in build/basic-reloc.sym -- build first")


def read(machine, cell):
    # The line must fit ONE row at the BOOT width -- 37 columns, the VG-8020's
    # (D-BOOTWIDTH), not 40 -- or its echo wraps and the reader finds no anchor:
    # the first two runs read INSTRUMENT FAULT on every row (41 characters, then
    # 37). `?` for PRINT and no `;` beside a string literal: 35.
    line = f'?"["PEEK(&H{cell:04X})+256*PEEK(&H{cell + 1:04X})"]"'
    assert len(line) < 37, line
    raw = omsx_repl.run_cases(machine, [("direct", ["SCREEN 0", line])], batch=False,
                              reset=("",), run_gap=6.0)[0]
    span = omsx_repl.result_span_after_echo(raw, line) if raw else None
    return int(span) if span and span.strip().lstrip("-").isdigit() else None


def main():
    ceil, top, nod = sym("TXTCEIL"), sym("TXTMAX"), sym("TXTMAX_NODISK")
    rows = [
        ("nodisk", "C-BIOS_MSX1_EU_REPACK_NODISK",
         lambda c, h: c == nod and h == nod, f"TXTCEIL = HIMEM = ${nod:04X}"),
        ("disk", "C-BIOS_MSX1_EU_REPACK_DISK",
         lambda c, h: c == top and h is not None and h < top,
         f"TXTCEIL = ${top:04X}, HIMEM below it"),
    ]
    bad = 0
    for name, machine, ok, want in rows:
        c, h = read(machine, ceil), read(machine, HIMEM)
        if c is None or h is None:
            print(f"{name:6s} INSTRUMENT FAULT: no reading (TXTCEIL={c}, HIMEM={h})")
            return 2
        good = ok(c, h)
        bad += not good
        print(f"{name:6s} {'PASS' if good else 'FAIL'}  TXTCEIL=${c:04X} HIMEM=${h:04X}"
              f"   want {want}", flush=True)
    print("ceiling gate:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
