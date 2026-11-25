#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for IF's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md region 5).
The cases come from probes/basic/spec/kif.py's committed run (scratchpad/KIF_run1.out, groups FX and FY).

THE MODEL IS AN INTERPRETER (goldfish pass 1, 2026-11-25, scratchpad/REVIEW-m2-gkwif.md: the first model was a
per-case table). It runs each case's line character by character -- statements end at `:` or at ELSE -- with the laws
the rules state:

  truth        a number is true unless it is zero (a zero EXPONENT byte is zero, whatever the digits); a string is
               error 13; a comparison is a number.
  true IF      THEN's part runs -- a line number is a jump -- and so does the rest of the line, until an ELSE is
               reached AS A STATEMENT: that ends the line. `IF c GOTO` with no line number after it is THEN.
  false IF     the rest of the line is scanned for the ELSE that matches: every IF on the way opens a level, every ELSE
               closes one (constants are numbers, not tokens); no match skips the whole line.
  an error     RESUME NEXT goes on at the next statement boundary after the error -- a `:` OR an ELSE.

A control (kif_controls.py) flips ONE of these laws (`alt`) and must be FALSE on some case."""
import os
import re
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kif  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "p"]
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = "each case's first and last error, WN% (a counter) and WP% (the bits of the parts of the line that ran)"
END = "R"


class Err(Exception):
    def __init__(self, n, at):
        self.n, self.at = n, at


class Machine:
    def __init__(self, lines, alt):
        self.lines, self.alt = lines, alt
        self.vars = {"WN%": 0, "WP%": 0}
        self.zero_exp = set()
        self.frames = []
        self.errs = []

    # -- text ---------------------------------------------------------------------------------------------------
    @staticmethod
    def word(L, i, w):
        return L.startswith(w, i) and (i == 0 or not L[i - 1].isalnum()) and not L[i + len(w):i + len(w) + 1].isalnum()

    def boundary(self, L, i):
        """the next statement boundary at or after i: a `:` or an ELSE (outside strings); len(L) at the end"""
        q = False
        while i < len(L):
            if L[i] == '"':
                q = not q
            elif not q and (L[i] == ":" or (self.word(L, i, "ELSE") and "resume-colon-only" not in self.alt)):
                return i
            i += 1
        return len(L)

    def stmt_end(self, L, i):
        q = False
        while i < len(L):
            if L[i] == '"':
                q = not q
            elif not q and (L[i] == ":" or self.word(L, i, "ELSE")):
                return i
            i += 1
        return len(L)

    def match_else(self, L, i):
        """the ELSE that matches an IF whose part starts at i, or None"""
        depth, q = 0, False
        while i < len(L):
            if L[i] == '"':
                q = not q
            elif not q:
                num = re.match(r"\d+", L[i:]) if not L[i - 1:i].isalnum() else None
                byte = "byte-scan" in self.alt and num and num.group(0) in ("139", "161")
                if self.word(L, i, "IF") or (byte and num.group(0) == "139"):
                    if "nest-after-then-only" not in self.alt or re.search(r"(THEN|ELSE)\s*$", L[:i]):
                        depth += 1
                elif self.word(L, i, "ELSE") or (byte and num.group(0) == "161"):
                    if depth == 0:
                        return i
                    depth -= 1
            i += 1
        return None

    # -- values -------------------------------------------------------------------------------------------------
    def expr(self, s, at):
        s = s.strip()
        if s == "":
            raise Err(2, at)
        m = re.fullmatch(r'(.+?)(<|=)(.+)', s)
        if m and not s.startswith('"') or (m and s.count('"') in (2, 4) and m.group(1).strip().endswith('"')):
            a, b = self.expr(m.group(1), at), self.expr(m.group(3), at)
            if isinstance(a, str) != isinstance(b, str):
                raise Err(13, at)
            if isinstance(a, str) and "string-compare-true" in self.alt:
                return Fr(-1)
            return Fr(-1) if (a < b if m.group(2) == "<" else a == b) else Fr(0)
        if "/" in s:
            a, b = (self.expr(x, at) for x in s.split("/"))
            if b == 0:
                raise Err(11, at)
            return a / b
        if s.startswith('"'):
            return s.strip('"')
        if re.fullmatch(r"[A-Z][A-Z0-9]*[%$]?", s):
            if s in self.zero_exp:
                return Fr(1) if "any-byte" in self.alt else Fr(0)
            return self.vars.get(s, "" if s.endswith("$") else Fr(0))
        return Fr(s.rstrip("#!"))

    def number(self, L, i):
        m = re.match(r"\d+", L[i:])
        return int(m.group(0))

    def jump(self, n, at):
        if n not in self.lines:
            raise Err(8, at)
        return (n, 0)

    # -- running ------------------------------------------------------------------------------------------------
    def run(self, start):
        pt, budget = (start, 0), 5000
        while pt != END and budget:
            budget -= 1
            pt = self.line(*pt)
        assert budget, "the model ran away"

    def fall(self, n):
        later = sorted(k for k in self.lines if k > n)
        return (later[0], 0) if later else END

    def line(self, n, i):
        L = self.lines[n]
        while True:
            while i < len(L) and L[i] == " ":
                i += 1
            if i >= len(L):
                return self.fall(n)
            if L[i] == ":":
                i += 1
                continue
            if self.word(L, i, "ELSE"):                     # an ELSE reached as a statement ends the line
                if "else-as-stmt-runs" in self.alt:
                    i += 4
                    continue
                return self.fall(n)
            try:
                r = self.stmt(n, L, i)
            except Err as e:
                self.errs.append(e.n)
                r = ("at", self.boundary(L, e.at))         # RESUME NEXT
            if r[0] == "at":
                i = r[1]
            elif r[0] == "fall":
                return self.fall(n)
            else:
                return r[1]

    def stmt(self, n, L, i):
        """one statement at L[i]; ("at", j) goes on at j, ("fall",) to the next line, ("go", point) jumps"""
        if self.word(L, i, "IF"):
            k = [(m.start(), m.group(1)) for m in re.finditer(r" (THEN|GOTO)\b", L[i:])]
            if not k:
                raise Err(2, i + 2)
            off, kind = k[0]
            after = i + off + 1 + len(kind)
            try:
                cond = self.expr(L[i + 2:i + off], i + 2)
                if isinstance(cond, str):
                    raise Err(13, i + 2)
            except Err as e:
                if "error-counts-false" not in self.alt:
                    raise
                self.errs.append(e.n)
                cond = 0
            if "fraction-false" in self.alt and cond != 0 and abs(cond) < 1:
                cond = 0
            q = after
            while q < len(L) and L[q] == " ":
                q += 1
            if "empty-then-syntax" in self.alt and (q >= len(L) or L[q] == ":"):
                raise Err(2, q)
            if "missing-line-always-8" in self.alt and L[q:q + 1].isdigit() and self.number(L, q) not in self.lines:
                raise Err(8, q)
            p = after
            while p < len(L) and L[p] == " ":
                p += 1
            if cond != 0:
                if L[p:p + 1].isdigit():
                    return ("go", self.jump(self.number(L, p), p))
                if kind == "GOTO" and "goto-needs-number" in self.alt:
                    raise Err(2, p)
                return ("at", p)
            if "false-skips-then-only" in self.alt:
                return ("at", self.stmt_end(L, after))
            e = self.match_else(L, after)
            if e is None:
                return ("fall",)
            p = e + 4
            while p < len(L) and L[p] == " ":
                p += 1
            if L[p:p + 1].isdigit():
                return ("go", self.jump(self.number(L, p), p))
            return ("at", p)
        j = self.stmt_end(L, i)
        s = L[i:j].strip()
        if s.startswith("GOTO"):
            t = s[4:].strip()
            if t == "R":
                return ("go", END)
            if not t[:1].isdigit():
                raise Err(2, i)
            return ("go", self.jump(int(t), i))
        if s.startswith("FOR "):
            m = re.fullmatch(r"FOR (\w+)=(\S+) TO (\S+)", s)
            self.vars[m.group(1)] = self.expr(m.group(2), i)
            self.frames.append((m.group(1), self.expr(m.group(3), i), (n, j)))
            return ("at", j)
        if s == "NEXT":
            if not self.frames:
                raise Err(1, i)
            v, lim, body = self.frames[-1]
            self.vars[v] += 1
            if self.vars[v] <= lim:
                return ("go", body)
            self.frames.pop()
            return ("at", j)
        m = re.fullmatch(r"POKE VARPTR\((\w+)\),0", s)
        if m:
            self.zero_exp.add(m.group(1))
            return ("at", j)
        m = re.fullmatch(r"([A-Z][A-Z0-9]*[%$]?)=(.+)", s)
        if m:
            name, rhs = m.groups()
            o = re.fullmatch(r"(\w+%?) OR (\d+)", rhs)
            if o:
                self.vars[name] = int(self.vars.get(o.group(1), 0)) | int(o.group(2))
            elif re.fullmatch(r"WN%\+1", rhs):
                self.vars[name] = self.vars.get(name, 0) + 1
            else:
                self.vars[name] = self.expr(rhs, i)
            self.zero_exp.discard(name)
            return ("at", j)
        raise Err(2, i)


def _program(c):
    n = c.base
    m = {f"L{k}": n + k for k in (5, 10, 15, 20)}
    m.update(R=END, L0=n, g="")
    lines = {n: c.stmt.format(**m) + ("" if "noend" in c.subs else ":GOTO R"), n + 1: "GOTO R"}
    for k, t in c.subs.items():
        if k != "noend":
            lines[n + k] = t.format(**m)
    return lines


def run(c, alt=frozenset()):
    mc = Machine(_program(c), alt)
    mc.run(c.base)
    e = mc.errs
    return (e[0] if e else 0), (e[-1] if e else 0), int(mc.vars["WN%"]), int(mc.vars["WP%"])


def ok(c, alt=frozenset()):
    return (c.e, c.f, c.n, c.p) == run(c, alt)


def load(kw):
    out = kif.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    s1, s2, s3 = "1. Truth", "2. THEN, ELSE and the rest of the line", "3. Errors"
    return [
        Rule("R-IF-TRUTH", s1, "A number is true unless it is zero -- -1, .5, -.5, 1E-30, a double are true; 0, an "
             "integer 0 and a variable holding 0 are false, and so is a number whose EXPONENT byte is zero whatever "
             "its digits (POKEd). A comparison is a number like any other (\"A\"<\"B\" true, \"B\"<\"A\" false).",
             by("-1 is true", "a fraction is true", "a tiny number is true", "a variable holding 0 is false",
                "a string comparison", "a false string comparison", "a zero exponent byte, the digits not zero",
                "an integer 0", "a double", "a negative fraction"), ok),
        Rule("R-IF-LINE", s2, "A true IF runs THEN's statements AND the rest of the line (a NEXT behind it included); a "
             "false IF skips the WHOLE rest of the line -- every statement after it, a GOTO and a NEXT included (a loop "
             "on one line ends there).",
             by("a true IF runs THEN and the rest of the line", "a false IF skips THEN and the rest of the line",
                "IF ... GOTO, false (the rest of the line too)", "a false IF skips the NEXT behind it",
                "NEXT after a true IF on the same line", "a NEXT behind a true IF"), ok),
        Rule("R-IF-JUMP", s2, "THEN n, ELSE n and IF ... GOTO n jump to line n when taken (also back to the IF's own "
             "line); a missing line is error 8 only when the jump is taken. `IF c GOTO` with no line number after it "
             "is THEN: what follows runs as a statement (nothing at all is no error).",
             by("THEN a line number", "THEN a line number, false", "IF ... GOTO", "THEN back to its own line",
                "THEN a line that does not exist", "THEN a missing line, false", "ELSE to a missing line, not taken",
                "IF ... GOTO a missing line", "IF ... GOTO a missing line, false", "ELSE to a missing line, taken",
                "THEN n ELSE m, false", "THEN n ELSE statements, true", "IF ... GOTO ... ELSE, false",
                "IF ... GOTO a statement", "IF ... GOTO with no number"), ok),
        Rule("R-IF-ELSE", s2, "ELSE runs when the IF is false -- its statements and the rest of the line after them, or "
             "a jump to ELSE n. When the IF is true, the first ELSE reached ends the line. A false IF finds its ELSE by "
             "counting: every IF further on opens a level -- after a colon or inside ELSE's part too -- and every ELSE "
             "closes one; a constant is never taken for a token (`WK=139`, `WK=161`).",
             by("ELSE, true", "ELSE, false", "ELSE a line number", "statements after ELSE's own",
                "statements after ELSE, true", "ELSE after a nested IF (true, false)",
                "ELSE after a nested IF (false outside)", "two ELSEs: the second belongs to the outer IF",
                "two ELSEs, both true", "two ELSEs: outer true, inner false", "an IF after a colon in THEN's part",
                "an IF inside ELSE's part", "a constant whose byte is IF's token",
                "a constant whose byte is ELSE's token"), ok),
        Rule("R-IF-EMPTY", s2, "THEN or ELSE followed by nothing, or by a colon, is no error -- true or false.",
             by("THEN followed by nothing", "THEN followed by a colon", "THEN at the end of the line",
                "a false IF, THEN followed by a colon", "ELSE at the end of the line"), ok),
        Rule("R-IF-ERRORS", s3, "A string as the condition is error 13 (Type mismatch), and so is a comparison of a "
             "string with a number; no THEN, no condition, junk after ELSE or a string after GOTO is error 2; the "
             "condition's own error is that error (1/0: 11). RESUME NEXT then goes on at the next `:` OR ELSE after "
             "the error -- and an ELSE reached that way ends the line, so neither part runs.",
             by("a string as the condition", "no THEN", "no condition", "the condition's own error",
                "the condition's error, then ELSE", "a mixed comparison, then ELSE",
                "a string literal as the condition", "IF ... GOTO a string", "ELSE followed by junk",
                "no condition, a line number"), ok),
    ]
