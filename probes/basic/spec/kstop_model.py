#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for END / STOP / CONT / RUN's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 5). The cases come from probes/basic/spec/kstop.py's committed run
(scratchpad/KSP_run1.out, groups FX and FY): each case's normalised SCREEN.

THE MODEL IS AN INTERPRETER (goldfish pass 1, 2026-11-25, scratchpad/REVIEW-m2-gkwstop.md: the first model was a table
of expected responses, and it dropped the prompts and the echo, so a hang read as "does nothing"). It types the case
into a small BASIC -- program lines stored, direct statements run -- and predicts the WHOLE screen: the prompt after
every direct command, the echo of every typed line (wrapped at 37), the program's output and the messages. The laws:

  END       stops; files are CLOSED, an error handler is finished; CONT goes on after it (a pending GOSUB kept).
  STOP      `Break in n`, n the STOP's own line (`Break` typed); an error handler stays active; CONT goes on after it.
  CONT      goes on at the resume point; none (`Can't CONTINUE`) after NEW, CLEAR, RUN -- dropped BEFORE RUN looks for
            its line -- or a successful program edit; a direct statement, a typed STOP / END / error, or a failed delete
            leaves it. After an error, CONT runs the failing statement again; after the program ran off its end, CONT
            does nothing. The rest of CONT's own line is never run.
  RUN       clears first -- variables, arrays, strings, the DATA pointer, ON ERROR, the resume point, open files --
            then starts at the first line or at n (also inside a program); `RUN A+0` is Type mismatch.
  an edit   (a program line typed) clears the variables and the resume point.

A control (kstop_controls.py) flips ONE of these laws (`alt`) and must be FALSE on some case."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kstop  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["scr"]
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = "each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)"
MSG = {1: "NEXT without FOR", 2: "Syntax error", 3: "RETURN without GOSUB", 4: "Out of DATA",
       5: "Illegal function call", 6: "Overflow", 7: "Out of memory", 8: "Undefined line number",
       9: "Subscript out of range", 10: "Redimensioned array", 11: "Division by zero", 12: "Illegal direct",
       13: "Type mismatch", 14: "Out of string space", 15: "String too long", 16: "String formula too complex",
       17: "Can't CONTINUE", 18: "Undefined user function", 19: "Device I/O error", 20: "Verify error",
       21: "No RESUME", 22: "RESUME without error", 24: "Missing operand", 25: "Line buffer overflow",
       50: "FIELD overflow", 51: "Internal error", 52: "Bad file number", 53: "File not found",
       54: "File already open", 55: "Input past end", 56: "Bad file name", 57: "Direct statement in file",
       58: "Sequential I/O only", 59: "File not OPEN"}


def msg(n):
    """the message of error n; a code with no message of its own is `Unprintable error`"""
    return MSG.get(n, "Unprintable error")
WIDTH = 37


class Err(Exception):
    def __init__(self, n):
        self.n = n


class Stop(Exception):
    pass


class Hang(Exception):
    """the program never comes back to the prompt (the model's step budget ran out)"""


def split(text, alt=frozenset()):
    """a line's statements; a REM -- or an apostrophe, which needs no colon before it -- takes the REST of the line,
    colons and all, as one statement"""
    out, cur, q = [], "", False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            q = not q
        if (not q or "apostrophe-in-string" in alt) and ch == "'" and "apostrophe-needs-colon" not in alt:
            if cur.strip():
                out.append(cur.strip())
            return out + ["REM" + text[i + 1:]]
        if not q and not cur.strip() and text.startswith("REM", i) and "rem-keeps-colon" not in alt:
            return out + [text[i:]]
        if ch == ":" and not q:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    return out + [cur.strip()]


