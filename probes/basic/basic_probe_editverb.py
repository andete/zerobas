#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-EDITVERB acceptance — `RENUM` / `AUTO` / `LLIST`, three sides.

Spec `docs/spec-basic-editverb.md`, measurement
`docs/editverb-msx1-characterization.md`.

Three batteries, and they do NOT share a readout — which is the whole reason
this is its own probe rather than more rows in `basic_probe_lnblank.py`:

  `rnm-`  the screen after the verb, anchored on the command's own echo. RENUM
          prints `Undefined line N in M` BEFORE the prompt and then the
          following `LIST` prints the result, so the reading has to span both.
  `aut-`  the same screen readout, but the case has to press **Ctrl-STOP** in
          the middle of it (`@BREAK`, omsx_repl) -- an AUTO session cannot be
          left by typing, because Ctrl-STOP is not a character.
  `llt-`  🔴 the PRINTER LOG, not the screen. `plug printerport logger` reports
          READY unconditionally, so LLIST cannot block, and the reading is the
          byte stream the program sent -- CR/LF included, no 40-column wrap and
          nothing to scroll off.

⚠️ THE `llt-` BATTERY RUNS BOOT-PER-CASE ON PURPOSE. openMSX truncates the log
when the pluggable is plugged, i.e. once per boot; in a batch the log
ACCUMULATES and a case's own output is a delta. Deltas are correct right up
until `run_differential` self-heals a case boot-per-case, at which point that
one case's capture is a whole log and every later delta is wrong -- silently,
and in the direction of a plausible-looking divergence. One boot per case makes
each capture exactly that case's output and deletes the class.

⚠️ `llt-ctl` IS NOT DECORATION. `LPRINT` is a Syntax error on zerobas too (no
`kwtable.inc` entry), so an empty log on our side has TWO candidate causes: no
LLIST, or no working printer path. `llt-ctl` drives the sink through
`OPEN"LPT:"`, which already ships, so every other empty reading is
attributable to LLIST alone.

Clean-room: observed inputs/outputs only. See CONTRIBUTING.md.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")

# ⚠️ The CF-3300 boots Disk BASIC in SCREEN 1 (32 columns, name table $1800),
# so the SCREEN-0 scrape reads the pattern generator unless the case puts it
# back. Its leading "" answers the boot date prompt. Both are the same setup
# `basic_probe_lnblank.py` uses; getting either wrong reads as VRAM garbage,
# which is at least loud -- it was, on this probe's first spike.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5, reset=("NEW",)),
}
REF_SIDES = ("vg8020", "cf3300")

# The reference program for the reference-rewriting rules. Numbered 1..9
# DELIBERATELY: 10/20/30 renumbers to 10/20/30, and that identity agrees with
# every candidate rule including "RENUM does nothing" (spec §2.4).
PROG9 = ["1 GOTO 3", '2 PRINT"A"', "3 GOSUB 5", "4 END", "5 RESTORE 6",
         "6 DATA 1", "7 ON 1 GOTO 2,4", "8 IF 1 THEN 4 ELSE 2", "9 RETURN"]

BREAK = omsx_repl.BREAK_PREFIX

