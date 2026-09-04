#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-SCRERR — SCREEN's argument is a CHECKED BYTE, and it is checked BEFORE the
mode is applied.

WHERE THIS CAME FROM. D-STMTPEND (2026-08-09) filed two `ex_screen` divergences
and could close neither, because SCREEN's error surface had never been measured:

  1. `SCREEN (1<5)` -- i.e. `SCREEN -1` -- is `Syntax error` (ERR 2) on zerobas
     and `Illegal function call` (ERR 5) on the VG-8020. `ex_screen` rejects an
     out-of-range mode with `jp stmt_error`, which is a GRAMMAR verdict on a
     DOMAIN fault.
  2. `SCREEN 0*(1/0)` applies the mode and THEN reports. D-STMTPEND made the
     statement boundary read the pending-error cell, so the CODE is right --
     but `CHGMOD` has already run by the time `jp exec_stmt` raises, so the
     screen is reinitialised before the message. Both references never apply
     the mode at all. That is the `u.scr.dz` DEFERRED row of
     `make stmtpend-acceptance`.

🎯 THEY ARE ONE QUESTION, NOT TWO: what does `ex_screen` check, in what order,
and what has it already done to the machine by the time it rejects.

⚠️ THE SCREEN IS THE INSTRUMENT HERE, WHICH IS EXACTLY THE HAZARD. A row that
changes the mode destroys the reading that would tell you it changed the mode --
which is why `u.scr.dz` was deferred rather than scored, and why D-STMTPEND's
own scouting got `<NO CAPTURE>` for `SCREEN 1` on BOTH sides
([[readout-blind-to-its-own-subject]]).

THIS PROBE'S ANSWER: DO NOT SCRAPE THE MODE, ASK FOR IT. Every trapped row
reads `[ E , M ]` where

    E = ERR   -- the error code, 0 if the statement completed
    M = PEEK(&HFCAF)  -- SCRMOD, the BIOS's current-screen-mode cell
                         (MSX2 Technical Handbook / MSX Assembly Page; the same
                          address basic/sysvars.inc cites for zerobas's own use)

captured in the HANDLER, before line 50 forces `SCREEN 0` to make the PRINT
readable whatever mode line 30 left behind. Every program seeds `SCREEN 1` on
line 20, so "the mode was applied" and "the mode was not applied" are DIFFERENT
readings for a target mode of 0 as well as for 2 -- the seed is what makes
`SCREEN 0*(1/0)` discriminating at all.

  M = 1  the statement rejected BEFORE `CHGMOD`  (both references)
  M = 0  `SCREEN 0*(1/0)` applied mode 0, then reported
  M = 2  `SCREEN 2+0*(1/0)` applied mode 2, then reported

THE ROW CLASSES:

  d.*  THE MODE VALUE DOMAIN. 0..5, negative, the int16 and byte boundaries,
       past int16, fractional (truncate or round?), and a string. This is the
       axis nobody had measured; `make missing-acceptance` and the graphics
       gates cover the MODES, not the REJECTS.
  a.*  THE ARGUMENT LIST SHAPE. Bare SCREEN, an omitted mode (`SCREEN ,x`),
       omitted middles (`,,`), a trailing comma, and the sprite-size argument
       in and out of its own domain.
  o.*  THE ORDERING ROWS. A deferred expression fault in the mode, in each of
       the four fault codes, plus one in a TRAILING argument (which the mode has
       legitimately been applied before reaching). These are the rows M exists
       for.
  n.*  NEGATIVE CONTROLS, each agreeing for a reason INDEPENDENT of the claim:
       a genuine syntax error in a statement that is not SCREEN, and an ordinary
       numeric fault at a reader that already checked before this slice existed.
  u.*  THE UNTRAPPED FACE: the message TEXT, its line, printed once, and whether
       the following line ran. NO SCREEN seed here -- seeding would clear the
       `RUN` echo this reading anchors on.

🟢 THE POSITIVE CONTROL FOR THE M INSTRUMENT IS `d.2`. A clean `SCREEN 2` must
read ` 0 , 2 `: that proves PEEK(&HFCAF) tracks the mode and that the seed is
overwritten by a mode that IS applied. It cannot fail because this slice's claim
about REJECT ordering is wrong -- there is no reject in it.

⚠️ Every row is a STORED program driven by `RUN`. In direct mode an abort on one
line does not stop the next.

Clean-room: observed screen output only; both reference ROMs are black boxes.
SCRMOD's address is a published MSX system-variable address, not a disassembly.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402
import probe_signal                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}

