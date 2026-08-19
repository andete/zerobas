#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Keyword-completeness SWEEP — the MSX1 BASIC reserved-word denominator.

WHY THIS EXISTS
===============
zerobas has twice discovered a missing keyword *by accident*, and both had the
same silent shape — the word parses as an ordinary VARIABLE, so nothing errors
and the program just computes the wrong answer:

  * `TIME`  — found as collateral during the T3 KEY slice (20e04b4). `TIME`
    parses as the variable `TI`, reads 0 forever, and `IF TIME-T<400 GOTO`
    becomes an infinite loop.
  * `TAB(`  — found 2026-07-26 while auditing coverage. Worse: it was recorded
    as "already faithful (NO work)" in docs/spec-basic-df2-2-intarg-coercion.md
    §1.2 because `PRINT TAB(99999)` raises ERR 6 on BOTH sides. It does so for
    the WRONG REASON — zerobas has no `TAB(`, so `TAB` is an ARRAY and the
    subscript bound-check produces the same error code. The probe agreed; the
    feature is absent.

This probe closes that discovery channel by measuring the WHOLE reserved-word
set at once, so "complete MSX1 BASIC" finally has an honest denominator.

TWO LAYERS, BECAUSE ONE IS NOT ENOUGH
=====================================
The `INTERVAL` retraction (60e0ab6) is the standing lesson: a crunch probe
answers a TOKENISATION question, not a SUPPORT question. `INTERVAL` is absent
from every MSX1 keyword table — it is not a keyword at all, it is the
reserved-word compound `INT`+"ER"+`VAL` — and it works perfectly on the
VG-8020. "Absent from the keyword table" != "absent from the language."

The `TAB(` case is the mirror-image trap: identical OBSERVED BEHAVIOUR on one
probe, for structurally different reasons.

So every word is measured twice, and the two layers are reported separately:

  Layer 1 CRUNCH  — store `1 <body>` (tokenised into the program area, never
                    executed) and diff the token bytes ref vs zerobas. Reuses
                    basic_probe_crunch's stored-line capture wholesale.
  Layer 2 SUPPORT — EXECUTE a usage chosen so that "parses as a variable/array"
                    yields a VISIBLY DIFFERENT answer than real support, then
                    compare the OUTCOME CLASS (value vs which error) rather than
                    raw text — zerobas's error wording is lowercase by design
                    (a documented divergence), so a raw text diff would flag
                    every case and classify nothing.

Layer 2 is the load-bearing one. Layer 1 alone would have mis-called both
`INTERVAL` (absent token, works) and `TAB(` (present-looking, absent feature).

