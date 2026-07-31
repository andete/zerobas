#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LNBLANK -- WHAT A BLANK INSIDE A LINE NUMBER DOES.

Spec: docs/spec-basic-lnblank.md.  Measurement: docs/lnblank-msx1-characterization.md.

WHY THIS EXISTS
===============
D-LINEMAX's `tok` battery had a FAILING TWO-SIDED CONTROL that had nothing to do
with line length (basic_probe_linemax.py:139):

    typed:      20 0#0#0#0#0#
    VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
    zerobas ->  line 20,  body = five double literals

The reference's line-number scan crossed the blank and kept accumulating
(`20` + ` ` + `0` = 200); zerobas stopped at it. Same source text, different line
number AND different body. There it was a confound and the battery dodged it by
putting `A=` in the payload. Here it is the subject.

TWO NAMED RULES, AND EVERY ROW SEPARATES THEM
=============================================
  rule T (terminate) -- the scan ends at the first non-digit.  zerobas today.
  rule S (skip)      -- blanks are transparent; the scan ends at the first
                        non-digit, non-blank.

A row where T and S predict the SAME bytes is a CONTROL and is labelled one. It
is pinned BECAUSE it agrees: a cell pinned that way is what caught the regression
D-BADFNUM's signed-off design shipped. Every other row is chosen so the two rules
predict DIFFERENT bytes -- a cell that agrees can agree for the wrong reason.

TWO ORACLES, NOT ONE
====================
The whole slice rests on ONE filed row from ONE machine. Every row here is asked
of the VG-8020 *and* the CF-3300. A rule both show is a property of MSX-BASIC,
which is what zerobas is a faithful implementation of; a rule only one shows is a
property of that ROM, and copying it would be a mistake a single oracle cannot
detect. Affordable only because the readout is MEMORY, not screen: the CF-3300
boots Disk BASIC in SCREEN 1, which would otherwise need the whole geometry
dance diskbasic_probe_chancost.py carries.

THE INSTRUMENT
==============
`("stored_line", TXTTAB)` -- omsx_repl's __hex_line dereferences TXTTAB ($F676)
and returns the EXACT bytes of the first stored line, using the link word for the
extent so an embedded $00 in a value byte never truncates it. It is the only
readout that tells "different line number" from "different body", and the filed
row differs in BOTH.