# 🔴 THE SEED IS PART OF THE MEASUREMENT, NOT SETUP. `SCREEN 1` on line 20 is
# what makes M discriminating: without it, a row whose target mode is 0 reads
# the same whether the mode was applied or not -- the exact shape of
# [[t.zero is blind to a cut that also disables its seed]], caught before it
# could bite. Q$ holds a string so the type rows are a TYPE fault and not an
# empty-variable one.
#
# Line 50's `SCREEN 0` is what makes the PRINT readable after a row that left
# the machine in SCREEN 2 or 3, and it CLEARS the screen, so the only '[' the
# reader can find is the printed one. M is captured BEFORE it, in the handler.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    '20 Q$="A":SCREEN 1',
    "30 {stmt}",
    "40 E=0:M=PEEK(&HFCAF)",
    '50 SCREEN 0:PRINT"[";E;",";M;"]":END',
    "100 E=ERR:M=PEEK(&HFCAF):RESUME 50",
]
# ⚠️ NO SCREEN SEED IN THE UNTRAPPED TEMPLATE. `screen_tail` anchors on the
# echoed `RUN`, and any mode change clears it -- so a seed would blind every
# untrapped row on every side, including the references.
UNTRAP_PROG = [
    '10 Q$="A"',
    "20 {stmt}",
    '30 PRINT"[RANON]"',
]