# --- the RENUM battery -------------------------------------------------------
# (label, typed lines, the row whose ECHO anchors the reading)
RNM = [
    # CONTROL. An identity renumbering: reads the same on a machine that
    # renumbers correctly and on one that does nothing, so it can never be a
    # test -- it is what says a divergence in the rows below is RENUM's and not
    # the detokeniser's or LIST's (docs/spec-basic-editverb.md §2.2).
    ("rnm-noop",     ["10 REM A", "20 REM B", "RENUM", "LIST"], "LIST"),
    ("rnm-bare",     PROG9 + ["RENUM", "LIST"], "LIST"),           # R-RN1/R-RN6
    ("rnm-new",      PROG9 + ["RENUM 100", "LIST"], "LIST"),       # R-RN2
    ("rnm-newold",   PROG9 + ["RENUM 100,3", "LIST"], "LIST"),     # R-RN3/R-RN7
    ("rnm-full",     PROG9 + ["RENUM 100,3,5", "LIST"], "LIST"),   # R-RN4
    ("rnm-incskip",  ["1 REM A", "2 REM B", "RENUM ,,5", "LIST"], "LIST"),   # R-RN5
    ("rnm-oldonly",  ["1 REM A", "2 REM B", "3 REM C", "RENUM ,3", "LIST"], "LIST"),
    ("rnm-selfref",  ["1 GOTO 1", "RENUM", "LIST"], "LIST"),       # R-RN23
    ("rnm-erl",      ["1 ON ERROR GOTO 3", "2 ERROR 7", "3 PRINT ERL",
                      "RENUM", "LIST"], "LIST"),                   # R-RN6
    ("rnm-runref",   ["1 REM A", "2 RUN 1", "RENUM", "LIST"], "LIST"),
    # R-RN19, the row that separates a token-aware walk from a byte scan.
    # `&H0E0E` stores $0C $0E $0E; a byte scan resolves 14, finds no line 14 and
    # must print `Undefined line 14 in 1`. Its own LIST-before control is
    # rnm-hexctl -- `&HE0E` is how BOTH references render 3598, before RENUM too.
    ("rnm-hexctl",   ["1 A=&H0E0E", "LIST"], "LIST"),
    ("rnm-hexref",   ["1 A=&H0E0E", "2 GOTO 1", "RENUM", "LIST"], "LIST"),
    ("rnm-octref",   ["1 A=&O16", "2 GOTO 1", "RENUM", "LIST"], "LIST"),
    ("rnm-strref",   ['1 A$="GOTO 1"', "2 GOTO 1", "RENUM", "LIST"], "LIST"),
    ("rnm-datref",   ["1 DATA 1,2", "2 GOTO 1", "RENUM", "LIST"], "LIST"),
    ("rnm-notaref",  ["1 A=3", "2 PRINT 3", "3 END", "RENUM", "LIST"], "LIST"),
    # dangling references: one message per REFERENCE, in program order, naming
    # the containing line's OLD number -- and the renumbering happens anyway.
    ("rnm-dang1",    ["1 GOTO 77", "2 END", "RENUM", "LIST"], "LIST"),
    ("rnm-dang3",    ["1 GOTO 77", "2 GOTO 88", "3 GOTO 99", "4 END",
                      "RENUM", "LIST"], "LIST"),                   # R-RN9
    ("rnm-dangline", ["1 ON 1 GOTO 77,88", "2 END", "RENUM", "LIST"], "LIST"),
    ("rnm-goto0",    ["1 GOTO 0", "2 END", "RENUM", "LIST"], "LIST"),   # R-RN22
    ("rnm-dangerr",  ["1 GOTO 77", "2 END", "RENUM", "PRINT ERR"], "PRINT ERR"),
    # the two error classes, and the pair that makes each boundary a measurement
    ("rnm-zeroinc",  ["1 REM A", "2 REM B", "RENUM 10,,0", "LIST"], "LIST"),
    ("rnm-ordeq",    ["10 REM A", "20 REM B", "30 REM C", "RENUM 20,30",
                      "LIST"], "LIST"),                            # R-RN12
    ("rnm-ordgt",    ["10 REM A", "20 REM B", "30 REM C", "RENUM 21,30",
                      "LIST"], "LIST"),
    ("rnm-args4",    ["1 REM A", "RENUM 10,1,10,7", "LIST"], "LIST"),   # R-RN15
    # 🔴 THE CEILING IS SWEPT, NOT SAMPLED. The one divergence this slice's
    # first build produced was `RENUM 65529` on a ONE-LINE program, where the
    # increment for a second line that does not exist overflowed and condemned
    # the first. A boundary found by one case is re-asked at 1/2/3 lines and on
    # both sides of it (spec §6.2).
    ("rnm-ceil1at",  ["1 REM A", "RENUM 65529", "LIST"], "LIST"),
    ("rnm-ceil2at",  ["1 REM A", "2 REM B", "RENUM 65519,,10", "LIST"], "LIST"),
    ("rnm-ceil2ov",  ["1 REM A", "2 REM B", "RENUM 65520,,10", "LIST"], "LIST"),
    ("rnm-ceil3at",  ["1 REM A", "2 REM B", "3 REM C", "RENUM 65509,,10",
                      "LIST"], "LIST"),
    ("rnm-ceil3ov",  ["1 REM A", "2 REM B", "3 REM C", "RENUM 65510,,10",
                      "LIST"], "LIST"),
    # R-RN14: a LITERAL past the ceiling is Syntax error, where a COMPUTED one
    # is Illegal function call. Two rules, two messages, and rnm-ceil2ov is the
    # row that keeps them apart.
    ("rnm-litover",  ["1 REM A", "RENUM 65530", "LIST"], "LIST"),
    ("rnm-tail",     ["1 REM A", "RENUM:B=9", "PRINT B"], "PRINT B"),  # R-RN16
    # 🔴 `llt-tailb` LIVES IN THE SCREEN BATTERY ON PURPOSE, AND KNIFE K3 IS WHY.
    # R-LL5 has TWO halves -- LLIST prints the line AND ends the line -- and the
    # printer log can only see the first. Deleting the ENDFLAG store left
    # `llt-tail`'s log byte-identical, so the row gated half a rule while
    # appearing to gate all of it. This reads `B` back off the SCREEN, which is
    # the only place the second half is visible.
    ("llt-tailb",    ["10 REM P", "LLIST:B=9", "PRINT B"], "PRINT B"),
    ("rnm-vars",     ["1 A=7", "RUN", "RENUM", "PRINT A"], "PRINT A"),  # R-RN17
    ("rnm-cont",     ["1 STOP", "2 PRINT 5", "RUN", "RENUM", "CONT"], "CONT"),
    ("rnm-empty",    ["RENUM", "LIST"], "LIST"),                   # R-RN18
    ("rnm-inprog",   ["1 RENUM", "2 REM B", "RUN", "LIST"], "LIST"),   # R-RN20
    ("rnm-dot",      ["1 REM A", "2 REM B", "RENUM 100,.", "LIST"], "LIST"),
]