⚠️ THE LINK WORD IS NEVER COMPARED. It is an ABSOLUTE address, and the CF-3300's
Disk BASIC text base is not the VG-8020's $8001 -- comparing raw captures would
report every row as divergent for a reason that is not a behaviour. `decode()`
reads the line number and body and drops the link.
"""
from __future__ import annotations
import argparse, os, shutil, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

TXTTAB = 0xF676          # sysvar: pointer to the BASIC text base (all machines)
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# side -> how to drive it. `reset` is emitted before EVERY case.
#
# ⚠️ THE CF-3300's LEADING "" IS THE BOOT DATE PROMPT. An empty line injects a
# bare CR, which accepts the default date; at the BASIC prompt every later one is
# a no-op. Emitting it per case rather than once costs a step and needs no
# library change. Its 4.5 s cadence is not a guess -- D-LOF measured the CF-3300
# EATING keystrokes at shorter ones (diskbasic_probe_chancost.py:479).
#
# ⚠️ `diska` is a /tmp COPY, never the committed image: nothing here writes to a
# disk, but a probe that hands openMSX the repo's own .dsk is one bug away from
# mutating a committed artifact.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=None),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "NEW"), diska=SRC_DSK),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=None),
}
REF_SIDES = ("vg8020", "cf3300")

TAB = "\t"

# --- the `num` battery: the LEADING line number (program.asm parse_lineno) ----
# Payloads end in `REMX` because REM keeps the rest of its line VERBATIM on every
# MSX (basic/tokenise.inc:99/181), so the body reads back as $8F + 'X' with no
# token decoding needed and no second variable in the way.
NUM = [
    # label          typed lines                       role
    ("num-plain",    ["20 REMX"]),        # CONTROL: T and S both -> line 20
    ("num-nospace",  ["20REMX"]),         # CONTROL: no blank at all
    ("num-stop",     ["2 X=1"]),          # CONTROL: a letter stops the scan on
                                          # both (linemax:145 already asserts it)
    ("num-lead",     [" 20 REMX"]),       # CONTROL: dispatch_line skip_spaces
    ("num-blank1",   ["2 0 REMX"]),       # T -> line 2;  S -> line 20
    ("num-blank2",   ["2  0 REMX"]),      # is ANY RUN of blanks transparent?
    ("num-blank3",   ["2 0 0 REMX"]),     # T -> line 2;  S -> line 200
    ("num-filed",    ["20 0#0#0#0#0#"]),  # THE FILED ROW, reproduced verbatim
    ("num-mid",      ["20 0REMX"]),       # T -> line 20 + '0'; S -> line 200
    ("num-body1",    ["20  REMX"]),       # BODY-OFFSET axis: is a blank kept?
    ("num-body2",    ["20   REMX"]),      # three blanks
    ("num-zero",     ["0 REMX"]),         # CONTROL: line 0
    ("num-max",      ["6 5 5 2 9 REMX"]), # S -> 65529, the documented ceiling
    ("num-over",     ["6 5 5 3 0 REMX"]), # S -> 65530: accepted, or refused?
    ("num-huge",     ["9 9 9 9 9 REMX"]), # S -> 99999: wraps, or refused?
    # ⚠️ INFORMATIONAL, NON-GATING. The MSX line editor may expand TAB inside the
    # INPUT BUFFER, in which case this row measures the editor and not the scan.
    # Reported with that caveat whichever way it reads.
    ("num-tab",      ["2" + TAB + "0 REMX"]),
    # THE CRISPEST SEPARATOR IN THE BATTERY. Store line 20, then type `2 0` with
    # no body. Under S that is "delete line 20" -> the program is EMPTY. Under T
    # it is "delete line 2", which does not exist -> line 20 survives. The two
    # rules differ in the NUMBER OF STORED LINES, which no adjacent behaviour can
    # produce by accident -- so this is also the falsification witness (spec §6).
    ("num-only",     ["20 REMY", "2 0"]),
]

# --- the `lit` battery: is it the LINE-NUMBER scan, or the NUMBER scanner? ----
# The structural question, and the one that sizes the fix. If these come back
# S-shaped then the defect is not in the line-number scan at all and the spec is
# wrong about its own subject -- which is worth knowing BEFORE a fix, not after.
LIT = [
    ("lit-ctl",      ["20 A=10"]),        # CONTROL
    ("lit-assign",   ["20 A=1 0"]),
    ("lit-print",    ["20 PRINT 1 0"]),
    # ⚠️ THE FIRST RUN ANSWERED THIS BATTERY "S", AND THAT MOVED THE SUBJECT.
    # `20 A=1 0` crunched to the SINGLE literal 10 ($0F,$0A) on BOTH references
    # -- byte-identical to `20 A=10`. So blank-transparency is NOT a property of
    # the line-number scan, which is all the TODO filed; it is a property of the
    # NUMBER SCANNER. These rows measure how far that reaches, because a fix
    # aimed at one scanner and a fix aimed at all of them are different slices.
    ("lit-add",      ["20 A=1 0+2 0"]),   # two literals in one expression
    ("lit-hex",      ["20 A=&H1 F"]),     # does a HEX literal skip blanks too?
    ("lit-float",    ["20 A=1 . 5"]),     # the decimal point
    ("lit-exp",      ["20 A=1E 2"]),      # the exponent
    # GATING CONTROLS -- the two places a blank MUST survive. Any fix that makes
    # blanks transparent to a scanner must not reach inside a string literal or
    # a REM tail, and these are what say so.
    ("lit-str",      ['20 A$="1 0"']),
    ("lit-rem",      ["20 REM1 0"]),
    # ⚠️ INFORMATIONAL, and it asks how deep the rule goes: MS-BASIC's blank
    # handling is famously a property of the character FETCH, not of any one
    # scanner, in which case `A B` is the variable `AB`. If that reads S-shaped
    # too, the mechanism is one thing and not three -- worth knowing, out of
    # scope to act on here (spec §7).
    ("lit-varname",  ["20 A B=1"]),
]

# --- the `body` battery: WHERE THE BODY STARTS -------------------------------
# ⚠️ THE FIRST RUN PRODUCED THREE READINGS NO SINGLE RULE FITS, and the body
# offset is not a cosmetic detail -- it is part of the stored bytes a faithful
# implementation has to reproduce:
#
#     `20 REMX`  -> body `<8F>X`    -- the blank is GONE
#     `0 REMX`   -> body ` <8F>X`   -- the blank SURVIVES
#     `2 X=1`    -> body `X<EF><12>`-- gone again, and this is also one digit
#
# One digit and one blank gives a different answer in `0 REMX` than in `2 X=1`,
# so neither "digit count" nor "one blank is eaten" explains it on its own. This
# battery separates the three candidate variables -- how many DIGITS, how many
# BLANKS, and whether the VALUE 0 or the REM body is what is special -- by moving
# exactly one of them at a time. Reasoning did not produce a rule here; the rows
# are the only thing that will.
BODY = [
    ("body-d1",      ["1 REMX"]),         # 1 digit, 1 blank, non-zero
    ("body-d1b2",    ["1  REMX"]),        # 1 digit, 2 blanks
    ("body-d2",      ["12 REMX"]),        # 2 digits
    ("body-d3",      ["123 REMX"]),       # 3 digits
    ("body-d4",      ["1234 REMX"]),      # 4 digits
    ("body-z1",      ["0 REMX"]),         # the anomalous row, repeated here
    ("body-z2",      ["0  REMX"]),        # value 0, 2 blanks
    ("body-z0",      ["00 REMX"]),        # value 0 written with 2 digits
    ("body-zl",      ["01 REMX"]),        # a LEADING ZERO: value 1, 2 digits
    ("body-x1",      ["1 X=1"]),          # 1 digit, non-REM body
    ("body-x2",      ["12 X=1"]),         # 2 digits, non-REM body
    ("body-x3",      ["123 X=1"]),        # 3 digits, non-REM body
    ("body-zx",      ["0 X=1"]),          # value 0, non-REM body
]

# --- the `ref` battery: a line-number REFERENCE inside a statement ------------
# tokenise.inc:444 branch_lineno -- DIFFERENT CODE from parse_lineno, and the
# TODO says in as many words to measure rather than assume it follows.
#
# The readout makes both halves visible at once: the crunched value appears as
# $0E,<lo>,<hi> and a blank that was COPIED rather than skipped appears as a $20
# byte. bl_yes copies blanks BEFORE the number verbatim, so `ref-sp` pins that
# behaviour separately from the blank INSIDE the number.
REF = [
    ("ref-ctl",      ["20 GOTO 10"]),         # CONTROL: $0E,0A,00
    ("ref-sp",       ["20 GOTO   10"]),       # CONTROL: leading blanks verbatim
    ("ref-goto",     ["20 GOTO 1 0"]),
    ("ref-gosub",    ["20 GOSUB 1 0"]),
    ("ref-then",     ["20 IF A THEN 1 0"]),
    ("ref-restore",  ["20 RESTORE 1 0"]),
    ("ref-run",      ["20 RUN 1 0"]),
    ("ref-resume",   ["20 RESUME 1 0"]),
    ("ref-onlist",   ["20 ON A GOTO 1 0,2 0"]),
    ("ref-oncomma",  ["20 ON A GOTO 1 0 , 2 0"]),
    # ⚠️ MEASURED, FILED, NOT FIXED (spec §7). zerobas emits $0E only for
    # GOTO/GOSUB/THEN/RESTORE/RUN/RESUME; LIST/DELETE/AUTO/RENUM are not in
    # bl_yes at all, so their arguments crunch as ordinary numeric literals. A
    # divergence here is a MISSING FEATURE sitting next to this defect, not this
    # defect -- it earns its own TODO item with these bytes attached. They are
    # measured anyway because leaving them out would sample the reference path
    # rather than cover it, which is the trap D-NOTOPEN2 hit (3 of 7 rows gave a
    # different answer than all 7).
    ("ref-list",     ["20 LIST 1 0"]),
    ("ref-delete",   ["20 DELETE 1 0"]),
    ("ref-auto",     ["20 AUTO 1 0"]),
    ("ref-renum",    ["20 RENUM 1 0"]),
    # ELSE <line> is a KNOWN, DOCUMENTED gap (tokenise.inc:441). Informational.
    ("ref-else",     ["20 IF A THEN 1 0 ELSE 2 0"]),
]

CASES = NUM + BODY + LIT + REF

INFORMATIONAL = {"num-tab", "ref-list", "ref-delete", "ref-auto", "ref-renum",
                 "ref-else", "lit-varname"}
CONTROLS = {"num-plain", "num-nospace", "num-stop", "num-lead", "num-zero",
            "lit-ctl", "lit-str", "lit-rem", "ref-ctl", "ref-sp"}


def battery(label):
    return label.split("-")[0]


# --- decoding ----------------------------------------------------------------
def gloss(b: bytes) -> str:
    """Body bytes -> a readable string: printable ASCII verbatim, everything else
    as <XX>. Byte-exact and legible in the same breath, so a characterization
    table can be read without a token decoder."""
    return "".join(chr(x) if 0x20 <= x < 0x7F else f"<{x:02X}>" for x in b)


def decode(hexstr):
    """One capture -> its reading. FOUR distinct values, never folded together:

      None                       -> NOCAPTURE: the run never produced a capture.
                                    ⚠️ FATAL. Two sides that both failed compare
                                    EQUAL and would print `agree`.
      "REFUSED (empty program)"  -> the line was rejected on entry. A BEHAVIOUR.
      "RUNT ..."                 -> a stored line too short to have a header.
      "line N | body"            -> the reading.

    The 2-byte LINK is dropped: it is an absolute address and the CF-3300's text
    base is not the VG-8020's."""
    if hexstr is None:
        return "NOCAPTURE"
    if hexstr == "":
        return "REFUSED (empty program)"
    b = bytes.fromhex(hexstr)
    if len(b) < 5:
        return f"RUNT {b.hex()}"
    lineno = b[2] | (b[3] << 8)
    body = b[4:]
    if body and body[-1] == 0:          # the line terminator, not a value byte:
        body = body[:-1]                # the link fixed the extent for us
    return f"line {lineno} | {gloss(body)}"


