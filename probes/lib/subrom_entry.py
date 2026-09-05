#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""subrom_entry — a page-0 tenant entry address DERIVED from sub/equates.inc.

Three probes inject a raw `ld ix,$00XX` into a bare machine and CALSLT it —
subrom_boot ($0040, PING), subrom_inttest ($0049, INTTEST) and graphics_floor
($0058, GRAPHICS). Each carried the address as literal opcode bytes, correct on
the day it was written and then correct only by luck: `sub/equates.inc` is the
one place that decides `SUBROM_ENTRY_BASE_P0 + 3*index`, and nothing joined the
two (TODO, filed 2026-08-06 by D-PADRPT: "deriving them from sub/equates.inc
needs its own falsification because they inject raw bytes into a bare machine
deliberately").

🔴 THE FALSIFICATION IS THE REFUSAL, NOT THE ARITHMETIC. A derivation that
quietly returned 0 when the parse broke would inject `ld ix,$0000` -- an RST
vector -- into a running machine, and the probe would then FAIL for a reason
that reads like a ROM defect. So a missing symbol RAISES, and the selftest below
plants both a missing symbol and a moved base and requires each to be seen.

    from subrom_entry import page0_entry, le16
    ...0xDD, 0x21, *le16(page0_entry("INTTEST"))...   # ld ix,<derived>
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EQUATES = os.path.join(REPO, "sub", "equates.inc")

_EQU = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)\s+equ\s+\$?([0-9A-Fa-f]+)\s*(?:;.*)?$",
                  re.M)


class EquatesError(RuntimeError):
    """A symbol the derivation needs is absent -- refuse, never default."""


def _symbols(text: str) -> dict[str, int]:
    out = {}
    for name, val in _EQU.findall(text):
        # a hex literal in this file is written `$XXXX`; a bare number is decimal
        out[name] = int(val, 16) if "$" in text.split(name, 1)[1].split("\n", 1)[0] else int(val)
    return out


def page0_entry(idx_name: str, text: str | None = None) -> int:
    """SUBROM_ENTRY_BASE_P0 + 3 * SUBROM_IDX_<idx_name>, from sub/equates.inc.

    ⚠️ Page-0 indices only: the page-1 table has its own base and its own index
    space (FORMAT is 10 in one and READVAL is 10 in the other), so a name that is
    only a page-1 tenant is refused here rather than silently pointed at the wrong
    table."""
    if text is None:
        if not os.path.exists(EQUATES):
            raise EquatesError(f"{EQUATES} is not there -- nothing to derive from")
        text = open(EQUATES, encoding="utf-8").read()
    syms = _symbols(text)
    base = syms.get("SUBROM_ENTRY_BASE_P0")
    if base is None:
        raise EquatesError("SUBROM_ENTRY_BASE_P0 is not defined in sub/equates.inc")
    key = f"SUBROM_IDX_{idx_name}"
    # the page-0 index block runs from the P0 header to the P1 header; an index
    # defined only below that line belongs to the other table
    p0 = text.find("Page-0 tenant indices")
    p1 = text.find("Page-1 tenant indices")
    block = text[p0:p1] if (p0 >= 0 and p1 > p0) else text
    m = re.search(rf"^{re.escape(key)}\s+equ\s+(\d+)", block, re.M)
    if not m:
        raise EquatesError(f"{key} is not a PAGE-0 index in sub/equates.inc")
    return base + 3 * int(m.group(1))


def le16(addr: int) -> tuple[int, int]:
    """The two operand bytes of `ld ix,addr` -- low first."""
    return (addr & 0xFF, (addr >> 8) & 0xFF)


def selftest() -> int:
    fails = 0
    live = {n: page0_entry(n) for n in ("PING", "INTTEST", "GRAPHICS")}
    # the three probes' historical literals -- a control, not a pin: if
    # equates.inc moves them the DERIVATION must move too, and this line is
    # then the one to update, deliberately
    if live != {"PING": 0x0040, "INTTEST": 0x0049, "GRAPHICS": 0x0058}:
        print(f"  selftest: live derivation {live} differs from the historical "
              f"literals -- if equates.inc moved, update this control ON PURPOSE")
        fails += 1
    fixture = ("; Page-0 tenant indices\nSUBROM_ENTRY_BASE_P0 equ $0040\n"
               "SUBROM_IDX_PING equ 0\nSUBROM_IDX_INTTEST equ 3\n"
               "; Page-1 tenant indices\nSUBROM_IDX_FORMAT equ 10\n")
    # 1. a MOVED base must move the answer (the derivation is live, not a table)
    moved = fixture.replace("$0040", "$0080")
    if page0_entry("INTTEST", moved) != 0x0080 + 9:
        print("  selftest: a moved base did not move the derived address"); fails += 1
    # 2. a MISSING index must refuse, never default
    try:
        page0_entry("GRAPHICS", fixture)
        print("  selftest: a missing index returned an address instead of refusing")
        fails += 1
    except EquatesError:
        pass
    # 3. a page-1-only index must refuse even though it is defined
    try:
        page0_entry("FORMAT", fixture)
        print("  selftest: a PAGE-1 index was accepted as page-0"); fails += 1
    except EquatesError:
        pass
    # 4. a missing base must refuse
    try:
        page0_entry("PING", fixture.replace("SUBROM_ENTRY_BASE_P0 equ $0040\n", ""))
        print("  selftest: a missing base returned an address"); fails += 1
    except EquatesError:
        pass
    if le16(0x0049) != (0x49, 0x00):
        print("  selftest: le16 byte order wrong"); fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


if __name__ == "__main__":
    sys.exit(2 if ("--selftest" in sys.argv and selftest()) else 0)
