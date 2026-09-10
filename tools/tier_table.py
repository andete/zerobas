#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""tier_table — the priority-tier table, compactly, whenever Joost asks.

    make tiers                 summary + every keyword-tier item, one line each
    make tiers ARGS=--keywords per keyword: the worst OPEN tier that names it
    make tiers ARGS=--all      every open item incl. APPARATUS / BUDGET / OTHER
    python3 tools/tier_table.py --selftest

WHAT IT READS. `TODO.md` § "Open — standing residuals": every open item carries
a `🎚️ TIER n — …` (or class) line (Joost's five tiers, 2026-09-10 — the legend
at the top of that section is the rule; this prints it, it does not define it).
The keyword denominator is `basic/kwtable.inc`, the SAME table the tokeniser
walks, so a keyword cannot be missing from this report and present on the
machine.

⚠️ WHAT THE `--keywords` VIEW IS AND IS NOT. It maps each keyword to the OPEN
items whose text names it in a backticked token (`LOF(1)`, `PUT#1,255`,
`DEF FN`). A keyword with no open item is reported as **"no open gap"**, which
is NOT "verified": the parked per-keyword-table block measured that "is this
keyword typed somewhere" is ~100 % and means nothing, and the column that
would mean something — is the keyword's behaviour differentially SCORED — needs
the `subject:` tag per gate row that step (c) will add. Until then this view
says where the KNOWN gaps are, tier by tier, and says so in its own footer
rather than letting a blank read as a pass
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

Backticked tokens only, on purpose: `AND`, `OR`, `IF`, `ON`, `TO`, `KEY` are
English words in prose, and the prose is the bulk of every block.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(ROOT, "TODO.md")
KWTABLE = os.path.join(ROOT, "basic", "kwtable.inc")

TIERS = ["TIER 1", "TIER 2", "TIER 3", "TIER 4", "TIER 5"]
CLASSES = ["APPARATUS", "BUDGET", "STANDING", "OTHER"]
TAG = re.compile(r"^[ \t]*🎚️\s*(TIER [1-5](?: \(latent\))?|APPARATUS|BUDGET|STANDING|OTHER)\s*—\s*(.*)$")
# 🔴 ONE DENOMINATOR: the marker is whatever `make todo-marker-check` says it is.
# A loose `^\s*🙋 ` regex here read a prose line beginning with 🙋 as the
# item's marker and disagreed with the gate on two items in its first run.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("check_todo_markers",
                                     os.path.join(ROOT, "tools", "check_todo_markers.py"))
_ctm = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_ctm)
GATE_MARKER = _ctm.MARKER            # {emoji: compiled regex}, the gate's own
BOX = re.compile(r"^- \[ \] ")
HEAD_END = re.compile(r"^(#{2,3} )|^- \[")
KWENT = re.compile(r'^\s*db\s+\d+,"([A-Z][A-Z$#]*)"')
TICK = re.compile(r"`([^`\n]{1,40})`")
WORD = re.compile(r"[A-Z][A-Z]*\$?")   # a trailing $ is part of STR$/MID$; a # never is (`PUT#1` names PUT)


# 🔴 THE DENOMINATOR MUST BE THE REFERENCE'S KEYWORD SET, NOT ZEROBAS'S OWN.
# kwtable.inc is the table the tokeniser walks, so a keyword zerobas does not
# tokenise is ABSENT from it by construction -- and those are exactly the TIER 1
# "missing keyword" rows this table exists to show. The first cut used kwtable
# alone and `COPY` / `LOC` / `DSKI$` / `DSKO$` could not appear at all. No
# machine-readable reference word list exists in the tree (kwsweep's SWEEP is a
# probe-row list keyed by lowercase row names, and the coverage doc is prose),
# so the missing set is listed HERE and the selftest fails the day one of them
# shows up in kwtable -- the list self-corrects instead of rotting.
KNOWN_MISSING = ["COPY", "LOC", "DSKI$", "DSKO$"]     # TODO.md, "EIGHT KEYWORDS THE REFERENCE TOKENISES"