DZ = "0*(1/0)"          # -> 11 division by zero
S5 = "0*SQR(-1)"        # ->  5 illegal function call
OV = "0*(1E38*1E38)"    # ->  6 overflow

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === d.* THE MODE VALUE DOMAIN =========================================
    # The axis this slice exists to measure. 0..3 are the MSX1 modes; 4+ are
    # MSX2 and must be refused ON AN MSX1; then the byte, int16 and float
    # boundaries of the coercion that gets there.
    ("d.0",       "t", "SCREEN 0"),
    ("d.1",       "t", "SCREEN 1"),
    ("d.2",       "t", "SCREEN 2"),
    ("d.3",       "t", "SCREEN 3"),
    ("d.4",       "t", "SCREEN 4"),
    ("d.5",       "t", "SCREEN 5"),
    ("d.neg1",    "t", "SCREEN -1"),
    # 🔴 THE FILED ROW. `(1<5)` is -1 written so that the reject cannot be
    # blamed on the unary minus; d.rel0 is its control -- the SAME syntax
    # yielding a VALID mode, which must be accepted.
    ("d.rel",     "t", "SCREEN (1<5)"),
    ("d.rel0",    "t", "SCREEN (1>5)"),
    ("d.255",     "t", "SCREEN 255"),
    ("d.256",     "t", "SCREEN 256"),
    ("d.32767",   "t", "SCREEN 32767"),
    ("d.32768",   "t", "SCREEN 32768"),
    ("d.m32768",  "t", "SCREEN -32768"),
    ("d.m32769",  "t", "SCREEN -32769"),
    ("d.70000",   "t", "SCREEN 70000"),
    # Truncate or round? d.frac1 answers the same on both hypotheses and is the
    # control; d.frac2 and d.frac3 are the discriminators (1.6 -> 1 or 2;
    # 3.6 -> 3 (legal) or 4 (ERR 5) -- a DIFFERENT CODE, not just a different M).
    ("d.frac1",   "t", "SCREEN 1.4"),
    ("d.frac2",   "t", "SCREEN 1.6"),
    ("d.frac3",   "t", "SCREEN 3.6"),
    ("d.str",     "t", 'SCREEN "1"'),
    ("d.strv",    "t", "SCREEN Q$"),

    # === a.* THE ARGUMENT LIST SHAPE =======================================
    ("a.bare",    "t", "SCREEN"),
    ("a.col",     "t", "SCREEN:V=1"),
    ("a.c1",      "t", "SCREEN ,1"),
    ("a.c2",      "t", "SCREEN ,,1"),
    ("a.c3",      "t", "SCREEN ,,,1"),
    ("a.m1",      "t", "SCREEN 2,1"),
    ("a.m2",      "t", "SCREEN 2,,1"),
    ("a.trail",   "t", "SCREEN 2,"),
    # 🔴 THE NEIGHBOURS OF a.trail, added because a fix for it is a `jp` target
    # and a `jp` target cannot tell these apart. Measured BEFORE the fix was
    # written: a change licensed by ONE row that silently also moves three
    # unmeasured ones is a scope claim, not a fix.
    ("a.conly",   "t", "SCREEN ,"),
    ("a.c2trail", "t", "SCREEN 2,,"),
    ("a.colarg",  "t", "SCREEN 2,:V=1"),
    ("a.spr",     "t", "SCREEN 1,3"),
    # The sprite-size argument's OWN domain, and whether it is a checked byte
    # the way the mode is. `SCREEN`'s extra arguments are "evaluated and
    # ignored" by construction here (basic/screen.asm's header), so these rows
    # measure a documented divergence rather than a suspected defect.
    ("a.sprbad",  "t", "SCREEN 1,99"),
    ("a.sprneg",  "t", "SCREEN 1,-1"),
    ("a.sprbig",  "t", "SCREEN 1,70000"),
    ("a.clk",     "t", "SCREEN 1,,99"),
    # 🔴 THE POSITION ROWS. a.clk says an argument after an omitted one must not
    # be taken for the sprite size, but it says it with an ERROR CODE -- which
    # only witnesses the rule while the size has a domain to violate. These two
    # witness the SIZE ITSELF, through the one reference-visible consequence it
    # has: LEN(SPRITE$(0)) is 8 for an 8x8 sprite and 32 for a 16x16 one.
    # a.sprslot1 is the control -- the SAME reading, on the slot that IS the
    # sprite size, where the size must change.
    ("a.sprskip", "t", "SCREEN 2,,3:IF LEN(SPRITE$(0))<>8 THEN ERROR 99"),
    ("a.sprslot1", "t", "SCREEN 2,3:IF LEN(SPRITE$(0))<>32 THEN ERROR 99"),
    ("a.clk300",  "t", "SCREEN 1,,300"),
    ("a.clkbig",  "t", "SCREEN 1,,70000"),

    # === t.* THE TRAILING SLOTS 3+ — the open risk this slice filed =========
    # Filed 2026-08-10: slot 1 (sprite size) is pinned 0..3 and slot 2 (key
    # click) 0..255, but `scr_extra` treats EVERY later slot exactly like slot 2,
    # so a reference that NARROWS one of them is an unmeasured divergence.
    # MSX documents slot 3 as the cassette BAUD RATE (1 or 2) and slot 4 as the
    # PRINTER TYPE (0 or 1) -- both far narrower than 0..255, which is precisely
    # the shape the filing worried about.
    # 🎯 t.b1/t.b2 and t.p0/t.p1 are the POSITIVE side: the documented-valid
    # values must be ACCEPTED, or a row rejecting 300 proves only that the
    # statement rejects everything.
    ("t.b1",      "t", "SCREEN 1,,,1"),
    ("t.b2",      "t", "SCREEN 1,,,2"),
    ("t.b0",      "t", "SCREEN 1,,,0"),
    ("t.b3",      "t", "SCREEN 1,,,3"),
    ("t.b300",    "t", "SCREEN 1,,,300"),
    ("t.bneg",    "t", "SCREEN 1,,,-1"),
    ("t.bbig",    "t", "SCREEN 1,,,70000"),
    ("t.p0",      "t", "SCREEN 1,,,,0"),
    ("t.p1",      "t", "SCREEN 1,,,,1"),
    ("t.p2",      "t", "SCREEN 1,,,,2"),
    ("t.p300",    "t", "SCREEN 1,,,,300"),
    # a SIXTH slot: MSX2 documents interlace there, so on an MSX1 this asks
    # whether the parser bounds the ARITY at all.
    ("t.s6",      "t", "SCREEN 1,,,,,1"),

    # === o.* THE ORDERING ROWS — a deferred fault vs the side effect ========
    # 🔴 M is the whole point of these. The CODE was already made right by
    # D-STMTPEND (the trapped twin s.scr.dz agrees); what was never measured is
    # whether CHGMOD ran first.
    ("o.dz0",     "t", f"SCREEN {DZ}"),
    ("o.dz",      "t", f"SCREEN 2+{DZ}"),
    ("o.s5",      "t", f"SCREEN 2+{S5}"),
    ("o.ov",      "t", f"SCREEN 2+{OV}"),
    ("o.tm",      "t", "SCREEN (Q$<5)"),
    # ...and the mirror image: a fault in a TRAILING argument, which the mode
    # has been LEGITIMATELY applied before reaching. If M is 2 on the references
    # here and 1 above, the rule is about the mode's own argument, not about
    # SCREEN deferring all its side effects to the end of the statement.
    ("o.arg2",    "t", f"SCREEN 2,{DZ}"),
    ("o.strarg",  "t", 'SCREEN 2,"A"'),
    # 🔴 THE ROWS THAT PICK THE ROUTINE, not just the ordering. A value that
    # BOTH faulted and overflows the coercion reports whichever was written
    # LAST unless the deferred check runs FIRST -- D-EVALCHK's rule, and the
    # only thing that separates `eval_byte_checked` from the cheaper
    # `eval_byte_arg` (whose own coercion also aborts on a pending code, just
    # after overwriting it). Without these two rows the choice between them is
    # unjustified by the row set. o.5ov is the one that says the rule is "the
    # expression's error wins" and not "division by zero is special": a
    # DIFFERENT code, 5 rather than 11.
    ("o.dzov",    "t", f"SCREEN 70000+{DZ}"),
    ("o.5ov",     "t", f"SCREEN 70000+{S5}"),

    # === n.* NEGATIVE CONTROLS =============================================
    ("n.zork",    "t", "ZORK 1,2"),
    ("n.dzw",     "t", f"WIDTH {DZ}+1"),
    ("n.tmw",     "t", "WIDTH Q$"),

    # === u.* THE UNTRAPPED FACE ============================================
    ("u.rel",     "u", "SCREEN (1<5)"),
    ("u.neg1",    "u", "SCREEN -1"),
    ("u.4",       "u", "SCREEN 4"),
    ("u.256",     "u", "SCREEN 256"),
    ("u.70000",   "u", "SCREEN 70000"),
    # 🔴 THE FILED `u.scr.dz` ROW, in this probe's own grammar. Before the fix
    # zerobas answers <NO ECHO> here -- CHGMOD wiped the `RUN` this reading
    # anchors on -- and the references print an ordinary message.
    ("u.dz0",     "u", f"SCREEN {DZ}"),
    ("u.dz",      "u", f"SCREEN 2+{DZ}"),
    ("u.zork",    "u", "ZORK 1,2"),
]

