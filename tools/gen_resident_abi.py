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

import collections
import glob
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
    "pu_deref_body",            # D-CVMOVE: hk_cv turns the evaluator's string
                                # DESCRIPTOR into a body pointer itself, rather
                                # than having one marshalled to it -- STRSCR is
                                # where MKI$/MKS$/MKD$ stage their result, so a
                                # pointer parked there is overwritten by the very
                                # round trip these verbs exist for
]
# RAM: NOT ceiling-checked, and that exemption is the point -- these are work-area
# cells above $8000, always mapped, and applying the page-0-resident test to them
# would reject every one. They are here rather than in disk/equates.inc so that a
# sysvar MOVE cannot leave disk.rom writing the old address: the same staleness
# argument the code half rests on.
REQUIRED_DISK_RAM = [
    "ARGA",                     # the 15-digit working record
    "STRSCR",                   # [len][bytes] staging buffer
    "FN_RESUME",                # D-DISKVERB: main stages the statement cursor
                                # here for the handler, and fname_expr overwrites
                                # it with the resume point -- one cell, both ways
    "DISKOP_STATUS",            # D-DISKVERB: the dirverb tenant's disposition,
                                # which main's kill_status decodes after the hook
    "DISK_FCB_NAME",            # D-DISKVERB2: the one 8.3 name field, which NAME
                                # fills twice -- old to look up, then new to stamp
    "FILES_HASPAT",             # D-DISKVERB4: 1 = a filespec pattern is staged,
                                # 0 = list the whole directory
    "FAC",                      # the packed float accumulator
    "FPERR",                    # D-DSKFSLOW: the evaluator's DEFERRED error;
                                # hk_dskf counts nothing while one is pending
    "FACTYP",                   # 2 / 4 / 8
    # D-LRSETMOVE: hk_lrset walks main's FLD_TAB entry and fills the three
    # cells the sub-ROM store tenant reads. It WALKS the table; main OWNS it.
    "FSECTOR_BUF",              # the shared record buffer the offset indexes
    # D-ALIASWCELL: install_basic_hooks publishes the DSKI$/DSKO$ raw-sector
    # buffer through DSKBUF_PTR ($F351), and it has to be the DIRECTORY/RAW
    # tier -- FSECTOR_BUF is the open channel's staged data sector, and sharing
    # it let `DSKO$` write an open file's records over the sector it was given.
    "FWBUF",                    # the FAT/dir metadata sector buffer
    "FLD_CHAN",                 # 0 = not fielded (D-LRVAR)
    "LRSET_W",                  # the field width
    "LRSET_DEST",               # the field's first byte
    "STRPTR",                   # D-CVMOVE: the evaluator's string DESCRIPTOR
                                # pointer, which hk_cv derefs (see pu_deref_body
                                # above); read-only from the disk side
    # D-DPLMOVE (spec-diskcode-eviction.md §6.6m, Joost's ruling): the tokenised
    # LOAD loop runs in disk.rom now and writes main's program area directly.
    # These five are what it touches. 🔴 TXTBASE/TXTMAX are REPACK-DEPENDENT
    # constants, not sysvars -- publishing them here rather than re-declaring
    # them in disk/equates.inc is the whole point: a repack that moves the text
    # ceiling must not leave the loader's bounds check reading the old one, and
    # a hand-copied constant drifts SILENTLY where a generated one cannot.
    "DISKOP_OP",                # the hook's verb selector (FOPEN_SEL aliases it)
    "DISKOP_ERR",               # D-DPLMOVE §6.6o: the ERR code of the last DSKIO
                                # failure. disk.rom's FAT engine reaches the drive
                                # LOCALLY, so it must map and publish this itself --
                                # main's `disk_error` raises whatever is here, and
                                # with nothing written it PRINTED instead
    "CLPTR",                    # store cursor into the program area
    "CLINK",                    # saved link word of the current line
    "TXTBASE",                  # text base: where the seed puts CLPTR/CLINK
    "TXTMAX",                   # text ceiling: the loop's out-of-memory bound
    # D-SAVEPORT (spec-diskcode-eviction.md §6.6ao), step 12: the tokenised SAVE
    # write engine runs in disk.rom now. basic/sv-savdisk.inc is shared BYTE-
    # IDENTICALLY by main, sub and disk, so every name it spells must resolve in
    # all three -- publishing them here is what keeps that body verbatim instead
    # of forking it for the third ROM.
    "PRGEND",                   # addr of the $0000 end-of-program marker: the
                                # image walk's inclusive end is PRGEND+1
    "DSV_PTR",                  # SAVE: the image walk's current source byte
    "DSV_END",                  # SAVE: its last source byte, inclusive
    "DISKSLOT_OK",              # disk_write_begin's own guard. disk.rom plainly
                                # IS the disk ROM, but the body is shared and the
                                # cell is main's -- reading it costs nothing and
                                # keeps the source identical in all three builds
    # D-NAMESTAMP (spec-diskcode-eviction.md §6.6aw): NAME's dir-entry stamp runs
    # in disk.rom now instead of calling back to the sub-ROM tenant. It needs the
    # entry location that main's fat_find recorded -- and these are ALIASED for
    # the same reason main_fat_mount/main_fat_find are: disk.rom HAS cells of
    # these names ($E552/$E554) and they are its OWN FAT's scratch, a DIFFERENT
    # address from main's ($E9F7/$E9F9). 🔴 Reading the wrong one would have been
    # silent -- the stamp would write a valid sector at the wrong offset.
    "main_FWR_DIRSEC=FWR_DIRSEC",   # sector holding the located dir entry
    "main_FWR_DIROFF=FWR_DIROFF",   # byte offset of the entry within it
    # D-COPYLOCAL (spec-diskcode-eviction.md §6.6az): COPY's body runs in
    # disk.rom now instead of calling back twice to the sub-ROM tenant.
    # 🎯 THESE THREE ARE **NOT** ALIASED, AND THE DIFFERENCE IS THE POINT.
    # FWR_DIRSEC above had to be, because disk.rom declares a cell of that name
    # itself. COPY_SRC/COPY_CLUS/COPY_LEFT have exactly ONE consumer in the whole
    # tree -- the body being moved -- and no disk-side twin, so the same address
    # serves both sides and there is nothing to reconcile. The declaration stays
    # in basic/sysvars.inc and arrives here generated, which is what keeps it
    # from drifting.
    # ⚠️ COPY_SRC IS NOT SCRATCH. DISK_FCB_NAME is the only 8.3 buffer, so the
    # SOURCE name has to survive main evaluating the DESTINATION expression
    # through a call-back -- which is exactly why the COPYSTASH selector existed.
    # A main sysvar owned by COPY alone is a cell main's evaluator does not
    # touch; a disk-local scratch pick would have had to argue that.
    "COPY_SRC",                 # the source's 11-byte 8.3 name, across fname_expr
    "COPY_CLUS",                # the source's first cluster, saved across the
                                # destination's delete/create (both clobber
                                # FAT_FIRSTCLUS through fat_find)
    "COPY_LEFT",                # bytes still to copy (4-byte LE)
    # D-FILESLOCAL (spec-diskcode-eviction.md §6.6ba): FILES/LFILES' walk and
    # emit run in disk.rom now. FILES_HASPAT is already published above.
    # ⚠️ FILES_ENTIDX IS AN ALIASED CELL AND THE ALIAS IS DELIBERATE.
    # basic/sysvars.inc puts IN_RDLEN on the same address ($E0FC) with the
    # stated argument that a directory listing and a file read are mutually
    # exclusive. Publishing the address UNCHANGED keeps that argument exactly as
    # it was -- the walk is still the only writer of this name, and it still
    # cannot overlap a read. A disk-local twin would have created a SECOND cell
    # and quietly retired an exclusion nobody re-derived.
    "FILES_ENTIDX",             # dir entry index 0..15 within the current sector
    "LPTPOS",                   # printer head column: LFILES zeroes it at the end
                                # of a listing that emitted something (D-DFEND)
    # D-KILLOPEN: KILL walks the channel table to refuse an OPEN file (64). Read
    # only. FCH_STATESZ is published so the offset of FWR_DIRSEC inside a saved
    # context block is DERIVED rather than written down as 46: sysvars.inc
    # defines FCH_STATESZ = FWR_DIROFF+2-FCH_STATE0, so the span base is
    # main_FWR_DIROFF+2-FCH_STATESZ, and a context-layout change moves both or
    # neither. (Publishing FCH_STATE0 itself failed ram-map-check: it names a
    # span's BASE, not a cell, and has no width of its own.)
    "FCH_ACTIVE",               # channel live in the engine globals, 0 = none
    "FCH_MODES",                # [ch] = 0 closed / 1..4 disk / 5.. device, cassette
    "FCH_STATESZ",              # ⚠️ a CONSTANT: the saved per-channel state size
    "LPT_MODE",                 # ⚠️ a CONSTANT, not a cell: modes below it are
                                # disk files. Published so the disk side's test
                                # cannot drift from fch_mode_class's `cp LPT_MODE`
]
# CALL-BACK: main PAGE-1 targets, reached by an INTER-SLOT CALL, not by an
# absolute one -- the third class, and the one the hook re-architecture needs
# (disk/docs/spec-diskbasic-hook-rearchitecture.md §4 phase 0a).
#
# 🎯 IT IS CEILING-CHECKED IN THE OPPOSITE DIRECTION. The CODE list must be
# BELOW __MEAS_LOW_END because a page-1 ROM reaches it by absolute address with
# page 0 still mapped. A call-back target must be AT OR ABOVE $4000, i.e. in
# page 1 -- because if it were page 0 it would already be reachable that way and
# the inter-slot call would be pure cost. Misfiling in either direction is
# fatal, which is the property that makes the two lists mean different things
# rather than just sit in different variables.
#
# 🔴 THIS PARAGRAPH SAID "Empty today, and that is a statement, not an
# oversight" UNTIL 2026-09-17, WITH SIX NAMES IN THE LIST BELOW IT. Phases 2 and
# 3 filled it and left the prose describing the tree as it was before them --
# and it was still being read as current: it is the sentence behind my telling
# Joost that this tree "has never made a disk->BASIC inter-slot call" and that
# its price was the gate on the channel-verb cluster. `calbak` (disk/kernel.asm)
# is `ld iy,(EXPTBL-1) / jp CALSLT` and stands at NINETEEN call sites.
# [[a-fix-falsifies-the-justification-beside-it]]
# 🟢 AND THE ABI IS MEASURED, NOT ASSUMED -- D-XSLOTABI, two-sided: HL/DE/BC/A
# cross both ways intact and CF crosses too (a callee that SETS it comes back
# set, one that CLEARS it comes back clear; scratchpad/xslot_abi.py leg 4).
# ⚠️ A name here must ALSO be reachable through that entry -- this list makes the
# address available and says nothing about the call sequence.
REQUIRED_DISK_CALLBACK: list[str] = [
    # D-DISKVERB phase 2: KILL's body runs in disk.rom and calls back for the
    # three things only main can do. Measured ABI (D-XSLOTABI): HL/DE/BC/A cross
    # both ways intact, so nothing here needs RAM staging it does not already use.
    "fname_expr",               # HL = cursor in; stashes FN_RESUME + STRSCR
    "pdfcb_resume",             # parse_disk_fcb, then HL = (FN_RESUME)
    "dirverb_op",               # A = DISKOP_SEL_*; runs the dirverb sub-ROM tenant
    # D-DISKVERB2 phase 3 (NAME). CF now crosses too -- measured two-sided, a
    # callee that SETS it comes back set and one that CLEARS it comes back clear
    # (scratchpad/xslot_abi.py leg 4) -- so these two may be read for their carry.
    # ⚠️ ALIASED, because disk.rom HAS ITS OWN fat_mount/fat_find for MSX-DOS.
    # NAME calls MAIN's deliberately: main's fat_find writes the entry location
    # that the dirverb NAME_STAMP tenant then reads, and the disk-local FAT
    # writes its own scratch instead. Which FAT a disk-ROM verb should use is
    # phase 4's question, and this does not pre-empt it.
    "main_fat_mount=fat_mount",   # CF=1: no disk / bad BPB
    "main_fat_find=fat_find",     # HL = 8.3 name; CF=1: not found
    "parse_disk_fcb",           # HL = [len]name text -> DISK_FCB_NAME
    # D-DSKFMOVE phase: DSKF's body runs in disk.rom and calls back for the
    # count, which is a 13 B stub onto the SUB ROM's fatprim tenant -- so the
    # walk is in neither ROM that this call crosses between.
    "fat_count_free",           # DE = free clusters; CF=1: no disk
    # D-LRSETMOVE: LSET/RSET's three BUNDLES. Each is one logical act, not
    # one helper -- the target parse alone would otherwise be five
    # crossings. All three may RAISE, which is safe from a call-back.
    # D-FIELDMOVE: FIELD's TWO bundles. field_item returns a CARRY for "another
    # item follows", so the handler's crossings scale with the item count.
    "field_prologue",           # channel + mode class + FLD_TAB reset
    "field_item",               # one `w AS v$`; CF=1 -> another follows
    "lrset_tgt",                # CF=1: HL = FLD_TAB entry; CF=0: not fielded
    "lrset_rhs",                # STRPTR = the RHS descriptor
    "lrset_finish",             # destination, then the sub-ROM store
    # D-KILLOPEN: KILL refuses a file that is OPEN (64), which needs every
    # open channel's directory position. The live channel's is in the engine
    # globals (main_FWR_DIRSEC above); a saved one is in its context block,
    # whose address only main can compute (the sub-ROM strheap op 18).
    "fch_ctx_addr",             # A = channel -> HL = its context block
]