# --- the AUTO battery --------------------------------------------------------
AUTO = [
    # CONTROL: an ordinary typed line through the SAME line editor AUTO drives,
    # so a divergence in the rows below cannot be a line-editor divergence.
    ("aut-ctl",      ["10 REM C", "LIST"], "LIST"),
    ("aut-bare",     ["AUTO", "REM X", BREAK, "LIST"], "LIST"),        # R-AU1
    ("aut-start",    ["AUTO 55", "REM X", BREAK, "LIST"], "LIST"),     # R-AU2
    ("aut-both",     ["AUTO 100,5", "REM A", "REM B", BREAK, "LIST"], "LIST"),
    # 🔴 R-AU4: `AUTO ,7` starts at 0, where `RENUM ,,5` starts at 10. The same
    # absent field, the same comma form, opposite answers -- the sibling trap
    # D-LSTRNG hit when DELETE's range rules did not transfer to LIST.
    ("aut-inconly",  ["AUTO ,7", "REM X", BREAK, "LIST"], "LIST"),
    ("aut-nocomma",  ["AUTO ,"], "AUTO ,"),                            # R-AU5
    # R-AU6: the `*` marks an EXISTING line and is screen-only -- the stored
    # line has the ordinary space. aut-plain is its no-star twin, without which
    # a machine that never prints `*` would pass on aut-star's LIST alone.
    ("aut-plain",    ["AUTO 10,10", "REM X", BREAK, "LIST"], "LIST"),
    ("aut-star",     ["10 REM OLD", "AUTO 10,10", "REM X", BREAK, "LIST"], "LIST"),
    # 🔴 R-AU7, with the SEPARATING case. Enter at a prompt whose line does not
    # exist cannot tell "skip" from "delete"; this one's line EXISTS.
    ("aut-empty",    ["10 REM KEEP", "20 REM B", "AUTO 10,10", "", BREAK,
                      "LIST"], "LIST"),
    ("aut-tail",     ["AUTO 10:B=9", BREAK, "PRINT B"], "PRINT B"),    # R-AU9
    ("aut-ceiling",  ["AUTO 65525,10", "REM A", "REM B", BREAK, "LIST"], "LIST"),
]

