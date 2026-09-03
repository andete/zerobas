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
REQUIRED_SUB = [
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
    # D-PUNUM: PRINT USING's numeric renderer (sub/punum.asm) renders the live
    # value with the main ROM's own float formatter rather than a second copy of
    # one -- so `PRINT USING` and `PRINT` cannot disagree about what a number
    # looks like. Low-region by construction (basic/float.asm).
    "flt_fmt",
]

# --- the DISK ROM's profile (D-DISKABI, docs/spec-basic-nodisk.md §13) -------
# disk.rom is a PAGE-1 ROM exactly like a sub-ROM page-1 tenant, so it faces the
# same rule and gets the same bridge: while it is mapped at $4000-$7FFF, page 0
# still holds slot 0, so main's LOW REGION is callable by absolute address and
# main page 1 is not. Until now it had no bridge at all, which is why the disk
# verbs' bodies could not follow their hooks (§8/§12).
#
# CODE: ceiling-checked, exactly as the sub list is.
REQUIRED_DISK_CODE = [
    "widen_rhs_operand",        # MKS$/MKD$: widen the live RHS into ARGA
    "round_single_and_pack",    # ...then pack it as single
    "round_and_finalize",       # ...or as double
]
# RAM: NOT ceiling-checked, and that exemption is the point -- these are work-area
# cells above $8000, always mapped, and applying the page-0-resident test to them
# would reject every one. They are here rather than in disk/equates.inc so that a
# sysvar MOVE cannot leave disk.rom writing the old address: the same staleness
# argument the code half rests on.
REQUIRED_DISK_RAM = [
    "ARGA",                     # the 15-digit working record
    "STRSCR",                   # [len][bytes] staging buffer
    "FAC",                      # the packed float accumulator
    "FACTYP",                   # 2 / 4 / 8
]

# out-path -> (code symbols, ram symbols, what it feeds)
PROFILES = {
    "sub/basic-resident-abi.inc":  (REQUIRED_SUB, [], "sub-ROM"),
    "disk/basic-resident-abi.inc": (REQUIRED_DISK_CODE, REQUIRED_DISK_RAM,
                                    "disk ROM"),
}


def profile_for(out_path: str, name: str | None = None):
    """`name` wins when given; otherwise the profile is inferred from the path.

    ⚠️ THE EXPLICIT NAME EXISTS BECAUSE THE PATH IS NOT ALWAYS THE REAL ONE.
    `check_patch_freshness.py` regenerates into a TEMP directory to diff against
    the tracked copy, and that path carries no `sub/` or `disk/` hint -- so
    path-only selection refused it and reddened a gate that had nothing to do
    with this change."""
    if name is not None:
        for key, prof in PROFILES.items():
            if key.startswith(name + "/"):
                return prof
        raise SystemExit(f"FAIL: gen_resident_abi.py: unknown --profile {name!r}")
    """Pick the symbol set from the OUTPUT path -- the one thing both call sites
    already state explicitly, so neither Makefile rule needs a new flag."""
    key = out_path.replace("\\", "/")
    for name, prof in PROFILES.items():
        if key.endswith(name):
            return prof
    raise SystemExit(
        f"FAIL: gen_resident_abi.py: no ABI profile for output path {out_path!r} "
        f"-- known: {', '.join(sorted(PROFILES))}")


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


def generate(sym_path: str, out_path: str, write: bool = True,
             profile: str | None = None) -> str:
    """`out_path` ALWAYS selects the profile, even when `write` is False -- the
    checker regenerates into memory and still has to know WHICH ABI it is
    checking. Passing None for that reason used to be the only way to say
    "do not write", and it took the profile with it."""
    code, ram, what = profile_for(out_path, profile)
    syms = load_syms(sym_path)

    missing = [n for n in code + ram if n not in syms]
    if missing:
        raise SystemExit(
            "FAIL: gen_resident_abi.py: missing resident symbol(s) in "
            f"{sym_path}: {', '.join(missing)} — the resident-ABI surface "
            "(docs/spec-basic-subrom-mathpack.md §4) could not be resolved"
        )

    ceiling = low_ceiling(syms)
    # ⚠️ THE CEILING APPLIES TO CODE ONLY. A RAM cell is above $8000 by
    # construction and is mapped in every configuration; testing it here would
    # reject the whole disk profile on its first symbol.
    not_resident = [
        f"{name}=${syms[name]:04X}" for name in code if syms[name] >= ceiling
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
        f"; {what} calling stale addresses. docs/spec-basic-subrom-mathpack.md §4.",
        ";",
        "; Clean-room: every value below is an address inside THIS project's own",
        "; main ROM, read out of our own build's symbol file. Nothing here is derived",
        "; from a disassembly or byte-copy of any reference ROM.",
        "",
    ]
    for name in code + ram:
        # Leading "0" (same convention pasmo's own --sym output uses, e.g.
        # "fp_div EQU 03632H") so a value whose hex form starts A-F never
        # parses as an identifier instead of a numeric literal.
        lines.append(f"{name} equ 0{syms[name]:04X}H")
    lines.append("")
    text = "\n".join(lines)

    if write and out_path:
        with open(out_path, "w") as fh:
            fh.write(text)
    return text


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--profile")]
    prof = next((a.split("=", 1)[1] for a in sys.argv[1:]
                 if a.startswith("--profile=")), None)
    if len(args) != 2:
        sys.exit(__doc__)
    text = generate(args[0], args[1], profile=prof)
    n = text.count("equ")
    print(f"wrote {args[1]}: {n} resident-ABI symbols (from {args[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
