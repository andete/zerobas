#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for GOTO / GOSUB / RETURN's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 5). The cases come from probes/basic/spec/kgosub.py's committed run
(scratchpad/KGS_run1.out, groups FX and FY). Each case's record -- the first and last error, WN% and WP% (the bits of
the lines it reached) -- is PREDICTED by running the case.

THE MODEL IS AN INTERPRETER (goldfish pass 1, 2026-11-25, scratchpad/REVIEW-m2-gkwgosub.md: the first model was a
per-case table). It runs the case's own lines -- statement by statement, RESUME NEXT going on after an error, an IF
whose test fails skipping the rest of its line -- with the laws the rules state:

  the line number     digits, spaces between them skipped (`GOTO 224 5` is GOTO 2245), read while the number stays
                      within 65529 (`GOTO 65530` is GOTO 6553: the rest is never read); anything after it is ignored;
                      no digit at all is error 2; a line that does not exist is 8.
  `GO TO`             one space: the tokenizer's synonym for GOTO, wherever it stands (`FOR I=GO TO 3` too).
  GOSUB n             the line is found FIRST (8: no frame), then a frame is pushed on the ONE stack FOR shares.
  RETURN [n]          no GOSUB frame: 3, before anything else is read; else the GOSUB frame and every FOR frame
                      above it are dropped, then -- with n -- the jump (8: the subroutine is already closed).
  NEXT                looks only at the FOR frames above the newest GOSUB frame.

A control (kgosub_controls.py) flips ONE of these laws (`alt`) and must be FALSE on some case."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kgosub  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "p"]
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = ("each case's first and last error, WN% (a counter; 21 = the probe's guard ended a loop that did not "
                "stop) and WP% (the bits of the lines the case reached)")
END = "R"


class Err(Exception):
    def __init__(self, n):
        self.n = n


class Jump(Exception):
    def __init__(self, to):
        self.to = to          # (line, statement index) or END