class Basic:
    def __init__(self, alt):
        self.alt = alt
        self.prog = {}
        self.vram = {}
        self.screen = ["<prompt>"]
        self.cur = ""
        self.cont = None              # None: nothing to continue; "END": ran off the end; (line, index)
        self.files = set()
        self.err, self.erl = 0, 0     # ERR / ERL: 0 before any error; ERL 65535 for an error typed at the prompt
        self.direct = []              # the statements of the line being typed: points ("D", i)
        self.last = None              # the last program line that ran
        self.disarmed = False
        self.trace = False            # TRON
        self.reset()

    def reset(self):
        if "reset-clears-err" in self.alt:
            self.err, self.erl = 0, 0
        self.vars, self.arrays = {}, set()
        self.data = None
        self.onerr = None
        self.handler = None           # the failing point while an error handler runs
        self.stack = []

    # -- the screen ---------------------------------------------------------------------------------------------
    def out(self, s):
        self.cur += s

    def newline(self):
        if self.cur.strip():
            self.screen.append(self.cur.strip())
        self.cur = ""

    def message(self, s):
        self.newline()
        self.screen.append(s)

    # -- values -------------------------------------------------------------------------------------------------
    def value(self, s):
        s = s.strip()
        if s.startswith('"'):
            return s.strip('"')
        m = re.fullmatch(r"VPEEK\((\d+)\)", s)
        if m:
            return self.vram.get(int(m.group(1)), 0)
        m = re.fullmatch(r"(\w+)\+(\d+)", s)
        if m:
            a = self.value(m.group(1))
            if isinstance(a, str):
                raise Err(13)
            return a + int(m.group(2))
        m = re.fullmatch(r"(\w+)/(\w+)", s)
        if m:
            a, b = self.value(m.group(1)), self.value(m.group(2))
            if b == 0:
                raise Err(11)
            return a / b
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"-?\d*\.\d+", s):
            return float(s)
        if s == "ERR" or (s == "ERR 1" and "err-tail-ok" in self.alt):
            return self.err
        if s == "ERL":
            return self.erl
        if re.fullmatch(r"[A-Z]\w*\$", s):
            return self.vars.get(s, "")
        if re.fullmatch(r"[A-Z]\w*", s):
            return self.vars.get(s, 0)
        raise Err(2)                                     # a form this BASIC does not read (`ERR 1`)

    @staticmethod
    def fmt(v):
        if isinstance(v, str):
            return v
        v = int(v) if float(v).is_integer() else v
        return (" " if v >= 0 else "") + str(v) + " "

    # -- running ------------------------------------------------------------------------------------------------
    def lines(self):
        return sorted(self.prog)

    def first(self, n=None):
        ls = self.lines()
        if n is None:
            return (ls[0], 0) if ls else None
        if n not in self.prog:
            raise Err(8)
        return (n, 0)

    def fetch(self, pt):
        line, i = pt
        if line == "D":
            return self.direct[i] if i < len(self.direct) else None
        return split(self.prog[line], self.alt)[i]

    def next_point(self, pt):
        line, i = pt
        if line == "D":                                  # a statement typed at the prompt
            return ("D", i + 1)
        if i + 1 < len(split(self.prog[line], self.alt)):
            return (line, i + 1)
        later = [k for k in self.lines() if k > line]
        return (later[0], 0) if later else "END"

    def run_from(self, pt, budget=400):
        """run the program from pt until it stops; returns when it does"""
        while pt != "END" and budget:
            budget -= 1
            line, i = pt
            st = self.fetch(pt)
            if st is None:                               # the end of a typed line
                return
            if line != "D":
                self.last = line
                entered = (i == 0 or "trace-per-statement" in self.alt
                           or ("trace-on-return" in self.alt and getattr(self, "_from", None) != line))
                if entered and self.trace:
                    if "trace-newline" in self.alt:
                        self.newline()
                    self.out(f"[{line}]")                # a line entered from its top: traced, no new line
            elif self.trace and "trace-typed" in self.alt and i == 0:
                self.out("[65535]")
            try:
                to = self.stmt(st, pt)
            except Err as e:
                self.err, self.erl = e.n, (65535 if line == "D" else line)
                if line == "D" and "typed-erl-zero" in self.alt:
                    self.erl = 0
                trap = not st.startswith("RESUME") or "resume-error-trapped" in self.alt  # a RESUME's own error
                if e.n == 22 and "code22-untrapped" in self.alt:
                    trap = False
                if "end-disarms-handler" in self.alt and self.disarmed:
                    trap = False
                if line == "D" and "typed-errors-untrapped" in self.alt:
                    trap = False
                if self.handler is not None and "handler-traps-own" in self.alt and self.onerr is not None:
                    pt = (self.onerr, 0)
                    continue
                if self.onerr is not None and self.handler is None and trap:
                    self.handler = pt
                    self.depth = len(self.stack)
                    pt = (self.onerr, 0)
                    continue
                if line == "D":
                    self.message(msg(e.n))
                    if "direct-error-drops-cont" in self.alt:
                        self.cont = None
                    return
                self.message(f"{msg(e.n)} in {line}")
                if "untrapped-keeps-handler" not in self.alt:
                    self.handler = None                  # an untrapped stop finishes the handler too
                self.cont = pt                           # CONT runs the failing statement again
                if "cont-after-error-cant" in self.alt:
                    self.cont = None
                if "cont-after-error-reprint" in self.alt:
                    self.cont = ("REPRINT", e.n, line)
                return
            except Stop:
                return
            if line == "D" and "direct-blocks-cont" in self.alt and not st.startswith("CONT"):
                self.cont = None
            self._from = line
            pt = self.next_point(pt) if to is None else to
        if not budget:
            raise Hang
        if pt == "END" and self.handler is not None:     # a handler ran off the end of the program
            self.err, self.erl = 21, self.last
            self.message(f"{msg(21)} in {self.last}")
            if "untrapped-keeps-handler" not in self.alt:
                self.handler = None
            return
        if pt == "END":
            self.newline()
            self.cont = "END" if "run-end-cant" not in self.alt else None
            if "run-end-clears" in self.alt:
                self.vars = {}

    def stmt(self, s, pt):
        """one statement; pt is its point ("D" in direct mode). Returns None (go on) or the next point"""
        direct = pt[0] == "D"
        if s.startswith("PRINT #"):
            m = re.fullmatch(r"PRINT #(\d+),(.+)", s)
            if int(m.group(1)) not in self.files:
                raise Err(59)
            self.out(self.value(m.group(2)))
            self.newline()
            return None
        if s in ("TRON", "TROFF"):
            self.trace = s == "TRON"
            if s == "TRON" and "tron-line-traced" in self.alt and pt[0] != "D":
                self.out(f"[{pt[0]}]")                   # (the rival: the TRON line traced as well)
            if s == "TROFF" and "troff-line-untraced" in self.alt and pt[0] != "D":
                self.cur = self.cur.replace(f"[{pt[0]}]", "")
            return None
        if s.startswith("TRON") or s.startswith("TROFF"):
            raise Err(2)                                 # anything after them
        if s.startswith("PRINT"):
            # PRINT's items: a string literal, or an expression up to the next `;`, `,` or `"`; `;` and juxtaposition
            # join, `,` moves to the next 14-column zone; a trailing `;` or `,` keeps the line open. A keyword where an
            # item belongs (`PRINT "A" REM X`) is error 2 -- after the items before it were printed.
            body, i, last = s[5:], 0, ""
            while True:
                while i < len(body) and body[i] == " ":
                    i += 1
                if i >= len(body):
                    break
                ch = body[i]
                if ch == ";":
                    i, last = i + 1, ";"
                    continue
                if ch == ",":
                    self.out(" " * (14 - len(self.cur) % 14))
                    i, last = i + 1, ","
                    continue
                if body.startswith("REM", i) or body.startswith("ELSE", i):
                    if "rem-after-stmt-ok" in self.alt and body.startswith("REM", i):
                        break
                    raise Err(2)
                if ch == '"':
                    j = body.find('"', i + 1)
                    j = len(body) if j < 0 else j
                    self.out(body[i + 1:j])
                    i = j + 1
                else:
                    m = re.match(r'[^;,"]+', body[i:])
                    item = m.group(0).rstrip()
                    for kw in (" REM", " ELSE"):
                        if kw in item:
                            item = item[:item.index(kw)]
                    self.out(self.fmt(self.value(item)))
                    i += len(item)
                last = ""
            if last not in (";", ","):
                self.newline()
            return None
        if s == "END":
            if direct:
                return None
            self.newline()
            if "end-keeps-files" not in self.alt:
                self.files.clear()
            self.disarmed = self.handler is not None     # (the rival law: END in a handler disarms ON ERROR)
            self.handler = None
            self.cont = self.next_point(pt)
            if "cont-after-end-cant" in self.alt:
                self.cont = None
            if "cont-after-end-next-line" in self.alt and self.cont != "END" and self.cont[0] == pt[0]:
                later = [k for k in self.lines() if k > pt[0]]
                self.cont = (later[0], 0) if later else "END"
            if "end-drops-gosub" in self.alt:
                self.stack = [f for f in self.stack if f[0] != "G"]
            raise Stop
        if s == "STOP":
            if direct:
                if "stop-direct-silent" not in self.alt:
                    self.message("Break")
                return None
            line = self.lines()[0] if "break-first-line" in self.alt else pt[0]
            self.message(f"Break in {line}")
            self.cont = self.next_point(pt) if "cont-from-stmt-start" not in self.alt else pt
            if "stop-ends-handler" in self.alt:
                self.handler = None
            raise Stop
        if s.startswith("CONT"):
            if self.cont is None:
                raise Err(17)
            if self.cont == "END":
                raise Stop
            if self.cont[0] == "REPRINT":
                self.message(f"{msg(self.cont[1])} in {self.cont[2]}")
                raise Stop
            pt2, self.cont = self.cont, None
            self.run_from(pt2)
            raise Stop                                   # the rest of CONT's line is never run
        if s.startswith("RUN"):
            arg = s[3:].strip()
            if "run-drops-cont-late" not in self.alt:
                self.cont = None
            if arg and not arg.isdigit():
                v = self.value(arg)
                if not isinstance(v, str):
                    raise Err(13)
            if "run-n-goto" in self.alt and arg and not direct:
                return self.first(int(arg))
            start = self.first(int(arg) if arg else None)
            if "run-keeps-vars" not in self.alt:
                keep_data, keep_err = self.data, self.onerr
                self.reset()
                if "run-keeps-data" in self.alt:
                    self.data = keep_data
                if "run-keeps-onerror" in self.alt:
                    self.onerr = keep_err
            if "run-keeps-files" not in self.alt:
                self.files.clear()
            self.cont = None
            if start is None:
                raise Stop
            self.run_from(start)
            raise Stop
        if s.startswith("GOTO"):
            m = re.match(r"\s*(\d+)", s[4:])               # the digits; anything after them is never read
            if not m:
                raise Err(2)
            return self.first(int(m.group(1)))
        m = re.fullmatch(r"ON (\S+) GOTO ([\d,]+)", s) if not s.startswith("ON ERROR") else None
        if m:
            k = int(self.value(m.group(1)))
            targets = m.group(2).split(",")
            return self.first(int(targets[k - 1])) if 1 <= k <= len(targets) else None
        if s.startswith("GOSUB"):
            self.stack.append(("G", self.next_point(pt)))
            return self.first(int(s[5:]))
        if s == "RETURN":
            g = [i for i, f in enumerate(self.stack) if f[0] == "G"]
            if not g:
                raise Err(3)
            ret = self.stack[g[-1]][1]
            del self.stack[g[-1]:]
            return ret
        if s.startswith("FOR "):
            m = re.fullmatch(r"FOR (\w+)=(\d+) TO (\d+)", s)
            self.vars[m.group(1)] = int(m.group(2))
            self.stack.append(("F", m.group(1), int(m.group(3)), self.next_point(pt)))
            return None
        if s == "NEXT":
            f = [i for i, x in enumerate(self.stack) if x[0] == "F"]
            if not f:
                raise Err(1)
            _, v, lim, body = self.stack[f[-1]]
            self.vars[v] += 1
            if self.vars[v] <= lim:
                return body
            self.stack.pop(f[-1])
            return None
        if s.startswith("ON ERROR GOTO"):
            arg = s[13:].strip()
            if arg and not arg.isdigit() and "onerr-var-syntax" in self.alt:
                raise Err(2)
            n = int(arg) if arg.isdigit() else 0         # no number (nothing, a variable) is GOTO 0 -- acted on FIRST
            if n == 0:
                self.onerr = None
                if self.handler is not None and "onerr0-just-disarms" not in self.alt:
                    self.cont = self.handler             # CONT runs the failing statement again, as after any error
                    self.handler = None
                    self.message(f"{msg(self.err)} in {self.erl}" if self.erl != 65535 else msg(self.err))
                    raise Stop
                if arg and not arg.isdigit():
                    raise Err(2)                         # ...and only then the rest: the trap is already off
                return None
            if n not in self.prog and "onerr-missing-late" not in self.alt:
                raise Err(8)
            self.onerr = n
            return None
        if s.startswith("RESUME"):
            if self.handler is None:
                raise Err(22)
            arg = s[6:].strip()
            if arg in ("", "0"):
                to = self.handler                        # the failing statement again
            elif arg == "NEXT":
                to = self.next_point(self.handler)
                if "resume-next-next-line" in self.alt:
                    to = self.next_line(self.handler)
            else:
                if not arg.isdigit():
                    raise Err(2)                         # `RESUME A`: in the active handler, so untrapped
                if "resume-missing-silent" in self.alt and int(arg) not in self.prog:
                    raise Stop
                to = self.first(int(arg))                # a missing line: 8, the handler still active
            self.handler = None
            if "resume-drops-frames" in self.alt:
                del self.stack[getattr(self, "depth", 0):]
            if "resume-keeps-err" not in self.alt:
                self.err = 0
            return to
        if s.startswith("ERROR"):
            arg = s[5:].strip()
            if not arg:
                raise Err(24)
            code, comma, _ = arg.partition(",")
            if comma and "error-comma-first" in self.alt:
                raise Err(2)
            v = self.value(code)
            if isinstance(v, str):
                raise Err(13)
            v = round(v) if "error-code-rounds" in self.alt else int(v)
            if not -32768 <= v <= (65535 if "error-bound-65535" in self.alt else 32767):
                raise Err(6)
            if not 1 <= v <= 255:
                raise Err(5)
            if comma:
                raise Err(2)                             # the code is refused before anything after it is looked at
            raise Err(v)
        if s.startswith("DIM "):
            name = s[4:].split("(")[0]
            if name in self.arrays:
                raise Err(10)
            self.arrays.add(name)
            return None
        if s.startswith("READ "):
            if self.data is None:
                self.data = [x.strip() for k in self.lines() for st in split(self.prog[k]) if st.startswith("DATA ")
                             for x in st[5:].split(",")]
            name = s[5:].strip()
            item = self.data.pop(0)
            if "data-stops-at-rem" in self.alt:
                item = item.split(" REM")[0]
            self.vars[name] = item if name.endswith("$") else int(item)
            return None
        if s.startswith("DATA") or s.startswith("REM"):
            if s.startswith("DATA") or "rem-keeps-colon" in self.alt:
                return None
            return self.next_line(pt)
        if s.startswith("VPOKE "):
            a, v = s[6:].split(",")
            self.vram[int(a)] = self.value(v)
            return None
        if s.startswith("IF "):
            m = re.fullmatch(r"IF (\w+)(?:=(\d+))? THEN ?(.*)", s)
            v = self.value(m.group(1))
            true = (v == int(m.group(2))) if m.group(2) else v != 0
            then, _, other = m.group(3).partition(" ELSE ")
            if then.strip().isdigit():
                then = "GOTO " + then.strip()            # THEN n is a jump
            if not then.strip():
                then = "REM"                             # an empty THEN (the rest of the line was a comment)
            if then.startswith("REM") and "else-past-rem" not in self.alt:
                other = ""                               # a REM swallows the ELSE too
            if true:
                return self.stmt(then, pt)
            if other:
                return self.stmt(other, pt)
            return self.next_line(pt)
        if s.startswith("OPEN "):
            self.files.add(int(s.split("#")[1]))
            return None
        if s == "CLEAR":
            self.reset()
            if "clear-keeps-cont" not in self.alt:
                self.cont = None
            return None
        if s == "NEW":
            if "new-keeps-trace" not in self.alt:
                self.trace = False
            self.prog = {}
            self.reset()
            self.cont = None
            return None
        m = re.fullmatch(r"([A-Z]\w*\$?)=(.+)", s)
        if m:
            self.vars[m.group(1)] = self.value(m.group(2))
            return None
        raise Err(2)

    def next_line(self, pt):
        later = [k for k in self.lines() if k > pt[0]]
        return (later[0], 0) if later else "END"

    # -- typing -------------------------------------------------------------------------------------------------
    def type(self, t):
        if getattr(self, "hung", False):
            return
        self.newline()
        self.screen += [t[i:i + WIDTH].strip() for i in range(0, len(t), WIDTH)]
        m = re.fullmatch(r"(\d+) ?(.*)", t)
        if m and not t.startswith("RUN"):
            n, text = int(m.group(1)), m.group(2).strip()
            if not text and n not in self.prog:
                self.message(msg(8))                     # a delete of a line that is not there: a direct error
                self.screen.append("<prompt>")
                if "delete-missing-drops-cont" in self.alt:
                    self.cont = None
                return
            if text:
                self.prog[n] = text
            else:
                del self.prog[n]
            if "edit-keeps-vars" not in self.alt:
                self.reset()
            if "edit-keeps-cont" not in self.alt:
                self.cont = None
            return
        self.direct = split(t)
        try:
            self.run_from(("D", 0))
        except Hang:
            self.newline()
            self.hung = True                             # no prompt; the keys typed after it are never read
            return
        self.newline()
        self.screen.append("<prompt>")


