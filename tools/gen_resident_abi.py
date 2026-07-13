#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Generate the sub-ROM's resident-ABI import (subrom-mathpack arc, spec §4).

`fp_sqrt` (sub/fp_sqrt.asm, a sub-ROM PAGE-1 tenant) calls back into a fixed
set of main-ROM page-0-resident routines. Their absolute addresses live in
build/basic-reloc.sym and SHIFT whenever the page-0 low region changes (any
edit to basic/float-arith.asm / basic/str-engine.asm / basic/input.asm /
basic/subromcall.asm, all assembled below $4000 in the repack build). This
tool re-extracts EXACTLY the routines fp_sqrt needs from a fresh
build/basic-reloc.sym and emits pasmo equates the sub-ROM build includes —
so a page-0-low shift can never leave a stale sub.rom calling wrong
addresses (the same class of stale-artifact trap as the old $(MAIN_ROM)
Makefile bug, see [[ips-rebuild-after-basic-change]]).

Fails loudly (nonzero exit) if:
  * any of the 9 required symbols is missing from the reloc sym file, or
  * any of them resolves to $3FE5 (__MEAS_LOW_END) or above — i.e. it is
    NOT page-0-resident (< $4000), so a page-1 CALSLT could never reach it
    by absolute address (page 0 is switched OUT while the page-1 tenant
    runs — spec §2).

    python3 tools/gen_resident_abi.py build/basic-reloc.sym sub/basic-resident-abi.inc
"""
from __future__ import annotations

import re
import sys

# The exact resident-ABI surface fp_sqrt needs (docs/spec-basic-subrom-
# mathpack.md §4) — compute-only leaves, all page-0-resident. flt_to_int16 is
# DELIBERATELY excluded (it moved main-side, called by evmc_sqr instead —
# spec §3). Never add a symbol here without updating the spec + fp_sqrt's own
# header comment (sub/fp_sqrt.asm) that documents this exact list.
REQUIRED = [
    "fp_add",
    "fp_sub",
    "fp_mul",
    "fp_div",
    "fp_cmp",
    "dig15_iszero",
    "arga_pack_fac",
    "widen_fac_to",
    "widen_uint_to",
]

# Page-0-resident ceiling (basic/main.asm __MEAS_LOW_END — the reclaimed low
# region ends here; $4000 is the cartridge header). Any resident-ABI address
# must be strictly below this, or a page-1 CALSLT (which switches page 0 OUT
# to the sub-ROM) could never call it by absolute address.
LOW_CEILING = 0x3FE5


def load_syms(path: str) -> dict[str, int]:
    syms = {}
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


def generate(sym_path: str, out_path: str) -> str:
    syms = load_syms(sym_path)

    missing = [name for name in REQUIRED if name not in syms]
    if missing:
        raise SystemExit(
            "FAIL: gen_resident_abi.py: missing resident symbol(s) in "
            f"{sym_path}: {', '.join(missing)} — the resident-ABI surface "
            "(docs/spec-basic-subrom-mathpack.md §4) could not be resolved"
        )

    not_resident = [
        f"{name}=${syms[name]:04X}" for name in REQUIRED if syms[name] >= LOW_CEILING
    ]
    if not_resident:
        raise SystemExit(
            "FAIL: gen_resident_abi.py: resident-ABI symbol(s) resolve at or "
            f"above __MEAS_LOW_END (${LOW_CEILING:04X}), so they are NOT "
            f"page-0-resident: {', '.join(not_resident)} — a page-1 tenant "
            "cannot reach them by absolute address (page 0 is switched out "
            "under a page-1 CALSLT)"
        )

    lines = [
        "; Copyright (c) 2026 Joost Yervante Damad",
        "; SPDX-License-Identifier: 0BSD",
        "",
        "; GENERATED FILE -- do not hand-edit. Produced by",
        "; tools/gen_resident_abi.py from build/basic-reloc.sym (Makefile rule);",
        "; regenerated on every build so a page-0-low shift can never leave this",
        "; sub-ROM calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.",
        "",
    ]
    for name in REQUIRED:
        # Leading "0" (same convention pasmo's own --sym output uses, e.g.
        # "fp_div EQU 03632H") so a value whose hex form starts A-F never
        # parses as an identifier instead of a numeric literal.
        lines.append(f"{name} equ 0{syms[name]:04X}H")
    lines.append("")
    text = "\n".join(lines)

    if out_path:
        with open(out_path, "w") as fh:
            fh.write(text)
    return text


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    text = generate(sys.argv[1], sys.argv[2])
    n = text.count("equ")
    print(f"wrote {sys.argv[2]}: {n} resident-ABI symbols (from {sys.argv[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
