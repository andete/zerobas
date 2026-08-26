# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""probe_report — the ONE report-row grammar this tree prints, and its parser.

docs/spec-probe-rowshape.md. A knife runner reads a probe's report to decide
whether a cut reddened anything, and twice in one session (D-CASOPEN, 2026-08-07)
it was defeated by the report's SHAPE rather than by its content:

  * a runner's truncation guard fired on a COMPLETE 32-row report, because the
    exit-2 rows are indented two spaces and the scored rows are not, so an
    `^`-anchored row regex matched every green run and no knifed one;
  * a runner diffing report LINES scored EVERY row as moved, because the same
    reading prints as `ok  label  'value'` when the sides agree and as
    `....  label  vg8020='..'  zb='..'` when nothing is scored.

⚠️ NEITHER FAULT CAN BE SEEN BY A GREEN RUN. A probe's failure-formatting branch
only ever executes under a knife, so four probes carried this for months while
every acceptance gate passed. That is the whole reason the rules below are
mechanised here and gated statically by tools/check_report_shape.py, instead of
being written down again in docs/dev-workflow.md and re-derived one runner at a
time.

THE GRAMMAR (spec §4):

    <TAG padded to 4> <SP> <label padded to W> <SP><SP> <side>=<repr> ...  <note>

  I1  the tag is a CONSTANT width, so the label starts at the same column on
      every row of every exit path. `{'ok ' if ok else 'DIFF'}` is 3-or-4 and is
      exactly what this exists to forbid.
  I2  ONE value encoding per probe. `row()` always names every side, on every
      path, including when they agree -- an `ok` row that shows a single value
      asks the reader to TRUST that both sides gave it.
  I3  every exit path that prints rows ends with footer(): a POSITIVE statement
      of how many rows were printed. A runner then detects truncation by reading
      a count, not by guessing a layout.

FOR A KNIFE RUNNER -- this is the supported entry point, and it is the answer to
"so a runner cannot be caught by the layout at all":

    sys.path.insert(0, "probes/lib")
    import probe_report
    rows = probe_report.parse(probe_stdout)      # raises ReportTruncated
    now  = {r.label: r.vals["zb"] for r in rows if "zb" in r.vals}

`parse()` recovers values by positively matching `name=<python-repr>` pairs. It
never strips the note, never anchors on a column, and never assumes an indent --
so a future layout change cannot silently turn it into a line differ.
"""
from __future__ import annotations

import re
# 🎯 ESTABLISHES THE PROJECT TEMP ROOT (`/tmp/zerobas`) AS A SIDE EFFECT OF
# IMPORT -- see probes/lib/probe_tmp.py. Imported here, at a chokepoint every
# probe reaches, so a bare `tempfile.*` anywhere lands under the one root.
import probe_tmp  # noqa: E402,F401
from typing import NamedTuple

# The closed tag set. Four characters wide as printed; the spellings here are
# what `row()` is given and what `parse()` accepts.
#   ok    the sides agree            DIFF  they do not
#   PIN   a pinned divergence,       ROT   ...that has MOVED (re-measure)
#         still reading as pinned
#   FAIL  a positive control failed  PASS  a positive control held
#   ....  not scored (an exit-2 row: the instrument was broken)
#   --    characterization, a single side, no agreement verdict possible
TAGS = ("ok", "DIFF", "PIN", "ROT", "FAIL", "PASS", "....", "--")
TAG_W = 4

_TAG_ALT = "|".join(re.escape(t) for t in sorted(TAGS, key=len, reverse=True))

# A row line. Leading whitespace is ALLOWED and ignored: `fat_error` indents its
# whole report by two and is perfectly consistent about it, and the invariant
# that matters is "the same column on every path", not "column 0".
ROW_RE = re.compile(rf"^\s*({_TAG_ALT})\s+(\S+)\s+(.*)$")

# `side=<python repr>`. Understanding repr quoting is what lets a value contain
# spaces, `=`, brackets or nothing at all without the parser guessing.
PAIR_RE = re.compile(r"([A-Za-z_][\w.\-]*)=("
                     r"'(?:[^'\\]|\\.)*'"
                     r'|"(?:[^"\\]|\\.)*"'
                     r")")

FOOTER_RE = re.compile(r"^ROWS: (\d+) printed, (\d+) scored\b")


class ReportTruncated(Exception):
    """The report is not whole, so nothing in it can be compared.

    Raised rather than returned: a runner that gets a SHORT list back cannot
    distinguish it from "the knife moved nothing", and that ambiguity is what
    turned a crashed probe into "twenty rows moved" (dev-workflow.md §Knives)."""


class Row(NamedTuple):
    tag: str
    label: str
    vals: dict           # side -> the value as printed (repr decoded)
    note: str            # everything after the last pair; never parsed


def row(tag: str, label: str, width: int, vals: dict, note: str = "") -> str:
    """ONE report row. Every report-row print in an in-contract probe is this."""
    if tag not in TAGS:
        raise ValueError(f"tag {tag!r} is not in the closed set {TAGS}")
    body = "  ".join(f"{s}={v!r}" for s, v in vals.items())
    return f"{tag:<{TAG_W}} {label:<{width}}  {body}{note}"


def footer(printed: int, scored: int, why: str) -> str:
    """The terminator, printed on EVERY exit path that printed rows (I3)."""
    return f"ROWS: {printed} printed, {scored} scored — {why}"


def _decode(lit: str) -> str:
    """A python string repr back to its value, without eval()."""
    out, i = [], 1
    while i < len(lit) - 1:
        c = lit[i]
        if c == "\\" and i + 1 < len(lit) - 1:
            nxt = lit[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                        "'": "'", '"': '"'}.get(nxt, "\\" + nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def parse(text: str, require_footer: bool = True) -> list[Row]:
    """Every report row in `text`, as (tag, label, {side: value}, note).

    Raises ReportTruncated if the ROWS: footer is missing or disagrees with the
    number of rows actually parsed -- the two ways a report can be a PREFIX."""
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        tag, label, tail = m.group(1), m.group(2), m.group(3)
        pairs = list(PAIR_RE.finditer(tail))
        vals = {p.group(1): _decode(p.group(2)) for p in pairs}
        note = tail[pairs[-1].end():] if pairs else tail
        rows.append(Row(tag, label, vals, note.strip()))

    if not require_footer:
        return rows

    foots = [m for m in (FOOTER_RE.match(l) for l in text.splitlines()) if m]
    if not foots:
        raise ReportTruncated(
            f"no `ROWS:` footer in {len(text.splitlines())} line(s) of output -- "
            "the report is a PREFIX, or the probe does not print the terminator. "
            "Either way nothing here can be compared to a baseline.")
    declared = sum(int(m.group(1)) for m in foots)
    if declared != len(rows):
        raise ReportTruncated(
            f"the footer declares {declared} row(s), {len(rows)} parsed -- "
            "the report was cut short (or the parser has gone blind to a shape "
            "the probe prints).")
    return rows
