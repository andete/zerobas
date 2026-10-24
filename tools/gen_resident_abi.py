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
    # D-EDCTRL (2026-10-05): the screen editor's cell helpers moved from
    # sub/readline.asm to main's low region (basic/edscreen.asm) so main's own
    # CTRL-B/E/F/N/U handlers share them; the readline tenant imports them here.
    "rl_vpeek",
    "rl_vpoke",
    "rl_vaddr",
    "rl_lastrow",
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
    # (`widen_rhs_operand` stood here until 2026-10-20: unused by disk.rom -- hk_mkfloat
    # names it in a comment only -- and NOT low-closed, its callee `factyp_is2` is
    # page 1. `check_tenant_closure.py --disk` found it; D-DISKREST slice 0.)
    "widen_int_to",             # MKS$/MKD$ (D-DISKREST slice 2): an int argument
    "widen_fac_to",             # ...or a float one, widened into ARGA here
    "round_single_and_pack",    # MKS$/MKD$: pack ARGA as single
    "round_and_finalize",       # ...or as double
    "pu_deref_body",            # D-CVMOVE: hk_cv turns the evaluator's string
                                # DESCRIPTOR into a body pointer itself, rather
                                # than having one marshalled to it -- STRSCR is
                                # where MKI$/MKS$/MKD$ stage their result, so a
                                # pointer parked there is overwritten by the very
                                # round trip these verbs exist for
    "subrom_call",              # D-FMTHOOK: hk_format dispatches the sub-ROM
                                # page-1 format_tenant itself. The dispatcher is
                                # low-region by policy (basic/subrom-boot.asm), so
                                # it is callable by absolute address while
                                # disk.rom holds page 1; CALSLT nests.
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
    # D-LRSETMOVE: hk_lrset walked main's FLD_TAB entry and filled the three
    # cells the sub-ROM store tenant reads (FLD_CHAN, LRSET_W, LRSET_DEST, all
    # gone from this list with D-FLDDESC, 2026-10-17: there is no table, a
    # FIELDed variable's descriptor points at its record, and main's lrset_*
    # bundles fill the cells). FSECTOR_BUF stays: disk/disk.asm asserts that
    # this ROM's SECTOR_BUF IS main's buffer (D-BUFMERGE).
    "FSECTOR_BUF",              # main's data sector buffer = this ROM's SECTOR_BUF
    # D-ALIASWCELL: install_basic_hooks publishes the DSKI$/DSKO$ raw-sector
    # buffer through DSKBUF_PTR ($F351), and it has to be the DIRECTORY/RAW
    # tier -- FSECTOR_BUF is the open channel's staged data sector, and sharing
    # it let `DSKO$` write an open file's records over the sector it was given.
    "FWBUF",                    # the FAT/dir metadata sector buffer
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
    "TXTTAB",                   # D-BASICROM: the program START a SAVE walks from
                                # (sv-savdisk.inc; a cartridge program is not at TXTBASE)
    "TXTMAX",                   # text ceiling: the loop's out-of-memory bound
    "TXTMAX_NODISK",            # the diskless ceiling: disk.asm asserts its cell block under it
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
    # D-ROMSIZE step 1 (2026-10-19): BSAVE's disk write engine
    # (basic/sv-bsvdisk.inc) runs in disk.rom now, not in the sub-ROM save
    # tenant. Main's do_bsave parses into these cells (DSV_END, above, is the
    # end) and crosses H_FOPEN once; the engine reads them, and walks CURPTR.
    "CURPTR",                   # BSAVE: start, then the data walk's cursor
    "EXECPTR",                  # BSAVE: the exec address (header bytes 5-6)
    "VRAM_FLAG",                # BSAVE: 1 = `,S`, the data comes from VRAM
    # D-ROMSIZE step 1 (2026-10-19): BLOAD from disk runs in disk.rom
    # (hk_dpbload) -- the LAST user of the sub-ROM's FAT engine. It reads the
    # $FE header into CURPTR / ENDPTR / EXECPTR (contiguous: the tape path's
    # layout, sysvars.inc), adds main's parsed `,offset` to all three and, with
    # VRAM_FLAG (above) set, stores through WRTVRM. Main's ,R hand-off reads
    # EXECPTR after the crossing.
    "ENDPTR",                   # BLOAD: the header's end address (inclusive)
    "BL_OFS",                   # BLOAD: the `,offset` main's pcr_bload parsed
    # (main_FWR_DIRSEC / main_FWR_DIROFF -- ALIASED imports of main's FWR_DIRSEC /
    # FWR_DIROFF for D-NAMESTAMP's stamp, because disk.rom declares cells of those
    # names itself -- are gone, 2026-10-19: hk_name finds the old entry with
    # disk.rom's OWN fat_find now, so the position is in disk.rom's own cells and
    # the stamp reads them by their bare names. Reading the wrong pair would have
    # been silent -- a valid sector written at the wrong offset -- which is why
    # the alias existed while the lookup was main's.)
    # D-COPYLOCAL (spec-diskcode-eviction.md §6.6az): COPY's body runs in
    # disk.rom now instead of calling back twice to the sub-ROM tenant.
    # 🎯 THESE THREE ARE **NOT** ALIASED, AND THE DIFFERENCE IS THE POINT.
    # FWR_DIRSEC had to be (while it was imported), because disk.rom declares a
    # cell of that name itself. COPY_SRC/COPY_CLUS/COPY_LEFT have exactly ONE consumer in the whole
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
    # only. FCH_STATESZ was published so the offset of FWR_DIRSEC inside a saved
    # context block was DERIVED rather than written down as 46: sysvars.inc
    # defines FCH_STATESZ = FWR_DIROFF+2-FCH_STATE0, so the span base was
    # main_FWR_DIROFF+2-FCH_STATESZ. (That arm went with S10.C, and the
    # main_FWR_* import on 2026-10-19; FCH_STATESZ stays for the row stride,
    # below.) (Publishing FCH_STATE0 itself failed ram-map-check: it names a
    # span's BASE, not a cell, and has no width of its own.)
    "FCH_ACTIVE",               # channel live in the engine globals, 0 = none
    "FCH_MODES",                # [ch] = 0 closed / 1..4 disk / 5.. device, cassette
    "FCH_STATESZ",              # ⚠️ a CONSTANT: the saved per-channel state size
    "FCH_CEIL",                 # ⚠️ a CONSTANT: the channel ceiling -- with TXTMAX and
                                # FCH_STATESZ it DERIVES the engine table's address
                                # (D-FCBSHAPE S2), so the two ROMs cannot drift
    "LPT_MODE",                 # ⚠️ a CONSTANT, not a cell: modes below it are
                                # disk files. Published so the disk side's test
                                # cannot drift from fch_mode_class's `cp LPT_MODE`
    # S10.B: an OUTPUT channel is an MSX-DOS FCB disk.rom keeps in the channel's
    # engine row. The mode and the row's layout are main's declarations (the
    # sub-ROM's t_fch_load read them too until S10.E retired it), published so
    # the ROMs agree on one layout.
    "DOUT_MODE",                # ⚠️ a CONSTANT: FCH_MODES value of such a channel
    "DOUT_BLK",                 # ⚠️ a CONSTANT: row offset of the cached block address
    "FCH_RECMAX",               # ⚠️ a CONSTANT: the record's size at block+9 --
                                # D-FLDDESC: RANDOM's record lives there, and
                                # hk_frnd / GET's clean end space-fill all of it
    "DOUT_FLG",                 # ⚠️ a CONSTANT: row offset of the flags byte
    "DOUT_RFULL",               # ⚠️ a CONSTANT: flag bit, a full record awaits its write
    "DOUT_DEAD",                # ⚠️ a CONSTANT: flag bit, a CLOSE failed
    # (main_FAT_FILESIZE / main_FWR_BYTES -- GONE with S10.E, 2026-10-19. disk.rom
    # kept main's two cells at the FCB's size and random record after every record
    # it wrote (dout_mirror), because LOF / LOC read them; LOF / LOC now ask disk.rom
    # through H_CHIN ops 6 / 8 and get the FCB's value in DE:HL, so no main cell is
    # written from this ROM.)
    # S10.D (2026-10-15): RANDOM files -- OPEN / GET / PUT / CLOSE -- run in
    # disk.rom (hk_frnd / hk_dget). The per-channel tables stay MAIN's (OPEN's
    # LEN= parse writes FCH_RECLENS, LOC reads FCH_RECNOS) and the record engine's
    # scratch cells are main's GP_* block, which nothing in main reads any more.
    # 🎯 NOT ALIASED, COPY_SRC's argument: disk.rom has no cells of these names,
    # one address serves the one consumer, and a sysvar move reaches it by regen.
    "FCH_RECLENS",              # [ch] word: the record length, OPEN's LEN= (default 256)
    "FCH_RECNOS",               # [ch] word: the last GET / PUT's record -- LOC
    "GP_RECNO",                 # the record number, 1-based
    "GP_SEC",                   # the record's file sector
    "GP_WITHIN",                # its offset in that sector
    "GP_CLUS",                  # chain walk: the current cluster
    "GP_CLIDX",                 # chain walk: clusters still to step
    "GP_SECINCL",               # the sector within the final cluster
    "GP_PHYS",                  # the absolute sector
    "GP_FLAGS",                 # 1 = extend (PUT), 0 = read only (GET)
    "GP_RECLEN",                # the live channel's record length
    "GP_SRC",                   # D-STRADDLE: the pass cursor into the record
    "GP_LEFT",                  # D-STRADDLE: record bytes still to move
    # S10.C (2026-10-15): an INPUT channel is disk.rom's FCB too, and its text
    # rules run there (hk_chin, disk/fat.asm). Main keeps the read loops
    # (read_into_strscr, INPUT$'s str_inputd_read) and sets the mode they read in;
    # the numeric item is built straight into STRSCR (published above), its
    # length byte the counter -- so IN_RDLEN, main's own, is not needed here.
    "FCH_RDMODE",               # 2 = INPUT$ (raw: a CR-LF is two bytes of data),
                                # else INPUT# / LINE INPUT# (the CR eats its LF)
    "STRMAX",                   # ⚠️ a CONSTANT: the longest string -- a numeric
                                # item's bytes past it are read and dropped
    # D-DISKREST slice 1: hk_lrset stores the justify flag and the target's
    # descriptor itself, and compares the `=` token.
    "LRSET_JUST",               # the verb's token: bit 0 = RSET
    "MIDS_DEST",                # the target's descriptor, for lrset_finish
    "EQ_TOKEN",                 # ⚠️ a CONSTANT: the `=` token
    # D-DISKREST slice 4: hk_field sets the record's span for field_item.
    "FLD_CUROFF",               # where the next field starts (block+9 first)
    "FLD_END",                  # the byte past the record: the ERR 50 bound
    "RVDESC",                   # slice 5: the [w][ptr] descriptor FIELD stores
    # D-FMTHOOK (C6-FORMAT-TO-DISKROM): CALL FORMAT's menu and its dispatch to
    # the sub-ROM format_tenant run in disk.rom's hk_format now; main keeps the
    # DISKSLOT_OK gate and the H_FORM crossing. The two tenant cells and the
    # entry constants come from main's sym file for the same reason as the rest:
    # a sysvar move or an entry-table change must not leave disk.rom stale.
    "FMT_GEOMSEL",              # main/disk -> tenant: 0 = 360k, 1 = 720k
    "FMT_RESULT",               # tenant -> main: 0 ok / 1 write error (or absent)
    "LINEBUF",                  # read_line's line buffer: the typed choice
    "SUBROM_ENTRY_BASE_P1",     # ⚠️ a CONSTANT: the sub-ROM page-1 jp-table base
    "SUBROM_IDX_FORMAT",        # ⚠️ a CONSTANT: format_tenant's entry index
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
    # (dirverb_op left with D-DSKLOCAL, 2026-10-15: disk.rom does DSKI$ / DSKO$'s
    # sector I/O itself in hk_dsk, and no handler calls back for it any more.)
    # D-DISKVERB2 phase 3 (NAME). CF now crosses too -- measured two-sided, a
    # callee that SETS it comes back set and one that CLEARS it comes back clear
    # (scratchpad/xslot_abi.py leg 4) -- so a call-back may be read for its carry.
    # (main_fat_mount / main_fat_find -- ALIASED imports of main's two FAT shims,
    # because disk.rom has its own fat_mount / fat_find -- are gone, 2026-10-19,
    # and the shims with them: NAME mounts and finds with disk.rom's OWN FAT, as
    # KILL and COPY already did, and AUTOEXEC.BAS's probe moved to disk.rom's
    # hk_auto. Phase 4's "which FAT a disk-ROM verb should use" is answered for
    # every verb here: its own.)
    "parse_disk_fcb",           # HL = [len]name text -> DISK_FCB_NAME
    # (D-DSKFLOCAL, 2026-09-29: `fat_count_free` is no longer a callback --
    # disk.rom assembles the body itself and hk_dskf calls it locally.)
    # D-LRSETMOVE: LSET/RSET's three BUNDLES. Each is one logical act, not
    # one helper -- the target parse alone would otherwise be five
    # crossings. All three may RAISE, which is safe from a call-back.
    # D-FIELDMOVE: FIELD's TWO bundles. field_item returns a CARRY for "another
    # item follows", so the handler's crossings scale with the item count.
    # (field_prologue -- gone, D-DISKREST slice 4: hk_field does the prologue
    # and calls back for its three main-side steps:)
    "eval",                     # FIELD's channel expression: DE
    "fch_check",                # 5 / 59 / 52
    "fch_mode_class",           # A = the mode, 59 if not open, CF = disk
    "field_item",               # one `w AS v$`, PARSED: DE = w, BC = key, HL
                                # (D-DISKREST slice 5: hk_field stores it)
    "tgt_store_desc",           # the variable := RVDESC (BC = key, TGT_ADDR)
    # D-DISKREST slice 1 (2026-10-20): lrset_tgt / lrset_rhs are gone -- hk_lrset
    # parses LSET / RSET itself and calls back ONE HELPER at a time:
    "req_letter",               # the target must be a name (ERR 2)
    "var_str_type",             # A = 1 for a string target
    "tgt_parse_req",            # BC = key, (TGT_ADDR), HL past the reference
    "tgt_desc",                 # HL = the target's descriptor / element offset
    "skip_eq",                  # A = the next non-space byte (Z does not cross)
    "req_operand",              # `LSET A$=` -> ERR 24
    "str_eval",                 # STRPTR = the RHS descriptor; CF = string
    "type_mismatch_error",      # ERR 13, raised from a call-back
    "stmt_error",               # ERR 2, likewise
    "lrset_finish",             # destination, then the sub-ROM store
    # D-KILLOPEN: KILL refuses a file that is OPEN (64), which needed every
    # open channel's directory position -- the live channel's in the engine
    # globals (main_FWR_DIRSEC, an import gone 2026-10-19), a saved one in its
    # context block, whose address only main can compute (the sub-ROM strheap
    # op 18). Since S10.C the walk compares the FCB rows' names (hoc_dout).
    "fch_ctx_addr",             # A = channel -> HL = its context block
    # S10.B: a record write that fails (66 disk full, or a DSKIO code) RAISES
    # from inside H_CHOUT / H_CHCLOSE, as hk_kill's call-backs may: the code is
    # pending in DISKOP_ERR, and disk_error raises it (load_error if none).
    "disk_error",
    # D-FMTHOOK: CALL FORMAT's menu runs in disk.rom (hk_format) and reads its
    # answer with MAIN's line editor, so the CHGET wait happens with main in
    # page 1 (PLAY and the traps keep ticking -- basic/repl.asm's rule). The
    # prompt itself is CHPUT'd from disk.rom: its text is there, and a
    # print_string call-back would read main page 1 at the text's address.
    "read_line",                # LINEBUF <- one edited line, echoed
    # D-CALLSYSTEM: CALL SYSTEM closes every file before handing over to MSX-DOS,
    # as the CF-3300 does (scratchpad/callsystem_peek.out `dosfile`).
    "fch_close_all",
    # S10.D: GET / PUT's `, recno` is parsed in disk.rom's hk_dget, as the CF-3300's
    # disk ROM parses it (scratchpad/dget_run*.out) -- HL = the cursor in, DE = the
    # record and HL past it out; it may RAISE (13, 6), which is safe from here.
    "eval_int16_checked",
    # D-DISKREST slice 3 (2026-10-20): DSKI$ / DSKO$'s `d,s` is parsed in hk_dsk.
    "eval_byte_arg",            # the drive: A = E (0..255, else ERR 5)
    "skip_comma",               # A = the next non-blank byte (Z does not cross)
    # (fch_select -- no longer a call-back since S10.E, 2026-10-19: hk_dget makes
    # its channel live with a plain store to FCH_ACTIVE, still AFTER the
    # evaluator, whose expression may itself select another (`GET #1,LOF(2)`).
    # The switch the call-back ran -- t_fch_load's LOF / LOC mirror -- is gone.)
    # ...and the record's own refusals (5 record 0, 55 past EOF) are raised with
    # their code in A. disk_error would need the code parked in DISKOP_ERR, where
    # a later verb's `disk_error` could find it stale.
    "raise_error",
]