def kwtable_keywords(path=KWTABLE):
    out = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = KWENT.match(ln)
        if m:
            out.append(m.group(1))
    return out


def keywords(path=KWTABLE):
    """kwtable.inc's keywords plus the ones filed as missing, in table order."""
    tab = kwtable_keywords(path)
    return tab + [k for k in KNOWN_MISSING if k not in tab]


def items(text):
    """Open items: dicts with line, tier, tag_text, marker, head, body."""
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if BOX.match(l)]
    res = []
    for k, a in enumerate(starts):
        b = len(lines)
        for j in range(a + 1, len(lines)):
            if HEAD_END.match(lines[j]):
                b = j
                break
        blk = lines[a:b]
        tier, tag_text = "UNTAGGED", ""
        marker = "?"
        for l in blk:
            m = TAG.match(l)
            if m:
                tier, tag_text = m.group(1), m.group(2)
            for emoji, rx in GATE_MARKER.items():
                if rx.match(l):
                    marker = emoji
        head = lines[a][6:]
        j = a + 1
        while head.count("**") < 2 and j < b and j < a + 6:
            head += " " + lines[j].strip()
            j += 1
        head = re.sub(r"\s+", " ", head).strip()
        e = head.find("**", head.find("**") + 2)
        head = head[:e + 2] if e > 0 else head[:120]
        head = head.replace("**", "")
        res.append(dict(line=a + 1, tier=tier, tag=tag_text, marker=marker,
                        head=head, body="\n".join(blk)))
    return res


def base_tier(t):
    return t.split(" (")[0]


def summary(its):
    counts = defaultdict(int)
    for it in its:
        counts[base_tier(it["tier"])] += 1
    rows = [(t, counts.get(t, 0)) for t in TIERS] + [(c, counts.get(c, 0)) for c in CLASSES]
    if counts.get("UNTAGGED"):
        rows.append(("UNTAGGED", counts["UNTAGGED"]))
    return rows


def kw_gaps(its, kws):
    """keyword -> sorted set of (tier, line) for open items naming it in a backtick."""
    kwset = set(kws)
    gaps = defaultdict(set)
    for it in its:
        if base_tier(it["tier"]) not in TIERS:
            continue
        # 🔴 HEADLINE + 🎚️ LINE ONLY, NOT THE BODY. The first cut scanned the
        # whole block and put 76 keywords at TIER 1, because one block about
        # missing keywords and one about a NAME corner mention dozens of others
        # in passing -- the exact "mentioned ≈ scored" trap the parked table
        # block measured. An item's SUBJECT is its headline, and the 🎚️ line is
        # where an item declares the keywords it is about: that line IS the
        # item-level `subject:` tag, and step (c) extends the same idea to rows.
        for tok in TICK.findall(it["head"] + " " + it["tag"]):
            for w in WORD.findall(tok):
                if w in kwset:
                    gaps[w].add((base_tier(it["tier"]), it["line"]))
    return {k: v for k, v in gaps.items() if v}    # a plain dict: a lookup must not CREATE a key


def fmt_items(its, tiers_only=True, width=78):
    keep = [it for it in its if (base_tier(it["tier"]) in TIERS) or not tiers_only]
    order = TIERS + CLASSES + ["UNTAGGED"]
    keep.sort(key=lambda it: (order.index(base_tier(it["tier"])), it["line"]))
    out, last = [], None
    for it in keep:
        t = base_tier(it["tier"])
        if t != last:
            out.append(f"\n{t}")
            last = t
        h = it["head"]
        if len(h) > width:
            h = h[:width - 1] + "…"
        out.append(f"  {it['marker']} {it['line']:>6}  {h}")
    return "\n".join(out)


