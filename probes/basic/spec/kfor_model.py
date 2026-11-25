#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for FOR / NEXT's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 5). The cases come from probes/basic/spec/kfor.py's committed run (scratchpad/KFR_run1.out, groups FX and FY).

THE MODEL IS AN INTERPRETER (goldfish pass 1, 2026-11-25, scratchpad/REVIEW-m2-gkwfor.md: the first model was a
per-case table, so no rule's law was ever computed). It runs each case's own line -- statement by statement, RESUME
NEXT going on after an error, the probe's guard ending a loop at 21 runs -- with the FOR / NEXT laws the rules state:

  FOR v=a TO b [STEP s]   the variable is made (if new) BEFORE anything else is checked; `=`; the start is evaluated
                          and STORED (converted to v's type) before TO is looked for; the limit, then STEP, each
                          evaluated ONCE and converted to v's type (an integer: cut towards zero, -32768..32767 or 6);
                          only then a frame is pushed -- ON TOP, even when v already has one; text after STEP's value is
                          error 2 AFTER the push. Any earlier error pushes no frame. The body runs at least once.
  NEXT [v{,v}]            a bare NEXT takes the top frame; a name is made (if new), then looked for from the top: a
                          miss is error 1 and leaves every frame where it was; a hit drops the frames above it. v + STEP
                          in v's type (an integer past the range: 6, v unchanged); the loop ends when v has passed the
                          limit in STEP's direction -- STEP 0 never ends. The rest of the list is read only when the loop
                          ends; an empty item (a trailing comma) is a bare NEXT; a name skips spaces (`NEXT I J` = IJ).

A control (kfor_controls.py) flips ONE of these laws (`alt`) and must be FALSE on some case."""
import os
import re
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kfor  # noqa: E402
import ramrec  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "v", "c"]
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = ("each case's first and last error, the number of errors, the body's runs (WN%, 21 = the probe's guard "
                "ended a loop that did not stop) and the loop variable's value after it")
GUARD = 20
NAME = r"[A-Z][A-Z0-9 ]*[%!#$]?"


class Err(Exception):
    def __init__(self, n):
        self.n = n


class Skip(Exception):
    pass


def _round(x, digits):
    if x == 0:
        return Fr(0)
    s, a, e = (-1 if x < 0 else 1), abs(x), 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fr(1, 10):
        a *= 10
        e -= 1
    m = a * 10 ** digits
    q = int(m) + (1 if m - int(m) >= Fr(1, 2) else 0)
    return s * Fr(q, 10 ** digits) * Fr(10) ** e


class Machine:
    def __init__(self, alt):
        self.alt = alt
        self.vars = {}
        self.frames = []          # [key, limit, step, body pc, (limit text, step text), the private count]
        self.errs = []
        self.wn = 0

    # -- values -------------------------------------------------------------------------------------------------
    def key(self, name):
        name = name.replace(" ", "")
        t = name[-1] if name[-1] in "%!#$" else "#"
        return name.rstrip("%!#$")[:2], t

    def conv(self, t, x, step=False):
        """x stored in type t (an integer: cut towards zero, -32768..32767 or error 6)"""
        if isinstance(x, str):
            raise Err(13)
        if t == "%":
            if "int-round" in self.alt and not step:
                q = int(x + Fr(1, 2)) if x >= 0 else -int(-x + Fr(1, 2))
            elif "int-floor" in self.alt:
                q = x.numerator // x.denominator
            else:
                q = int(x)
            if not -32768 <= q <= 32767:
                if "int-wrap" in self.alt and not step:
                    return Fr((q + 32768) % 65536 - 32768)
                raise Err(6)
            return Fr(q)
        return _round(x, 6 if t == "!" else 14)

    def expr(self, s):
        s = s.strip()
        if s == "":
            raise Err(24)
        if s.startswith('"'):
            return s.strip('"')
        if "/" in s:
            a, b = (self.expr(x) for x in s.split("/"))
            if b == 0:
                raise Err(11)
            return _round(a / b, 14)
        if re.fullmatch(r"-?[A-Z][A-Z0-9]*[%!#]?", s):
            v = self.vars.get(self.key(s.lstrip("-")), Fr(0))
            return -v if s.startswith("-") else v
        return Fr(s.rstrip("!#"))

    # -- statements ---------------------------------------------------------------------------------------------
    def for_(self, rest, pc):
        m = re.match(r"\s*([A-Z][A-Z0-9]*[%!#$]?)(.*)$", rest)
        if not m:
            raise Err(2)                                   # a number as the variable: nothing is made
        name, rest = m.group(1), m.group(2)
        if rest.startswith("("):
            raise Err(2)                                   # an array element
        k = self.key(name)
        if k[1] == "$":
            raise Err(13)
        if "make-late" not in self.alt:
            self.vars.setdefault(k, Fr(0))                 # made FIRST
        if not rest.startswith("="):
            raise Err(2)
        parts = re.split(r"\s(TO|STEP)(?=\s|$)", rest[1:])
        self.vars.setdefault(k, Fr(0))
        start = self.expr(parts[0])
        if "store-late" not in self.alt:
            self.vars[k] = self.conv(k[1], start)          # stored before TO is looked for
        if len(parts) < 3 or parts[1] != "TO":
            raise Err(2)
        lim = self.expr(parts[2])
        if k[1] == "%" and "range-first" in self.alt and not isinstance(lim, str) and not -32768 <= lim <= 32767:
            raise Err(6)
        lim = self.conv(k[1], lim)
        step, stext, trail = Fr(1), "1", False
        if len(parts) >= 5 and parts[3] == "STEP":
            stext, comma, _ = parts[4].partition(",")
            trail = bool(comma)
            step = self.expr(stext)
            if isinstance(step, str):
                raise Err(13)
            if not (k[1] == "%" and "int-step-kept" in self.alt):
                step = self.conv(k[1], step, step=True)
        if "store-late" in self.alt:
            self.vars[k] = self.conv(k[1], start)
        if "replace-frame" in self.alt:
            for i, f in enumerate(self.frames):
                if f[0] == k:
                    del self.frames[i:]
                    break
        if trail and "comma-before-push" in self.alt:
            raise Err(2)
        self.frames.append([k, lim, step, pc + 1, (parts[2], stext), self.vars[k]])
        if trail:
            raise Err(2)                                   # after the push: the loop still runs
        v = self.vars[k]
        if "skip-past" in self.alt and ((step > 0 and v > lim) or (step < 0 and v < lim)):
            self.frames.pop()
            raise Skip

    def next_(self, rest):
        items = rest.split(",")
        if "list-first" in self.alt:
            for it in items[1:]:
                if it.strip() and not re.fullmatch(NAME, it.strip()):
                    raise Err(2)
        for it in items:
            it = it.strip()
            if it and not re.fullmatch(NAME, it):
                raise Err(2)
            if " " in it and "no-space-skip" in self.alt:
                raise Err(2)
            if not it:                                     # a bare NEXT (or an empty item after a comma)
                if not self.frames:
                    raise Err(1)
                i = len(self.frames) - 1
            else:
                k = self.key(it)
                if "next-no-create" not in self.alt:
                    self.vars.setdefault(k, Fr(0))
                i = max((j for j, f in enumerate(self.frames) if f[0] == k), default=None)
                if i is None:
                    if "next-fail-drops" in self.alt:
                        self.frames.clear()
                    raise Err(1)
            del self.frames[i + 1:]
            fr = self.frames[i]
            k, lim, step, body, (lt, st) = fr[:5]
            if "limit-live" in self.alt:
                lim = self.conv(k[1], self.expr(lt))
            if "step-live" in self.alt:
                step = self.conv(k[1], self.expr(st), step=True)
            cur = fr[5] if "private-copy" in self.alt else self.vars.get(k, Fr(0))
            new = cur + step if "sum-unrounded" in self.alt and k[1] != "%" else self.conv(k[1], cur + step)
            self.vars[k] = fr[5] = new
            if step > 0 or (step == 0 and "step0-past" in self.alt):
                go = new <= lim
            elif step < 0:
                go = new >= lim
            else:
                go = "step0-sign" not in self.alt or new != lim
            if go:
                return body
            self.frames.pop()
        return None

    def run(self, line):
        sts = line.split(":")
        pc = 0
        while pc < len(sts):
            s = sts[pc].strip()
            nxt = pc + 1
            try:
                if s.startswith("FOR"):
                    self.for_(s[3:], pc)
                elif s.startswith("NEXT"):
                    b = self.next_(s[4:])
                    if b is not None:
                        nxt = b
                elif s.startswith("WN%=WN%+1"):
                    self.wn += 1
                elif s.startswith("ON -(WN%>20)"):
                    if self.wn > GUARD:
                        return
                else:
                    lhs, rhs = s.split("=", 1)
                    k = self.key(lhs)
                    self.vars[k] = self.conv(k[1], self.expr(rhs))
            except Err as e:
                self.errs.append(e.n)
                if "failed-for-ends-line" in self.alt and s.startswith("FOR"):
                    return
            except Skip:                                   # the rival: on past the loop's NEXT
                nxt = next((j for j in range(pc + 1, len(sts)) if sts[j].strip().startswith("NEXT")), len(sts)) + 1
            pc = nxt


def run(c, alt=frozenset()):
    """(e, f, count, n, the loop variable as (type, value) / "none" / None) the interpreter gives for case c"""
    mc = Machine(alt)
    mc.run(c.stmt.replace("{g}", "ON -(WN%>20) GOTO R"))
    e = mc.errs
    v = None
    if c.var:
        k = mc.key(c.var)
        v = (k[1], mc.vars[k]) if k in mc.vars else "none"
    return (e[0] if e else 0), (e[-1] if e else 0), len(e), mc.wn, v


def got_v(c):
    if c.v is None or c.v == "none":
        return c.v
    t, b = c.v
    return t, ramrec.number(b)


def ok(c, alt=frozenset()):
    e, f, cnt, n, v = run(c, alt)
    return (c.e, c.f, c.c, c.n, got_v(c)) == (e, f, cnt, n, v)


def load(kw):
    out = kfor.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "FOR":
        s1, s2, s3 = "1. The loop", "2. An integer loop variable", "3. Errors"
        return [
            Rule("R-FOR-RUNS", s1, "FOR stores the start in the variable, and the body runs AT LEAST ONCE -- also when "
                 "the start is already past the limit. NEXT adds STEP (default 1) and runs the body again unless the "
                 "variable has passed the limit in STEP's direction, so a loop ends one step past the last value its "
                 "body saw (FOR I=1 TO 3: I 4; FOR I=3 TO 1: one run, I 4).",
                 by("three runs", "start = limit", "start past the limit", "a negative step",
                    "a negative step, start below", "a double variable, a large limit"), ok),
            Rule("R-FOR-FRACTION", s1, "STEP is converted to the variable's type at FOR and the sum is stored in that "
                 "type: STEP 1/3 is .333333 for a single (4 runs, ending at 1.33333) and fourteen digits for a double.",
                 by("a fractional step (double)", "a fractional step (single)", "a fractional step (double literal)",
                    "a step inexact in single (single)", "a step inexact in single (double)"), ok),
            Rule("R-FOR-STEP0", s1, "STEP 0 never ends -- with the start below, at or past the limit (the probe's guard "
                 "stops all three).",
                 by("STEP 0", "STEP 0, start past the limit", "STEP 0, start = limit"), ok),
            Rule("R-FOR-ONCE", s1, "The limit and STEP are evaluated once, at FOR: changing them in the body changes "
                 "nothing. The VARIABLE is the counter itself: I=5 in the body ends the loop after one run with I 6.",
                 by("the limit changed in the body", "the step changed in the body", "the variable changed in the body",
                    "the limit raised in the body"), ok),
            Rule("R-FOR-NEST", s1, "Loops nest, and a FOR pushes its frame ON TOP even when its variable already has "
                 "one: FOR I=1 TO 2:FOR I=1 TO 3 ... NEXT I:NEXT I runs 3 bodies and ends with no error (I 5); a FOR on "
                 "I above an open FOR J leaves J's frame alone. A FOR without NEXT is no error.",
                 by("nested, NEXT J,I", "nested, two bare NEXTs", "the same variable twice", "no NEXT",
                    "the same variable twice, two NEXT I", "FOR I again above FOR J"), ok),
            Rule("R-FOR-INT", s2, "An integer variable cuts the start, the limit and the STEP towards zero at FOR "
                 "(-1.6 is -1; STEP 1.5 is 1; STEP .5 and -.5 are 0 and never end).",
                 by("an integer variable", "an integer variable, a fractional start",
                    "an integer variable, a fractional limit", "an integer variable, STEP .5",
                    "an integer variable, a negative fractional start", "an integer variable, STEP 1.5",
                    "an integer variable, STEP -.5"), ok),
            Rule("R-FOR-OVERFLOW", s2, "A start, limit or STEP an integer variable cannot hold is error 6 (Overflow) at "
                 "the FOR, after the cut (32767.9 is 32767 and fits); stepping past 32767 or below -32768 is error 6 at "
                 "NEXT, the variable keeping its last value.",
                 by("an integer variable up to 32767", "an integer variable down to -32768",
                    "an integer variable, a limit past 32767", "an integer variable, a limit below -32768",
                    "an integer variable, a start past 32767", "an integer variable, a step past 32767",
                    "an integer variable, a limit of 32767.9"), ok),
            Rule("R-FOR-ERRORS", s3, "FOR works in order, and an error stops it where it stands: the variable is MADE "
                 "first (a number as the variable makes nothing; an array element is error 2), then `=` (error 2), "
                 "then the start is evaluated and STORED (its own error, or 13 for a string; a variable that existed "
                 "keeps its value), then TO (error 2), the limit (nothing: 24; a string: 13), STEP (nothing: 24). A "
                 "string variable is 13.",
                 by("a string variable", "a string limit", "a string step", "no TO", "nothing after TO", "no `=`",
                    "a number as the variable", "an array element as the variable", "STEP with nothing",
                    "the start's own error", "the limit's own error", "the step's own error", "a string start",
                    "the start's own error, I preset", "no `=`, I preset"), ok),
            Rule("R-FOR-NOFRAME", s3, "A FOR that stops on an error pushes NO frame: RESUME NEXT goes on with the "
                 "statement after it, so the body runs once and its NEXT is error 1. Text after STEP's value is the "
                 "one error that comes after the push: error 2, and the loop then runs.",
                 by("no TO, a body after it", "no `=`, a body after it", "nothing after TO, a body after it",
                    "a number as the variable, a body after it", "a comma after STEP's value"), ok),
        ]
    s1, s2 = "1. Closing loops", "2. Errors"
    return [
        Rule("R-NEXT-MATCH", s1, "NEXT I closes the innermost frame whose variable has the same name AND type, and "
             "drops every frame above it (NEXT I inside FOR J: J's frame is gone, a later NEXT J is error 1). A name "
             "skips spaces (`NEXT I J` is NEXT IJ); `NEXT A` does not match FOR A% or FOR AB.",
             by("NEXT I inside FOR J", "is J's frame dropped by NEXT I", "a space inside the name",
                "two names without a comma", "NEXT A after FOR A%", "NEXT A after FOR AB"), ok),
        Rule("R-NEXT-LIST", s1, "NEXT J,I steps J; only when J's loop ends does it read on to I. So a bad item later in "
             "the list -- a trailing comma (read as a bare NEXT), a number (error 2), a name with no frame (error 1) "
             "-- is met only once the loops before it have finished.",
             by("nested, NEXT J,I", "NEXT J,I: the outer variable", "a trailing comma", "a number after NEXT",
                "a third name past the frames", "a number later in the list", "NEXT J,K with K not open"), ok),
        Rule("R-NEXT-ERRORS", s2, "NEXT with no frame to close is error 1 (NEXT without FOR), and a miss leaves every "
             "frame where it was: after a failed NEXT J inside FOR I, a bare NEXT still steps I.",
             by("NEXT without FOR", "NEXT J inside FOR I", "does I's frame survive a failed NEXT J",
                "a bare NEXT without FOR: VARPTR(I) refuses"), ok),
        Rule("R-NEXT-CREATE", s2, "A NEXT that names a variable MAKES it, even when it then fails (NEXT I without FOR: "
             "I exists and reads 0; a failed NEXT J makes J) -- a bare NEXT makes nothing.",
             by("NEXT I without FOR", "a failed NEXT J: does it create J"), ok),
    ]