# --- the LLIST battery -------------------------------------------------------
# The reading is the printer log; `anchor` is unused here and kept as None.
LLT = [
    # 🔴 THE CONTROL (see the module docstring).
    ("llt-ctl",      ['OPEN"LPT:" FOR OUTPUT AS #1', 'PRINT#1,"CTL"',
                      "CLOSE#1"]),
    ("llt-all",      ["10 REM P", "20 REM Q", "30 REM R", "LLIST"]),   # R-LL1
    ("llt-one",      ["10 REM P", "20 REM Q", "30 REM R", "LLIST 20"]),
    ("llt-from",     ["10 REM P", "20 REM Q", "30 REM R", "LLIST 20-"]),
    ("llt-upto",     ["10 REM P", "20 REM Q", "30 REM R", "LLIST -20"]),
    ("llt-range",    ["10 REM P", "20 REM Q", "30 REM R", "LLIST 15-25"]),
    ("llt-rev",      ["10 REM P", "20 REM Q", "LLIST 30-20"]),         # R-LL3
    ("llt-above",    ["10 REM P", "20 REM Q", "LLIST 99"]),
    ("llt-comma",    ["10 REM P", "LLIST 10,20"]),                     # R-LL4
    ("llt-tail",     ["10 REM P", "LLIST:B=9"]),                       # R-LL5
    ("llt-empty",    ["LLIST"]),
    # R-LL6: the screen sink is restored, so the PRINT adds nothing to the log.
    ("llt-sink",     ["10 REM P", "LLIST", 'PRINT "SCR"']),
]

PROMPTS = omsx_repl.PROMPTS


def screen_rows(raw):
    """The capture as 40-column rows, WITHOUT the function-key row, and with the
    machine's LEFT MARGIN normalised away.

    ⚠️ Row 24 is the SCREEN-0 function-key display, which the two references
    show (`color auto goto list run`) and zerobas does not. Left in, EVERY row
    of this probe would diverge for a reason that has nothing to do with the
    verb under test.

    ⚠️ AND THE LEFT MARGIN IS NOT THE SAME ON THE TWO MACHINES -- C-BIOS renders
    at column 1 and the VG-8020 at column 2 ([[lean-retire-s2-switch]], where
    porting a differential to a new machine MOVED the instrument). This probe's
    first run returned `<NO ECHO>` on every screen row for exactly that reason:
    ` ZBLIST` does not start with `ZB`. So rows are FULLY stripped, which
    deliberately discards leading whitespace -- including the sign space in a
    number like ` 7`. That is a real loss and it is the right trade here: the
    sign space is gated by the print/float batteries, and keeping it would make
    every row of this one diverge on the margin instead."""
    txt = raw or ""
    return [txt[i:i + 40].strip() for i in range(0, len(txt), 40)][:-1]


def strip_prompt(row):
    """Drop a leading machine prompt. The reference opens each command with
    `Ok` and zerobas with `ZB`; a row that STARTS with one is an echo, a row
    EQUAL to one is a bare prompt (omsx_repl.PROMPTS' own note)."""
    for p in PROMPTS:
        if row.startswith(p):
            return row[len(p):]
    return row