Profile = collections.namedtuple("Profile", "code ram callback what p0cb",
                                 defaults=((),))

# P0CB: main addresses a zerobas-sub2 PAGE-0 tenant calls through p0cb (D-P0CB,
# docs/spec-sub2-p0cb.md) -- the BIOS's RAM CLPRIM maps main's page 0 back in for
# the call, so a target may sit ANYWHERE in main (the low region, the islands,
# page 1). The fourth class, and the only one with no ceiling in either direction:
# what it must NOT be is mistaken for a CODE import -- a page-1 tenant calling one
# of these by absolute address would find its page 0 switched out -- so it is
# emitted under its own header, and check_tenant_closure.py's seed scan stops there.
P0CB_HEADER = ("; --- page-0 call-back (p0cb) targets: zerobas-sub2 page 0 reaches "
               "these through CLPRIM, never by absolute address ---")
REQUIRED_SUB2_P0CB: list[str] = [
    # Every name ALIASED `p0_`: the file is shared with zerobas-sub, which has
    # its own skip_spaces (sub/readdata.asm), and the prefix says at each call
    # site that the address is for p0cb's IX, never for a `call`.
    "p0_chrgtr=chrgtr",         # sub2's RST 10h (s2_chrgtr)
    "p0_outdo=outdo",           # sub2's RST 18h (s2_outdo)
    "p0_bp_ret=bp_ret",         # a bare `ret`: p0cb_selftest's register round trip
    "p0_skip_spaces=skip_spaces",  # p0cb_selftest: a page-1 routine with a contract
    # D-P0CB slice B (2026-10-21): the event-trap statements, sub2/trapstmt.asm.
    "p0_exec_stmt=exec_stmt",   # the continuation every arm returns in DE
    "p0_pl_syntax=pl_syntax",   # trap_syntax: a trappable ERR 2
    "p0_gb_illegal=gb_illegal",  # strig_illegal / eoi_err5: ERR 5
    "p0_ers_undef=ers_undef",   # tll_undef: ERR 8
    "p0_req_gosub=req_gosub",
    "p0_lref_bc=lref_bc",
    "p0_find_line_bc=find_line_bc",
    "p0_onoff_decode=onoff_decode",
    "p0_set_state=set_state",
    "p0_trap_pend=trap_pend",
    "p0_skip_eq=skip_eq",
    "p0_eval_addr=eval_addr",
    "p0_check_fperr_only=check_fperr_only",
    "p0_ztrap_entry=ztrap_entry",
    "p0_skip_comma=skip_comma",
    "p0_inc_skip_paren=inc_skip_paren",
    "p0_inc_eval=inc_eval",
    "p0_get_byte_arg=get_byte_arg",
    # D-P0CB slice C1 (2026-10-21): OPEN / CLOSE / MERGE / MAXFILES,
    # sub2/filestmt.asm. Raises (never return through p0cb):
    "p0_stmt_error=stmt_error",
    "p0_raise_error=raise_error",
    "p0_pdf_badname=pdf_badname",
    "p0_oo_fail_bfn=oo_fail_bfn",
    "p0_dpl_dio=dpl_dio",
    "p0_dpl_direct=dpl_direct",
    "p0_df_notfound=df_notfound",
    "p0_loc_missing=loc_missing",
    # CONTINUATIONS, handed back in DE for main's ex_sub2 to `push de / ret` --
    # never called through p0cb (disk_error / load_error PRINT AND RETURN):
    "p0_clr_wipe=clr_wipe",
    "p0_end_line_end=end_line_end",
    "p0_disk_error=disk_error",
    "p0_load_error=load_error",
    # DATA in main page 1, read by main's dev_cmp (called through p0cb):
    "p0_dev_lpt=dev_lpt",
    "p0_dev_crt=dev_crt",
    "p0_dev_grp=dev_grp",
    "p0_dev_cas=dev_cas",
    # ordinary returning routines:
    "p0_fname_expr=fname_expr",
    "p0_dev_cmp=dev_cmp",
    "p0_nodisk_dev=nodisk_dev",
    "p0_pdfcb_resume=pdfcb_resume",
    "p0_skipsp_test=skipsp_test",
    "p0_upcase=upcase",
    "p0_eval=eval",
    "p0_eval_byte_arg=eval_byte_arg",
    "p0_stmt_bare_end=stmt_bare_end",
    "p0_mxf_require_end=mxf_require_end",
    "p0_oo_parse_reclen=oo_parse_reclen",
    "p0_fch_check_d=fch_check_d",
    "p0_fch_check_nz=fch_check_nz",
    "p0_fch_modes_ptr=fch_modes_ptr",
    "p0_fch_ctx_addr=fch_ctx_addr",
    "p0_fch_do_close_ch=fch_do_close_ch",
    "p0_fch_close_all=fch_close_all",
    "p0_fopen_cross=fopen_cross",
    "p0_fatprim_op=fatprim_op",
    "p0_cas_capture_cut=cas_capture_cut",
    "p0_cas_open_match=cas_open_match",
    "p0_cas_bufp_set=cas_bufp_set",
    "p0_cas_ascii_setup=cas_ascii_setup",
    "p0_cas_write_ea_header=cas_write_ea_header",
    "p0_cas_ascii_drive=cas_ascii_drive",
    "p0_dsk_aopen=dsk_aopen",
    "p0_dsk_ascii_drive=dsk_ascii_drive",
    # D-P0CB slice C2 (2026-10-21): SAVE / CSAVE / BSAVE / LOAD / CLOAD / BLOAD /
    # RUN <name>, sub2/loadsave.asm. CONTINUATIONS (returned in DE, never p0cb'd):
    "p0_run_prog_top=run_prog_top",   # LOAD ,R / RUN <name>
    # (p0_bp_ret above doubles as the handler's own `ret`)
    # ordinary returning routines -- the loaders and writers stay main's:
    # (p0_do_tape_prog left with D-P0CB's tape-loop slice: the reader is sub2's own)
    "p0_disk_prog_load=disk_prog_load",
    "p0_sv_tenant=sv_tenant",         # the sub-ROM tape writers (an inline-byte call)
    "p0_bload_cont=bload_cont",       # BLOAD: the load + its status, in main (D-BLOADSTK)
    "p0_fch_park=fch_park",
    "p0_list_all=list_all",
    "p0_cas_ascii_finish=cas_ascii_finish",
    "p0_cas_capture_name=cas_capture_name",
    "p0_cas_name_cut=cas_name_cut",
    "p0_req_comma=req_comma",
    "p0_check_expr_errors=check_expr_errors",
    # D-P0CB slice D (2026-10-24): SCREEN / COLOR / WIDTH / KEY, sub2/scrstmt.asm.
    # CONTINUATION (returned in DE, never p0cb'd):
    "p0_key_drain=key_drain",         # KEY LIST / KEY n,"str": the print loop, in main
    # ordinary returning routines (CHGMOD / CHGCLR / ERAFNK / DSPFNK are the
    # BIOS's fixed jump-table addresses, from sysvars.inc -- not imports):
    "p0_req_operand=req_operand",
    "p0_eval_byte_checked=eval_byte_checked",
    "p0_spr_tenant=spr_tenant",       # SCREEN's sprite-size ops (shared with SPRITE)
    "p0_key_repaint=key_repaint",     # shared with CLS and the prompt
    "p0_key_op=key_op",               # the keystr tenant (an inline-byte call)
    # D-P0CB, the tape-loop slice (2026-10-24): the tape program reader,
    # sub2/tapeprog.asm. Its TAPION / TAPIN / TAPIOF are the BIOS's fixed
    # jump-table addresses (sysvars.inc), not imports. All are p0cb TAILS or
    # returning calls -- the read's per-byte path imports nothing:
    "p0_cas_ascii_load=cas_ascii_load",       # an $EA program (the ASCII reader)
    "p0_load_commit_prog=load_commit_prog",   # the commit, shared with the disk LOAD
    "p0_dpl_err=dpl_err",             # an unknown id / CLOAD? of $EA: printed, CF set
    "p0_dpl_oom=dpl_oom",             # a store overflow, shared with the disk LOAD
    "p0_print_msg=print_msg",         # CLOAD?'s "Verify error"
    # DATA in main page 1, read by main's print_msg (called through p0cb):
    "p0_err_verify=err_verify",       # err_msgtab[20] names it too
    # D-P0CB, the editor-verb slice (2026-10-24): DELETE / AUTO / RENUM,
    # sub2/pgmedit.asm. CONTINUATION (returned in DE, never p0cb'd):
    "p0_exa_loop=exa_loop",           # AUTO's modal loop: blocks on the keyboard, in main
    # ordinary returning routines (end_line_end / raise_error are imported above):
    "p0_le_call_op=le_call_op",       # the lineedit tenant (LIST and the line store too)
    "p0_print_string=print_string",
    "p0_list_num=list_num",
    "p0_print_crlf=print_crlf",
    # DATA in main's page-0 islands, read by main's print_string (through p0cb):
    "p0_rn_undefined=rn_undefined",   # "Undefined line "
    "p0_rn_in=in_msg",                # " in " (DATA's error suffix shares it)
]

# out-path -> Profile(code symbols, ram symbols, page-1 call-back symbols, what)
PROFILES = {
    "sub/basic-resident-abi.inc":  Profile(REQUIRED_SUB, [], [], "sub-ROM",
                                           REQUIRED_SUB2_P0CB),
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
    # itself (disk.rom has its own fat_mount/fat_find; main_fat_* were the case
    # until 2026-10-19, and none is declared today). A first cut split it only
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
    emit = [(local_of(n), sym_of(n))
            for n in prof.code + prof.ram + prof.callback + list(prof.p0cb)]
    callback_first = sym_of(prof.callback[0]) if prof.callback else None
    p0cb_first = sym_of(prof.p0cb[0]) if prof.p0cb else None
    callback = [sym_of(n) for n in callback]
    p0cb = [sym_of(n) for n in prof.p0cb]

    missing = [n for n in code + ram + callback + p0cb if n not in syms]
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
        if p0cb_first and sym == p0cb_first:
            lines.append("")
            lines.append(P0CB_HEADER)
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