BAD = ("NOCAPTURE", "UNSTABLE")


def is_bad(v) -> bool:
    return any(v.startswith(p) for p in BAD)


# --- the echo guard ----------------------------------------------------------
# ⚠️ THE STANDARD ECHO GUARD SQUEEZES WHITESPACE, AND HERE THAT WOULD MAKE IT
# BLIND TO THE ONLY CHARACTER UNDER TEST. diskbasic_probe_chancost.py's
# echo_missing() collapses runs of blanks so a wrapped echo still matches; this
# subject IS the blank, so `2 0 REMX` and `20 REMX` would squeeze to the same
# string and a dropped space -- the exact mangle this guard exists to catch --
# would read as a clean echo. Blanks are compared INTACT. Nothing here is longer
# than 26 characters, so no echo wraps and the squeeze buys nothing anyway.
#
# ⚠️ AND NOT SQUEEZING IS WHAT EXPOSED THE LEFT MARGIN. The first cut compared
# `row.rstrip()` against the typed text and reported MANGLED for EVERY row on
# BOTH references -- while the memory pass was reading those same rows perfectly.
# The screen puts a two-column margin in front of everything:
#
#     row 0: '  Ok                 '
#     row 1: '  20 REMX            '
#
# The squeeze the other probes use had been hiding that margin, not tolerating
# it. `lstrip()` is NOT the fix either: `num-lead` types ' 20 REMX', whose
# leading blank is the measurement, and lstrip would eat it along with the
# margin. So the margin is MEASURED per capture -- the narrowest indent on the
# screen, which the prompt row always supplies -- and only exactly that many
# columns are removed. A payload's own leading blanks survive; an inserted or
# dropped one still fails.
def echo_missing(raw, lines, prompt):
    if raw is None:
        return ["<NO CAPTURE>"]
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].rstrip()
            for r in range(omsx_repl.ROWS)]
    live = [r for r in rows if r.strip()]
    if not live:
        return ["<BLANK SCREEN>"]
    margin = min(len(r) - len(r.lstrip(" ")) for r in live)
    seen = {r[margin:] for r in live}
    seen |= {r[len(prompt):] for r in seen if prompt and r.startswith(prompt)}
    return [ln for ln in lines if ln not in seen]


