#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Split TODO.md: closed work moves to docs/TODO-done.md, the pickup list stays.

WHAT MOVES: a TOP-LEVEL `- [x]` block whose D-TODOSWEEP verdict is not LIVE.
WHAT STAYS: every `- [ ]` block, every `- [x]` block whose verdict IS live, and
all section headings and prose.

🔴 THE SWEEP IS WHAT MAKES THIS SAFE. Before 2026-08-26 a `- [x]` block could
not be trusted to be finished -- 30 of the sweep's subject blocks were live
residuals written up INSIDE a closed block, which is why `## Open -- standing
residuals` exists at all. The split rule is therefore the VERDICT, not the
checkbox, and four `- [x]` blocks stay behind because of it.

LOSSLESS BY CONSTRUCTION AND BY CHECK: every source line is emitted to exactly
one of the two files, in order, and --verify recomputes the original by
interleaving them back and compares byte for byte.

Citations are repointed from an exact old-line -> (file, new-line) map, so a
`TODO.md` line reference in another doc becomes the right line of the right
file. (Line numbers are spelled out in prose here rather than as a
`TODO.md:NNN`, which `check_todo_citations.py` would read as a live citation
into a file that no longer has that line -- a tool's own example is the first
thing its sibling gate finds.) Each
repointed citation also gains the block's CONTENT-DERIVED id, which is what
`tools/check_todo_citations.py` re-resolves when the line drifts again.

`--apply` also REPOINTS every citation, in this same process -- see `repoint()`.

Usage:  python3 tools/split_todo_archive.py --dry-run
        python3 tools/split_todo_archive.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                 # noqa: E402
SRC = os.path.join(ROOT, "TODO.md")
DST = os.path.join(ROOT, "docs", "TODO-done.md")
VERDICTS = os.path.join(ROOT, "scratchpad", "sweep_verdicts.json")

HEADER = """<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# TODO — done, archived

Closed work split out of [`TODO.md`](../TODO.md) on 2026-08-26 so the pickup
list is the length of the work that is actually left. **Nothing was rewritten:
every block below is byte-identical to what it was in `TODO.md`, under the
section heading it was written beneath.**

🔴 **THE SPLIT RULE IS THE VERDICT, NOT THE CHECKBOX.** A `- [x]` block was not
evidence of finished work before D-TODOSWEEP — **30 of that sweep's 178 subject
blocks were live residuals written up inside a closed block**, which is why
`## Open — standing residuals` exists in `TODO.md` at all. Only blocks the sweep
verdicted **not live** were moved; four closed blocks stayed behind because
their verdict is LIVE. Record:
[`docs/todo-sweep-2026-08-26.md`](todo-sweep-2026-08-26.md), verdicts
`scratchpad/sweep_verdicts.json`.

⚠️ **THIS FILE IS A RECORD, NOT A WORK LIST.** Nothing here is a task. If a
block here turns out to still be live, it belongs back in `TODO.md` as an open
item — move it, do not re-open it in place.

Regenerate the split with `tools/split_todo_archive.py`; the citations that
point into it are checked by `make todo-citation-check`.

"""


# Sections whose ITEMS all move and whose remaining prose is itself a
# done-record, so the heading would be left standing over nothing. Named
# EXPLICITLY rather than detected: "has no surviving items" is also true of the
# living prose sections (`Phases at a glance`, `Status today`, `Beyond`), and a
# heuristic that moved those would be moving the charter out of the charter file.
WHOLE_SECTIONS = {
    "## Phase 1 record — committed work (all ✅ done)":
        "its preamble says so: 'nothing here is outstanding'",
    "## Done — Phase 1 (loader-stub BASIC)":
        "'Complete and oracle-validated; kept below as the provenance record'",
    "## Done — storage transports":
        "a prose done-record of disk and tape; no items at all",
}

STUB = """{heading}

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — {why}.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
"""


def load_blocks():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "todo_inventory.py"),
                          "--json", probe_tmp.tmp("_split_inv.json")],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"todo_inventory failed:\n{out.stdout}{out.stderr}")
    return [b for b in json.load(open(probe_tmp.tmp("_split_inv.json"))) if b["depth"] == 0]


def is_live(block, verdicts):
    d = verdicts.get(block["id"])
    return bool(d) and d["verdict"].upper().lstrip("🔴 ").startswith("LIVE")


def classify(blocks, verdicts):
    """-> {block id: 'stay'|'move'}, and the reason each stayer stayed."""
    plan = {}
    for b in blocks:
        if b["state"] == "open":
            plan[b["id"]] = ("stay", "open")
        elif is_live(b, verdicts):
            plan[b["id"]] = ("stay", "closed block, LIVE verdict")
        elif b["id"] not in verdicts and b["id"] in {x["id"] for x in blocks
                                                     if x["state"] == "open"}:
            plan[b["id"]] = ("stay", "unverdicted")          # belt and braces
        else:
            plan[b["id"]] = ("move", "closed, verdict not live")
    return plan