def run(c, alt=frozenset()):
    b = Basic(alt)
    for t in c.lines:
        b.type(t)
    return b.screen


def ok(c, alt=frozenset()):
    try:
        return list(c.scr or []) == run(c, alt)
    except (Err, Stop, ArithmeticError, TypeError, KeyError, IndexError, ValueError, AttributeError):
        return False                 # a law that cannot even produce the screen reads FALSE (goldfish pass 1)


def load(kw):
    out = kstop.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "END":
        return [
            Rule("R-END-STOP", "1. Stopping", "END stops the program where it stands, with no message, and the prompt "
                 "returns; in direct mode it does nothing. CONT after END goes on with the statement after it -- "
                 "mid-line if one follows -- and a GOSUB still pending is KEPT (its RETURN works).",
                 by("END stops the program mid-line", "CONT after END", "END in direct mode", "END inside a GOSUB",
                    "END inside a GOSUB, then CONT", "CONT after a mid-line END"), ok),
            Rule("R-END-CLOSE", "1. Stopping", "END closes every open file (a `PRINT #1` after it is `File not OPEN`) "
                 "and finishes an error handler (a typed RESUME is then `RESUME without error`).",
                 by("END leaves a file open", "END inside an error handler"), ok),
        ]
    if kw == "STOP":
        return [
            Rule("R-STOP-BREAK", "1. Stopping", "STOP stops the program with `Break in n`, n the STOP's own line (also "
                 "inside a subroutine or an error handler); in direct mode it prints `Break` alone.",
                 by("STOP stops with Break in", "STOP in direct mode", "Break in names the STOP's own line"), ok),
            Rule("R-STOP-CONT", "2. Going on", "CONT goes on with the statement AFTER the STOP: inside a GOSUB the "
                 "RETURN still works, inside a FOR the loop goes on to its end, inside an error handler the handler is "
                 "still active (its RESUME NEXT works), a file opened before it is still open, and a variable "
                 "changed while stopped is seen.",
                 by("CONT after STOP goes on after it", "STOP inside a GOSUB, then CONT returns normally",
                    "STOP inside a FOR, CONT twice", "a variable changed while stopped",
                    "STOP inside an error handler, then CONT", "STOP inside a FOR, CONT to the loop's end",
                    "STOP leaves a file open"), ok),
        ]
    if kw == "CONT":
        return [
            Rule("R-CONT-WHEN", "1. When CONT can go on", "There is nothing to continue -- `Can't CONTINUE` -- before "
                 "anything ran, after NEW or CLEAR, after a program line was added, changed or deleted, and after a "
                 "RUN, even one that then failed on a missing line. A direct statement in between -- a typed STOP, "
                 "END, an error, a FOR loop, a delete of a line that is not there -- leaves the resume point alone. An "
                 "edit also clears the variables.",
                 by("CONT before anything ran", "CONT after a line was added", "CONT after a direct statement",
                    "CONT after the stopped line was changed", "CONT after deleting a line that does not exist",
                    "CONT after deleting a line", "an edit clears the variables", "CONT after NEW", "CONT after CLEAR",
                    "CONT after RUN to a missing line", "CONT after a typed STOP", "CONT after a typed END",
                    "CONT after a typed error", "CONT after a typed FOR loop"), ok),
            Rule("R-CONT-WHERE", "2. Where it goes on", "After an error, CONT runs the failing statement AGAIN (with "
                 "whatever was changed meanwhile); after the program ran off its end, CONT does nothing, every time. "
                 "The rest of CONT's own line is never run; CONT inside a program with nothing to continue is `Can't "
                 "CONTINUE in n`.",
                 by("CONT after an error", "CONT after the program ran to its end",
                    "CONT after an error runs the statement again", "the rest of CONT's line", "CONT inside a program"),
                 ok),
        ]
    return [
        Rule("R-RUN-START", "1. Starting", "RUN starts at the first line, RUN n (also `RUN20`) at line n -- inside a "
             "program too, after clearing; a bare RUN inside a program restarts it. A missing n is `Undefined line "
             "number`; a number expression is `Type mismatch`; RUN with no program does nothing.",
             by("RUN n starts at line n", "RUN to a line that does not exist", "RUN inside a program",
                "RUN with no program", "RUN n inside a program clears and jumps", "a bare RUN inside a program restarts it",
                "RUN n without a space", "RUN and a number expression"), ok),
        Rule("R-RUN-CLEAR", "1. Starting", "RUN clears first: numbers, strings, arrays (DIM again is no error), the "
             "DATA pointer, ON ERROR and open files. The end of a run clears nothing (the variables are still there "
             "at the prompt).",
             by("RUN clears the variables", "RUN clears a string", "RUN clears an array", "RUN resets the DATA pointer",
                "RUN resets ON ERROR", "RUN closes a file", "the end of a run keeps the variables",
                "RUN closes a file left open by STOP"), ok),
    ]