class Machine:
    def __init__(self, lines, alt):
        self.lines, self.alt = lines, alt
        self.order = sorted(k for k in lines if k != END)
        self.stack = []       # ("G", return point) / ("F", var, limit, step, body point)
        self.vars = {"WN%": 0, "WP%": 0}
        self.errs = []

    # -- pieces -------------------------------------------------------------------------------------------------
    def number(self, arg):
        """the line number at the start of arg (the laws above), or Err"""
        s = arg.lstrip()
        if not s[:1].isdigit():
            if s[:1] == "R" and s.strip() == "R":
                return END
            raise Err(2)
        v, i = 0, 0
        while i < len(s) and (s[i].isdigit() or (s[i] == " " and "no-join" not in self.alt)):
            if s[i] == " ":
                i += 1
                continue
            nv = v * 10 + int(s[i])
            if nv > 65529 and "big-undefined" not in self.alt:
                break
            v, i = nv, i + 1
        if "tail-syntax" in self.alt and s[i:].strip():
            raise Err(2)
        return v

    def target(self, n):
        if n == END:
            return END
        if n not in self.lines:
            raise Err(8)
        return (n, 0)

    def expr(self, s):
        s = s.strip()
        m = re.fullmatch(r"-?\((\w+%?)>(\d+)\)", s)
        if m:
            return -(-1 if self.vars.get(m.group(1), 0) > int(m.group(2)) else 0)
        m = re.fullmatch(r"(\w+%?)<(\d+)", s)
        if m:
            return -1 if self.vars.get(m.group(1), 0) < int(m.group(2)) else 0
        m = re.fullmatch(r"(\w+%?) OR (\d+)", s)
        if m:
            return self.vars.get(m.group(1), 0) | int(m.group(2))
        m = re.fullmatch(r"(\w+%?)\+(\d+)", s)
        if m:
            return self.vars.get(m.group(1), 0) + int(m.group(2))
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"[A-Z][A-Z0-9]*%?", s):
            return self.vars.get(s, 0)
        raise Err(2)

    # -- one statement ------------------------------------------------------------------------------------------
    def stmt(self, s, here):
        """run statement s at point `here` (line, index); returns the next point, END, or None (the next statement)"""
        s = s.strip()
        if s.startswith("IF "):
            m = re.match(r"IF (.+?)(?: THEN (.*)| (GOTO.*))$", s)
            if not m:
                raise Err(2)                             # neither THEN nor GOTO after the test
            if not self.expr(m.group(1)):
                return "NEXTLINE"
            return self.stmt(m.group(2) or m.group(3), here)
        if s.startswith("ON "):
            m = re.match(r"ON (.+) GOTO (.+)$", s)
            if not m:
                raise Err(2)
            if self.expr(m.group(1)) == 1:
                return self.target(self.number(m.group(2)))
            return None
        if s.startswith("GOTO"):
            to = self.target(self.number(s[4:]))
            if "goto-drops-gosub" in self.alt:
                while self.stack and self.stack[-1][0] == "G":
                    self.stack.pop()
            return to
        if s.startswith("GOSUB"):
            n = self.number(s[5:])
            if "gosub-frame-first" in self.alt:
                self.stack.append(("G", (here[0], here[1] + 1)))
            to = self.target(n)
            if "gosub-frame-first" not in self.alt:
                self.stack.append(("G", (here[0], here[1] + 1)))
            return to
        if s.startswith("RETURN"):
            arg = s[6:].strip()
            if arg and "return-line-first" in self.alt:
                self.target(self.number(arg))
            g = max((i for i, f in enumerate(self.stack) if f[0] == "G"), default=None)
            if g is None:
                raise Err(3)
            ret = self.stack[g][1]
            if arg and "return-missing-keeps" in self.alt:
                self.target(self.number(arg))
            if not (arg and "return-n-keeps-frame" in self.alt):
                if "return-keeps-for" in self.alt:
                    del self.stack[g]
                elif "return-unwinds-all" in self.alt:
                    self.stack.clear()
                else:
                    del self.stack[g:]
            if arg:
                return self.target(self.number(arg))
            return ret
        if s.startswith("FOR "):
            m = re.fullmatch(r"FOR (\w+)=(\S+) TO (\S+)", s)
            if not m:
                raise Err(2)
            self.vars[m.group(1)] = self.expr(m.group(2))
            self.stack.append(("F", m.group(1), self.expr(m.group(3)), 1, (here[0], here[1] + 1)))
            return None
        if s.startswith("NEXT"):
            name = s[4:].strip()
            top = max((i for i, f in enumerate(self.stack) if f[0] == "G"), default=-1)
            if "next-crosses-gosub" in self.alt:
                top = -1
            cand = [i for i, f in enumerate(self.stack) if i > top and f[0] == "F" and (not name or f[1] == name)]
            if not cand:
                raise Err(1)
            i = cand[-1]
            del self.stack[i + 1:]
            _, v, lim, step, body = self.stack[i]
            self.vars[v] += step
            if self.vars[v] <= lim:
                return body
            self.stack.pop()
            return None
        m = re.fullmatch(r"([A-Z][A-Z0-9]*%?)=(.+)", s)
        if m:
            self.vars[m.group(1)] = self.expr(m.group(2))
            return None
        raise Err(2)                                     # GO alone, `GO SUB`, `GO  TO`

    def run(self, start):
        pt, budget = (start, 0), 20000
        while pt != END and budget:
            budget -= 1
            line, i = pt
            sts = self.lines[line].split(":")
            if i >= len(sts):
                pt = self.fall(line)
                continue
            try:
                r = self.stmt(sts[i], pt)
            except Err as e:
                self.errs.append(e.n)
                r = None                                 # RESUME NEXT: the next statement
            if r is None:
                pt = (line, i + 1)
            elif r == "NEXTLINE":
                pt = self.fall(line)
            else:
                pt = r
        assert budget, "the model ran away"

    def fall(self, line):
        later = [k for k in self.order if k > line]
        return (later[0], 0) if later else END


def _program(c, alt):
    n = c.base
    m = {f"L{k}": n + k for k in (5, 10, 15, 20)}
    m["L5a"], m["L5b"], m["R"] = (n + 5) // 10, (n + 5) % 10, END
    fix = (lambda t: t) if "no-goto-space" in alt else (lambda t: re.sub(r"\bGO TO\b", "GOTO", t))
    lines = {n: fix(c.stmt.format(**m)) + ":GOTO R"}
    for k, t in c.subs.items():
        lines[int(k[1:]) if isinstance(k, str) else n + k] = fix(t.format(**m))
    lines[n + 25] = None                                 # the record line: reaching it ends the case
    return lines


def run(c, alt=frozenset()):
    lines = _program(c, alt)
    rec = c.base + 25
    body = {k: v for k, v in lines.items() if v is not None}
    mc = Machine(body, alt)
    mc.order = sorted(list(body) + [rec])
    mc.lines[rec] = "GOTO R"
    mc.run(c.base)
    e = mc.errs
    return (e[0] if e else 0), (e[-1] if e else 0), mc.vars["WN%"], mc.vars["WP%"]


def ok(c, alt=frozenset()):
    return (c.e, c.f, c.n, c.p) == run(c, alt)


