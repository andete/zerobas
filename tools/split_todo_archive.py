#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Archive closed roadmap items into docs/TODO-done.md; the pickup list stays.

📂 ONE FILE PER ITEM (2026-11-23, tools/todo_items.py). Closing an item is now
`todo/open/X.md` -> `todo/done/X.md` with its box ticked, and its stub in the
TODO.md skeleton stays. The TODO.md size cap that made this tool necessary is
gone, but its PURPOSE is not: todo/done/ and the skeleton's `[x]` stubs would
otherwise grow forever, and docs/TODO-done.md stays the long-term record. So a
pass now ARCHIVES DONE ITEM FILES: the item's text is appended VERBATIM to
docs/TODO-done.md under its section heading, its stub line leaves TODO.md and
its file leaves todo/done/. Everything is computed on `todo_items.full_text()`
-- the old single-file text, rebuilt exactly -- so the verdicts, the block ids,
the lossless check and the citation map (`TODO.md:<n>` = line n of that text,
as tools/check_todo_citations.py reads it) are the single-file tool's, unchanged.
🔴 What moves is the ITEM FILE, not the inventory block: a block runs on to the
next item or heading and can include skeleton prose below the item, which stays
in the skeleton. A pass whose moved lines are not exactly whole done-item files
(e.g. a WHOLE_SECTIONS heading not yet stubbed) is REFUSED, not approximated.

WHAT MOVES: a TOP-LEVEL `- [x]` item whose D-TODOSWEEP verdict is not LIVE.
WHAT STAYS: every `- [ ]` item, every `- [x]` item whose verdict IS live, and
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

Usage:  python3 tools/split_todo_archive.py [--dry-run]     (the default)
        python3 tools/split_todo_archive.py --apply
        python3 tools/split_todo_archive.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
# temp-root-check: every bare tempfile call here lands under the /tmp/zerobas root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import probe_tmp  # noqa: E402,F401 -- sets tempfile.tempdir


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import todo_inventory                                            # noqa: E402
import todo_items                                                # noqa: E402
SRC = os.path.join(ROOT, "TODO.md")
DST = os.path.join(ROOT, "docs", "TODO-done.md")
VERDICTS = os.path.join(ROOT, "scratchpad", "sweep_verdicts.json")