Profile = collections.namedtuple("Profile", "code ram callback what")

# out-path -> Profile(code symbols, ram symbols, page-1 call-back symbols, what)
PROFILES = {
    "sub/basic-resident-abi.inc":  Profile(REQUIRED_SUB, [], [], "sub-ROM"),
    "disk/basic-resident-abi.inc": Profile(REQUIRED_DISK_CODE,
                                           REQUIRED_DISK_RAM,
                                           REQUIRED_DISK_CALLBACK, "disk ROM"),
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
    prof = profile_for(out_path, profile)
    code, ram, callback, what = prof.code, prof.ram, prof.callback, prof.what
    syms = load_syms(sym_path)

    # 🔴 THE ALIAS SPLIT HAPPENS ONCE, HERE, BEFORE ANY CHECK RUNS. An entry may
    # be written "local=symbol" when the importing ROM already defines that name
    # itself (disk.rom has its own fat_mount/fat_find). A first cut split it only
    # in the EMIT loop, so `missing` looked the whole "local=symbol" string up in
    # the symbol table and refused the build -- the checks must see the SYMBOL
    # half, or an alias could smuggle an unresolvable or mis-classed import past
    # every one of them. `local_of` is only ever used for the emitted spelling.
    def sym_of(entry: str) -> str:
        return entry.rpartition("=")[2]

    def local_of(entry: str) -> str:
        head, _, tail = entry.rpartition("=")
        return head or tail

    code = [sym_of(n) for n in code]
    ram = [sym_of(n) for n in ram]
    emit = [(local_of(n), sym_of(n)) for n in prof.code + prof.ram + prof.callback]
    callback_first = sym_of(prof.callback[0]) if prof.callback else None
    callback = [sym_of(n) for n in callback]

    missing = [n for n in code + ram + callback if n not in syms]
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

    # THE OPPOSITE TEST, and the reason the call-back list is a separate class
    # rather than more entries in the code one: a target BELOW $4000 is already
    # mapped while disk.rom runs, so routing it through an inter-slot call buys
    # nothing and pays for it. PAGE_BASE, not `ceiling` -- the low-region end
    # moves with every carve, and page 1 does not.
    not_page1 = [
        f"{name}=${syms[name]:04X}" for name in callback
        if syms[name] < LOW_CEILING_FALLBACK
    ]
    if not_page1:
        raise SystemExit(
            "FAIL: gen_resident_abi.py: call-back symbol(s) resolve BELOW "
            f"${LOW_CEILING_FALLBACK:04X}, so they are not in page 1: "
            f"{', '.join(not_page1)} — page 0 stays mapped while disk.rom "
            "runs, so these are callable by absolute address and belong in the "
            "CODE list; an inter-slot call to them would be pure overhead"
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
    for local, sym in emit:
        # The section marker goes where the block STARTS, not where the emit
        # loop does -- a header printed above the wrong block is a label that
        # lies, and this file is read by humans deciding which class a new
        # symbol belongs in.
        if callback_first and sym == callback_first:
            lines.append("")
            lines.append("; --- page-1 call-back targets: reached by an "
                         "INTER-SLOT call (MSX2 TH), not an absolute one ---")
        # Leading "0" (same convention pasmo's own --sym output uses, e.g.
        # "fp_div EQU 03632H") so a value whose hex form starts A-F never
        # parses as an identifier instead of a numeric literal.
            # 🔬 CARRY THE SOURCE COMMENT ACROSS (D-RAMABI). This file used to emit
        # bare `NAME equ 0XXXXH` lines, so every ABI cell reached the other ROM
        # with NO declaration of how long it is -- and `scratchpad/
        # ram_map.py`, which IS the only RAM map this project has, could
        # therefore produce no unattributed run for any of them. Main already
        # says: 229 `equ` comments in basic/sysvars.inc end in a bare `(N)`
        # meaning the width in bytes. Copying the comment carries that width
        # (and the cell's MEANING, which is worth more) into disk.rom's and
        # sub.rom's view for free.
        note = ORIGIN.get(sym, "")
        tail = f"   ; main's {sym}" if local != sym else ""
        if note:
            tail = (tail + " -- " + note) if tail else f"   ; {note}"
        lines.append(f"{local} equ 0{syms[sym]:04X}H" + tail)
    lines.append("")
    text = "\n".join(lines)

    if write and out_path:
        with open(out_path, "w") as fh:
            fh.write(text)
    return text


# Where the names are DECLARED, for the comment carry-over above. Sorted globs
# keep the generator deterministic, which `check_resident_abi.py` relies on: it
# re-runs this generator in memory and diffs byte-for-byte.
ORIGIN_TREES = ("basic/*.inc", "basic/*.asm", "sub/*.inc", "sub/*.asm")
_ORIGIN_EQU = re.compile(r"^([A-Za-z_]\w*)\s+equ\s+[^;]*;\s*(.+?)\s*$",
                         re.IGNORECASE)


def _scrape_origin():
    """name -> the source comment on its `equ` line. First declaration wins,
    matching the assembler's own view and this file's other lookups."""
    out = {}
    for pat in ORIGIN_TREES:
        for p in sorted(glob.glob(pat)):
            try:
                lines = open(p).readlines()
            except OSError:
                continue
            for ln in lines:
                m = _ORIGIN_EQU.match(ln.rstrip("\n"))
                if m:
                    out.setdefault(m.group(1), m.group(2))
    return out


ORIGIN = _scrape_origin()


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