def load(kw):
    out = kgosub.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "GOTO":
        s1, s2 = "1. The jump", "2. The line number"
        return [
            Rule("R-GOTO-JUMP", s1, "GOTO n continues at line n: the rest of its own line and every line in between "
                 "are skipped; a GOTO back to its own line loops; a GOTO inside a subroutine leaves the GOSUB pending, "
                 "so a RETURN on the line it reaches comes back after the GOSUB.",
                 by("a forward GOTO skips the rest of the line", "GOTO skips the lines between",
                    "a GOTO loop (the guard ends it)", "a GOTO inside a subroutine, RETURN from elsewhere"), ok),
            Rule("R-GOTO-GOTO", s1, "`GO TO` written with exactly ONE space is the tokenizer's synonym for GOTO, "
                 "wherever it stands: at a statement's start, after THEN, after IF without THEN, after ON -- and "
                 "inside an expression, so `FOR I=GO TO 3` is error 2. Two spaces, or `GO` alone, are error 2.",
                 by("GO TO with a space", "GO TO after THEN", "GO TO with two spaces", "GO alone",
                    "GO TO after IF without THEN", "ON 1 GO TO", "a variable GO before TO"), ok),
            Rule("R-GOTO-NUMBER", s2, "The line number is read digit by digit, spaces between digits skipped "
                 "(`GOTO 224 5` is GOTO 2245), and only while it stays within 65529: `GOTO 65530` is GOTO 6553, "
                 "`GOTO 70000` GOTO 7000, the rest never read. Anything after the number is ignored (`GOTO n ZZ` "
                 "jumps).",
                 by("something after the line number", "GOTO: digits joined across a space",
                    "GOTO: letters after the line number", "GOTO 65530 with a line 6553",
                    "GOTO 70000 with a line 7000", "a line number past 65529"), ok),
            Rule("R-GOTO-ERRORS", s2, "A line that does not exist is error 8 (Undefined line number); no digit where "
                 "the number belongs -- nothing, a variable, a minus sign, a string -- is error 2.",
                 by("a line that does not exist", "no line number", "a variable as the line", "a negative line",
                    "a string as the line"), ok),
        ]
    if kw == "GOSUB":
        s1, s2 = "1. The call", "2. Errors"
        return [
            Rule("R-GOSUB-CALL", s1, "GOSUB n runs line n on; RETURN continues after the GOSUB on its own line -- also "
                 "inside a THEN clause, whose rest then runs. GOSUBs nest and recurse, each RETURN closing one level "
                 "(three deep: three RETURNs); recursion without a RETURN runs on (the guard stopped it at 21 levels, "
                 "no error). A subroutine without RETURN simply runs on. The line number is read as GOTO's (digits "
                 "joined across a space; letters after it ignored).",
                 by("GOSUB / RETURN comes back after the GOSUB", "nested GOSUBs",
                    "recursion five deep, each level falling through to RETURN",
                    "a subroutine without RETURN (runs on into the record)", "unbounded recursion (the guard ends it)",
                    "recursion three deep, the returns counted", "GOSUB in a THEN clause comes back to it",
                    "GOSUB: digits joined across a space", "GOSUB: letters after the line number"), ok),
            Rule("R-GOSUB-ERRORS", s2, "A line that does not exist is error 8, and NO frame is pushed (a RETURN after "
                 "it is error 3); no line number is error 2; `GO SUB` with a space is error 2 (only GO TO has a "
                 "spelled-out form).",
                 by("a line that does not exist", "no line number", "GO SUB with a space",
                    "GOSUB to a missing line pushes no frame"), ok),
        ]
    s1, s2 = "1. Coming back", "2. Errors"
    return [
        Rule("R-RETURN-BACK", s1, "RETURN continues after its GOSUB; the rest of RETURN's own line is not run. RETURN n "
             "closes the subroutine and continues at line n (a second RETURN there is error 3). A GOSUB inside a FOR "
             "returns into the loop, which goes on; a whole FOR inside the subroutine runs before RETURN.",
             by("RETURN with a line number", "statements after RETURN", "GOSUB inside FOR",
                "a whole FOR inside the subroutine", "RETURN n closes the subroutine"), ok),
        Rule("R-RETURN-FRAMES", s1, "GOSUB and FOR share one stack. RETURN drops every FOR frame opened since its "
             "GOSUB, however many: a NEXT after it is error 1 (NEXT without FOR); and a NEXT inside a subroutine -- "
             "bare or named -- does not reach a FOR opened before the GOSUB (error 1).",
             by("RETURN from inside a FOR in the subroutine, then NEXT",
                "NEXT inside the subroutine for a FOR outside it", "RETURN drops every FOR opened in the subroutine",
                "NEXT I in the subroutine for a FOR outside it"), ok),
        Rule("R-RETURN-ERRORS", s2, "RETURN with no GOSUB pending is error 3 (RETURN without GOSUB), checked BEFORE "
             "anything after it is read (`RETURN 65000`, `RETURN WK` with nothing open: 3) -- also a second RETURN "
             "once the GOSUB came back. RETURN n to a line that does not exist is error 8 with the subroutine already "
             "closed (a RETURN after it is 3); RETURN and a string is error 2.",
             by("RETURN without GOSUB", "a second RETURN once the GOSUB came back",
                "RETURN to a line that does not exist", "RETURN n to a missing line closes the subroutine first",
                "RETURN n with nothing open", "RETURN and a variable with nothing open", "RETURN and a string"), ok),
    ]