def anchor_for(lines, declared):
    """The typed line the reading starts AFTER: the VERB's own command line.

    🔴 THIS IS THE READOUT'S LOAD-BEARING CHOICE, AND THE FIRST VERSION GOT IT
    WRONG. Anchoring on the trailing `LIST` made the reading the LISTING ONLY --
    so `Undefined line 77 in 1` (printed before the prompt that precedes the
    LIST), `Illegal function call` vs `Syntax error`, and AUTO's whole session
    including the `*` marker were ALL outside the window. A machine that
    renumbered correctly and printed no message at all would have passed
    `rnm-dang3`; a machine that never printed `*` would have passed `aut-star`.
    That is [[readout-blind-to-its-own-subject]] exactly: it fails by AGREEING.

    Anchoring on the verb instead makes the reading span everything the verb
    emitted AND the listing that follows. Derived rather than hand-listed, so a
    new row cannot quietly reintroduce the narrow window."""
    for ln in lines:
        for verb in ("RENUM", "AUTO", "LLIST"):
            if ln.startswith(verb):
                return ln
    return declared


def reading(raw, anchor):
    """Everything the machine printed AFTER the anchor command's echo.

    Two DISTINCT empty sentinels, never one: `<NO ECHO>` says the apparatus
    lost the anchor and the case produced no reading at all; `<nothing>` says
    the machine printed nothing, which for `rnm-empty` IS the answer. Collapsing
    them would make an apparatus failure compare equal across sides."""
    rows = [strip_prompt(r) for r in screen_rows(raw)]
    idx = None
    for i, r in enumerate(rows):
        if r == anchor:
            idx = i
    if idx is None:
        return "<NO ECHO>"
    out = [r for r in rows[idx + 1:] if r and r not in PROMPTS]
    return " / ".join(out) if out else "<nothing>"


def prn_reading(raw):
    """The printer half of a `screen_printer` capture, decoded with CR and LF
    VISIBLE. The framing is part of the answer -- `10 REM P\\r\\n` is the rule,
    not `10 REM P` -- so they may not be stripped."""
    if raw is None:
        return "<NO CAPTURE>"
    _, _, prn = raw.partition("7c")
    if not prn:
        return "<nothing printed>"
    try:
        b = bytes.fromhex(prn)
    except ValueError:
        return "<BAD CAPTURE>"
    return "".join({13: "\\r", 10: "\\n"}.get(c, chr(c) if 32 <= c < 127 else
                                              f"\\x{c:02x}") for c in b)


