#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DEFFN RAM HUNT -- where is the BASIC workspace actually free?

🔴 THE REASON THIS IS A TOOL AND NOT A READING. `basic/sysvars.inc` said
*"-> top $E3E8, well below the disk WBUF wall at $E560 (376 B spare)"* and TEN
bytes were free; three later slices had spent the window while the header still
advertised it. **A free-space figure in a comment is a reading with a date on
it, and RAM figures have NO GATE** -- `make wall-assertion-check` polices ROM
claims only. So the map gets WALKED, never read.

WHAT IT DOES. Resolves every `NAME equ <expr>` in a component's source
(including `X equ Y + N*M` chains, iteratively to a fixed point), keeps those
landing in a RAM window, parses each cell's DECLARED WIDTH out of its own
comment, and prints the UNATTRIBUTED RUNS -- the bytes no declaration covers.

🔴 THREE BLINDNESSES FIXED 2026-09-19 (D-RAMMAP), ALL OF THE SAME SHAPE: the
only RAM map we have could not see cells that exist.

**(1) IT READ ONLY `.inc`.** `disk/init.asm` declares ~20 page-3 cells with
`equ` -- `BOOT_SV_A8`, the `R30_*`/`CALSLT_*` save set, ten `RDBLK_*`,
`P1_DEST`/`P1_BLIT`, `WA_SEG`, `CONOUT_CHAR`, `PG_SV_A8`, the 48-byte interrupt
stack, `INT_SP_SAVE`, `CONIN_BUF`, `DRV_TRAMP` -- and NONE of them were in the
map, because the glob was `*.inc`. That is not hypothetical: it is why
`$E7FD..$E813` read as a 25-byte gap when it is `RDBLK_RRSTART` + `DRV_TRAMP`
back to back (`disk/docs/spec-diskcode-eviction.md` §6.6f). Selftest arm A4
pins it, with the old `.inc`-only glob as the negative control.

**(2) IT RANKED BY DELTA BETWEEN NAMES.** It printed *"95 B $E761..$E7C0
RRND_CLUSSEC"* when that cell is ONE BYTE, and left every reader to re-derive
the sizes by hand. An address says where a cell STARTS and never how long it
is -- so the width is now READ FROM THE DECLARATION and an UNDECLARED width is
reported as undeclared, never as 1. A run is printed only when BOTH ends are
pinned by a declared width; everything else stays in the ⚠️ list as *"go read
this"*, which is exactly what the old output was, no better and no worse.

**(3) A NAME DECLARED IN TWO COMPONENTS SILENTLY LOST ONE ADDRESS.** `parse`
kept the first `setdefault` winner, so with basic parsed before disk the whole
per-ROM FAT block at `$E4A0..$E4BF` (`FAT_CURCLUS`, `FAT_FILESIZE`, 20-odd
cells that Option 2 parametrises per ROM) was ABSENT from the merged map --
shadowed by its main-ROM twin at `$E9C9`. Components are therefore resolved in
SEPARATE NAMESPACES and reported separately, which is also the only correct
arithmetic: a run is a statement about one machine's map, and merging two
mutually-exclusive maps computes a gap that exists in neither. Arm A6 pins it.

