#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""probe_signal — D-SNCAP: capture-on-signal, the plumbing every probe shares.

A case's own BASIC POKEs a watched address the instant its readout is FINAL.
`omsx_repl`'s `sentinel=` / `sentinel_capture=` watch that address and capture
THEN, so the scheduled budget stops being a guess at the completion time and
becomes what it should always have been: a pure FAILURE detector, firing only if
the case never signalled at all.

🔴 WHAT LIVES HERE, AND WHAT DELIBERATELY DOES NOT. The ADDRESS, the kwargs and
the tally are shape-free -- every probe wants the same three, and a second copy
of them is how two probes end up watching two addresses and reporting two
different things. WHERE THE MARK GOES IS NOT SHAREABLE: it is a property of the
program a probe builds, and it is the ONLY part of this that can be silently
WRONG. `mark_ends` below is one such rule -- the one the error-shaped suites
need -- and a probe whose programs have another shape states its own
(basic_probe_graphics.py's `paint_mark` handles four).

🔴 A MARK PLACED TOO EARLY IS THE FAILURE THIS MECHANISM CAN CAUSE, AND THE
TALLY CANNOT SEE IT. A mark never REACHED shows up as a fallback and is loud. A
mark that fires before the work is done captures a half-finished machine on BOTH
sides and can agree wrongly -- which is exactly what the budget existed to
prevent, now firing deterministically instead of occasionally. The only check
with teeth is a row-by-row diff of the probe's whole report against a run taken
BEFORE the conversion (scratchpad/sncap/rowdiff.py).

THE THREE RULES THAT DECIDE WHETHER A SITE CAN BE CONVERTED AT ALL:

  1. BATCHED MATRICES CANNOT BENEFIT. With `batch=True` the later cases are
     scheduled at FIXED emulated instants and the generated Tcl only exits early
     on the LAST case, so capturing early reclaims nothing. Convert `batch=False`
     (boot-per-case) sites only.
  2. A CASE THAT RAISES NEVER REACHES ITS POKE. It falls back to the budget --
     no saving, no harm, measured (an `ONERRORGOTO` row fell back at 113.0 s).
     Error-path phases are out of scope rather than converted-and-noisy: pass no
     sentinel at all for them, so they are not counted as fallbacks either.
  3. 🔴 A LAYOUT-SENSITIVE READOUT CANNOT TAKE A MARK IN ITS OWN PROGRAM, and
     this rule was learned on the third gate, not designed in. The mark is
     BASIC TEXT: it makes the tokenised program ~8 bytes longer per marked line,
     VARTAB sits directly above the program text, and so every reading that IS a
     RAM address moves by exactly that much. `basic_probe_deffn.py`'s five
     `ADDR` rows report `VARPTR`s and are therefore left unmarked -- not because
     marking them fails, but because it would MOVE THE ANSWER. Ask of any probe:
     does its readout name a place, or a value?

⚠️ THE `capture="screen"` BURDEN. omsx_repl's blanket refusal was lifted
2026-08-25 and replaced by a burden, because the measurement behind it stands: a
screen captured at signal time is missing the `Ok`/`ZB` prompt -- 2 characters,
on all three machines. A probe adopting this for a TEXT readout must show its
OWN readout is prompt-independent. `omsx_repl.result_span` (the last `[`..`]`
span) and `basic_probe_deffn.face` (the first such span) are, by construction --
neither prompt is a bracket. `omsx_repl.screen_tail`, which TERMINATES at the
prompt, is not, and no probe may convert a row that reads through it.
"""
from __future__ import annotations

import re

MARK_ADDR = 0xE000
MARK_VAL = 255
# The BASIC that signals. 🔴 ONE CONSTANT, BECAUSE THE WATCHPOINT'S VALUE FILTER
# AND THE POKE HAVE TO AGREE: two spellings is a probe whose sentinel never fires
# and whose tally reads "fell back" forever without anything looking broken.
POKE = f"POKE&H{MARK_ADDR:04X},{MARK_VAL}"

# `<n> END`, the one terminal shape `:END` cannot match.
_NUM_END = re.compile(r"^(\d+\s+)END$")


def kwargs(out: dict) -> dict:
    """The capture-on-signal kwargs, wired to record HOW each capture happened.

    🔴 ONE FRESH `out` PER `run_cases` CALL. Every call indexes its cases from 0,
    so a dict reused across CALLS overwrites the earlier call's entries -- and
    the tally would under-count without anything ever looking wrong. (Within
    ONE call, boot-per-case included, each case has its own key since
    D-SETTLEKEY, 2026-09-28; before that a `batch=False` call piled every
    case's readings under key 0.)"""
    return dict(sentinel=(MARK_ADDR, MARK_VAL), sentinel_capture=True,
                settle_out=out)


def mark_ends(lines: list[str], poke: str = POKE) -> list[str]:
    """Put the signal immediately before EVERY `END` in `lines`.

    🔴 EVERY ONE, NOT THE FIRST. A trapped scaffold has a normal exit and a
    handler exit. The five error-shaped suites happen to converge both onto one
    printer (`RESUME 50`), but `basic_probe_deffn.py`'s does not -- it ends at
    line 60 or at line 900 -- and marking only the first would leave the whole
    error half of that matrix falling back with nothing to say why.

    🔴 AND THE MARK MUST BE THE LAST THING THAT RUNS ON ITS LINE. `END` is what
    makes that automatic here: everything the readout needs has been PRINTed by
    the time control reaches it. That is the entire reason this rule is
    expressed as "before END" and not "at the end of the printing line".

    Raises rather than returning `lines` unchanged when nothing matched: a probe
    that silently marked nothing captures on the budget forever and reports a
    perfectly clean 0-of-0 tally."""
    out, marked = list(lines), 0
    for i, ln in enumerate(out):
        if ln == "END":
            out[i], marked = f"{poke}:END", marked + 1
        elif ln.endswith(":END"):
            out[i], marked = f"{ln[:-4]}:{poke}:END", marked + 1
        else:
            m = _NUM_END.match(ln)
            if m:
                out[i], marked = f"{m.group(1)}{poke}:END", marked + 1
    if not marked:
        raise AssertionError(
            f"probe_signal.mark_ends: no `END` to mark in {lines!r} -- this "
            "program has no terminal point, so it can never signal and the "
            "budget would silently stay the only capture")
    return out


class Tally:
    """How every capture in this probe ACTUALLY happened -- and it must be
    PRINTED, or the adoption is unfalsifiable.

    🔴 A CASE WHOSE SENTINEL NEVER FIRES FALLS BACK TO THE BUDGET AND PASSES
    IDENTICALLY. A green probe therefore says NOTHING about whether
    capture-on-signal is happening at all -- [[savestate-slice]]: an optimisation
    that does nothing is indistinguishable from one that works. This is the line
    that separates them.

    The emulated instants are the DETERMINISTIC figure here. Wall time is not:
    it moves with host contention, and the conversion is not sold on it."""

    def __init__(self) -> None:
        self.hit = 0
        self.fell_back = 0
        self.at: list[float] = []      # emulated instant of each signal capture
        self.missed: list[str] = []    # which case never signalled
        self.replayed = 0              # D-REFCACHE: served from the store, so
                                       # these instants describe an EARLIER run

    def add(self, *outs: dict, label: str | None = None) -> None:
        """Fold one `run_cases` call's `settle_out` in. Pass `label` -- 🔴 AN
        UNNAMED FALLBACK IS AN UNNAMED OUTCOME. The first run of the converted
        `deffn-strict` reported "1 fell back" out of 72 and could not say WHICH
        row, so the one thing the tally exists to find could not be looked at
        without re-running the gate. A count says the detector fired; only the
        label says what it caught."""
        for o in outs:
            # \U0001f534 A REPLAYED PROVENANCE IS NOT A READING OF THIS RUN
            # (D-REFCACHE). These are emulated-time instants; served from the
            # store they say how an EARLIER run captured. Counted separately so
            # `line()` can never report a recording as live apparatus health.
            if o.get("replayed"):
                self.replayed += 1
            sig = o.get("sentinel", {})
            self.hit += len(sig)
            self.at += list(sig.values())
            fb = o.get("fallback", {})
            self.fell_back += len(fb)
            self.missed += [label or "?"] * len(fb)

    def line(self, budget: float | None = None, indent: str = "    ") -> str:
        b = ("the scheduled budget" if budget is None
             else f"the {budget:.0f}s budget")
        s = (f"{indent}capture-on-signal: {self.hit} on signal, "
             f"{self.fell_back} fell back to {b}")
        if self.replayed:
            s += (f"   \u26a0\ufe0f {self.replayed} REPLAYED from the refcache "
                  f"-- not measured on this run")
        if self.at:
            s += (f"   [signalled at {min(self.at):.1f}-{max(self.at):.1f} "
                  f"emulated s]")
        if self.fell_back:
            s += ("\n" + indent + "  ⚠️ NEVER SIGNALLED (captured on the budget, "
                  "as before this conversion): " + ", ".join(self.missed))
        return s