def fmt_keywords(gaps, kws):
    out = []
    by_tier = defaultdict(list)
    for kw in kws:
        if kw in gaps:
            worst = min(gaps[kw], key=lambda p: TIERS.index(p[0]))[0]
            by_tier[worst].append((kw, sorted({ln for _, ln in gaps[kw]})))
    for t in TIERS:
        if by_tier[t]:
            cells = ", ".join(f"{kw}({','.join(map(str, lns))})" for kw, lns in by_tier[t])
            out.append(f"{t:7} {len(by_tier[t]):3}  {cells}")
    none = [kw for kw in kws if kw not in gaps]
    out.append(f"\nno open gap {len(none):3}  of {len(kws)} — NOT verified: no open item names them; "
               "step (c)'s `subject:` tag is what turns this into a scored column")
    return "\n".join(out)


FOOTER = ("**\"No open gap\" is not \"verified\".** It means no open TODO item names the "
          "keyword; the column that would mean something — is the keyword's behaviour "
          "differentially scored by a row that goes red if it breaks — is step (c) of the "
          "per-keyword-table item and does not exist yet.")


def fmt_markdown(its, kws):
    """The same table as a document -- the go-public status page in embryo.

    Joost, 2026-09-10: *"this table will also be very valuable if we eventually
    go public, because if we wait till everything is 100% correct that will be a
    _long_ time."* One source, two renderings; the honesty footer travels with
    both.
    """
    out = ["# zerobas — priority-tier status", "",
           "Generated by `make tiers ARGS=--markdown` from the `🎚️` tag on every open "
           "`TODO.md` item and the keyword table `basic/kwtable.inc` (plus the keywords "
           "filed as missing). Regenerate; never edit.", "",
           "| tier | meaning | open items |", "|---|---|---|"]
    meaning = {"TIER 1": "works correctly in the happy path", "TIER 2": "works in reasonable time",
               "TIER 3": "handles the most common error situations",
               "TIER 4": "faster than or on par with the reference",
               "TIER 5": "handles every error situation correctly"}
    counts = dict(summary(its))
    for t in TIERS:
        out.append(f"| {t} | {meaning[t]} | {counts.get(t, 0)} |")
    out += ["", f"{len(its)} open items in all; {sum(counts.get(c, 0) for c in CLASSES)} are "
            "apparatus, ROM budget, standing rulings or other (not keyword work).", "",
            "## Keywords with a known open gap, by worst tier", "",
            "| tier | n | keywords (TODO.md line) |", "|---|---|---|"]
    gaps = kw_gaps(its, kws)
    by_tier = defaultdict(list)
    for kw in kws:
        if kw in gaps:
            worst = min(gaps[kw], key=lambda p: TIERS.index(p[0]))[0]
            by_tier[worst].append(f"`{kw}` ({', '.join(str(l) for l in sorted({ln for _, ln in gaps[kw]}))})")
    for t in TIERS:
        if by_tier[t]:
            out.append(f"| {t} | {len(by_tier[t])} | {', '.join(by_tier[t])} |")
    none = [kw for kw in kws if kw not in gaps]
    out += ["", f"**{len(none)} of {len(kws)} keywords have no open gap.** " + FOOTER, "",
            "## Open keyword-tier items", "", "| tier | marker | line | item |", "|---|---|---|---|"]
    keep = [it for it in its if base_tier(it["tier"]) in TIERS]
    keep.sort(key=lambda it: (TIERS.index(base_tier(it["tier"])), it["line"]))
    for it in keep:
        h = it["head"].replace("|", "\\|")
        out.append(f"| {base_tier(it['tier'])} | {it['marker']} | {it['line']} | {h} |")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--keywords", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--markdown", action="store_true",
                    help="the same table as a document (status page)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    its = items(open(TODO, encoding="utf-8").read())
    kws = keywords()
    if a.markdown:
        sys.stdout.write(fmt_markdown(its, kws))
        return 0
    print("PRIORITY TIERS — open items in TODO.md (recounted now, never quoted)\n")
    for t, n in summary(its):
        print(f"  {t:10} {n:3}")
    print(f"  {'open':10} {len(its):3}    keywords: {len(kws)} "
          f"({len(kwtable_keywords())} in kwtable.inc + {len(kws) - len(kwtable_keywords())} filed as missing)")
    if a.keywords:
        print("\nKEYWORDS with an OPEN item naming them, by worst tier (item lines in brackets):\n")
        print(fmt_keywords(kw_gaps(its, kws), kws))
    else:
        print(fmt_items(its, tiers_only=not a.all))
        if not a.all:
            print(f"\n({sum(1 for it in its if base_tier(it['tier']) not in TIERS)} "
                  "APPARATUS/BUDGET/STANDING/OTHER items hidden — `--all` shows them; "
                  "`--keywords` for the per-keyword view)")
    return 0