**(4) AND EIGHT OF THE CELLS (1) MADE VISIBLE STILL DID NOT RESOLVE.** `WA_SEG
equ P1_BLIT + (p1_blit_end - p1_blit_tmpl)` is derived from ASSEMBLER LABELS,
which no source-text resolver can evaluate -- so `WA_SEG`, `CONOUT_CHAR`,
`PG_SV_A8`, `INT_STK_TOP`, `INT_SP_SAVE`, `CONIN_BUF`, `CONIN_MAX` and
`CONIN_COUNT` parsed, landed in `raw`, and then fell out of the map silently.
Reading them was necessary and not sufficient. The build's own `.sym` supplies
them, so it is SEEDED -- but only for names the source resolver could not do
alone, and every name BOTH can do is CROSS-CHECKED. A disagreement is printed
as a finding, because a stale `.sym` filtering real cells away is the failure
this fix would otherwise introduce (`--no-sym` is arm A7's negative control).

🔴 A RUN IS STILL A CANDIDATE, NOT A GUARANTEE. A declared width can be a lie,
and a cell with no `equ` at all -- addressed only as `(SOMETHING + 6)` in code --
is invisible to every version of this tool. Treat a run as *"go read this"*;
the ⚠️ OVERLAPS list exists because a width parsed wrong shows up there first.

🔴 AND OVERLAP IS DESIGNED HERE, NOT A BUG. This tree deliberately aliases
windows between mutually-exclusive execution contexts (the standalone disk
ROM's `SECTOR_BUF` over basic-core's string pool; DRAW's frame buffer over
PAINT's span stack). So the same address legitimately carries several names,
and a hole in ONE component's map can be solidly occupied in another's. That is
the second reason the components are printed apart rather than merged.

⚠️ CALIBRATION: `--selftest` runs six arms, each with a negative control, and
prints every one. A2 plants a synthetic pair with a known gap and asserts the
walk reports THAT gap, so "no holes" is a statement about the map rather than
about a walk that finds nothing by construction. A1 plants an `X equ Y+N` chain,
because a resolver that silently dropped arithmetic would under-report
occupancy -- the failure direction that costs RAM.

USAGE: ram_map.py [lo] [hi] [--basic|--disk] [--inc-only] [--no-sym]
       [--widths] [--check] [--doc] [--selftest]
       --doc writes docs/ram-map.md, one row per ADDRESS with the cell's
       own comment as its purpose; --check verifies that file matches.
       --check is the gate (`make ram-map-check`): a ratchet on the cells
       whose width is not machine-readable, plus the cross-ROM overlay
       table. It never fails on a RUN -- see check()'s own note.
"""
from __future__ import annotations
import glob
import os
import re
import sys

EQU = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+(.+?)\s*(?:;(.*))?$",
                 re.IGNORECASE)

# The BASIC workspace this project owns, below the standard MSX sysvar block.
DEFAULT_LO, DEFAULT_HI = 0xE000, 0xF380
# 🔴 THE DOCUMENT REACHES HIGHER THAN THE ANALYSIS, AND ON PURPOSE (Joost,
# 2026-09-21: *"Does it also contain the officially documented ram variables?"*
# It did not). Above $F380 lies the MSX STANDARD work area -- LINLEN, CSRY/CSRX,
# RG0SAV, EXPTBL/SLTTBL, the published hook table. This project DECLARES 101 of
# those cells because it uses them; it does not OWN them.
# 🎯 SO THEY BELONG IN THE TABLE AND NOT IN THE ARITHMETIC. A reader asking
# "what is at $F3B0" must find LINLEN here. But an unattributed RUN up there
# would be a statement about bytes the BIOS owns and we merely never named, and
# the width RATCHET would demand our comments re-declare extents the MSX
# standard already fixes. Runs and the ratchet stay in [DEFAULT_LO, DEFAULT_HI);
# the document covers DOC_HI and says which half a row is in.
DOC_HI = 0x10000
STD_LO = 0xF380

# ⚠️ THE COMPONENTS ARE SEPARATE ON PURPOSE -- see blindness (3) above and the
# aliasing note. The standalone MSX1 disk ROM (slot 3-1) only ever runs while
# booting/driving MSX-DOS, NEVER while the BASIC interpreter is live, and this
# tree ALREADY aliases across that boundary deliberately (basic-core's string
# pool sits over disk's SECTOR_BUF; PAINT's span stack sits over disk's BDOS
# scratch). So a hole that exists only in BASIC's own map is a REAL candidate
# for BASIC-resident state, and merging the two components hides it.
COMPONENTS = {
    "basic": ("basic/*.inc", "sub/*.inc", "basic/*.asm", "sub/*.asm"),
    "disk":  ("disk/*.inc", "disk/*.asm"),
}

# The build's own symbol tables, per component -- see blindness (4). Missing
# files are simply skipped and SAID SO; this tool must run in a tree that has
# never been built.
SYMS = {
    "basic": ("build/basic-reloc.sym", "build/sub.sym"),
    "disk":  ("build/disk.sym",),
}
SYMLINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+EQU\s+([0-9A-Fa-f]+)H\s*$")


def sym_seed(paths):
    """name -> value, from pasmo `NAME\tEQU 0XXXXH` lines. Also the files
    actually read, so the report can name its own denominator."""
    vals, seen = {}, []
    for p in paths:
        try:
            lines = open(p).readlines()
        except OSError:
            continue
        seen.append(p)
        for ln in lines:
            m = SYMLINE.match(ln.rstrip("\n"))
            if m:
                vals[m.group(1)] = int(m.group(2), 16)
    return vals, seen


def files_for(comp: str, inc_only: bool = False) -> list[str]:
    out: list[str] = []
    for pat in COMPONENTS[comp]:
        if inc_only and not pat.endswith(".inc"):
            continue
        out += sorted(glob.glob(pat))
    return out


# ---------------------------------------------------------------- width parse
# 🔴 ORDER IS LOAD-BEARING AND EACH RULE EARNED ITS PLACE.
#   R1 an explicit `$LO-$HI` in the comment is the author stating the extent.
#   R2 `word`/`int16` -> 2, AHEAD of any N-byte figure. 🔴 THIS ORDER WAS
#      WRONG IN THE FIRST CUT AND THE OVERLAP CHECK CAUGHT IT: `FAT_NAMEPTR
#      equ $E4B9 ; -> 11-byte search name (word)` is a POINTER -- the 11 bytes
#      are what it points AT. So is `DBUF_PTR ; word -> the 512-byte DATA/
#      sector buffer`. In this tree `(word)` types the CELL and a byte count
#      describes the payload, so `word` wins whenever both appear.
#   R3 `N bytes` / `N-byte` / `N B`.   `B` is UPPERCASE-only on purpose: a
#      lowercase alternative makes "24-bit" parse as 24 bytes.
#   R4 `N-bit` (N a multiple of 8).
#   R5 a trailing `(N)` -- THIS TREE'S OWN CONVENTION, and the first cut threw
#      it away. 229 `equ` comments in basic/sysvars.inc + disk/equates.inc end
#      in a bare parenthesised integer and it always means the width in bytes.
#      ANCHORED at the end on purpose: `(0..4)`, `(M19)` and `($F9)` are not
#      widths. Adding it took the basic map from 31% to ~70% covered.
#   R6 `(byte)` -> 1, last, and ONLY parenthesised. 🔴 The first cut matched
#      `byte` anywhere, so "computed VRAM BYTE address ... (2)" read as ONE and
#      "the media BYTE ($F9)" read as one too -- a width too SMALL, which is the
#      direction that INVENTS free space. Five of the runs this tool printed on
#      the day it shipped rested on that mis-parse. R5's negative controls are
#      what caught it.
# Anything else is UNDECLARED, which is NOT the same as 1 and is never rendered
# as a run. Under-reporting free space is the safe direction; inventing it is
# the one that costs a slice a day.
RANGE = re.compile(r"\$([0-9A-Fa-f]{4})\s*(?:-|\.\.|\bto\b)\s*\$([0-9A-Fa-f]{4})")
# 🔴 THE LOOKBEHIND IS NOT DECORATION: `$0B` READ AS "0 BYTES" (D-WIDTHJOIN,
# 2026-09-21). `TKRTOK ; ... token to emit ($0C/$0B)` names two HEX LITERALS,
# and the `0` of `$0B` with the `B` after it is exactly this rule's shape, so
# the cell declared itself ZERO BYTES WIDE and the map believed it. There was
# already a negative control for `($F9)` -- a hex literal in PARENS -- which is
# why this one slipped: the hazard is the `$`, not the parentheses.
NBYTES = re.compile(r"(?<!\$)\b(\d+)[\s-]*(?:[Bb]ytes?|B)\b")
NBITS = re.compile(r"\b(\d+)[\s-]*bit\b")
WORDY = re.compile(r"\b(?:word|int16)\b", re.IGNORECASE)
# 🔴 `byte` ONLY AS A PARENTHESISED TYPE ANNOTATION, never as prose. The first
# cut matched `\bbyte\b` anywhere, so "computed VRAM BYTE address ... (2)" read
# as ONE byte and "the media BYTE ($F9)" read as one too. That is the DANGEROUS
# direction -- a width too small invents an unattributed run that is not free --
# and the R6 vectors are what caught it. `(word)` stays unanchored because in
# this tree it is only ever used as the annotation; `byte` is an ordinary noun.
BYTEY = re.compile(r"\(byte\)", re.IGNORECASE)
# R6 A TRAILING `(N)`, WHICH IS THIS TREE'S OWN CONVENTION AND I WAS THROWING IT
# AWAY. 229 `equ` comments in basic/sysvars.inc + disk/equates.inc end in a bare
# parenthesised integer -- `HOOK_SLOT ... our slot byte for the HPHYD inter-slot
# hook (1)`, `CLOC ... computed VRAM byte address of the current pixel (2)` --
# and it always means the cell's WIDTH IN BYTES. It is last in the order so any
# explicit form wins, and it must be ANCHORED AT THE END: `(0..4)`, `(M19)` and
# `($F9)` are not widths, and an unanchored rule would eat them.
PARENN = re.compile(r"\((\d+)\)\s*$")


# \U0001f534 A `FREE-RAM` CLAIM IS A STATEMENT ABOUT EMPTY SPACE, NOT A CELL'S EXTENT,
# AND READING IT AS ONE IS BACKWARDS (D-WIDTHFREE, 2026-09-21). `; FREE-RAM
# $LO..$HI` is `tools/check_ram_claims.py`'s declared-free-window syntax. One sat
# in `SL_CEIL`'s comment block starting at SL_CEIL's OWN address, and because
# RANGE is the FIRST and most authoritative rule it outranked the `(2)` the cell
# actually declares: a 2-byte pointer read as 40 bytes wide.
FREERAM = re.compile(r"FREE-RAM\s+\$[0-9A-Fa-f]{4}\s*(?:-|\.\.|\bto\b)\s*"
                     r"\$[0-9A-Fa-f]{4}")


def _declared_width_inner(addr: int, comment: str | None):
    """(width, rule) from the cell's own comment, or (None, None).

    🔴 A WIDTH OF ZERO IS NOT A WIDTH, AND THE FIRST CUT RETURNED ONE. Two
    cells read 0 B off hex literals (`$0B`) and the map carried the figure --
    a cell cannot be zero bytes wide, so the structural floor below is a second
    line of defence that does not depend on any one rule's regex being right.
    """
    if not comment:
        return None, None
    comment = FREERAM.sub(" ", comment)     # a free-window claim is not an extent
    m = RANGE.search(comment)
    if m:
        lo, hi = int(m.group(1), 16), int(m.group(2), 16)
        if lo == addr and hi >= lo:
            return hi - lo + 1, "range"
    if WORDY.search(comment):
        return 2, "word"
    m = NBYTES.search(comment)
    if m:
        return int(m.group(1)), "bytes"
    m = NBITS.search(comment)
    if m and int(m.group(1)) % 8 == 0 and int(m.group(1)) > 0:
        return int(m.group(1)) // 8, "bits"
    m = PARENN.search(comment)
    if m:
        return int(m.group(1)), "(n)"
    if BYTEY.search(comment):
        return 1, "byte"
    return None, None


def declared_width(addr: int, comment: str | None):          # noqa: F811
    """`_declared_width` with the structural floor applied: a width of 0 (or
    less) is refused outright, whichever rule produced it."""
    w, r = _declared_width_inner(addr, comment)
    if w is not None and w <= 0:
        return None, None
    return w, r


# ---------------------------------------------------------------- resolve
# 🔴 A GENERATED ABI FILE IMPORTS ANOTHER ROM'S CELLS, AND A GAP BETWEEN TWO OF
# THEM IS NOT THIS ROM'S TO SPEND. `disk/basic-resident-abi.inc` publishes ~35 of
# main's addresses so disk.rom can reach them; main has several HUNDRED cells,
# and the ones in between are simply invisible here. Before D-RAMABI carried the
# source comments across, those cells had no width and produced no run, so the
# problem was hidden by a second defect. Now they have widths -- so the runs must
# be suppressed explicitly: an IMPORTED cell may TERMINATE a run (it is a real
# boundary) but may never OWN one.
IMPORTED_FILES = ("basic-resident-abi.inc",)


def is_imported(path: str) -> bool:
    return any(path.endswith(s) for s in IMPORTED_FILES)


# 🔴 BLINDNESS (5), FOUND 2026-09-20 (D-RAMWIDTH): THE WIDTH WAS DECLARED AND I
# WAS READING THE WRONG LINE. `declared_width` only ever saw the comment on the
# `equ` LINE ITSELF. This tree wraps: a cell whose comment runs past the column
# limit continues on the next line as a bare `; ...`, and the width very often
# lands THERE --
#     SH_SRC   equ  SH_LEN + 1   ; SNAPSHOT arg: source descriptor
#                                ; address (2 B)
# Seventeen main cells inside disk's SECTOR_BUF window read as width-UNDECLARED
# for that reason alone (spec-diskcode-eviction.md §6.6ak), which made the window
# look 27 B occupied when its own source says otherwise. A cell is now read with
# its FULL comment block: the `equ` line plus every following comment-only line,
# stopping at the first line that is not one.
# ⚠️ IT STOPS AT THE NEXT DECLARATION, DELIBERATELY. A trailing prose paragraph
# between two cells belongs to neither, and swallowing it would let a number from
# an unrelated sentence become a width -- the direction that INVENTS free space,
# which is the one this file keeps paying for. Arm A8 is the negative control:
# the same corpus parsed with continuations OFF must read FEWER widths, never
# more, and a paragraph number must not become a width.
CONT = re.compile(r"^\s*;(.*)$")


# 🔴 A SECTION HEADER ENDS A CELL'S COMMENT, AND WITHOUT THIS THE WALK RAN
# STRAIGHT THROUGH ONE (D-WIDTHSECT, 2026-09-21). `; --- Math float pack ... ---`
# is a comment-only line, so the continuation walk kept going and glued the whole
# NEXT SECTION onto `LHS_VARTYPE` -- 1800+ characters, including "a 26-byte map"
# describing `DEFTBL`, a different cell entirely. The width reader then declared
# LHS_VARTYPE 26 bytes wide; it is 1. `PG_SV_A8` read 48 the same way, off a
# neighbouring paragraph about a 48-byte interrupt stack.
# 🎯 `purpose()` ALREADY SPLITS ON `---` FOR EXACTLY THIS REASON. That is the
# THIRD time a lesson lived in that function and not in the width reader beside
# it [[two-correct-rules-can-cancel-each-other]] -- so the stop belongs HERE, in
# the shared walk, where both readers get it.
SECTION = re.compile(r"^\s*-{3,}|-{3,}\s*$")


def continuation(lines, i):
    """The comment-only lines immediately following declaration line `i`
    (1-based), stopping at the next SECTION HEADER."""
    out = []
    for ln in lines[i:]:
        m = CONT.match(ln.rstrip("\n"))
        if not m:
            break
        if SECTION.search(m.group(1)):
            break
        out.append(m.group(1))
    return out


def parse(paths, joint: bool = True):
    """name -> (expr, file, line, comment); plus the intra-component clashes.

    `joint` appends the declaration's continuation comment lines to its comment,
    which is where this tree usually spells the width. False is arm A8's control."""
    raw, clash = {}, {}
    for p in paths:
        try:
            lines = open(p).readlines()
        except OSError:
            continue
        for i, ln in enumerate(lines, 1):
            m = EQU.match(ln.rstrip("\n"))
            if not m:
                continue
            n, e, c = m.group(1), m.group(2).strip(), m.group(3)
            if joint and c is not None:
                c = " ".join([c] + continuation(lines, i))
            if n in raw and raw[n][0] != e:
                clash.setdefault(n, [raw[n]]).append((e, p, i, c))
                continue
            raw.setdefault(n, (e, p, i, c))
    return raw, clash


def resolve(raw):
    """Iterate to a fixed point: `X equ Y+N*M` needs Y resolved first."""
    vals = {}
    expr = dict(raw)
    for _ in range(24):
        progress = False
        for n, rec in expr.items():
            e = rec[0]
            if n in vals:
                continue
            s = e.replace("$", "0x")
            s = re.sub(r"\b([0-9A-Fa-f]+)H\b", r"0x\1", s)
            s = s.replace("&H", "0x").replace("&h", "0x")
            # 🔴 STRIP HEX LITERALS BEFORE SCANNING FOR NAMES. `0xE3E8` yields
            # the identifier `xE3E8` to a bare [A-Za-z_]\w* scan, so every
            # literal reads as an unresolved symbol and the whole map resolves
            # to nothing. The --selftest caught this; a run without it would
            # have printed "0 land in the window" and looked like an answer.
            bare = re.sub(r"0x[0-9A-Fa-f]+", " ", s)
            names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", bare))
            if names - set(vals):
                continue
            try:
                v = eval(s, {"__builtins__": {}}, dict(vals))  # noqa: S307
            except Exception:
                continue
            if isinstance(v, int):
                vals[n] = v
                progress = True
        if not progress:
            break
    return vals, expr


class Map:
    """One component's resolved RAM map inside [lo, hi)."""

    def __init__(self, comp, lo, hi, inc_only=False, raw=None, files=None,
                 use_sym=True, joint=True):
        self.comp, self.lo, self.hi = comp, lo, hi
        self.files = files if files is not None else files_for(comp, inc_only)
        if raw is None:
            self.raw, self.clash = parse(self.files, joint=joint)
        else:
            self.raw, self.clash = raw, {}
        self.vals, self.expr = resolve(self.raw)
        # 🔬 THE SYM IS A SECOND SOURCE, NOT A SUBSTITUTE. It fills only what
        # the source resolver could not do, and disagrees loudly about the
        # rest -- so a stale `.sym` shows up as a finding instead of quietly
        # moving cells around.
        self.from_sym, self.symfiles, self.disagree = {}, [], []
        self.crosschecked = 0
        if use_sym:
            sym, self.symfiles = sym_seed(SYMS.get(comp, ()))
            for n in self.raw:
                if n in sym and n in self.vals:
                    self.crosschecked += 1
                    if self.vals[n] != sym[n]:
                        self.disagree.append((n, self.vals[n], sym[n]))
                elif n in sym:
                    self.vals[n] = sym[n]
                    self.from_sym[n] = sym[n]
        inwin = sorted((v, n) for n, v in self.vals.items() if lo <= v < hi)
        self.byaddr: dict[int, list[str]] = {}
        for v, n in inwin:
            self.byaddr.setdefault(v, []).append(n)
        self.addrs = sorted(self.byaddr)
        # 🔴 PER-ADDRESS WIDTH IS A CONSENSUS, NOT A MAXIMUM. The first cut
        # took the widest declaration among aliased names, and `INT_STK_TOP`
        # ("SP top; 48-byte stack grows down" -- the 48 bytes are BELOW it)
        # then overrode `INT_SP_SAVE` ("(word)") at the same address and ran
        # 46 B into `CONIN_BUF`. When aliased names disagree about their own
        # extent, NOBODY knows the extent: the address becomes DISPUTED and
        # produces no run. An explicit `$LO-$HI` range is the one declaration
        # authoritative enough to settle it.
        self.width: dict[int, int] = {}
        self.rule: dict[int, str] = {}
        self.disputed: dict[int, list] = {}
        # 🔴 THE DECLARATION LINE IS TRIED FIRST, THE JOINED BLOCK SECOND, AND
        # THE TWO RULES THAT MAKE THAT NECESSARY ARE BOTH DELIBERATE (D-WIDTHJOIN,
        # 2026-09-21). Joining continuation lines is why `SH_SRC` has a width at
        # all (A10) -- this tree often spells an extent one line below the `equ`.
        # But rule R6 `(n)` is ANCHORED AT THE END on purpose: its own negative
        # control is "a (2) that is not at the END of the comment", because a
        # parenthesised number mid-prose is not a width. JOINING BREAKS THAT
        # ANCHOR -- `; element address (2)` ends its line with a width and then
        # has the next section's paragraph glued after it, so the `(2)` stops
        # being final and the cell reads UNDECLARED.
        # 🎯 MEASURED: 19 cells were pinned `undeclared` whose OWN line declares
        # a width in so many words. `purpose()` already carries half of this
        # lesson ("it reads the DECLARATION LINE, not the joined block") and the
        # width reader did not. Line first, joined as the fallback, keeps both:
        # the anchor works where it was designed to, and a continuation-line
        # extent still resolves.
        line_raw, _ = parse(self.files, joint=False)
        for a in self.addrs:
            cand = []
            for n in self.byaddr[a]:
                own = line_raw.get(n, (None, None, None, None))[3]
                w, r = declared_width(a, own)
                if w is None:
                    w, r = declared_width(a, self.expr[n][3])
                if w is not None:
                    cand.append((w, r, n))
            if not cand:
                continue
            rng = [c for c in cand if c[1] == "range"]
            if rng:
                self.width[a], self.rule[a] = rng[0][0], rng[0][1]
            elif len({c[0] for c in cand}) == 1:
                self.width[a], self.rule[a] = cand[0][0], cand[0][1]
            else:
                self.disputed[a] = cand
        # 🔴 AND A WIDTH THAT OVERRUNS ITS NEIGHBOUR IS NOT TRUSTED EITHER.
        # `BDOS_RECIDX ; next 128-byte record within SECTOR_BUF (0..4)` is a
        # ONE-BYTE index whose comment names the record size; `ZTRAP`'s range
        # `($E1D1..$E207)` is end-EXCLUSIVE where `DRV_TRAMP`'s `($E800-$E813)`
        # is inclusive. Both parse to a plausible number and both are wrong, so
        # the overlap DEMOTES the width instead of reporting a run from it.
        # Suppressing a run is the safe direction; a wrong run is a day lost.
        # 🔴 BUT AN EXPLICIT `$LO..$HI` RANGE IS EXEMPT, AND LEAVING IT IN WAS
        # THE MAP'S WORST BLINDNESS (D-RAMGATE, 2026-09-21). This tree hosts
        # cells INSIDE big buffers on purpose -- `CAL_BUF $E600` lives inside
        # `FSECTOR_BUF $E5C0..$E7BF` and says so in its own comment, `CAL_BUF2
        # $E800` inside `FWBUF $E7C0..$E9BF`. The overrun rule read those
        # tenants as "the 512 is wrong" and DELETED the width, so the three
        # biggest buffers in the map carried NO trusted extent at all, and the
        # bytes inside them were then reported as unattributed runs. That is
        # where §6.6ar's four false candidates came from.
        # 🎯 A RANGE IS A CLAIM ABOUT A SPAN, NOT ABOUT THE NEXT NAME. The
        # width-consensus code above already calls it "the one declaration
        # authoritative enough to settle" a dispute; it is equally
        # authoritative here. A derived width (`(n B)`, `* N`) keeps the old
        # demotion, because those really are guesses about extent.
        self.overrun: dict[int, tuple] = {}
        for a, b in zip(self.addrs, self.addrs[1:]):
            w = self.width.get(a)
            if w is not None and a + w > b and self.rule.get(a) != "range":
                self.overrun[a] = (w, b)
        for a in self.overrun:
            del self.width[a]
        # 🔑 AND THE SPANS THOSE RANGES COVER ARE WHAT MAKES A GAP ATTRIBUTED.
        # `runs()` used to walk CONSECUTIVE pairs, so a gap between two cells
        # that both sit inside one declared buffer was reported as free. Every
        # address a declared span covers is recorded here once, and a candidate
        # run must clear all of them.
        self.spans: list[tuple] = [(a, a + self.width[a]) for a in self.width
                                   if self.width[a] > 1]
        self.spans.sort()

    def covering(self, lo: int, hi: int):
        """The declared span that CONTAINS [lo, hi), or None.

        A gap inside a buffer is that buffer's, not free space. Returns the
        enclosing span's start so the report can name who owns the bytes.
        """
        for a, b in self.spans:
            if a <= lo and hi <= b:
                return a
        return None

    def site(self, a):
        _, f, i, _ = self.expr[self.byaddr[a][0]]
        return f"{f}:{i}"

    def imported(self, a) -> bool:
        """True when EVERY name at this address came from a generated ABI
        import -- i.e. the cell belongs to another ROM's map, not this one's."""
        return all(is_imported(self.expr[n][1]) for n in self.byaddr[a])

    def runs(self):
        """(size, from, after_name) for gaps NO declaration covers."""
        out = []
        for a, b in zip(self.addrs, self.addrs[1:]):
            w = self.width.get(a)
            if w is None:
                continue
            if self.imported(a):
                continue        # see IMPORTED_FILES: not this ROM's gap to claim
            gap = b - (a + w)
            if gap > 0 and self.covering(a + w, b) is None:
                out.append((gap, a + w, b, a))
        tail = self.hi - (self.addrs[-1] + self.width[self.addrs[-1]]) \
            if (self.addrs and self.addrs[-1] in self.width
                and not self.imported(self.addrs[-1])) else None
        return out, tail

    def undeclared(self):
        """(delta, addr, next, why) where no width can be trusted."""
        out = []
        for a, b in zip(self.addrs, self.addrs[1:]):
            if a in self.width:
                continue
            why = ("overruns" if a in self.overrun else
                   "disputed" if a in self.disputed else "undeclared")
            out.append((b - a, a, b, why))
        return out

    def overlaps(self):
        out = []
        for a, (w, b) in self.overrun.items():
            out.append((a + w - b, a, b, w))
        return out


def report(m: Map) -> None:
    nin = sum(1 for p in m.files if p.endswith(".inc"))
    print(f"\n=== component {m.comp} -- {len(m.files)} files "
          f"({nin} .inc, {len(m.files) - nin} .asm) ===")
    print(f"  denominator: {len(m.raw)} equ definitions; "
          f"{len(m.vals)} resolved; {len(m.addrs)} distinct addresses in "
          f"[{m.lo:04X},{m.hi:04X}); "
          f"{sum(1 for a in m.addrs if len(m.byaddr[a]) > 1)} carrying more "
          f"than one name (deliberate aliasing is normal -- see the header)")
    if m.clash:
        print(f"  ⚠️ {len(m.clash)} name(s) declared twice WITHIN this "
              f"component with different expressions -- first wins: "
              f"{', '.join(sorted(m.clash)[:6])}")
    if m.symfiles:
        insym = sum(1 for n in m.from_sym
                    if m.lo <= m.from_sym[n] < m.hi)
        print(f"  🔬 SYM: {', '.join(m.symfiles)} supplied {len(m.from_sym)} "
              f"name(s) the source alone could not resolve ({insym} in "
              f"window), and cross-checked {m.crosschecked} it could -- "
              f"{len(m.disagree)} disagree.")
        for n, a, b in m.disagree[:10]:
            print(f"     🔴 {n}: source says ${a:04X}, sym says ${b:04X} "
                  f"(stale build, or the expression is mis-parsed)")
    else:
        print("  ⚠️ SYM: no symbol table read -- every cell whose `equ` is "
              "derived from an assembler label is MISSING from this map. "
              "Build first, or expect holes that are really cells.")
    cov = len(m.width)
    pct = (100.0 * cov / len(m.addrs)) if m.addrs else 0.0
    print(f"  🔬 WIDTH COVERAGE: {cov} of {len(m.addrs)} addresses declare "
          f"their width in their own comment ({pct:.0f}%). The rest cannot "
          f"produce a run -- they are the ⚠️ list below, which is exactly the "
          f"old output.")

    runs, tail = m.runs()
    runs.sort(reverse=True)
    nimp = sum(1 for a in m.addrs if m.imported(a))
    print(f"\n  🟢 UNATTRIBUTED RUNS -- {len(runs)} gap(s) that NO declared "
          f"width covers. A candidate, not a guarantee: a cell addressed only "
          f"as an offset in code has no `equ` and is invisible here."
          + (f"\n     ⚠️ {nimp} address(es) here are IMPORTED from another ROM "
             f"through a generated ABI. They bound runs but never own one: this "
             f"map sees only the handful of that ROM's cells the ABI publishes, "
             f"so a gap between two of them is FULL of cells it cannot see."
             if nimp else ""))
    for g, s, e, owner in runs[:20]:
        print(f"  {g:5d} B  ${s:04X}..${e:04X}  after "
              f"{'/'.join(m.byaddr[owner])} (${owner:04X} + "
              f"{m.width[owner]} B, {m.rule[owner]})")
        print(f"            {m.site(owner)}")
    if tail is not None and tail > 0:
        a = m.addrs[-1]
        print(f"  {tail:5d} B  ${a + m.width[a]:04X}..${m.hi:04X}  after "
              f"{'/'.join(m.byaddr[a])} -- to the window top")

    und = m.undeclared()
    und.sort(reverse=True)
    nd = sum(1 for u in und if u[3] == "disputed")
    no = sum(1 for u in und if u[3] == "overruns")
    print(f"\n  ⚠️ NO TRUSTED WIDTH -- {len(und)} cell(s): "
          f"{len(und) - nd - no} declare none, {nd} disputed between aliased "
          f"names, {no} overrun their neighbour. 🔴 Each figure is 'the cell "
          f"at the low address PLUS whatever follows', NEVER free space -- "
          f"this list is exactly the old output. Go read the source.")
    for d, a, b, why in und[:20]:
        print(f"  {d:5d} B  ${a:04X}..${b:04X}  {'/'.join(m.byaddr[a])} "
              f"[{why}]")
        print(f"            {m.site(a)}")

    ov = m.overlaps()
    if ov:
        ov.sort(reverse=True)
        print(f"\n  🔴 OVERLAPS -- {len(ov)}, each already DEMOTED out of the "
              f"runs above. Three classes, and only the third is a defect: "
              f"(a) a CONTAINER whose fields are named separately inside it "
              f"(DISK_FCB, FREAD_LEFT); (b) DESIGNED ALIASING between "
              f"mutually-exclusive contexts (FAT buffers under the cassette "
              f"buffers); (c) a comment this parser read wrong. Read every "
              f"one -- a comment a tool cannot parse is one a human misreads "
              f"too, and (c) is a fixable doc defect.")
        for x, a, b, w in ov[:20]:
            print(f"  {x:5d} B over  ${a:04X}+{w} > ${b:04X}  "
                  f"{'/'.join(m.byaddr[a])} -> {'/'.join(m.byaddr[b])}")
            print(f"            {m.site(a)}")



# ------------------------------------------------------ cross-ROM overlays
# 🔑 THE THING THAT ACTUALLY BITES IS NOT A HOLE, IT IS AN OVERLAY. This tree
# aliases windows between contexts that were mutually exclusive until they
# stopped being: `disk.rom`'s `SECTOR_BUF` sits on top of basic-core's string
# pool, `WBUF` on top of main's own `FSECTOR_BUF`, and the cassette buffers
# live inside both of main's disk buffers. A per-component map cannot answer
# *"what does the disk side destroy while main is running?"* -- and that is
# exactly the question steps 10 and 11 of the disk-code eviction turn on
# (disk/docs/spec-diskcode-eviction.md §6.6aq/§6.6ar).
def overlays(maps: dict, min_width: int = 64) -> list:
    """[(owner_comp, owner_names, lo, hi, [(comp, addr, names)])] -- for every
    declared span of at least `min_width` bytes, the cells of OTHER components
    that fall inside it."""
    out = []
    for comp, m in maps.items():
        for a in sorted(m.width):
            w = m.width[a]
            if w < min_width:
                continue
            guests = []
            for other, om in maps.items():
                if other == comp:
                    continue
                for b in om.addrs:
                    if a <= b < a + w:
                        guests.append((other, b, "/".join(om.byaddr[b])))
            if guests:
                out.append((comp, "/".join(m.byaddr[a]), a, a + w, guests))
    return out



# ------------------------------------------------- the per-ADDRESS document
# 🙋 JOOST ASKED FOR EXACTLY THIS, 2026-09-21: *"what I was expecting is a table
# that says for each RAM address what its purpose(es) is (are)."* The overlay
# table added earlier that day answers a different question -- which SPANS sit
# on top of which -- and he had to say so. This is the table: one row per
# address, every name at it, every component that claims it, and the purpose in
# the author's own words.
DOC = "docs/ram-map.md"
PURPOSE_MAX = 150


def purpose(m, a, flat=None) -> str:
    """The cell's own comment, flattened to one line.

    🔴 THE AUTHOR'S WORDS, NOT A SUMMARY. A generated map that paraphrases is a
    second place for the truth to drift; this quotes and truncates.
    🔴 AND IT READS THE DECLARATION LINE, NOT THE JOINED BLOCK. Joining
    continuation lines is right for the WIDTH -- that is why it exists (§6.6al)
    -- and wrong for the purpose: the first draft of this table had `ERRMARK`
    swallow the next section's whole paragraph. The joined text is the fallback
    for a cell whose own line carries no comment at all.
    """
    for src in ([flat, m] if flat is not None else [m]):
        best = ""
        for n in m.byaddr[a]:
            if n not in src.expr:
                continue
            c = re.sub(r"\s+", " ", (src.expr[n][3] or "").strip())
            c = re.split(r"\s+---+\s+", c)[0].strip()
            if len(c) > len(best):
                best = c
        if best:
            if len(best) > PURPOSE_MAX:
                best = best[:PURPOSE_MAX - 1].rstrip() + "…"
            return best.replace("|", "\\|")
    return ""


def doc_rows(maps: dict, flat: dict | None = None) -> list:
    """[(addr, [(comp, names, width, rule, purpose, site)], [covering])]."""
    everything = sorted({a for m in maps.values() for a in m.addrs})
    out = []
    for a in everything:
        cells, cover = [], []
        for comp in sorted(maps):
            m = maps[comp]
            if a in m.byaddr:
                cells.append((comp, "/".join(m.byaddr[a]), m.width.get(a),
                              m.rule.get(a),
                              purpose(m, a, (flat or {}).get(comp)),
                              m.site(a)))
            else:
                # not a cell of this component -- but is it INSIDE one of its
                # declared buffers? That is the "what does the disk side sit on
                # top of" question, asked one address at a time.
                owner = m.covering(a, a + 1)
                if owner is not None:
                    cover.append((comp, "/".join(m.byaddr[owner]), owner))
        out.append((a, cells, cover))
    return out


def write_doc(maps: dict, path: str | None = None) -> str:
    """Render the document; write it only when `path` is given.

    🔴 RENDERING AND WRITING ARE SEPARATE so the gate and the selftest can
    compare without putting a temporary file anywhere -- the first cut wrote a
    `.gen` beside the real one and a scratch file in the system temp dir, which
    is precisely what `tools/check_temp_root.py` exists to stop.
    """
    # the document's own maps reach into the standard work area; the callers'
    # maps (runs, ratchet, overlays) deliberately do not.
    wide = {c: Map(c, m.lo, DOC_HI) for c, m in maps.items()}
    flat = {c: Map(c, m.lo, DOC_HI, joint=False) for c, m in maps.items()}
    rows = doc_rows(wide, flat)
    L = []
    L.append("<!--")
    L.append("Copyright (c) 2026 Joost Yervante Damad")
    L.append("SPDX-License-Identifier: 0BSD")
    L.append("-->")
    L.append("")
    L.append("# The RAM map — every declared address, and what it is for")
    L.append("")
    L.append("🔴 **GENERATED. Do not edit.** `make ram-map-doc` rewrites it from")
    L.append("`basic/sysvars.inc`, `sub/`, `disk/equates.inc` and `disk/*.asm`;")
    L.append("`make ram-map-check` fails if it has drifted. Change a cell's")
    L.append("comment, not this file.")
    L.append("")
    L.append("Each row is ONE address. **Purpose is the author's own comment**,")
    L.append("quoted and truncated, never a paraphrase — a generated map that")
    L.append("summarises is a second place for the truth to drift.")
    L.append("")
    L.append("🔴 **THREE THINGS THIS TABLE CANNOT TELL YOU**, and they are the")
    L.append("three that have cost this project days:")
    L.append("")
    L.append("* **A cell addressed only as an offset in code has no `equ` and is")
    L.append("  not here at all.** Absence from this table is not emptiness.")
    L.append("* **A blank SIZE means the extent is not machine-readable** — it is")
    L.append("  pinned in `tools/ram-width-allow.txt` with the reason. It does")
    L.append("  NOT mean one byte.")
    L.append("* **A width can be present and WRONG.** `; 32 B … (word)` read as 2")
    L.append("  and `; (4 B each)` read as 4 for a 32-byte array, both on")
    L.append("  2026-09-21. No gate catches that; only reading does.")
    L.append("")
    L.append("⚠️ **OVERLAP IS DESIGNED HERE.** The standalone disk ROM's buffers")
    L.append("sit on top of BASIC's cells on purpose, and the cassette buffers")
    L.append("sit inside both of main's disk buffers. The `also` column names the")
    L.append("other component's cell at the same address; the `inside` column")
    L.append("names the other component's BUFFER this address falls within. That")
    L.append("second one is the question a per-component map cannot answer.")
    L.append("")
    for comp in sorted(maps):
        m, w = maps[comp], wide[comp]
        std = sum(1 for a in w.addrs if a >= STD_LO)
        L.append(f"* **{comp}** — {len(m.addrs)} declared addresses in this "
                 f"project's own workspace `${m.lo:04X}..${STD_LO - 1:04X}` "
                 f"({len(m.width)} with a machine-readable width), plus "
                 f"**{std}** in the MSX standard work area at or above "
                 f"`${STD_LO:04X}`.")
    L.append("")
    L.append(f"## This project's own workspace (`${DEFAULT_LO:04X}..${STD_LO - 1:04X}`)")
    L.append("")
    L.append("| address | size | component | name(s) | purpose | inside |")
    L.append("|---|---|---|---|---|---|")
    split_done = False
    for a, cells, cover in rows:
        if a >= STD_LO and not split_done:
            split_done = True
            L.append("")
            L.append(f"## The MSX standard work area (`${STD_LO:04X}` and above)")
            L.append("")
            L.append("🔴 **THIS PROJECT USES THESE CELLS; IT DOES NOT OWN THEM.**")
            L.append("Their addresses and meanings are the MSX standard's (and")
            L.append("C-BIOS's), not this tree's, so the *purpose* column quotes")
            L.append("our comment about why WE touch the cell — which is not the")
            L.append("same thing as the standard's definition of it. Look the cell")
            L.append("up in the MSX2 Technical Handbook before relying on a row.")
            L.append("")
            L.append("⚠️ **AND THEY ARE DELIBERATELY OUTSIDE THE ARITHMETIC.** The")
            L.append("unattributed-run walk and the width ratchet both stop at")
            L.append(f"`${STD_LO:04X}`: a gap here would be bytes the BIOS owns and")
            L.append("we merely never named, and demanding our comments re-declare")
            L.append("extents the standard already fixes would be noise, not rigour.")
            L.append("")
            L.append("| address | size | component | name(s) | purpose | inside |")
            L.append("|---|---|---|---|---|---|")
        ins = "; ".join(f"`{c}` {n}" for c, n, _o in cover) or ""
        for i, (comp, names, w, rule, why, site) in enumerate(cells):
            size = f"{w} B" if w else ""
            L.append(f"| `${a:04X}` | {size} | `{comp}` | `{names}` | {why} "
                     f"| {ins if i == 0 else ''} |")
    L.append("")
    body = "\n".join(L) + "\n"
    if path is not None:
        with open(path, "w") as f:
            f.write(body)
    return body


# -------------------------------------------------------------- the gate
ALLOW = "tools/ram-width-allow.txt"
ALLOW_RE = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s*(?:#.*)?$")


def width_key(m, a) -> tuple:
    """(component, names, why) -- keyed by NAME, never by address.

    🔴 THE ADDRESS IS THE WRONG KEY AND THIS TREE PROVED IT ON 2026-09-21:
    `SH_OP..SH_ERR` moved 18 bytes out of the disk sector-buffer window that
    same day. A pin on `$E36D` would have gone red on a correct change; a pin
    on the NAME follows the cell.
    """
    why = ("overruns" if a in m.overrun else
           "disputed" if a in m.disputed else "undeclared")
    return (m.comp, "/".join(sorted(m.byaddr[a])), why)


def load_allow(path: str) -> list:
    out = []
    try:
        lines = open(path).readlines()
    except OSError:
        return out
    for ln in lines:
        ln = ln.split("#", 1)[0].strip() if ln.lstrip().startswith("#") else ln
        ln = ln.rstrip("\n")
        if not ln.strip():
            continue
        m = ALLOW_RE.match(ln.strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def check(maps: dict, allow: list) -> tuple:
    """(rc, lines). A RATCHET, in this tree's own allowlist idiom.

    🔴 AN ALLOWLIST THAT ONLY SUPPRESSES IS ROT (`tools/check_temp_root.py`
    says so about its own). This one is a CONTROL IN BOTH DIRECTIONS: a cell
    that appears with no trusted width and is NOT pinned is an error, and a
    PIN that no longer matches is equally an error. The list may SHRINK and
    may never grow, so the ~100 cells whose width lives only in prose can be
    burned down and can never quietly come back.

    ⚠️ AND IT DOES NOT GATE THE RUNS, ON PURPOSE. An unattributed run is a
    CANDIDATE -- a cell addressed only as an offset in code has no `equ` and is
    invisible to every version of this tool. Failing a build on "this looks
    free" would encode exactly the error `tools/check_ram_claims.py`'s header
    warned about.
    """
    have, lines, rc = set(), [], 0
    for comp in sorted(maps):
        m = maps[comp]
        for a in m.addrs:
            if a not in m.width:
                have.add(width_key(m, a))
    want = set(allow)
    new = sorted(have - want)
    stale = sorted(want - have)
    lines.append(f"ram-map: {len(have)} cell(s) with no trusted width, "
                 f"{len(want)} pinned in {ALLOW}")
    if new:
        rc = 1
        lines.append(f"🔴 {len(new)} cell(s) have NO TRUSTED WIDTH and are NOT "
                     f"pinned. Declare the width in the cell's own comment "
                     f"(`(2 B)`, `(n bytes)`, or an explicit `$LO..$HI`), or "
                     f"add a line here with the reason:")
        for c, n, w in new:
            lines.append(f"     {c} {n} {w}")
    if stale:
        rc = 1
        lines.append(f"🔴 {len(stale)} pin(s) no longer match anything -- the "
                     f"cell gained a width, was renamed, or is gone. 🎯 THIS "
                     f"IS THE GOOD DIRECTION: delete the line. The list may "
                     f"SHRINK and may never grow.")
        for c, n, w in stale:
            lines.append(f"     {c} {n} {w}")
    if not new and not stale:
        lines.append("🟢 every cell with no trusted width is pinned, and every "
                     "pin still matches.")
    lines.append("⚠️ THIS GATE DOES NOT CHECK THE RUNS. An unattributed run is "
                 "a CANDIDATE, never free space: a cell addressed only as an "
                 "offset in code has no `equ` and is invisible here.")
    return rc, lines


# ---------------------------------------------------------------- selftest
WIDTH_VECTORS = [
    # (addr, comment, expected width, why this vector exists)
    (0xE800, "4 CALLF trampolines, 5 bytes each ($E800-$E813)", 20,
     "R1 explicit range -- and 4*5=20 agrees with the prose"),
    (0xE7FD, "k_47B2 entry RR, FCB+33..35 (24-bit, 3 bytes)", 3,
     "R3 beats R4: '33..35' is not a width, '24-bit' is not 24 bytes"),
    (0xE774, "byte offset into SECTOR_BUF (word, 0..512)", 2,
     "R4 order: 'byte offset' must not beat '(word)'"),
    (0xE2A0, "512-byte sector buffer", 512, "R2 hyphenated"),
    (0xE9F1, "write buffer length (2 B)", 2, "R3 bare B"),
    (0xE4B9, "-> 11-byte search name (word)", 2,
     "R2 beats R3: the 11 bytes are the POINTEE, the cell is a word"),
    (0xE816, "word -> the 512-byte DATA/sector buffer", 2,
     "R2 beats R3 again -- the overlap check found both of these"),
    (0xE55D, "our slot byte for the HPHYD inter-slot hook (1)", 1,
     "R6 this tree's OWN convention: 229 equ comments end in a bare (N)"),
    (0xF92A, "computed VRAM byte address of the current pixel (2)", 2,
     "R6 again -- and it is why coverage went 31% -> 72% on the basic map"),
    (0xF247, "current drive index (0..4)", None,
     "🔴 NEGATIVE CONTROL: a RANGE in parens is not a width"),
    (0x5058, "MSX-DOS-1 kernel SETDTA-time entry (M19)", None,
     "🔴 NEGATIVE CONTROL: a finding id in parens is not a width"),
    (0xE000, "the media byte ($F9)", None,
     "🔴 NEGATIVE CONTROL: a hex literal in parens is not a width"),
    (0xE001, "a (2) that is not at the END of the comment", None,
     "🔴 NEGATIVE CONTROL: R6 is ANCHORED -- unanchor it and this reads as 2"),
    (0xE760, "saved $A8 primary-slot config", None,
     "🔴 NEGATIVE CONTROL: no width declared -> UNDECLARED, never 1"),
    (0xE761, "saved slot secondary ($FFFF) live value", None,
     "🔴 NEGATIVE CONTROL: a $-literal is not a range"),
    (0xE800, "lives at $E900-$E9FF", None,
     "🔴 NEGATIVE CONTROL: a range that is not THIS cell's is ignored"),
    # 🔴 D-WIDTHJOIN (2026-09-21): TWO DEFECTS THE ARMS ABOVE ALL MISSED,
    # pinned here by the real comment that produced one of them.
    (0xE02A, "tokeniser: &H/&O constant token to emit ($0C/$0B)", None,
     "🔴 NEGATIVE CONTROL, AND IT SHIPPED WRONG: `$0B` read as `0 B`, so "
     "TKRTOK declared itself ZERO bytes wide. The `($F9)` control above "
     "missed it because the hazard is the `$`, not the parens"),
    (0xE02B, "a plain 0 B claim", None,
     "🔴 NEGATIVE CONTROL: a width of ZERO is refused whatever rule made it"),
    (0xE02C, "0 bytes of anything", None,
     "🔴 NEGATIVE CONTROL: the same floor through the spelled-out form"),
    (0xE02D, "emit $1B then $2B", None,
     "🔴 NEGATIVE CONTROL: neither hex literal is a byte count"),
    (0xE02E, "a 12 B cell that mentions $0B in passing", 12,
     "🟢 POSITIVE CONTROL: the lookbehind must not blind the rule to a REAL "
     "count sitting beside a hex literal"),
    # 🔴 D-WIDTHFREE (2026-09-21): a FREE-RAM claim is about EMPTY space.
    (0xE058, "ceiling (2) FREE-RAM $E058..$E07F the rest of the retired stack",
     None,
     "🔴 NEGATIVE CONTROL, AND IT SHIPPED WRONG: a `FREE-RAM $LO..$HI` claim "
     "starting at the cell's OWN address outranked the `(2)` it declares, "
     "because RANGE is the first rule -- SL_CEIL read 40 B and is a POINTER. "
     "\u26a0\ufe0f The answer is None, NOT 2: stripping the claim removes a WRONG "
     "width, it does not manufacture a right one (the `(2)` is no longer final, "
     "and R6 is anchored). The cell still has to declare itself on its own line"),
    (0xE059, "ceiling FREE-RAM $E059..$E07F the rest (2 B)", 2,
     "\U0001f7e2 POSITIVE CONTROL: ...and once it DOES, the claim beside it is "
     "harmless"),
    (0xE5C0, "file data / read sector buffer ($E5C0..$E7BF)", 512,
     "🟢 POSITIVE CONTROL: a REAL declared range is still authoritative -- the "
     "FREE-RAM strip must not blind the rule that settles the big buffers"),
]


def selftest(lo, hi) -> int:
    ok = {}

    # ---- A3 width vocabulary, with three negative controls -----------------
    bad = []
    for addr, cmt, want, why in WIDTH_VECTORS:
        got, _ = declared_width(addr, cmt)
        if got != want:
            bad.append(f"${addr:04X} {cmt!r}: want {want}, got {got}")
        print(f"    A3 {'ok ' if got == want else 'FAIL'} "
              f"{str(want):>5} <- {cmt[:46]!r:48} {why}")
    ok["A3 width vocabulary (22 vectors, 13 negative)"] = not bad
    for b in bad:
        print(f"    A3 MISMATCH {b}")

    # ---- A1/A2 planted chain + planted gap, in the OLD shape ---------------
    raw, _ = parse(files_for("basic"))
    real, _ = resolve(dict(raw))
    ra = sorted({v for n, v in real.items() if lo <= v < hi})
    # 🔴 PLANT IN A WINDOW NO REAL CELL OCCUPIES -- AND THAT IS THE SECOND TIME
    # THIS FIXTURE HAS BEEN WRONG WHILE THE WALK WAS RIGHT. The first cut
    # planted at a hand-picked $E7A0..$E7F0 and read a 24 B gap instead of 72,
    # because a REAL name sits at $E7C0 between the two plants; the fix was to
    # take the map's own largest gap. **That fix died the day `runs()` learned
    # about containment (D-RAMGATE):** the largest raw gap is now INSIDE
    # `TOKBUF`'s declared span, so every planted run was correctly suppressed
    # and three arms went red on a corpus change rather than on a defect.
    # 🎯 SO THE FIXTURE STOPS RIDING THE CORPUS. `$D000..$D800` carries no `equ`
    # in either component (asserted below, so this cannot rot silently), the
    # plants get a window of their own, and an arm can never again fail because
    # a real declaration moved. The real corpus is still exercised -- by A6, A7
    # and A10, which are ABOUT it.
    PLANT_LO, PLANT_HI = 0xD000, 0xD800
    ok["A0 the plant window is empty of real cells, in BOTH components -- "
       "without this every planted arm below is a claim about a collision"] = \
        not [v for v in real.values() if PLANT_LO <= v < PLANT_HI] and \
        not [v for v in resolve(dict(parse(files_for("disk"))[0]))[0].values()
             if PLANT_LO <= v < PLANT_HI]
    base = PLANT_LO + 8
    p = dict(raw)
    p["__PLANT_BASE"] = (f"${base:04X}", "<plant>", 0, None)
    p["__PLANT_STEP"] = ("__PLANT_BASE + 4*2", "<plant>", 0, None)
    p["__PLANT_FAR"] = (f"${base + 24:04X}", "<plant>", 0, None)
    # A5's plants ride in the same fixture: a DECLARED 8-byte cell 24 B before
    # its neighbour must yield a 16 B RUN, and an undeclared one must not.
    p["__PW_BASE"] = (f"${base + 64:04X}", "<plant>", 0, "the thing (8 bytes)")
    p["__PW_NEXT"] = (f"${base + 88:04X}", "<plant>", 0, "next (word)")
    m = Map("basic", PLANT_LO, PLANT_HI, raw=p, files=files_for("basic"))
    want_step = m.vals["__PLANT_BASE"] + 8
    ok["A1 arithmetic chain `X equ Y+N*M` resolves"] = \
        m.vals.get("__PLANT_STEP") == want_step
    gap = next((b - a for a, b in zip(m.addrs, m.addrs[1:])
                if a == want_step), None)
    ok["A2 planted 16 B gap is found by the walk"] = gap == 16

    # ---- A5 run vs undeclared, with the undeclared plant as the control ----
    runs, _ = m.runs()
    got_run = [(g, s) for g, s, e, o in runs if o == m.vals["__PW_BASE"]]
    ok["A5 declared width -> a 16 B unattributed run"] = \
        got_run == [(16, m.vals["__PW_BASE"] + 8)]
    und_addrs = {a for _, a, _, _ in m.undeclared()}
    run_owners = {o for _, _, _, o in runs}
    ok["A5 NEGATIVE: undeclared plant is in ⚠️, NOT in 🟢"] = \
        (m.vals["__PLANT_BASE"] in und_addrs
         and m.vals["__PLANT_BASE"] not in run_owners)

    # ---- A4 .asm visibility, with the old .inc-only glob as the control ----
    d_all = Map("disk", lo, hi)
    d_inc = Map("disk", lo, hi, inc_only=True)
    ok["A4 `.asm` cells are visible (DRV_TRAMP $E800, disk/init.asm)"] = \
        d_all.vals.get("DRV_TRAMP") == 0xE800
    ok["A4 NEGATIVE: the old `.inc`-only glob could NOT see it"] = \
        "DRV_TRAMP" not in d_inc.vals
    ok["A4 and it brought >=15 more page-3 cells with it"] = \
        len(d_all.addrs) - len(d_inc.addrs) >= 15

    # ---- A6 per-component namespaces (the shadowing control) ---------------
    b_all = Map("basic", lo, hi)
    ok["A6 per-ROM twin visible in BOTH maps (FAT_CURCLUS)"] = \
        (b_all.vals.get("FAT_CURCLUS") == 0xE9C9
         and d_all.vals.get("FAT_CURCLUS") == 0xE4A9)
    merged, _ = parse(files_for("basic") + files_for("disk"))
    mvals, _ = resolve(merged)
    ok["A6 NEGATIVE: one merged namespace shadows it to a single address"] = \
        mvals.get("FAT_CURCLUS") == 0xE9C9 and 0xE4A9 not in set(mvals.values())

    # ---- A8 an untrustworthy width must DEMOTE, not produce a number ------
    p2 = dict(raw)
    p2["__OV_A"] = (f"${base + 128:04X}", "<plant>", 0, "big (64 bytes)")
    p2["__OV_B"] = (f"${base + 136:04X}", "<plant>", 0, "next (word)")
    p2["__DI_A"] = (f"${base + 200:04X}", "<plant>", 0, "one way (8 bytes)")
    p2["__DI_A2"] = (f"${base + 200:04X}", "<plant>", 0, "other way (word)")
    p2["__DI_B"] = (f"${base + 240:04X}", "<plant>", 0, "after (word)")
    m2 = Map("basic", PLANT_LO, PLANT_HI, raw=p2, files=files_for("basic"))
    a_ov, a_di = m2.vals["__OV_A"], m2.vals["__DI_A"]
    r2_owners = {o for _, _, _, o in m2.runs()[0]}
    ok["A8 a width that overruns its neighbour yields NO run"] = \
        a_ov in m2.overrun and a_ov not in r2_owners and a_ov not in m2.width
    ok["A8 aliased names that disagree -> DISPUTED, no run"] = \
        a_di in m2.disputed and a_di not in r2_owners
    ok["A8 NEGATIVE: both still appear in the ⚠️ list"] = \
        {a_ov, a_di} <= {a for _, a, _, _ in m2.undeclared()}

    # ---- A9 an IMPORTED cell bounds a run but never owns one --------------
    p3 = dict(raw)
    # same cell, same width, same following gap -- the ONLY difference is which
    # file declared it. That is what makes this a control rather than a demo.
    p3["__IMP_A"] = (f"${base + 300:04X}", "disk/basic-resident-abi.inc", 0,
                     "imported (2)")
    p3["__IMP_B"] = (f"${base + 340:04X}", "<plant>", 0, "native (2)")
    p3["__NAT_A"] = (f"${base + 400:04X}", "<plant>", 0, "native (2)")
    p3["__NAT_B"] = (f"${base + 440:04X}", "<plant>", 0, "native (2)")
    m3 = Map("basic", PLANT_LO, PLANT_HI, raw=p3, files=files_for("basic"))
    owners3 = {o for _, _, _, o in m3.runs()[0]}
    ok["A9 an ABI-IMPORTED cell owns NO run (the gap after it is full of the "
       "other ROM's cells this map cannot see)"] = \
        m3.vals["__IMP_A"] in m3.width and m3.vals["__IMP_A"] not in owners3
    ok["A9 NEGATIVE: the SAME shape in a native file DOES own one, so the "
       "suppression is about the FILE and not about the fixture"] = \
        m3.vals["__NAT_A"] in owners3

    # ---- A10 the width was DECLARED and the parser read the wrong line ----
    # D-RAMWIDTH, blindness (5). This tree wraps a long `equ` comment onto bare
    # `;` continuation lines and the width very often lands there.
    lines = ["SH_SRC   equ  SH_LEN + 1   ; SNAPSHOT arg: source descriptor\n",
             "                           ; address (2 B)\n",
             "SH_PTR   equ  SH_SRC + 2   ; result: ALLOC's body ptr\n",
             "\n",
             "; a loose paragraph that mentions 99 bytes and owns no cell\n"]
    ok["A10 a continuation line is joined to its declaration"] = \
        continuation(lines, 1) == [" SNAPSHOT-less second line placeholder"][:0] + \
        [l.rstrip("\n").split(";", 1)[1] for l in lines[1:2]]
    joined = "x " + " ".join(continuation(lines, 1))
    ok["A10 ...and the width on it is then READ (2 B)"] = \
        declared_width(0xE36F, joined)[0] == 2
    ok["A10 NEGATIVE: the declaration line ALONE has no width -- which is "
       "exactly what made 17 cells read as undeclared"] = \
        declared_width(0xE36F, " SNAPSHOT arg: source descriptor")[0] is None
    ok["A10 NEGATIVE: joining STOPS at the next declaration, so a later "
       "cell's comment cannot donate a width"] = \
        continuation(lines, 3) == []
    ok["A10 NEGATIVE: and it stops before a loose paragraph, so its '99 "
       "bytes' can never become a width"] = \
        all("99" not in c for c in continuation(lines, 1))
    # ---- A16 a SECTION HEADER ends the comment (D-WIDTHSECT) --------------
    # 🔴 THE A10 PARAGRAPH ARM ABOVE IS SEPARATED BY A BLANK LINE, AND THAT IS
    # WHY IT MISSED THIS: a `; --- ... ---` header is itself a COMMENT line, so
    # the walk ran straight through it into the next section. Measured on the
    # real corpus -- `LHS_VARTYPE` swallowed 1800+ characters including "a
    # 26-byte map" describing DEFTBL and declared itself 26 bytes wide; it is 1.
    sect = ["LV   equ  $F152   ; the LHS variable's resolved\n",
            "                  ; type, latched before eval\n",
            "; --- Math float pack, slice F3 S3b RAM -------------------\n",
            "; docs/spec.md: the per-letter DEFtbl, a 26-byte map\n",
            "; (index name0-'A', A..Z) holding the default type\n"]
    ok["A16 the walk STOPS at a `; --- section --- ` header"] = \
        len(continuation(sect, 1)) == 1
    ok["A16 NEGATIVE: so the NEXT section's '26-byte' cannot become this "
       "cell's width"] = \
        declared_width(0xF152, "x " + " ".join(continuation(sect, 1)))[0] is None
    ok["A16 NEGATIVE: without the stop it WOULD have -- the arm can fail"] = \
        declared_width(0xF152, "x " + " ".join(
            l.split(";", 1)[1] for l in sect[1:]))[0] == 26
    # 🔴 POSITIVE CONTROL: an ordinary continuation still joins, or this stop
    # would silently undo A10 and take SH_SRC's width with it.
    ok["A16 POSITIVE: a continuation with no header still joins"] = \
        len(continuation(lines, 1)) == 1
    # ...and the same thing on the REAL corpus, two-sided.
    b_joint = Map("basic", lo, hi, joint=True)
    b_flat = Map("basic", lo, hi, joint=False)
    ok["A10 on the real corpus it RAISES coverage"] = \
        len(b_joint.width) > len(b_flat.width)
    ok["A10 NEGATIVE: and the control reproduces the OLD coverage exactly, "
       "so the gain is the continuations and nothing else"] = \
        len(b_flat.width) == len(Map("basic", lo, hi, joint=False).width)
    a_shsrc = b_joint.vals["SH_SRC"]
    ok[f"A10 SH_SRC ${a_shsrc:04X} reads 2 B with joining and nothing "
       "without it (the ADDRESS is derived, not typed -- it moved on "
       "2026-09-21 and a typed one would have rotted)"] = \
        b_joint.width.get(a_shsrc) == 2 and b_flat.width.get(a_shsrc) is None


    # ---- A11 CONTAINMENT: a gap inside a declared span is NOT a run --------
    # D-RAMGATE. This is the blindness that produced §6.6ar's false candidates:
    # `CAL_BUF2 $E800` sits inside `FWBUF $E7C0..$E9BF` and the walk reported
    # the 192 B after it as unattributed, because it only ever compared
    # CONSECUTIVE pairs.
    p4 = dict(raw)
    p4["__BUF"] = (f"${PLANT_LO + 0x100:04X}", "<plant>", 0,
                   f"a buffer (${PLANT_LO + 0x100:04X}..${PLANT_LO + 0x1FF:04X})")
    p4["__TENANT"] = (f"${PLANT_LO + 0x140:04X}", "<plant>", 0, "inside it (2)")
    p4["__AFTER"] = (f"${PLANT_LO + 0x200:04X}", "<plant>", 0, "next (word)")
    m4 = Map("basic", PLANT_LO, PLANT_HI, raw=p4, files=files_for("basic"))
    a_buf, a_ten = m4.vals["__BUF"], m4.vals["__TENANT"]
    ok["A11 an explicit RANGE keeps its width although a cell sits inside "
       "it -- the overrun demotion would have deleted it"] = \
        m4.width.get(a_buf) == 256 and a_buf not in m4.overrun
    r4 = {(g, st) for g, st, e, o in m4.runs()[0]}
    ok["A11 the gap after the TENANT is attributed to the enclosing buffer, "
       "not reported as free"] = \
        not any(st == a_ten + 2 for _g, st in r4)
    ok["A11 covering() names the owner"] = \
        m4.covering(a_ten + 2, a_buf + 256) == a_buf
    # NEGATIVE: the same gap OUTSIDE any span is still a run, so containment
    # suppresses by CONTAINMENT and not by accident.
    p5 = dict(raw)
    p5["__L"] = (f"${PLANT_LO + 0x300:04X}", "<plant>", 0, "lone (2)")
    p5["__R"] = (f"${PLANT_LO + 0x340:04X}", "<plant>", 0, "next (word)")
    m5 = Map("basic", PLANT_LO, PLANT_HI, raw=p5, files=files_for("basic"))
    ok["A11 NEGATIVE: the same shape with NO enclosing span IS a run"] = \
        any(st == m5.vals["__L"] + 2 for _g, st, _e, _o in m5.runs()[0])
    ok["A11 NEGATIVE: a DERIVED width that overruns is still demoted -- the "
       "exemption is for explicit ranges only"] = \
        m2.vals["__OV_A"] in m2.overrun

    # ---- A12 the gate: a ratchet that fails in BOTH directions ------------
    class _M:
        def __init__(self, comp, addrs, width, byaddr):
            self.comp, self.addrs, self.width, self.byaddr = \
                comp, addrs, width, byaddr
            self.overrun, self.disputed = {}, {}
    fake = {"x": _M("x", [1, 2], {1: 2}, {1: ["A"], 2: ["B"]})}
    rc0, _ = check(fake, [("x", "B", "undeclared")])
    ok["A12 pinned + matching -> green"] = rc0 == 0
    rc1, l1 = check(fake, [])
    ok["A12 NEGATIVE: an UNPINNED width-less cell is RED"] = \
        rc1 == 1 and any("NOT pinned" in x for x in l1)
    rc2, l2 = check(fake, [("x", "B", "undeclared"), ("x", "GONE", "undeclared")])
    ok["A12 NEGATIVE: a pin that matches NOTHING is RED -- the list may "
       "SHRINK and may never grow"] = \
        rc2 == 1 and any("no longer match" in x for x in l2)
    ok["A12 the gate SAYS it does not police the runs"] = \
        any("CANDIDATE, never free space" in x for x in check(fake, [
            ("x", "B", "undeclared")])[1])
    ok["A12 the pin is keyed by NAME, not by address"] = \
        width_key(_M("x", [9], {}, {9: ["Z", "Y"]}), 9) == \
        ("x", "Y/Z", "undeclared")
    ok["A12 the real allowlist parses and is non-empty"] = \
        len(load_allow(ALLOW)) > 0
    ok["A12 NEGATIVE: a missing allowlist parses as EMPTY, which makes the "
       "gate RED rather than silently green"] = \
        load_allow("/nonexistent/ram-width-allow.txt") == []

    # ---- A13 the cross-ROM overlay, which is the whole point --------------
    maps13 = {"basic": b_all, "disk": d_all}
    ov13 = overlays(maps13)
    owners13 = {(c, n) for c, n, _a, _b, _g in ov13}
    ok["A13 disk's SECTOR_BUF is reported as hosting main's cells -- the "
       "overlay §6.6aq is about"] = \
        any(c == "disk" and "SECTOR_BUF" in n for c, n in owners13)
    ok["A13 ...and it names more than one guest"] = \
        any(c == "disk" and "SECTOR_BUF" in n and len(g) > 1
            for c, n, _a, _b, g in ov13)
    ok["A13 NEGATIVE: a component never reports ITSELF as a guest"] = \
        all(all(gc != c for gc, _ga, _gn in g)
            for c, _n, _a, _b, g in ov13)
    ok["A13 NEGATIVE: a span below the threshold is not reported"] = \
        overlays(maps13, min_width=0x10000) == []


    # ---- A14 the per-ADDRESS document, which is what was actually asked for -
    maps14 = {"basic": b_all, "disk": d_all}
    rows14 = doc_rows(maps14, {c: Map(c, lo, hi, joint=False)
                               for c in maps14})
    byaddr14 = {a: (cells, cover) for a, cells, cover in rows14}
    ok["A14 every declared address of BOTH components has a row"] = \
        set(byaddr14) == set(b_all.addrs) | set(d_all.addrs)
    # 🔴 THE PROBE ADDRESS MUST BE A DECLARED CELL, NOT JUST AN ADDRESS INSIDE
    # THE BUFFER: this table has a row per DECLARATION, so a byte in the middle
    # of TEMPPOOL's body has no row to carry the annotation. The first cut asked
    # about SECTOR_BUF+$100 and read an empty default as a failure.
    ok["A14 a basic cell INSIDE disk's SECTOR_BUF names that buffer"] = \
        any("SECTOR_BUF" in n for _c, n, _o
            in byaddr14[b_all.vals["GFX_PTOP"]][1])
    ok["A14 NEGATIVE: an address outside every foreign buffer names none"] = \
        byaddr14[b_all.vals["TKLNUM"]][1] == []
    # SH_SRC's width lives on its continuation line ("address (2 B)"), which is
    # exactly why joining exists -- and exactly why the PURPOSE must not join.
    flat14 = Map("basic", lo, hi, joint=False)
    a_src = b_all.vals["SH_SRC"]
    ok["A14 the purpose is the DECLARATION line, not the joined block -- the "
       "first draft had a cell swallow the next section's paragraph"] = \
        len(purpose(b_all, a_src, flat14)) < len(purpose(b_all, a_src))
    ok["A14 a pipe in a comment is escaped, so one cell cannot split a row"] = \
        all("|" not in p.replace("\\|", "")
            for _a, cells, _cv in rows14 for p in [c[4] for c in cells])
    ok["A14 NEGATIVE: a purpose longer than the cap is truncated with an "
       "ellipsis rather than silently cut"] = \
        all(len(p) <= PURPOSE_MAX and (len(p) < PURPOSE_MAX or p.endswith("…"))
            for _a, cells, _cv in rows14 for p in [c[4] for c in cells])


    # ---- A15 the document reaches the MSX standard work area; the ARITHMETIC
    # does NOT. 🙋 Joost, 2026-09-21: "Does it also contain the officially
    # documented ram variables?" -- it did not, and the fix must not drag the
    # run walk and the width ratchet up there with it.
    wide15 = {c: Map(c, lo, DOC_HI) for c in ("basic", "disk")}
    ok["A15 the wide map SEES the standard work area (LINLEN, EXPTBL)"] = \
        any(a >= STD_LO for a in wide15["basic"].addrs) and \
        wide15["basic"].vals.get("LINLEN", 0) >= STD_LO and \
        wide15["disk"].vals.get("EXPTBL", 0) >= STD_LO
    ok["A15 NEGATIVE: the ANALYSIS map stops below it, so no run and no pin "
       "is ever claimed up there"] = \
        all(a < STD_LO for a in b_all.addrs) and \
        all(a < STD_LO for a in d_all.addrs)
    doc15 = write_doc({c: Map(c, lo, hi) for c in ("basic", "disk")})
    ok["A15 the document carries BOTH sections"] = \
        "## This project's own workspace" in doc15 and \
        "## The MSX standard work area" in doc15
    ok["A15 a standard-area cell has a row"] = "`$F3B0`" in doc15
    ok["A15 NEGATIVE: the standard section says the cells are NOT ours"] = \
        "IT DOES NOT OWN THEM" in doc15

    # ---- A7 sym seeding, with --no-sym as the control ---------------------
    d_nosym = Map("disk", lo, hi, use_sym=False)
    ok["A7 sym supplies a label-derived cell (WA_SEG $E795)"] = \
        d_all.vals.get("WA_SEG") == 0xE795 and "WA_SEG" in d_all.from_sym
    ok["A7 NEGATIVE: without the sym it is absent from the map"] = \
        "WA_SEG" not in d_nosym.vals
    ok["A7 cross-check is non-vacuous and clean"] = \
        d_all.crosschecked > 20 and not d_all.disagree

    print()
    for k, v in ok.items():
        print(f"  SELFTEST: {'PASS' if v else 'FAIL'}  {k}")
    print(f"  SELFTEST: {sum(ok.values())}/{len(ok)} arms pass")
    return 0 if all(ok.values()) else 1


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lo = int(args[0], 16) if len(args) > 0 else DEFAULT_LO
    hi = int(args[1], 16) if len(args) > 1 else DEFAULT_HI
    if "--selftest" in sys.argv:
        return selftest(lo, hi)

    inc_only = "--inc-only" in sys.argv
    comps = [c for c in ("basic", "disk")
             if f"--{c}" in sys.argv] or ["basic", "disk"]
    if "--doc" in sys.argv:
        maps = {c: Map(c, lo, hi) for c in ("basic", "disk")}
        body = write_doc(maps, DOC)
        nrows = sum(1 for ln in body.splitlines()
                    if ln.startswith("| `$"))
        print(f"{DOC}: {body.count(chr(10))} lines, {nrows} row(s) "
              f"(one per declared address; the count used to come from the "
              f"NARROW maps and under-reported the standard work area)")
        return 0
    if "--check" in sys.argv:
        maps = {c: Map(c, lo, hi) for c in ("basic", "disk")}
        rc, lines = check(maps, load_allow(ALLOW))
        # 🔴 THE DOCUMENT IS GENERATED, SO IT CAN DRIFT, SO IT IS CHECKED.
        # Same discipline as docs/tier-status.md: regenerate into memory and
        # compare, and say which command fixes it.
        try:
            have = open(DOC).read()
        except OSError:
            have = None
        want = write_doc(maps)
        if have != want:
            rc = 1
            lines.append(f"🔴 {DOC} has DRIFTED from its generator "
                         f"({'absent' if have is None else 'differs'}) -- "
                         f"run `make ram-map-doc`.")
        else:
            lines.append(f"🟢 {DOC} matches its generator.")
        for ln in lines:
            print(ln)
        ov = overlays(maps)
        print(f"\n🔑 CROSS-ROM OVERLAYS -- {len(ov)} declared span(s) of "
              f">=64 B host another component's cells. This is DESIGNED, and "
              f"it is what a per-component map cannot show:")
        for oc, on, a, b, guests in ov:
            print(f"  {oc:5} {on} ${a:04X}..${b - 1:04X} hosts "
                  f"{len(guests)} cell(s) of the other map: "
                  + ", ".join(f"{g[2]} ${g[1]:04X}" for g in guests[:6])
                  + (" …" if len(guests) > 6 else ""))
        return rc
    maps = {}
    for c in comps:
        m = Map(c, lo, hi, inc_only=inc_only,
                use_sym="--no-sym" not in sys.argv,
                joint="--no-joint" not in sys.argv)
        maps[c] = m
        report(m)
        if "--widths" in sys.argv:
            print("\n  --widths: every address, its names and its width")
            for a in m.addrs:
                w = m.width.get(a)
                print(f"    ${a:04X}  {str(w) if w else '?':>5}  "
                      f"{'/'.join(m.byaddr[a])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