# 🟢 POSITIVE CONTROLS, three readings covered. 🔴 EVERY ONE IS FIXED BY
# SOMETHING OTHER THAN THIS SLICE'S CLAIM.
CONTROLS = ("d.2", "n.zork", "n.dzw", "u.zork")

CONTROL_WANT = {
    # the M INSTRUMENT itself: a clean SCREEN 2 over a SCREEN 1 seed. No reject
    # anywhere in the row, so no ordering claim can make it fail.
    "d.2":     " 0 , 2 ",
    # a genuine syntax error in a statement that is not SCREEN: still ERR 2, and
    # the seed mode survives.
    "n.zork":  " 2 , 1 ",
    # an ordinary numeric fault at a reader that checked long before this slice.
    "n.dzw":   " 11 , 1 ",
    # the untrapped reading -- ONE message, naming its line, and line 30 skipped.
    "u.zork":  "Syntax error in 20",
}

NEGATIVE = {
    "d.2":     "NEGATIVE CONTROL — the M instrument: a clean mode IS applied",
    "d.rel0":  "NEGATIVE CONTROL — the same syntax as d.rel, a LEGAL value",
    "d.frac1": "NEGATIVE CONTROL — truncate and round agree at 1.4",
    "n.zork":  "NEGATIVE CONTROL — a syntax error outside SCREEN stays ERR 2",
    "n.dzw":   "NEGATIVE CONTROL — one numeric fault at a checking reader",
    "n.tmw":   "NEGATIVE CONTROL — a type fault at a checking reader is 13",
    "u.zork":  "NEGATIVE CONTROL — the untrapped reading itself",
    "a.sprslot1":
               "NEGATIVE CONTROL — the size witness on the slot that IS the size",
}
LABEL_W = 10

