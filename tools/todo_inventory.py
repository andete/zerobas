#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""todo_inventory.py — the DENOMINATOR instrument for a TODO.md sweep.

A hand-listed denominator is a scope claim, so this one is mechanical and
re-runnable. It parses `TODO.md` into checkbox BLOCKS and emits one record per
block: id, line range, state, section, headline, and the markers the block
carries. A sweep then attaches a VERDICT to every id, and §"audit" here proves
the verdict set is complete and disjoint over the real file — not over a list
retyped from it.

🔴 WHY THIS IS A TOOL AND NOT A HEREDOC. The 2026-08-09 sweep
(`docs/todo-staleness-sweep-2026-08.md`) built its denominator with an inline
`python3 - <<EOF`, which cannot be re-run against a later commit without being
retyped — and its central finding was that a list nobody re-runs cannot be
trusted. The instrument had the property it was measuring.

⚠️ NESTING IS REAL: 21 checkbox lines in this file are INDENTED sub-items of an
outer block. They are recorded with `depth > 0` and attributed to their parent,
because an indented `- [x]` inside an open parent is not an independent item and
counting it as one inflates the denominator.

Usage:
  python3 tools/todo_inventory.py                 # human summary
  python3 tools/todo_inventory.py --json OUT      # machine-readable inventory
  python3 tools/todo_inventory.py --audit FILE    # check a verdict file covers it
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "TODO.md"

BOX = re.compile(r"^(\s*)- \[([ x])\] ?(.*)$")
H2 = re.compile(r"^## (.+)$")
BOLD = re.compile(r"^\*\*(.+?)\*\*\s*$")

# Markers that say a block carries an unresolved claim. Deliberately COARSE:
# this is used to SCOPE a manual read, so over-inclusion is the safe direction.
# It is a proxy and is labelled one — the real surface is reading the block.
RESIDUAL = re.compile(
    r"UNMEASURED|unmeasured|NOT MEASURED|unpriced|Unpriced|UNPRICED"
    r"|STILL OPEN|still open|left open|no gate|NO GATE|nothing checks"
    r"|not re-run|NOT RUN|unverified|UNVERIFIED")

# What kind of instrument can falsify the block's claim. First match wins; the
# order encodes precedence, and `unclassified` is a REPORTED bucket, never a
# silent default.
KIND = [
    ("behavioural", re.compile(
        r"\bERR \d|Syntax error|Illegal function|Type mismatch|reads?\b.*\bvs\b"
        r"|prints?\b|raises?\b|the reference|CF-3300|VG-8020|divergen", re.I)),
    ("space", re.compile(r"\b\d+ ?B\b|page 1|page-1|wall|carve|byte-identical"
                         r"|free\b|eviction", re.I)),
    ("gate", re.compile(r"gate|knife|acceptance|probe|battery|row set|denominator"
                        r"|falsif", re.I)),
    ("doc", re.compile(r"doc debt|citation|spec |README|stale|prose", re.I)),
]


def blocks():
    lines = TODO.read_text().split("\n")
    out, section, bold, cur = [], None, None, None

    def close(end):
        if cur is not None:
            cur["end"] = end
            cur["text"] = "\n".join(lines[cur["start"] - 1:end])
            out.append(cur)

    for i, l in enumerate(lines, 1):
        m2 = H2.match(l)
        if m2:
            close(i - 1); cur = None; section = m2.group(1); bold = None; continue
        mb = BOLD.match(l)
        if mb and cur is None:
            bold = mb.group(1); continue
        m = BOX.match(l)
        if m:
            close(i - 1)
            indent, mark, head = m.group(1), m.group(2), m.group(3)
            cur = dict(start=i, depth=len(indent) // 2, state="open" if mark == " " else "done",
                       section=section, group=bold, headline=head.strip()[:160])
            continue
    close(len(lines))
    # 🔴 AN ID DERIVED FROM POSITION IS NOT STABLE ACROSS EDITS. The first
    # version numbered blocks T001.. in file order, and the very next edit to
    # TODO.md (inserting a paragraph in the pickup-list header) renumbered
    # everything below it — so a verdict file written against those ids would
    # silently re-point at different items. The bookkeeping would have rotted in
    # exactly the way this sweep exists to catch. The id is CONTENT-derived:
    # a digest of the headline, which survives reflow, renumbering and moving
    # the block to another file (which the archive split will do).
    seen = {}
    for b in out:
        h = hashlib.sha256(b["headline"].encode()).hexdigest()[:6].upper()
        n = seen.get(h, 0); seen[h] = n + 1
        b["id"] = f"T-{h}" + (f".{n}" if n else "")
        b["lines"] = b["end"] - b["start"] + 1
        b["residual_marker"] = bool(RESIDUAL.search(b["text"]))
        b["kind"] = next((k for k, r in KIND if r.search(b["text"])), "unclassified")
        del b["text"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--audit", help="a JSON file mapping id -> verdict")
    a = ap.parse_args()
    bs = blocks()
    top = [b for b in bs if b["depth"] == 0]
    nested = [b for b in bs if b["depth"] > 0]
    subj = [b for b in top if b["state"] == "open" or b["residual_marker"]]

    print(f"TODO.md blocks: {len(bs)}  (top-level {len(top)}, nested {len(nested)})")
    for st in ("open", "done"):
        n = [b for b in top if b["state"] == st]
        print(f"  {st:5s} {len(n):4d}   lines {sum(b['lines'] for b in n):6d}")
    print(f"\nSWEEP SUBJECT = every open block + every done block carrying a "
          f"residual marker: {len(subj)}")
    for k in sorted({b["kind"] for b in subj}):
        rows = [b for b in subj if b["kind"] == k]
        o = sum(1 for b in rows if b["state"] == "open")
        print(f"  {k:14s} {len(rows):4d}  (open {o}, done-with-marker {len(rows)-o})")

    if a.json:
        Path(a.json).write_text(json.dumps(bs, indent=1))
        print(f"\nwrote {a.json}")
    if a.audit:
        v = json.loads(Path(a.audit).read_text())
        ids = {b["id"] for b in subj}
        # keys starting with "_" are the verdict file's own metadata, not a
        # verdict; counting them as one made the first audit report a
        # "verdict for a NON-subject" that was nothing of the kind.
        got = {k for k in v if not k.startswith("_")}
        print("\n--- audit ---")
        print(f"  subject ids            : {len(ids)}")
        print(f"  verdicts supplied      : {len(got)}")
        print(f"  subject with NO verdict: {len(ids - got)}  {sorted(ids - got)[:10]}")
        print(f"  verdicts for NON-subject: {len(got - ids)}  {sorted(got - ids)[:10]}")
        return 0 if ids == got else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