def run_side(side, only, repeat):
    """Every battery on one machine -> {label: reading}."""
    cfg = SIDES[side]
    out = {}

    def sel(rows):
        return [r for r in rows if not only or any(r[0].startswith(o)
                                                   for o in only)]

    log = os.path.join(tempfile.gettempdir(), f"zb_editverb_{side}.log")
    plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")

    rnm = sel(RNM)
    if rnm:
        # RENUM leaves no modal state -- it ends the line and the program on
        # every path -- so these batch safely.
        #
        # 🔴 BUT THE PRINTER IS PLUGGED HERE TOO, AND IT IS NOT SPARE WIRING.
        # `llt-tailb` is an LLIST row living in this battery (the ENDFLAG half of
        # R-LL5 is only visible on the SCREEN), and with NO printer plugged the
        # VG-8020's LSTOUT tight-polls port $90 FOREVER -- the machine hangs and
        # the echo guard reports a mangled delivery. That unplugged hang is
        # exactly what D-KWGAP4 filed and it is REAL; what was wrong was the
        # conclusion drawn from it, that a reference cannot be used at all. The
        # plug costs the other rows nothing: a logger changes no screen output.
        cases = [("direct", list(lines)) for _, lines, _ in rnm]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=True, reset=cfg["reset"],
            boot=cfg["boot"], step=cfg["step"], prologue=plug)
        for (label, lines, declared), raw in zip(rnm, caps):
            out[label] = reading(raw, anchor_for(lines, declared))

    aut = sel(AUTO)
    if aut:
        # 🔴 BOOT-PER-CASE, AND IT IS NOT CAUTION. AUTO is MODAL: a case that is
        # still inside a session when the batch moves on feeds the NEXT case's
        # reset and command lines to the session's line editor, and everything
        # after it measures that instead of its own subject. Measured here:
        # batched, `aut-nocomma` read `0` on BOTH references -- an AUTO prompt --
        # and `aut-plain` read `<NO ECHO>`; run alone, `aut-nocomma` is
        # `Illegal function call` on all three sides and agrees. A batched modal
        # verb produces a PLAUSIBLE reading of the wrong thing, which is the one
        # failure mode `--repeat` cannot catch (it reproduces exactly).
        # ⚠️ THE RESET HAS TO BE CARRIED INTO THE CASE. `run_cases(batch=False)`
        # IGNORES `reset` (its own docstring says so), and the CF-3300's reset is
        # not cosmetic: the leading "" answers the boot date prompt and
        # `SCREEN 0` puts it in the 40-column mode this scrape reads. Without
        # them every CF-3300 row returned `<NO ECHO>` while the other two sides
        # agreed perfectly -- an apparatus failure that looks exactly like one
        # machine disagreeing.
        cases = [("direct", list(cfg["reset"]) + list(lines))
                 for _, lines, _ in aut]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False,
            boot=cfg["boot"], step=cfg["step"], prologue=plug)
        for (label, lines, declared), raw in zip(aut, caps):
            out[label] = reading(raw, anchor_for(lines, declared))

    llt = sel(LLT)
    if llt:
        # boot-per-case: see the module docstring. `reset` is ignored on that
        # path, so each case carries the side's reset itself (the CF-3300's
        # date-prompt CR and SCREEN 0 among them).
        cases = [("direct", list(cfg["reset"]) + list(lines)) for _, lines in llt]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False, boot=cfg["boot"],
            step=cfg["step"], prologue=plug,
            capture=("screen_printer", log))
        for (label, _), raw in zip(llt, caps):
            out[label] = prn_reading(raw)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across the sides run")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {}
    for s in sides:
        for r in range(a.repeat):
            got = run_side(s, only, a.repeat)
            if r and got != results[s]:
                sys.stderr.write(
                    f"⚠️  {s}: repeat {r + 1} disagrees with repeat 1 -- "
                    "the reading is not stable, so no verdict is possible\n")
                for k in sorted(set(got) | set(results[s])):
                    if got.get(k) != results[s].get(k):
                        sys.stderr.write(
                            f"    {k}: {results[s].get(k)!r} vs {got.get(k)!r}\n")
                return 2
            results[s] = got

    labels = [r[0] for r in RNM] + [r[0] for r in AUTO] + [r[0] for r in LLT]
    labels = [l for l in labels if l in results[sides[0]]]

    refs = [s for s in sides if s in REF_SIDES]
    agree = dis = 0
    print(f"D-EDITVERB — RENUM / AUTO / LLIST   sides: {', '.join(sides)}")
    print("=" * 78)
    for label in labels:
        vals = {s: results[s].get(label, "<MISSING>") for s in sides}
        ok = len(set(vals.values())) == 1
        # An apparatus sentinel is NEVER an agreement, however many sides show
        # it: `<NO ECHO>` on every side means nothing was measured at all.
        if any(v in ("<NO ECHO>", "<NO CAPTURE>", "<BAD CAPTURE>", "<MISSING>")
               for v in vals.values()):
            ok = False
        agree += ok
        dis += not ok
        print(f"{'ok ' if ok else 'DIFF'} {label:<14} "
              + ("  ".join(f"{s}={vals[s]!r}" for s in sides)
                 if not ok else repr(vals[sides[0]])))
    print("=" * 78)
    print(f"{agree}/{agree + dis} rows agree across {len(sides)} sides"
          + (f" ({len(refs)} reference)" if refs else ""))
    if a.gate and dis:
        sys.stderr.write(f"editverb: {dis} row(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