# 🔴 THE TRAILING-SLOT DIVERGENCES, MEASURED 2026-09-04 and PRICED, not fixed.
# The filing (2026-08-10) worried that a reference might NARROW a later slot.
# It does: slot 3 is the cassette BAUD RATE and its domain is 1..2 on BOTH
# references, where `scr_extra` treats every slot after the first as a plain
# 0..255 byte. And the ARITY is bounded at five -- a sixth slot is Syntax error.
# ⚠️ DEFERRED ON A MEASURED PRICE, NOT ON TASTE. Both `scr_extra` and
# `spr_extra_arg` live in main page 1, which `make basic-reloc` reports at 6
# BYTES FREE; the slot-3 dispatch plus its domain test is ~12 B and the arity
# bound another ~8. Re-price before inheriting this -- a wall reading rots
# [[repricing-page1-slice]].
# 🟢 t.b1/t.b2 (accepted) and t.b300/t.bneg (ERR 5) are what make the pair a
# domain rather than a blanket reject, and they AGREE -- so the divergence is
# exactly "0 and 3 are accepted here and refused there", not "this slot is
# unchecked".
DEFERRED: dict[str, str] = {
    "t.b0":  "slot 3 domain is 1..2 on both refs; ~12 B against 6 B free",
    "t.b3":  "slot 3 domain is 1..2 on both refs; ~12 B against 6 B free",
    "t.s6":  "arity bounded at 5 slots on both refs (ERR 2); ~8 B, same wall",
}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    zerobas emits `ZB` with no trailing newline, so the prompt shares a row with
    the next echoed line and `omsx_repl.screen_tail`'s own prompt terminator
    never fires on zb (D-ONERR0, docs/onerr0-msx1-characterization.md §3.1)."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


def program(kind: str, stmt: str) -> list[str]:
    tpl = TRAP_PROG if kind == "t" else UNTRAP_PROG
    lines = [ln.format(stmt=stmt) for ln in tpl]
    # D-SNCAP: only the TRAPPED template has a terminal point every path reaches.
    return probe_signal.mark_ends(lines) if kind == "t" else lines


# --- D-SNCAP: capture-on-signal (probes/lib/probe_signal.py) -----------------
# Every case here is its OWN BOOT (`batch=False`), so the scheduled RUN..capture
# budget is a guess at how long the case takes. The TRAPPED template ends at a
# single `:END` that BOTH paths reach -- the handler `RESUME`s onto the printing
# line -- so the case can announce completion itself and the budget becomes a
# pure FAILURE detector, firing only when a row never signalled at all.
#
# 🔴 THE UNTRAPPED ROWS ARE OUT OF SCOPE, FOR TWO INDEPENDENT REASONS, and
# either alone is enough. (1) They are BUILT to abort -- the statement raises and
# the next line is the run-on detector -- so control never reaches a POKE and
# they would fall back every time. (2) Their readout is `screen_tail`, which
# TERMINATES AT THE `Ok`/`ZB` PROMPT -- exactly the 2 characters a signal-time
# capture has not printed yet -- so converting them would change what they mean.
# They pass no sentinel at all, rather than being converted and then counted as
# fallbacks.
#
# 🟢 HOW THE TRAPPED ROWS DISCHARGE THE PROMPT BURDEN. They read through
# `omsx_repl.result_span` -- the text between the LAST `[` and the following
# `]`. Neither prompt is a bracket, so the reading is prompt-independent BY
# CONSTRUCTION. That argument is not what this rests on: the whole report was
# diffed row-by-row against a run taken BEFORE the conversion, and every row was
# identical (scratchpad/sncap/rowdiff.py).
SIG = probe_signal.Tally()


def read_case(kind: str, raw: str | None) -> str:
    if raw is None:
        return "<NO CAPTURE>"
    if kind == "t":
        v = omsx_repl.result_span(raw)
        return "<NO CAPTURE>" if v is None else v
    t = omsx_repl.screen_tail(raw, "RUN")
    return "<NO ECHO>" if t is None else clip_at_prompt(t)