HEADER = """<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
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

STUB_MARK = "➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md)"
STUB = """{heading}

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — {why}.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
"""


def load_blocks(text=None):
    """Top-level blocks of the rebuilt single text, ids as the sweep keyed them."""
    return [b for b in todo_inventory.blocks(text=todo_items.full_text() if text is None else text)
            if b["depth"] == 0]


class Refused(Exception):
    pass


def expand(skel, texts):
    """skeleton lines + {(state, id): item text} -> (the single text's lines,
    {first line of an item: (state, id, last line)}). Exactly todo_items.full_text()."""
    full, spans = [], {}
    for line in skel:
        m = todo_items.STUB.search(line)
        if m:
            key = (m.group(1), m.group(2))
            t = texts[key]
            t = (t[:-1] if t.endswith("\n") else t).split("\n")
            spans[len(full) + 1] = key + (len(full) + len(t),)
            full.extend(t)
        else:
            full.append(line)
    return full, spans


def plan_split(skel, texts, blocks, plan):
    """The split, in the item layout. -> (full lines, new skeleton, src_out, dst_out, mapping, moved keys).

    build() runs on the single text with each block CLIPPED to its item file, so
    only item lines can move; the new skeleton is the old one minus the moved
    stubs, and it must expand to exactly src_out or nothing is written."""
    full, spans = expand(skel, texts)
    iblocks, moved = [], set()
    for b in blocks:
        sp = spans.get(b["start"])
        if plan[b["id"]][0] == "move":
            if sp is None or sp[0] != "done":
                raise Refused(f"block {b['id']} at line {b['start']} would move but is not a "
                              f"todo/done/ item file ({sp and sp[0]})")
            moved.add(sp[:2])
        iblocks.append(dict(b, end=sp[2]) if sp else b)
    src_out, dst_out, mapping = build(full, iblocks, plan)
    new_skel = [l for l in skel if not ((m := todo_items.STUB.search(l))
                                       and (m.group(1), m.group(2)) in moved)]
    if expand(new_skel, texts)[0] != src_out:
        raise Refused("the split would move lines that are not whole done-item files "
                      "(a WHOLE_SECTIONS heading not yet stubbed?) -- the item layout "
                      "cannot express that; do it by hand")
    return full, new_skel, src_out, dst_out, mapping, moved


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
    # D-SPLITSTUB: a WHOLE section already moved is left as its STUB; moving it
    # again re-archived the stub and wrote a fresh one on every pass.
    already = set()
    sec = None
    for line in lines:
        if line.startswith("## "):
            sec = line
        elif sec in WHOLE_SECTIONS and line.startswith(STUB_MARK):
            already.add(sec)
    for i, line in enumerate(lines, 1):
        b = span.get(i)
        if line.startswith("## "):
            section = line
        whole = section in WHOLE_SECTIONS and section not in already
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

# 🔴 `(?!\d)` IS LOAD-BEARING, AND ITS ABSENCE CORRUPTED 19 CITATIONS IN 12 FILES
# ON 2026-08-30. The `(?!\s*\(T-)` lookahead is meant to skip a citation that
# ALREADY carries its block id -- and BACKTRACKING defeats it: on
# `TODO<dot>md:4618 (T-529ABE)` the greedy `\d+` takes `4618`, the lookahead correctly
# rejects it, and the engine then RETRIES with `461`, where the next character is
# `8` rather than ` (T-` -- so the lookahead passes, `TODO.md:461` is rewritten,  NOT-A-CITATION
# and the orphaned `8 (T-529ABE)` is left behind. Every already-id'd citation in
# the tree was mangled that way, each into a plausible-looking hybrid.
# `(?!\d)` forces the match to be the WHOLE number, so there is no shorter
# alternative to backtrack into. Arms S1/S2 in --selftest.
CITE = re.compile(r"(?<![-\w])(\.\./)?TODO\.md:(\d+)(?!\d)(?!\s*\(T-)")

# 🔴 THE REPOINTER REWRITES A CITATION QUOTED AS AN EXAMPLE, TOO. The opt-out
# marker was introduced for `check_todo_citations.py --fix` (D-FILEDROT) and
# honoured ONLY there, so this file's own arms sat exposed to the rewriter it
# ships: measured 2026-09-01, FIVE lines here carry the marker and match CITE,
# including S2's and S3's input vectors. One of them corrupts SILENTLY -- S1's
# `already` fixture still asserts `== []` after a rewrite, so its MEANING would
# go while the arm stayed green, which is the same failure this marker exists to
# stop [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
NOCITE = "NOT-A-CITATION"


def _repoint_text(txt, sub_for_line):
    """Substitute citations LINE BY LINE, leaving any line marked `NOCITE`
    byte-identical.

    🎯 FACTORED FOR THE ARM, NOT FOR TIDINESS -- inline in `repoint()` the only
    way to check the exemption is to READ it, and reading is what missed the
    defect the first time. `_append_or_write` exists for the same reason.
    Per-line is also what makes the marker checkable at all: a whole-text
    `CITE.sub` cannot see which line a match landed on."""
    out = []
    for src_line in txt.splitlines(keepends=True):
        out.append(src_line if NOCITE in src_line
                   else CITE.sub(sub_for_line(src_line), src_line))
    return "".join(out)


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
        done = []

        def sub_for_line(line):
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
                # `](path (T-x))` is not a URL. The offset is into the LINE now,
                # which is where a `](` could ever be anyway.
                in_href = line[:m.start()].endswith("](")
                done.append(old)
                return f"{tgt}:{new}" + ("" if in_href or not bid else f" ({bid})")
            return sub

        new_txt = _repoint_text(txt, sub_for_line)
        if misses:
            print(f"  ⚠️  {rel}: {len(misses)} citation(s) name a line the map "
                  f"does not have: {sorted(set(misses))}")
        if new_txt != txt:
            open(path, "w").write(new_txt)
            n_files += 1
            n_cites += len(done)      # rewrites, not matches: a marked line is
            #                              a match this pass deliberately left alone
    print(f"  repointed {n_cites} citation(s) in {n_files} file(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="the default")
    a = ap.parse_args()
    # line-for-line what the single-file tool read (`.splitlines()` of a file
    # ending in a newline): no trailing empty element, and one written back
    skel = todo_items.skeleton().split("\n")
    if skel and skel[-1] == "":
        skel.pop()
    items = todo_items.items()
    texts = {(it.state, it.id): it.text for it in items}
    blocks = load_blocks()
    verdicts = json.load(open(VERDICTS))
    plan = classify(blocks, verdicts)
    try:
        lines, new_skel, src_out, dst_out, mapping, moved = plan_split(skel, texts, blocks, plan)
    except Refused as e:
        sys.exit(f"REFUSED: {e}")
    if "\n".join(lines) + "\n" != todo_items.full_text():
        sys.exit("REFUSED: expand() is not todo_items.full_text() -- the instrument disagrees with itself")

    moved_b = [b for b in blocks if plan[b["id"]][0] == "move"]
    print(f"  whole sections moved: {len(WHOLE_SECTIONS)}")
    for h, why in WHOLE_SECTIONS.items():
        print(f"        {h[3:60]} -- {why[:44]}")
    stay = [b for b in blocks if plan[b["id"]][0] == "stay"]
    print(f"TODO.md {len(lines)} lines, {len(blocks)} top-level blocks")
    print(f"  MOVE  {len(moved_b):4d} blocks  {sum(1 for w, _ in mapping.values() if w == 'dst'):6d} lines "
          f"-> docs/TODO-done.md")
    print(f"  STAY  {len(stay):4d} blocks  {sum(b['lines'] for b in stay):6d} lines")
    for b in stay:
        if b["state"] == "done":
            print(f"        kept closed block {b['id']}: {plan[b['id']][1]} "
                  f"-- {b['headline'][:60]}")
    for st, ident in sorted(moved):
        print(f"        archive todo/{st}/{ident}.md (file + its stub in TODO.md)")
    print(f"  result: TODO.md {len(src_out)} lines, archive {len(dst_out)} lines")

    if not verify(lines, src_out, dst_out, mapping):
        sys.exit("REFUSED: the split is not lossless -- reconstruction differs.")
    print("  lossless: reconstruction is byte-identical to the source ✅")

    if not any(w == "dst" for w, _ in mapping.values()):
        print("\nnothing to move -- no file written (D-SPLITSTUB)")
        return 0
    if not a.apply:
        print("\n(dry run; pass --apply to write)")
        return 0
    # 🔴 APPEND, NEVER OVERWRITE. `dst_out` is built from what is in TODO.md
    # RIGHT NOW, so writing it wholesale rebuilds the archive out of only what is
    # still in the pickup list. On 2026-08-30 a second run DELETED 8857 of the
    # 8903 lines already there, and `verify()` printed "lossless" while it did:
    # that check reconstructs the SOURCE, and had nothing to say about the
    # DESTINATION's prior content. This is a repeated-split tool that had only
    # ever been run once.
    prior = open(DST).read() if os.path.exists(DST) else ""
    out = _append_or_write(DST, dst_out)
    how = (f"APPENDED to (prior {prior.count(chr(10))} lines kept)"
           if prior.strip() else "wrote")
    if len(out) < len(prior):
        sys.exit(f"REFUSED: the archive would SHRINK ({len(prior)} -> {len(out)} "
                 f"bytes). Nothing archived is ever removed by a split.")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, "w").write(out)
    open(SRC, "w").write("\n".join(new_skel) + "\n")
    for st, ident in sorted(moved):
        os.remove(os.path.join(todo_items.DIR, st, ident + ".md"))
    print(f"\nwrote {SRC} ({len(moved)} stub(s) out), removed {len(moved)} todo/done/ "
          f"file(s), and {how} {DST}")
    # 🔴 THE MAP COUNTS `dst_out`, NOT THE ARCHIVE AS WRITTEN (2026-10-23, the third
    # split). Appending shifts every moved line down by the prior archive, so the
    # repoint wrote `TODO-done.md:717` for a block at :11056 -- 30 citations, caught  NOT-A-CITATION
    # by todo-citation-check and re-anchored by --fix because they carried ids.
    if prior.strip():
        off = _dst_offset(dst_out, out)
        mapping = {k: (w, n + off if w == "dst" else n) for k, (w, n) in mapping.items()}
    repoint(mapping, blocks)
    bad = todo_items.check()
    for b in bad:
        print("  🔴", b)
    print(f"  todo_items --check: {len(bad)} problem(s)")
    return 1 if bad else 0


def selftest() -> int:
    """Both 2026-08-30 defects, as arms. Collected by `make selftest-check`."""
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else '🔴 FAIL'}  {name}")
        ok = ok and bool(cond)

    # --- defect 2: the backtracking lookahead, on the exact corrupting input --
    # 🔴 ASSEMBLED, NOT WRITTEN LITERALLY -- AND THAT IS THE THIRD INSTANCE OF
    # ONE CLASS IN A DAY. `check_todo_citations.py --fix` cannot tell a citation
    # QUOTED AS AN EXAMPLE from a live one, so it repointed this fixture (4618 ->
    # 3251 -> 3287 across two runs) and rewrote the comment above it until the
    # explanation contradicted itself. The arm kept passing -- any already-id'd
    # citation is skipped -- so nothing would have caught the drift except
    # reading it. Concatenating keeps the input EXACT and invisible to the fixer.
    # [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
    already = "TODO" + ".md:4618 (T-529ABE), a Phase-1 entry"
    arm("S1 an ALREADY-ID'D citation is not matched at all (the backtracking "
        "bug rewrote `TODO.md:461` and orphaned the `8`)",   # NOT-A-CITATION
        CITE.findall(already) == [])
    arm("S2 ...and a BARE citation still is -- the fix must not blind the tool",
        [m.group(0) for m in CITE.finditer("see TODO.md:2811 for the rest")]  # NOT-A-CITATION
        == ["TODO.md:2811"])   # NOT-A-CITATION
    arm("S3 the same holds for the `../` form used from docs/",
        CITE.findall("../TODO.md:668 (T-6FE392)") == []   # NOT-A-CITATION
        and len(CITE.findall("../TODO.md:273")) == 1)   # NOT-A-CITATION

    # --- D-REPOINTMARK: the opt-out marker, honoured by the REWRITER too ------
    # 🔬 Both directions on the same apparatus. The control matters more than
    # the exemption here: an exemption scored against a line nothing would have
    # rewritten passes for free. Fixtures assembled by concatenation so no
    # literal citation exists in this file to be repointed [[an-instrument-can-
    # fail-the-way-the-thing-it-replaced-failed]].
    bare = "see TODO" + ".md:2811 for the rest\n"
    marked = bare.rstrip("\n") + "   # " + NOCITE + "\n"
    bump = lambda line: (lambda m: "TODO" + ".md:%d" % (int(m.group(2)) + 400))
    arm("S8 an UNMARKED citation is still rewritten (the control)",
        _repoint_text(bare, bump) == "see TODO" + ".md:3211 for the rest\n")
    arm("S9 ...and a line carrying the marker comes back BYTE-IDENTICAL",
        _repoint_text(marked, bump) == marked)
    arm("S10 the marker is line-scoped, not file-scoped -- a marked line does "
        "not exempt its neighbours",
        _repoint_text(marked + bare, bump)
        == marked + "see TODO" + ".md:3211 for the rest\n")

    # --- defect 1: the archive clobber ---------------------------------------
    # Exercised against a REAL file rather than by reading the branch, because
    # the branch is what was already believed to be right.
    import tempfile
    d = tempfile.mkdtemp(prefix="splitself-")
    dst = os.path.join(d, "TODO-done.md")
    prior = "# archive\n\n## From TODO.md\n\n- [x] an old block\n" * 40
    open(dst, "w").write(prior)
    fresh = ["# generated header", "", "## From `TODO.md` § Open", "",
             "- [x] a newly moved block"]
    g = dict(globals()); g["DST"] = dst
    src = _append_or_write(dst, fresh)
    arm("S4 a second pass APPENDS: every prior line survives",
        all(l in src for l in prior.splitlines() if l.strip()))
    arm("S5 ...and the newly moved block is there too",
        "- [x] a newly moved block" in src)
    arm("S6 the archive never SHRINKS across a pass", len(src) >= len(prior))
    off = _dst_offset(fresh, src)
    arm("S11 the repoint offset lands a moved line on its line in the WRITTEN "
        "archive (the third split numbered from the appended part)",
        src.split("\n")[5 + off - 1] == "- [x] a newly moved block")
    empty = os.path.join(d, "empty.md")
    arm("S7 a FIRST pass (no archive yet) still writes the header",
        _append_or_write(empty, fresh).startswith("# generated header"))

    # --- D-SPLITSTUB: a whole section already stubbed does not move again ----
    h = next(iter(WHOLE_SECTIONS))
    stubbed_src = ["# TODO", ""] + STUB.format(heading=h, why="x").splitlines() + ["## Open", ""]
    so, do, mp = build(stubbed_src, [], {})
    arm("S12 an already-stubbed whole section stays put: nothing moves",
        so == stubbed_src and not any(w == "dst" for w, _ in mp.values()))
    raw_src = ["# TODO", "", h, "", "some done prose", "## Open", ""]
    so, do, mp = build(raw_src, [], {})
    arm("S13 ...and an un-stubbed one still moves, leaving the stub (the control)",
        "some done prose" in do and any(l.startswith(STUB_MARK) for l in so))

    # --- the item layout: an archived item leaves as its WHOLE FILE + stub ----
    # A real fixture through the same plan_split() main() runs: a closed item
    # with no verdict (moves), a closed item with a LIVE verdict (stays), an open
    # item (stays), and skeleton prose directly below the moved item -- which
    # the inventory block includes and the item file does not, so it must STAY.
    sk = ["# TODO", "", "## Open", "",
          "- [x] **gone** -> [A](todo/done/A.md) <!-- item:done/A -->",
          "prose under A, part of the skeleton", "",
          "- [x] **kept** -> [B](todo/done/B.md) <!-- item:done/B -->",
          "- [ ] **open** -> [C](todo/open/C.md) <!-- item:open/C -->", ""]
    tx = {("done", "A"): "- [x] **gone**\n      body of A\n",
          ("done", "B"): "- [x] **kept**\n      body of B\n",
          ("open", "C"): "- [ ] **open**\n      \U0001f916 AUTONOMOUS — x.\n"}
    full, _ = expand(sk, tx)
    bl = load_blocks("\n".join(full))
    vd = {b["id"]: {"verdict": "LIVE"} for b in bl if "kept" in b["headline"]}
    pl = classify(bl, vd)
    fl, ns, so, do, mp, mv = plan_split(sk, tx, bl, pl)
    arm("S14 a closed, not-LIVE item moves as its whole file: stub out of the "
        "skeleton, text verbatim in the archive under its section",
        mv == {("done", "A")} and "<!-- item:done/A -->" not in "\n".join(ns)
        and do[-2:] == ["- [x] **gone**", "      body of A"]
        and "## From `TODO.md` § Open" in do)
    arm("S15 ...the skeleton prose below it, inside its inventory BLOCK, stays",
        "prose under A, part of the skeleton" in ns
        and not any("prose under A" in l for l in do))
    arm("S16 ...a LIVE closed item and an open item stay, and the new skeleton "
        "expands to exactly the split's source side",
        any("item:done/B" in l for l in ns) and any("item:open/C" in l for l in ns)
        and expand(ns, tx)[0] == so and verify(fl, so, do, mp))
    bad_pl = dict(pl, **{b["id"]: ("move", "x") for b in bl if "open" in b["headline"]})
    try:
        plan_split(sk, tx, bl, bad_pl)
        refused = False
    except Refused:
        refused = True
    arm("S17 a plan that would move an OPEN item is REFUSED, not written", refused)

    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


def _dst_offset(dst_out, out):
    """Lines to add to a `dst_out` line number to get its line in the written
    archive. Appending drops `dst_out`'s header and resumes at its first `## `
    line, so that line is found again in `out` and the two positions compared."""
    h = next(i for i, l in enumerate(dst_out) if l.startswith("## "))
    lines = out.split("\n")
    at = max(i for i, l in enumerate(lines) if l == dst_out[h]
             and lines[i:i + len(dst_out) - h] == dst_out[h:])
    return at - h


def _append_or_write(dst, dst_out):
    """The write half of main(), factored so --selftest can exercise it.

    🎯 FACTORED FOR THE ARM, NOT FOR TIDINESS. Inline in main() the only way to
    check it was to read it, and reading it is what missed the defect.
    """
    prior = open(dst).read() if os.path.exists(dst) else ""
    body = "\n".join(dst_out) + "\n"
    if prior.strip():
        keep = body.split("\n## ", 1)
        body = ("\n---\n\n## Appended by a later split pass\n\n"
                "Blocks that moved out of `TODO.md` in a subsequent run, under\n"
                "the section headings they were written beneath.\n\n"
                + ("## " + keep[1] if len(keep) > 1 else body))
        return prior.rstrip("\n") + "\n" + body
    return body


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