def build(lines, blocks, plan):
    """Emit both files and the old-line -> (which, new-line) map.

    `which` is 'src' or 'dst'. Line numbers are 1-based on BOTH sides.
    """
    span = {}
    for b in blocks:
        for n in range(b["start"], b["end"] + 1):
            span[n] = b
    src_out, dst_out, mapping = [], HEADER.splitlines(), {}
    section = None            # current `## ` heading text in the source
    emitted_sections = set()
    stubbed = set()
    for i, line in enumerate(lines, 1):
        b = span.get(i)
        if line.startswith("## "):
            section = line
        whole = section in WHOLE_SECTIONS
        move = whole or (b is not None and plan[b["id"]][0] == "move")
        if move:
            if whole:
                # The section's REAL heading and prose travel with it, so the
                # synthesized mirror below must not also fire for this section.
                emitted_sections.add(section)
                if section not in stubbed:
                    stubbed.add(section)
                    src_out.extend(STUB.format(heading=section,
                                               why=WHOLE_SECTIONS[section]).splitlines())
            elif section is not None and section not in emitted_sections:
                # 🔴 A BLOCK WITHOUT ITS HEADING IS A BLOCK WITHOUT ITS SUBJECT.
                # The archive mirrors the source's section structure so a moved
                # block is still read under the phase it belonged to.
                if dst_out and dst_out[-1].strip():
                    dst_out.append("")
                dst_out.append(f"## From `TODO.md` § {section[3:]}")
                dst_out.append("")
                emitted_sections.add(section)
            dst_out.append(line)
            mapping[i] = ("dst", len(dst_out))
        else:
            src_out.append(line)
            mapping[i] = ("src", len(src_out))
    return src_out, dst_out, mapping


def verify(lines, src_out, dst_out, mapping):
    """Reconstruct the original from the two outputs via the map, byte for byte."""
    rebuilt = []
    for i in range(1, len(lines) + 1):
        which, n = mapping[i]
        rebuilt.append((src_out if which == "src" else dst_out)[n - 1])
    return rebuilt == lines


# --- citation repointing, IN THE SAME PROCESS AS THE SPLIT -------------------
# 🔴 THIS WAS A SECOND TOOL AND THAT WAS THE DEFECT. The map is a handoff, and
# a handoff through a temp file is both a lifetime problem (`probe_tmp` owns a
# per-process directory and removes it at exit) and an ordering trap: the split
# and the repoint are ONE operation, and running them as two is exactly how the
# first pass shipped a repoint that rewrote link LABELS and left their TARGETS.
# One process, one map, no file between them.

CITE = re.compile(r"(?<![-\w])(\.\./)?TODO\.md:(\d+)(?!\s*\(T-)")


def repoint(mapping, blocks):
    """Rewrite every `TODO.md:NNN` citation from the map; attach the block id."""
    def block_at(n):
        hit = [b for b in blocks if b["start"] <= n <= b["end"]]
        return max(hit, key=lambda b: b["depth"])["id"] if hit else None

    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                           text=True).stdout.split()
    n_files = n_cites = 0
    for rel in files:
        if not rel.endswith((".md", ".py", ".asm", ".inc")) and rel != "Makefile":
            continue
        path = os.path.join(ROOT, rel)
        try:
            txt = open(path).read()
        except (OSError, UnicodeDecodeError):
            continue
        if not CITE.search(txt):
            continue
        misses = []

        def sub(m):
            old = int(m.group(2))
            if old not in mapping:
                misses.append(old); return m.group(0)
            which, new = mapping[old]
            if rel.startswith("docs/"):
                tgt = "TODO-done.md" if which == "dst" else "../TODO.md"
            else:
                tgt = "TODO.md" if which == "src" else "docs/TODO-done.md"
            bid = block_at(old)
            # ⚠️ THE ID GOES ON THE LABEL, NEVER INSIDE A LINK TARGET -- a
            # `](path (T-x))` is not a URL.
            in_href = txt[:m.start()].endswith("](")
            return f"{tgt}:{new}" + ("" if in_href or not bid else f" ({bid})")

        new_txt = CITE.sub(sub, txt)
        if misses:
            print(f"  ⚠️  {rel}: {len(misses)} citation(s) name a line the map "
                  f"does not have: {sorted(set(misses))}")
        if new_txt != txt:
            open(path, "w").write(new_txt)
            n_files += 1
            n_cites += len(CITE.findall(txt))
    print(f"  repointed {n_cites} citation(s) in {n_files} file(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    lines = open(SRC).read().splitlines()
    blocks = load_blocks()
    verdicts = json.load(open(VERDICTS))
    plan = classify(blocks, verdicts)
    src_out, dst_out, mapping = build(lines, blocks, plan)

    moved = [b for b in blocks if plan[b["id"]][0] == "move"]
    print(f"  whole sections moved: {len(WHOLE_SECTIONS)}")
    for h, why in WHOLE_SECTIONS.items():
        print(f"        {h[3:60]} -- {why[:44]}")
    stay = [b for b in blocks if plan[b["id"]][0] == "stay"]
    print(f"TODO.md {len(lines)} lines, {len(blocks)} top-level blocks")
    print(f"  MOVE  {len(moved):4d} blocks  {sum(b['lines'] for b in moved):6d} lines "
          f"-> docs/TODO-done.md")
    print(f"  STAY  {len(stay):4d} blocks  {sum(b['lines'] for b in stay):6d} lines")
    for b in stay:
        if b["state"] == "done":
            print(f"        kept closed block {b['id']}: {plan[b['id']][1]} "
                  f"-- {b['headline'][:60]}")
    print(f"  result: TODO.md {len(src_out)} lines, archive {len(dst_out)} lines")

    if not verify(lines, src_out, dst_out, mapping):
        sys.exit("REFUSED: the split is not lossless -- reconstruction differs.")
    print("  lossless: reconstruction is byte-identical to the source ✅")

    if not a.apply:
        print("\n(dry run; pass --apply to write)")
        return 0
    open(SRC, "w").write("\n".join(src_out) + "\n")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, "w").write("\n".join(dst_out) + "\n")
    print(f"\nwrote {SRC} and {DST}")
    repoint(mapping, blocks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