def run_side(side: str, only: list[str]) -> dict:
    """BOOT-PER-CASE IS LOAD-BEARING HERE, AND IT IS MEASURED (D-BATCH6).

    🔴 `a.sprskip` READS ` 99 , 2 ` BATCHED AND ` 0 , 2 ` FRESH -- on ALL THREE
    SIDES. The sprite-size argument survives into the next case, so a batched
    matrix measures a polluted state. This file's own DENOMINATOR names that
    persistence ("the sprite size's persistence across a later bare SCREEN") as
    something it does NOT sweep; batching would have swept it accidentally and
    silently.
    ⚠️ THE ROW STILL SAYS `ok` IN BOTH MODES, because all three sides agree on
    the polluted value too. Cross-side agreement cannot see this; only
    `scratchpad/batchcheck.py`'s both-ways diff can
    [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    🟢 Its sibling `penderr` -- a byte-identical run_side -- IS convertible: the
    difference there is only the signal tally. Same shape, different verdict,
    which is why each one gets the control rather than an argument by analogy."""
    cfg = SIDES[side]
    out = {}
    for label, kind, stmt in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_scre_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(kind, stmt) + ["RUN"]
        # 🔴 A FRESH `so` PER CALL. Each case is its own boot and every boot
        # indexes from 0, so one dict reused across the loop would hold a single
        # entry and the tally would silently under-count.
        so: dict = {}
        sn = probe_signal.kwargs(so) if kind == "t" else {}
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw, **sn)
        SIG.add(so, label=f"{side}:{label}")
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHAT `ex_screen` accepts as a mode) x (WHAT IT HAS ALREADY DONE by the "
    "time it refuses). The routine has exactly TWO argument positions that "
    "reach a value -- the mode and the trailing-argument loop -- and exactly "
    "ONE side effect, the `CHGMOD` between them, so the ordering axis is "
    "two-valued and fully swept by the o.* rows rather than sampled. The VALUE "
    "axis is the one with a real population: an MSX1 accepts 0..3, so the "
    "denominator is every boundary the coercion from a FLOAT expression to "
    "that range can be asked about -- the mode edges (3/4/5), the byte edges "
    "(255/256), the int16 edges (32767/32768, -32768/-32769), past int16 "
    "(70000), the sign (-1, and `(1<5)` so the reject cannot be blamed on "
    "unary minus), the fractional boundary in BOTH directions (1.4/1.6, and "
    "3.6 where truncate-vs-round changes the ERROR CODE and not just the "
    "mode), and a string (literal and variable). Crossed with the four "
    "deferred fault codes 11/6/5/13 in the mode position and one in a trailing "
    "one. The ARGUMENT-LIST axis is swept structurally, not sampled: bare, "
    "statement-terminated, mode omitted, one and two middles omitted, a "
    "trailing comma, and the sprite-size argument in and out of ITS domain -- "
    "which is every path through ex_screen's `scr_extra` loop. NOT swept: what "
    "each mode DOES once set (the graphics gates own that), and the sprite "
    "size's persistence across a later bare SCREEN (spec-basic-graphics-g7)."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-SCRERR: SCREEN's mode is a checked byte, checked BEFORE "
                    "CHGMOD")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    print(SIG.line())
    present = [lab for lab, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-SCRERR — SCREEN's mode is a CHECKED BYTE, checked BEFORE the mode "
          f"is applied    sides: {', '.join(sides)}")
    print("=" * 78)

    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            got = results[s].get(ctl)
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    d.2    = the M INSTRUMENT — PEEK(&HFCAF) tracks the mode, "
              "and a clean\n"
              "             SCREEN 2 overwrites the SCREEN 1 seed. If this is "
              "red, every\n"
              "             M reading below it is meaningless.\n"
              "    n.zork = a syntax error OUTSIDE SCREEN is still ERR 2.\n"
              "    n.dzw  = an ordinary numeric fault reports its OWN code "
              "(11).\n"
              "    u.zork = the UNTRAPPED reading — ONE message, naming its "
              "line.\n"
              "    🔴 None of the four can fail because this slice's claim is "
              "wrong: three\n"
              "    contain no reject at all, and the fourth is not a SCREEN.\n"
              "    🔴 CLASSIFY BY WHICH SIDE FAILED: red on a REFERENCE is a "
              "broken fixture\n"
              "    (report it, score nothing); red on zb is an ordinary "
              "divergence that\n"
              "    belongs in the row set, not in the control set.\n"
              "    Check build/*.rom, `make repack-machine` and `make "
              "latch-check`, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for lab in present:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{n} row(s) on {sides[0]} — no agreement verdict from one side")
        return 0

    agree = dis = refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False
        refs = {vals[s] for s in ("vg8020", "cf3300") if s in vals}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEGATIVE:
            note = f"   [{NEGATIVE[lab]}]"
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative controls, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("READING: trapped rows are `[ ERR , SCRMOD ]` — the error code and "
          "the screen mode the statement LEFT BEHIND, captured in the handler "
          "over a `SCREEN 1` seed. Untrapped rows are the clipped screen tail "
          "of `RUN`.")
    print("SIDES: vg8020,cf3300,zb — SCREEN, ON ERROR, ERR, RESUME, PEEK and "
          "WIDTH are core MSX-BASIC, present on every MSX1, so BOTH references "
          "are legitimate oracles for every row here")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"screenerr: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