# --- driving one side --------------------------------------------------------
def run_side(side, cases, repeat, echo):
    """Deliver `cases` to one machine and return a reading per case.

    ⚠️ REPEAT IS NOT OPTIONAL ON A REFERENCE PASS, AND THE REASON IS ASYMMETRIC.
    A dropped keystroke changes the stored bytes and looks EXACTLY like a
    semantic divergence. In the differential direction that produces a false
    FAIL -- loud, and safe. In the ORACLE-LOCK direction, where the reference's
    answer is written down as the oracle, it produces a false PASS forever. So
    every reference pass runs twice on independent boots and any row whose two
    readings differ is UNSTABLE and fatal. The two directions do not deserve the
    same guard."""
    cfg = dict(SIDES[side])
    diska = cfg.pop("diska")
    tmp = None
    if diska:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"lnb_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    reset = cfg.pop("reset")
    if echo:
        # The echo pass reads the SCREEN, so every case must start from a cleared
        # one -- otherwise 30+ cases scroll each other off a 24-row display and a
        # missing echo means nothing. `SCREEN 0` is explicit because the CF-3300
        # boots Disk BASIC in SCREEN 1, whose name table this scraper does not
        # read. The MEMORY pass deliberately does NOT set it: a RAM reading is
        # mode-independent, so the memory pass observes each machine in its own
        # boot mode and only the guard pass perturbs it.
        reset = reset + ("SCREEN 0", "CLS")
    capture = "screen" if echo else ("stored_line", TXTTAB)

    runs = []
    for _ in range(repeat):
        runs.append(omsx_repl.run_cases(
            cfg["machine"], [("direct", lines) for _l, lines in cases],
            reset=reset, capture=capture, boot=cfg["boot"], step=cfg["step"],
            diska=tmp))
    if tmp:
        os.unlink(tmp)

    if echo:
        prompt = "ZB" if side == "zb" else "Ok"
        out = []
        for i, (label, lines) in enumerate(cases):
            miss = set()
            for r in runs:
                miss |= set(echo_missing(r[i], lines, prompt))
            out.append("ECHOED" if not miss else f"MANGLED not echoed: {sorted(miss)}")
        return out

    out = []
    for i, (label, _lines) in enumerate(cases):
        vals = [decode(r[i]) for r in runs]
        if len(set(vals)) != 1:
            out.append(f"UNSTABLE across {repeat} boots: {vals}")
        else:
            out.append(vals[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", default=",".join(REF_SIDES),
                    help="comma-separated: vg8020,cf3300,zb")
    ap.add_argument("--only", help="comma-separated label substrings")
    ap.add_argument("--repeat", type=int, default=2,
                    help="boots per side; 2 is mandatory for an ORACLE-LOCK pass")
    ap.add_argument("--echo", action="store_true",
                    help="run the ECHO GUARD pass (screen capture) instead of "
                         "the measurement: proves the cadence delivers these "
                         "payloads verbatim on this machine")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()

    sides = [s.strip() for s in args.sides.split(",") if s.strip()]
    for s in sides:
        if s not in SIDES:
            print(f"APPARATUS FAILURE: unknown side {s!r}")
            return 1
    want = [t.strip() for t in (args.only or "").split(",") if t.strip()]
    sel = [c for c in CASES if not want or any(t in c[0] for t in want)]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1
    if args.repeat < 1:
        print("APPARATUS FAILURE: --repeat must be >= 1")
        return 1

    cols = {s: run_side(s, sel, args.repeat, args.echo) for s in sides}

    wide = max(len(v) for vs in cols.values() for v in vs)
    wide = min(wide, 60)
    print(f"{'label':13} {'battery':8} " + " ".join(f"{s:{wide}}" for s in sides))
    for i, (label, lines) in enumerate(sel):
        tag = label + ("*" if label in INFORMATIONAL else
                       "^" if label in CONTROLS else "")
        print(f"{tag:13} {battery(label):8} "
              + " ".join(f"{cols[s][i][:wide]:{wide}}" for s in sides))
        print(f"{'':13} typed    {lines!r}")
    print("\n^ = two-sided control (T and S predict the SAME bytes)"
          "   * = informational, non-gating")

    if args.echo:
        # ⚠️ AN INFORMATIONAL ROW MAY FAIL THIS GUARD AS ITS MEASUREMENT, not as
        # an apparatus fault. `num-tab`'s whole premise is that the MSX line
        # editor may transform a TAB inside the input buffer -- if it does, the
        # echo cannot match what was injected, and that is the row's finding
        # rather than a mangle. Reported loudly, but it does not condemn the run;
        # a gating row that fails still does.
        soft, hard = [], []
        for i, (label, _l) in enumerate(sel):
            for s in sides:
                if cols[s][i] != "ECHOED":
                    (soft if label in INFORMATIONAL else hard).append(
                        f"{label} on {s}: {cols[s][i]}")
        if soft:
            print("\nINFORMATIONAL rows whose echo does not match what was "
                  "injected (the machine transformed it -- a reading, not a "
                  "fault):")
            for m in soft:
                print(f"  {m}")
        if hard:
            print("\nAPPARATUS FAILURE -- the harness did not type these "
                  "verbatim; no row in this run is a finding:")
            for m in hard:
                print(f"  {m}")
            return 1
        print("\nECHO GUARD: every gating payload typed verbatim on every side.")
        return 0

    # --- guards, BEFORE any row is read as a finding --------------------------
    bad = []
    for i, (label, _l) in enumerate(sel):
        for s in sides:
            if is_bad(cols[s][i]):
                bad.append(f"{label} on {s}: {cols[s][i]}")
    if bad:
        print("\nAPPARATUS FAILURE -- no row in this run is a finding:")
        for m in bad:
            print(f"  {m}")
        return 1

    if len(sides) < 2:
        return 0

    # --- the comparison -------------------------------------------------------
    # Every side must read IDENTICALLY. With two references that is "do the two
    # oracles agree with each other"; with zerobas in the list it is the
    # differential. Informational rows are reported but never gate.
    npass = ngate = 0
    diverge = []
    for i, (label, _l) in enumerate(sel):
        vals = {cols[s][i] for s in sides}
        ok = len(vals) == 1
        if label not in INFORMATIONAL:
            ngate += 1
            npass += 1 if ok else 0
        if not ok:
            diverge.append((label, {s: cols[s][i] for s in sides}))
    print(f"\n{npass}/{ngate} gating rows agree across {sides}")
    if diverge:
        print("\nDIVERGENT:")
        for label, d in diverge:
            note = "  (informational)" if label in INFORMATIONAL else ""
            print(f"  {label}{note}")
            for s, v in d.items():
                print(f"      {s:8} {v}")

    return 1 if (args.gate and npass != ngate) else 0


if __name__ == "__main__":
    sys.exit(main())
