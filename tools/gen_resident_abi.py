#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Generate the sub-ROM's resident-ABI import (subrom-mathpack arc, spec §4).

Several sub-ROM PAGE-1 tenants call back into a fixed set of main-ROM
page-0-resident routines (fp_sqrt started this list, docs/spec-basic-subrom-
mathpack.md §4; sub/lineedit.asm's vars_reset call, docs/spec-eviction-g4-
space.md §4, is the newest addition). Their absolute addresses live in
build/basic-reloc.sym and SHIFT whenever the page-0 low region changes (any
edit to basic/float-arith.asm / basic/str-engine.asm / basic/input.asm /
basic/subromcall.asm / basic/arrays.asm, all assembled below $4000 in the
repack build). This tool re-extracts EXACTLY the routines the sub-ROM needs
from a fresh build/basic-reloc.sym and emits pasmo equates the sub-ROM build
includes — so a page-0-low shift can never leave a stale sub.rom calling
wrong addresses (the same class of stale-artifact trap as the old
$(MAIN_ROM) Makefile bug, see [[ips-rebuild-after-basic-change]]).

Fails loudly (nonzero exit) if:
  * any of the required symbols is missing from the reloc sym file, or
  * any of them resolves to __MEAS_LOW_END or above — i.e. it is NOT
    page-0-resident (< $4000), so a page-1 CALSLT could never reach it
    by absolute address (page 0 is switched OUT while the page-1 tenant
    runs — spec §2).

    python3 tools/gen_resident_abi.py build/basic-reloc.sym sub/basic-resident-abi.inc
"""
from __future__ import annotations

import re
import sys

# The resident-ABI surface the sub-ROM's page-1 tenants need — compute-only
# leaves, all page-0-resident. The first 9 are fp_sqrt's own list (docs/spec-
# basic-subrom-mathpack.md §4; flt_to_int16 was excluded for the math pack, but
# the CIRCLE-parse tenant (sub/circleparse.asm) needs it for its 8.8/brad rounds
# — cpt_round's abs+0.5+trunc, page-0-resident at $3280, re-added here); fp_atan/fp_exp/
# fp_log/fp_pow/fp_sin/fp_cos/fp_tan/fp_rnd reuse a SUBSET, no new symbols.
# vars_reset (docs/spec-eviction-g4-space.md §4, carve #2) is sub/
# lineedit.asm's relink-tail call — arrays slice-1/4b's re-anchor + string-
# heap reset, page-0-low-region resident (basic/arrays.asm). Never add a
# symbol here without updating the spec + the calling tenant's own header
# comment that documents its exact resident-ABI list.
# penderr_set (D-PENDERR, docs/spec-basic-penderr.md §4) is the interpreter's
# single set-if-empty writer for the pending-error cell FPERR. sub/fp_pow.asm
# and sub/fp_exp.asm each raise deferred codes into that cell from page-1
# tenant code, so they must go through the same writer as the twenty main-ROM
# ones or first-error-wins would hold everywhere EXCEPT `x^y` and `EXP(x)`.
# It is page-0-resident by construction (basic/str-engine.asm, low region),
# which is exactly the property this file's low_ceiling() check enforces.
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
    "flt_to_int16",
    "vars_reset",
    "penderr_set",
]

# Page-0-resident ceiling. Any resident-ABI address must be strictly below the
# END OF THE LOW REGION, or a page-1 CALSLT (which switches page 0 OUT to the
# sub-ROM) could never call it by absolute address.
#
# 🔴 THIS WAS A HARDCODED `0x3FE5` WHOSE OWN COMMENT CALLED IT `__MEAS_LOW_END`,
# AND IT HAS NEVER TRACKED IT (D-DUPSPAN2, 2026-08-22). The build MEASURES that
# label on every run and prints it -- it read `$3FD2` before this session's
# carve and `$3FA4` after -- so the constant was 19 B, then 65 B, too high, and
# the guard was that much weaker than its own docstring claimed. Nothing caught
# it: `make wall-assertion-check` scopes itself to TODO.md's `- [ ]` items by
# design (its §SCOPE), which is where a stale figure misleads the next SLICE --
# a stale figure inside a GATE misleads the gate instead, and no one reads it.
# 🎯 The fix is that there was never anything to hardcode: this tool already
# loads the sym file the label lives in.
LOW_CEILING_FALLBACK = 0x4000       # a symbol at/above $4000 is page 1, always fatal


def low_ceiling(syms: dict[str, int]) -> int:
    """The measured end of the low region, from the same sym file."""
    return syms.get("__MEAS_LOW_END", LOW_CEILING_FALLBACK)


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

    ceiling = low_ceiling(syms)
    not_resident = [
        f"{name}=${syms[name]:04X}" for name in REQUIRED if syms[name] >= ceiling
    ]
    if not_resident:
        raise SystemExit(
            "FAIL: gen_resident_abi.py: resident-ABI symbol(s) resolve at or "
            f"above __MEAS_LOW_END (${ceiling:04X}), so they are NOT "
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
        ";",
        "; Clean-room: every value below is an address inside THIS project's own",
        "; main ROM, read out of our own build's symbol file. Nothing here is derived",
        "; from a disassembly or byte-copy of any reference ROM.",
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