def selftest():
    fake = """## Open — x
- [ ] 🔴 **`LOF` RETURNS −256 FOR A BIG FILE — and `PUT#1,255`
      extends it.** see also `CLEAR` in passing.
      🎚️ TIER 1 — happy path: `LOF`
      🤖 AUTONOMOUS — x.
- [ ] ⚠️ **A GATE THING** the word AND and KEY appear here unbackticked.
      🎚️ APPARATUS — gates
      🙋 NEEDS-JOOST — y.
- [ ] 🔴 **NESTED `DEF FN` DEPTH**
      🎚️ TIER 5 — depth
      ~~🙋 NEEDS-JOOST — old~~
      🤖 AUTONOMOUS — z.
- [ ] **UNTAGGED ONE**
      🤖 AUTONOMOUS — q.
## Next
- [ ] **NOT IN OPEN SECTION BUT STILL AN ITEM**
      🎚️ TIER 3 — e
      🤖 AUTONOMOUS — w.
"""
    its = items(fake)
    ok = True
    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond
    arm("S1 five open items parsed", len(its) == 5)
    arm("S2 tiers read from the 🎚️ line", [it["tier"] for it in its] ==
        ["TIER 1", "APPARATUS", "TIER 5", "UNTAGGED", "TIER 3"])
    arm("S3 a struck marker is not the marker", its[2]["marker"] == "🤖")
    arm("S4 headline spans lines and drops the bold", its[0]["head"].startswith("🔴 `LOF` RETURNS −256"))
    kws = ["LOF", "PUT", "AND", "KEY", "DEF", "FN", "ZZZ", "CLEAR"]
    g = kw_gaps(its, kws)
    arm("S5 backticked keywords map to their item's tier", g.get("LOF") == {("TIER 1", 2)} and g.get("PUT") == {("TIER 1", 2)})
    arm("S6 `DEF FN` yields both keywords", g.get("DEF") == {("TIER 5", 9)} and g.get("FN") == {("TIER 5", 9)})
    arm("S7 unbackticked English words (AND, KEY) do NOT match", "AND" not in g and "KEY" not in g)
    arm("S8 a keyword with no item is absent from gaps, present in the footer",
        "ZZZ" not in g and "no open gap   4  of 8" in fmt_keywords(g, kws))
    arm("S9 summary counts UNTAGGED separately", ("UNTAGGED", 1) in summary(its))
    arm("S11 a keyword named only in the BODY does not count", "CLEAR" not in g)
    arm("S10 the real kwtable parses to 150+ keywords", len(kwtable_keywords()) >= 150)
    landed = [k for k in KNOWN_MISSING if k in kwtable_keywords()]
    arm("S12 no KNOWN_MISSING keyword has landed in kwtable.inc (else delete it from the list)"
        + (f" -- LANDED: {landed}" if landed else ""), not landed)
    arm("S13 the denominator is kwtable + the missing set", len(keywords()) == len(kwtable_keywords()) + len(KNOWN_MISSING))
    md = fmt_markdown(its, kws)
    arm("S14 markdown carries the summary, the keyword rows and the honesty footer",
        "| TIER 1 | works correctly in the happy path | 1 |" in md
        and "`LOF` (2)" in md and "not \"verified\"" in md)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