READING THE VERDICT
===================
  SUPPORTED    both sides produce the same outcome class and the same text
  DIVERGENT    both sides run it, but the answers differ  <- a faithfulness bug
  MISSING      the reference runs it, zerobas errors       <- a coverage gap
  SILENT-GAP   BOTH sides "succeed" but zerobas's answer betrays a
               variable/array parse (the TIME / TAB( shape)  <- the worst kind
  EXTRA        zerobas runs it, the reference errors
  SKIPPED      not safely executable in a batch (see SKIP_EXEC) — crunch only

Clean-room: this only *compares observed outputs*. No disassembly; the reference
ROM is a black box. The candidate word list is a generator only — every verdict
comes from measurement. See the clean-room firewall (CONTRIBUTING.md).

USAGE
    python3 probes/basic/basic_probe_kwsweep.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK
    ... --only tab,spc,locate      # a subset, by word key
    ... --layer crunch|support     # one layer only
    ... --boot-per-case            # isolation escape hatch
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import hashlib
import subprocess

import omsx_repl  # typing-free KEYBUF-injection REPL driver

MACHINE = "Philips_VG_8020"
# A DISK-EQUIPPED reference, for the rows whose verbs live in Disk BASIC.
#
# This exists because the first full run tripped its own control group: `mki`
# (MKI$, which zerobas implements correctly) came back as the reference raising
# `Illegal function call` while zerobas printed the right answer. The language was
# never the asymmetry — the MACHINES were. The default reference is a DISKLESS
# VG-8020, while the zerobas side is C-BIOS_MSX1_EU_REPACK_**DISK**, so every
# MK$/CV/Disk-BASIC row was comparing "no disk ROM" against "disk ROM" and
# attributing the difference to zerobas. Rows tagged NEEDS-DISK: get their
# reference capture from this machine instead.
#
# STATUS 2026-07-26: this machine does NOT yet yield a readable SCREEN-0 capture
# under omsx_repl — a trivial `PRINT 1+1` comes back as VRAM pattern garbage, so
# it is presumably still in the boot/logo video mode when the capture fires, or
# needs a longer boot than the shared default. Until that is chased down, the
# NEEDS-DISK rows report NO-ORACLE rather than a verdict: the probe declines to
# answer instead of answering from the wrong machine. Chasing it is cheap and
# worthwhile, but the MK/CV family it gates is ALREADY tracked as deferred in
# TODO.md, so it blocks no finding in this sweep.
DISK_MACHINE = "National_CF-3300"
TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base (both machines)

# Widest direct-mode exec line whose prompt echo still fits ONE SCREEN-0 row, so
# omsx_repl.screen_tail can find it. Anything wider must use mode="stored" (whose
# echoed command is the short "RUN"). Enforced at startup — see main().
MAX_DIRECT_ECHO = 38

# The MSX1 BASIC reserved-word set. CANDIDATE GENERATOR ONLY — this list decides
# what gets measured, never what the answer is. Sourced from the published
# keyword/token tables (MSX Technical Data Book; MSX2 Technical Handbook Table
# 2.20 — both allowed-sources.md tier B), which is the same provenance the
# existing kwtable.inc token locks already cite.
#
# Each row: (key, crunch_body, exec_line, exec_mode, note)
#   crunch_body — stored as `1 <body>`; never executed
#   exec_line   — the Layer-2 usage; None => crunch-only (also list in SKIP_EXEC)
#   exec_mode   — "direct" (typed at the prompt) or "stored" (numbered + RUN)
#
# The exec_line for a SUSPECTED-MISSING word is designed against the failure mode
# in this file's header: it must distinguish real support from a variable/array
# parse. `PRINT TAB(99999)` is the counter-example of how NOT to write one.

SWEEP: list[tuple[str, str, str | None, str, str]] = [

    # ---------------------------------------------------------------- controls
    # Known-shipped words. They are the CONTROL GROUP: if one of these comes back
    # anything but SUPPORTED, the apparatus is lying and no other row is
    # trustworthy. (The T3 KEY lesson: distrust a baseline that cannot produce a
    # non-zero answer.)
    ("abs",     "a=abs(-5)",          'PRINT"[";ABS(-5);"]"',            "direct", "control"),
    ("int",     "a=int(1.7)",         'PRINT"[";INT(1.7);"]"',           "direct", "control"),
    ("len",     'a=len("ab")',        'PRINT"[";LEN("ab");"]"',          "direct", "control"),
    ("chr",     "a$=chr$(65)",        'PRINT"[";CHR$(65);"]"',           "direct", "control"),
    ("mid",     'a$=mid$("hi",1,1)',  'PRINT"[";MID$("hi",2,1);"]"',     "direct", "control"),
    ("instr",   'a=instr("ab","b")',  'PRINT"[";INSTR("ab","b");"]"',    "direct", "control"),
    ("hex",     "a$=hex$(255)",       'PRINT"[";HEX$(255);"]"',          "direct", "control"),
    ("sqr",     "a=sqr(9)",           'PRINT"[";SQR(9);"]"',             "direct", "control"),
    ("peek",    "a=peek(0)",          'PRINT"[";PEEK(0)>=0;"]"',         "direct", "control"),
    ("varptr",  "a=varptr(b)",        'B=1:PRINT"[";VARPTR(B)>0;"]"',    "direct", "control"),
    ("stick",   "a=stick(0)",         'PRINT"[";STICK(0);"]"',           "direct", "control"),
    ("erase",   "erase a",            'DIM Q(2):ERASE Q:PRINT"[ok]"',    "direct", "control"),
    ("swapctl", "a=1",                'A=1:PRINT"[";A;"]"',              "direct", "control (bare assign)"),

    # -------------------------------------------------- suspected MISSING words
    # Console / cursor. All three fail the same way if absent: the word parses as
    # a numeric variable (0) or an array, so the probe must make 0 the WRONG
    # answer rather than a plausible one.
    # COLUMN ONLY, not `LOCATE 10,0`. The first design used row 0 — and on the
    # reference the feature under test then MOVED THE CURSOR ONTO THE ECHOED
    # COMMAND and overprinted it, so screen_tail could not find the echo and the
    # reference row came back ?noecho/UNREADABLE. The probe was destroying its own
    # anchor. `LOCATE 10` keeps output on the current row, just indented.
    ("locate",  "locate 10,0",
     'LOCATE 10:PRINT"[X]"',                         "direct",
     "absent => `LOCATE 10` is a bare word + juxtaposition => syntax error; "
     "real => `[X]` indented to column 10"),
    ("csrlin",  "a=csrlin",
     # ⚠️ THIS ROW'S "DIVERGENT" IS A PROBE ARTIFACT, NOT A FAITHFULNESS BUG,
     # and it cannot be pinned here. CSRLIN is a POSITION, so with no leading
     # CLS the row reports wherever the boot banner and the batch's own
     # scrolling left the cursor. Measured: unpinned it reads ref 4 vs zb 3 in
     # this batch and ref 9 vs zb 7 in a differently scrolled one -- the
     # REFERENCE disagreeing with itself is the proof that the row is reading
     # ambient state. Prefix `CLS:` and both machines answer 2, with or without
     # a WIDTH pin.
     #
     # But CLS cannot be used HERE: this probe's readout anchors on the typed
     # ECHO, and CLS erases it -- the row then reads '' on both sides and
     # classifies UNREADABLE, which is strictly worse than a divergence you can
     # explain (tried, 2026-07-27). The two requirements are incompatible for
     # this one row, so it stays unpinned and stays explained.
     #
     # CSRLIN itself is CORRECT and properly gated elsewhere: cursor-acceptance
     # 67/67 covers it at a pinned WIDTH 40 + CLS across six cases
     # (docs/cursor-vg8020-characterization.md §2). Treat this row as evidence
     # that CSRLIN is PRESENT, never as evidence about its value.
     'PRINT:PRINT:PRINT"[";CSRLIN;"]"',              "direct",
     "absent => variable CSRLIN reads 0; real => the (non-zero) cursor row"),
    ("pos",     "a=pos(0)",
     'PRINT"    ";:PRINT"[";POS(0);"]"',             "direct",
     "absent => array POS(0) auto-dims to 0; real => the (non-zero) column"),

    # The two PRINT-item pseudo-functions. THE `TAB(` TRAP: with TAB absent,
    # `PRINT TAB(5);"X"` prints ` 0 X` (array element 0 then X) instead of
    # padding to column 5 — so compare the TEXT, and never a bare error code.
    ("tab",     'print tab(5);"x"',
     'PRINT"[";TAB(5);"X]"',                         "direct",
     "absent => array TAB(5)=0 prints ` 0 `; real => pad to column 5"),
    ("spc",     'print spc(5);"x"',
     'PRINT"[";SPC(5);"X]"',                         "direct",
     "absent => array SPC(5)=0 prints ` 0 `; real => 5 spaces"),

    # Program / editor management.
    ("swap",    "swap a,b",
     'A=1:B=2:SWAP A,B:PRINT"[";A;B;"]"',            "direct",
     "absent => syntax error; real => ` 2  1 `"),
    ("fre",     "a=fre(0)",
     'PRINT"[";FRE(0)>1000;"]"',                     "direct",
     "absent => array FRE(0)=0 => `0` (false); real => -1 (true)"),
    ("tron",    "tron",
     "TRON:TROFF:PRINT\"[ok]\"",                     "direct",
     "absent => syntax error; real => accepted (trace toggled off again)"),
    ("troff",   "troff",
     'TROFF:PRINT"[ok]"',                            "direct",
     "absent => syntax error"),
    ("renum",   "renum",
     None,                                           "direct",
     "renumbers the stored program; harmless but needs a program to be visible"),
    ("delete",  "delete 10",
     None,                                           "direct",
     "deletes stored lines — would eat the batch's own program"),
    ("auto",    "auto",
     None,                                           "direct",
     "INTERACTIVE: enters auto-line-number mode and swallows all following input"),

    # D-DEFTYPETOK (2026-08-19): DEFSNG/DEFDBL/DEFSTR now have whole-word
    # kwtable.inc rows and single-byte tokens of their own ($AD/$AE/$AB, beside
    # DEFINT's $AC from D-DEFINTTOK), so they TOKENISE and reach ex_deftype
    # (basic/usr.asm) as one byte each. The DEF_TOKEN + literal ASCII mechanism
    # they used to arrive by is gone, and so is ex_def_type (merged into
    # ex_deftype). Until then they were the one family where "absent from the
    # keyword table" was expected AND support was expected — the INTERVAL
    # shape, in-tree, flagged by this probe's own coverage audit as a blind spot.
    # They are ordinary tokenising rows now; the three cases below are kept
    # because they gate the BEHAVIOUR, which is what they always gated.
    ("defsng",  "defsng a",
     'DEFSNG A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defdbl",  "defdbl a",
     'DEFDBL A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defstr",  "defstr a",
     'DEFSTR A:A="x":PRINT"[";A;"]"',                "direct", "control"),

    # User-defined functions.
    # STORED, not direct: the reference answers `Illegal direct` to a direct-mode
    # DEF FN — measured, first run of this sweep. So the direct form tests the
    # direct-mode restriction, not the feature.
    ("deffn",   "def fna(x)=x+1",
     'DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"',           "stored",
     "absent => syntax error; real => 3"),

    # The two missing logical operators.
    ("eqv",     "a=5 eqv 3",
     'PRINT"[";5 EQV 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -7"),
    ("imp",     "a=5 imp 3",
     'PRINT"[";5 IMP 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -5"),

    # Printer surface. The LPTOUT device layer ships (zerobas-tape page-0 patch),
    # so a divergence here is statement-surface only. Printer is UNPLUGGED in the
    # harness by default and LSTOUT is NOT hang-safe unplugged (openmsx-printer-
    # pluggable), so these are crunch-only — executing LPRINT could wedge the run.
    ("lprint",  'lprint"x"',   None, "direct", "LSTOUT not hang-safe with no printer plugged"),
    ("llist",   "llist",       None, "direct", "same LSTOUT hazard"),
    ("lpos",    "a=lpos(0)",   None, "direct", "same LSTOUT hazard"),

    # Cassette / misc statements.
    ("motor",   "motor on",
     'MOTOR OFF:PRINT"[ok]"',                        "direct",
     "absent => syntax error; MOTOR OFF is the safe direction"),
    # KEPT DELIBERATELY, AND KEPT WEAK. This row is the TAB( mistake reproduced
    # on purpose: `TIME>=T` is `0>=0` on a machine with no TIME at all, so BOTH
    # sides answer -1 and the row reports SUPPORTED for a feature that does not
    # exist. It is the in-tree demonstration that a passing differential case
    # proves nothing unless the absent-feature parse gives a DIFFERENT answer.
    # WEAK: rows are excluded from the tally and flagged in the report.
    ("time",    "time=0",
     'T=TIME:PRINT"[";TIME>=T;"]"',                  "direct",
     "WEAK: absent => variable TI, always 0, and `0>=0` is STILL true, so this "
     "row passes on a machine with no TIME. The `timetick` row is the real test."),
    # STORED mode, not direct: the line is 46 chars, so its prompt echo wraps
    # across two 40-column rows and screen_tail's echo match fails -> ?noecho ->
    # UNREADABLE. In stored mode the echoed command is just "RUN". (Caught by the
    # MAX_DIRECT_ECHO guard below, which exists so this cannot recur silently.)
    ("timetick", "a=time",
     'T=TIME:FOR I=1 TO 400:NEXT:PRINT"[";TIME>T;"]"', "stored",
     "THE discriminator: a real TIME advances across a delay loop; the variable "
     "`TI` does not. This is the row that catches the silent gap."),

    # INTERVAL — the retraction case. It is NOT a keyword on either side (it is
    # INT+"ER"+VAL), so CRUNCH is expected to MATCH while SUPPORT is expected to
    # differ. Any probe design that reports this row as "fine" is broken.
    ("interval", "interval on",
     None,                                           "direct",
     "needs a stored ON INTERVAL=n GOSUB program + a timed window; covered by "
     "probes/basic/basic_probe_interval_trap.py (T5 slice), not duplicated here"),

    # Random-access float conversions (the MKI$/CVI integer pair ships).
    # MKI$ is the FAMILY CONTROL: the first run had the reference answering
    # `Illegal function call` to `LEN(MKS$(1))`, which could mean either "MKS$
    # needs Disk BASIC on this diskless VG-8020" or "my expression is wrong".
    # MKI$ is implemented on BOTH sides, so it separates those two readings.
    ("mki",     'a$=mki$(1)',   'PRINT"[";LEN(MKI$(1));"]"',  "direct",
     "NEEDS-DISK: " "control for the MK/CV family — MKI$ ships in zerobas"),
    ("mks",     'a$=mks$(1)',   'PRINT"[";LEN(MKS$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 4"),
    ("mkd",     'a$=mkd$(1)',   'PRINT"[";LEN(MKD$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 8"),
    ("cvs",     'a=cvs("abcd")', 'PRINT"[";CVS(MKS$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),
    ("cvd",     'a=cvd("abcdefgh")', 'PRINT"[";CVD(MKD$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),

    # Disk-BASIC surface. Sector I/O and the destructive/interactive ones are
    # crunch-only ON PURPOSE — see SKIP_EXEC.
    ("dski",    'a$=dski$(0,0)', None, "direct", "NEEDS-DISK: " "raw sector READ — needs a disk, out of scope here"),
    ("dsko",    "dsko$0,0",      None, "direct", "NEEDS-DISK: " "raw sector WRITE — DESTRUCTIVE, never executed"),
    ("copy",    'copy"a:x"to"a:y"', None, "direct", "NEEDS-DISK: " "file copy — needs a disk fixture"),
    ("set",     'set password',  None, "direct", "NEEDS-DISK: " "Disk-BASIC SET — needs a disk fixture"),
    ("attr",    'a$=attr$(0)',   None, "direct", "NEEDS-DISK: " "MSX-DOS2-era; measured for the record"),
    ("ipl",     "ipl",           None, "direct", "NEEDS-DISK: " "boot-sector write — DESTRUCTIVE, never executed"),
    ("cmd",     'cmd"x"',        None, "direct", "vendor hook; unknown side effects"),
    ("lfiles",  "lfiles",        None, "direct", "NEEDS-DISK: " "printer-bound (LSTOUT hazard); tracked in TODO"),
    ("loc",     "a=loc(1)",      None, "direct", "NEEDS-DISK: " "needs an open channel; tracked in TODO §File-position"),
    ("bin",     "a$=bin$(5)",
     'PRINT"[";BIN$(5);"]"',                         "direct",
     "absent => syntax error; real => 101"),

    # WAIT: `WAIT p,a` spins until ((INP(p) XOR x) AND a) <> 0 — with the wrong
    # operand it NEVER RETURNS and wedges the whole batch. Crunch-only.
    ("wait",    "wait 0,0",      None, "direct", "can spin forever — never executed in a batch"),

    # Keyboard INPUT$(n) — blocks for n keypresses. Crunch-only; the channel form
    # INPUT$(n,#f) already ships.
    ("inputdol", 'a$=input$(1)', None, "direct", "BLOCKS waiting for a keypress"),
]

# Rows deliberately not executed, with the reason surfaced in the report. Named
# explicitly so a reader can audit the exclusions instead of inferring them from
# a silent absence (no-silent-caps).
SKIP_EXEC = {k for k, _, ex, _, _ in SWEEP if ex is None}

# 🔴 EVERY ENTRY MUST STAY LOWERCASE. `classify` below does `low = tail.lower()`
# and then `phrase in low`, so a capitalised entry can NEVER match -- it does not
# fail loudly, it silently reclassifies that row from `error:<phrase>` to
# `value`, which reads as "the keyword ran and printed something".
# ⚠️ D-MSGEXACT nearly broke exactly this. A tree-wide sweep that capitalised
# message literals hit seven of these, because they LOOK like the message
# expectations it was updating. They are not: this is a CLASSIFIER vocabulary,
# not an assertion, and it is deliberately case-insensitive.
# The original reason for lowercasing -- zerobas's own lowercase wording being a
# documented divergence -- is GONE (D-MSGEXACT made every message the
# reference's verbatim text). The lowercasing stays anyway: the CLASS is the
# comparable thing here, and a classifier that is insensitive to case cannot be
# broken by a future wording change.
ERROR_WORDS = (
    "syntax error", "type mismatch", "overflow", "illegal function call",
    "out of memory", "undefined line", "subscript out of range",
    "division by zero", "redimensioned array", "missing operand",
    "illegal direct", "nexus", "bad file", "file not found", "disk offline",
    "device i/o error", "not found", "error",   # bare "error" LAST: catch-all
)


def tokens(raw: str | None) -> bytes | None:
    """Body tokens from a stored_line capture — the bytes after the 4-byte
    header (link + line number). None when the line was never stored (a crunch
    that errored on entry leaves the program empty)."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:] if len(b) >= 5 else None


def classify(raw: str | None, cmdline: str) -> tuple[str, str]:
    """(outcome_class, text) for one executed case.

    class is "value" (ran, printed something), "error:<phrase>", or "?<reason>".
    Comparing the CLASS first is what makes the sweep readable across zerobas's
    lowercase error wording."""
    tail = omsx_repl.screen_tail(raw, cmdline)
    if tail is None:
        return ("?noecho", "")
    low = tail.lower()
    for phrase in ERROR_WORDS:
        if phrase in low:
            return (f"error:{phrase}", tail)
    return ("value", tail)


def verdict(ref_cls: str, ref_txt: str, zb_cls: str, zb_txt: str,
            crunch_state: str | None) -> str:
    """The six-way call described in the module header.

    `crunch_state` ("SAME"/"DIFF"/None) is what separates SILENT-GAP from a
    plain DIVERGENT: when NEITHER side errors, the answers still differ, AND
    zerobas failed to tokenise the word, the word is being parsed as an ordinary
    variable/array — the TIME / TAB( shape, the failure mode this whole probe
    exists to catch. That inference needs BOTH layers, which is why the support
    pass runs after the crunch pass rather than standalone."""
    if ref_cls.startswith("?") or zb_cls.startswith("?"):
        return "UNREADABLE"
    ref_err = ref_cls.startswith("error")
    zb_err = zb_cls.startswith("error")
    # A DIFF crunch is a DEFINITIVE fact: zerobas did not tokenise the word, so
    # whatever it did instead was a variable/array parse. When it then declines to
    # error, that is a silent wrong answer NO MATTER what the reference did —
    # including when the reference itself refused the case (MKS$/MKD$ on a
    # diskless VG-8020). Checking this before the ref-vs-zb comparison stops such
    # rows being labelled "EXTRA", which would read as zerobas having a feature it
    # provably lacks.
    # AGREEMENT WINS FIRST. An earlier revision tested the DIFF-crunch rule before
    # comparing the outputs, and promptly called DEFSNG/DEFDBL/DEFSTR "SILENT-GAP"
    # while printing two IDENTICAL answers — at the time those three had no
    # kwtable entry by design (they reached the then-ex_def_type as DEF_TOKEN +
    # literal ASCII) and worked fine. A no-entry word that produces the right
    # answer is the INTERVAL shape, not a gap, so identical observable behaviour
    # must be decided before tokenisation is allowed to weigh in at all.
    # ⚠️ THE ORDERING RULE OUTLIVED ITS EXAMPLE: those three got rows and
    # tokens of their own in D-DEFTYPETOK (2026-08-19) and no longer exercise this
    # path. INTERVAL still does, and the rule is kept for the CLASS, not the
    # instance — any word supported without a kwtable entry lands here.
    if not ref_err and not zb_err and ref_txt.strip() == zb_txt.strip():
        return "SUPPORTED"
    if crunch_state == "DIFF" and not zb_err:
        return "SILENT-GAP"
    if not ref_err and zb_err:
        return "MISSING"
    if ref_err and not zb_err:
        return "EXTRA"
    if ref_err and zb_err:
        # both refuse it — same class = faithful refusal, different = divergent
        return "SUPPORTED" if ref_cls == zb_cls else "DIVERGENT"
    return "SILENT-GAP" if crunch_state == "DIFF" else "DIVERGENT"


def _rom_fingerprint() -> str:
    """Hash the ROMs the repack machine actually loads, so a report can never be
    silently attributed to a different build. The machine XML points straight at
    build/*.rom in the project tree, so a concurrent `make` in another session
    changes the measurement target mid-flight — this is the tripwire for that."""
    root = _os.path.dirname(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
    parts = []
    for name in ("zerobas-main-eu.rom", "sub.rom", "disk.rom"):
        p = _os.path.join(root, "build", name)
        try:
            with open(p, "rb") as fh:
                parts.append(f"{name}={hashlib.sha256(fh.read()).hexdigest()[:12]}")
        except OSError:
            parts.append(f"{name}=<missing>")
    try:
        rev = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        rev = "?"
    return f"git={rev} " + " ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help="reference machine (built-in BASIC oracle; default VG-8020)")
    ap.add_argument("--disk-machine", dest="disk_machine", default=DISK_MACHINE,
                    help="disk-equipped reference for NEEDS-DISK rows (default "
                         f"{DISK_MACHINE}); the default VG-8020 has no disk ROM, "
                         "so Disk-BASIC verbs would compare machines, not languages")
    ap.add_argument("--zb-machine", dest="zb_machine", required=True,
                    help="repack machine with BASIC baked into slot 0")
    ap.add_argument("--only", help="comma-separated word keys to run")
    ap.add_argument("--layer", choices=("crunch", "support", "both"), default="both")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (rule out leakage)")
    args = ap.parse_args()

    # A direct-mode line wider than one SCREEN-0 row wraps, so screen_tail can
    # never match its echo and the case silently reports ?noecho -> UNREADABLE.
    # That is a probe defect masquerading as a measurement, so fail loudly at
    # startup rather than emitting an unreadable row (the T3 KEY lesson: the
    # apparatus is part of the measurement).
    too_long = [(k, len(ex)) for k, _, ex, mode, _ in SWEEP
                if ex is not None and mode == "direct" and len(ex) > MAX_DIRECT_ECHO]
    if too_long:
        print("probe defect — direct-mode exec lines exceed one screen row "
              f"({MAX_DIRECT_ECHO} cols); use mode='stored' for these:")
        for k, n in too_long:
            print(f"    {k:9} {n} chars")
        return 2

    rows = SWEEP
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r[0] in want]
        missing = want - {r[0] for r in rows}
        if missing:
            print(f"unknown word keys: {', '.join(sorted(missing))}")
            return 2
    batch = not args.boot_per_case

    fp_before = _rom_fingerprint()
    print(f"build under measurement: {fp_before}\n")

    results: dict[str, dict] = {k: {} for k, *_ in rows}

    # Route each row's REFERENCE capture to a machine that can actually run it.
    # A Disk-BASIC verb on a diskless reference measures the absence of a disk
    # ROM, not the absence of a language feature — see DISK_MACHINE.
    def ref_machine_for(note: str) -> str:
        return args.disk_machine if note.startswith("NEEDS-DISK:") else args.machine

    def ref_capture(specs, sel_rows, **kw):
        """Capture `specs` on the reference, splitting the batch by which
        reference machine each row needs, then re-interleaving in row order."""
        out: list[str | None] = [None] * len(specs)
        for mach in sorted({ref_machine_for(r[4]) for r in sel_rows}):
            idx = [i for i, r in enumerate(sel_rows) if ref_machine_for(r[4]) == mach]
            got = omsx_repl.run_cases(mach, [specs[i] for i in idx], batch=batch, **kw)
            for i, g in zip(idx, got):
                out[i] = g
        return out

    # ---- Layer 1: CRUNCH ---------------------------------------------------
    if args.layer in ("crunch", "both"):
        specs = [("direct", [f"1 {body}"]) for _, body, _, _, _ in rows]
        ref_raws = ref_capture(specs, rows, reset=("NEW",),
                               capture=("stored_line", TXTTAB))
        zb_raws = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                      reset=("NEW",),
                                      capture=("stored_line", TXTTAB))
        for (key, body, _, _, _), rr, zr in zip(rows, ref_raws, zb_raws):
            ref, zb = tokens(rr), tokens(zr)
            results[key]["crunch"] = (
                "SAME" if (ref is not None and ref == zb) else "DIFF",
                " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>",
                " ".join(f"{b:02X}" for b in zb) if zb else "<not stored>",
                body,
            )

    # ---- Layer 2: SUPPORT --------------------------------------------------
    if args.layer in ("support", "both"):
        ex_rows = [r for r in rows if r[2] is not None]
        if ex_rows:
            specs = []
            for _, _, line, mode, _ in ex_rows:
                specs.append((mode, omsx_repl.as_stored(line) if mode == "stored"
                              else [line]))
            ref_raws = ref_capture(specs, ex_rows,
                                   reset=("NEW", "CLS"), capture="screen")
            zb_raws = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                          reset=("NEW", "CLS"), capture="screen")
            for (key, _, line, mode, _), rr, zr in zip(ex_rows, ref_raws, zb_raws):
                cmd = "RUN" if mode == "stored" else line
                rc, rt = classify(rr, cmd)
                zc, zt = classify(zr, cmd)
                cs = results[key].get("crunch", (None,))[0]
                note = next(n for k, _, _, _, n in rows if k == key)
                if note.startswith("NEEDS-DISK:") and rc.startswith("?"):
                    # The oracle for this row is the disk-equipped reference, and
                    # it produced nothing readable. Refuse to compare rather than
                    # silently fall back to the diskless default and call the
                    # resulting machine difference a language difference.
                    v = "NO-ORACLE"
                else:
                    v = verdict(rc, rt, zc, zt, cs)
                results[key]["support"] = (v, rc, rt, zc, zt, line)

    fp_after = _rom_fingerprint()

    # ---- report ------------------------------------------------------------
    print("=" * 78)
    print("LAYER 1 — CRUNCH (tokenisation only; NOT a support answer)")
    print("=" * 78)
    for key, *_ in rows:
        c = results[key].get("crunch")
        if not c:
            continue
        state, ref, zb, body = c
        print(f"{state:5}  {key:9} {body}")
        if state == "DIFF":
            print(f"           ref: {ref}")
            print(f"           zb : {zb}")

    print()
    print("=" * 78)
    print("LAYER 2 — SUPPORT (the load-bearing layer)")
    print("=" * 78)
    order = {"SILENT-GAP": 0, "MISSING": 1, "DIVERGENT": 2, "EXTRA": 3,
             "UNREADABLE": 4, "NO-ORACLE": 5, "SUPPORTED": 6}
    executed = [(key, results[key]["support"]) for key, *_ in rows
                if "support" in results[key]]
    notes = {k: n for k, _, _, _, n in rows}
    for key, s in sorted(executed, key=lambda kv: order.get(kv[1][0], 9)):
        v, rc, rt, zc, zt, line = s
        weak = notes[key].startswith("WEAK:")
        print(f"{v:10}{'  ! WEAK' if weak else '  '}  {key:9} {line}")
        print(f"            ref  [{rc}] {rt!r}")
        if v != "SUPPORTED" or weak:
            print(f"            zb   [{zc}] {zt!r}")
        if weak:
            print(f"            {notes[key]}")

    # ---- the combined view: absence (layer 1) + consequence (layer 2) --------
    # Neither layer is readable alone. Layer 1 says whether zerobas TOKENISES the
    # word; layer 2 says what a program actually observes. INTERVAL is why: SAME
    # crunch, no support. TAB( is why: value on both sides, no support.
    if args.layer == "both":
        print()
        print("=" * 78)
        print("COMBINED — tokenised? x observable consequence")
        print("=" * 78)
        print(f"{'word':10} {'crunch':7} {'support':11} consequence")
        print("-" * 78)
        for key, *_ in rows:
            c = results[key].get("crunch")
            s = results[key].get("support")
            cs = c[0] if c else "-"
            tok = {"SAME": "present", "DIFF": "ABSENT", "-": "-"}[cs]
            if s:
                sv = s[0]
                cons = f"ref {s[2]!r} vs zb {s[4]!r}" if sv != "SUPPORTED" else "match"
            else:
                sv, cons = "not-run", "crunch-only — support UNKNOWN"
            print(f"{key:10} {tok:7} {sv:11} {cons}")

    skipped = [(k, n) for k, _, ex, _, n in rows if ex is None]
    if skipped:
        print()
        print("=" * 78)
        print(f"NOT EXECUTED — {len(skipped)} words, crunch-only. Reasons below; these "
              "are\nCOVERAGE HOLES IN THIS PROBE, not evidence of support.")
        print("=" * 78)
        for k, n in skipped:
            print(f"  {k:9} {n}")

    # ---- summary + the apparatus tripwire ----------------------------------
    # WEAK rows are excluded from the tally: counting a known-false SUPPORTED
    # would overstate coverage, which is the exact error this probe was built to
    # stop making.
    tally: dict[str, int] = {}
    for key, s in executed:
        tally["WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0]] = \
            tally.get("WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0], 0) + 1
    print()
    print("=" * 78)
    print("SUMMARY  " + "  ".join(f"{k}={v}" for k, v in
                                  sorted(tally.items(), key=lambda kv: order.get(kv[0], 9))))
    print(f"         executed {len(executed)} / {len(rows)} words; "
          f"{len(skipped)} crunch-only")
    print("=" * 78)

    if fp_before != fp_after:
        print("\n*** APPARATUS WARNING — the ROMs changed DURING this run:")
        print(f"      before: {fp_before}")
        print(f"      after : {fp_after}")
        print("    Another session rebuilt the tree. DISCARD this report and re-run.")
        return 3

    # NEEDS-DISK rows cannot be controls: their oracle is the disk-equipped
    # reference, which is not yet readable (see DISK_MACHINE).
    controls = [k for k, _, ex, _, n in rows
                if ex is not None and n.startswith("control")]
    bad = [k for k in controls
           if results[k].get("support", ("?",))[0] != "SUPPORTED"]
    if bad:
        print(f"\n*** CONTROL GROUP FAILED: {', '.join(bad)}")
        print("    The apparatus is not measuring what it claims. Every other row "
              "in this\n    report is untrustworthy until this is explained.")
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
