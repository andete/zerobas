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
KNOWN_MISSING = []     # the eight all landed by 2026-09-11 (D-LOC, D-DSKIO, D-COPY); S12 said so     # TODO.md, "EIGHT KEYWORDS THE REFERENCE TOKENISES"


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


NESTED = re.compile(r"^[ \t]+- \[ \] ")


def nested_open(text):
    """Indented `- [ ]` lines: open work INSIDE a block, which the marker gate,
    the 🎚️ tags and this table all key on top-level items and therefore cannot
    see. 2026-09-10: `LOC(#n)` (a missing keyword with its oracle measured) and
    the second-disk-channel residual under `MAXFILES` both sat here while the
    keyword view called LOC "no known gap". Reported, never silently counted."""
    return [(k + 1, l.strip()[6:80]) for k, l in enumerate(text.split("\n")) if NESTED.match(l)]


def summary(its):
    counts = defaultdict(int)
    for it in its:
        counts[base_tier(it["tier"])] += 1
    rows = [(t, counts.get(t, 0)) for t in TIERS] + [(c, counts.get(c, 0)) for c in CLASSES]
    if counts.get("UNTAGGED"):
        rows.append(("UNTAGGED", counts["UNTAGGED"]))
    return rows


def item_keywords(it, kwset):
    """The keywords an item is ABOUT, sorted so two items about the same set
    list it identically.

    🎯 A DECLARATION BEATS AN INFERENCE. If the 🎚️ line backticks any keyword,
    or says "no single keyword", it is the item's declared subject and the
    headline is NOT scanned -- the same rule step (c)'s `subject:` tag will
    apply to rows. Only an item whose 🎚️ line declares nothing falls back to
    its headline. (The stack item's headline names `DEF FN` as the SYMPTOM; the
    finding is every expression, and the union rule kept filing it under the
    symptom.)"""
    def scan(text):
        found = set()
        for tok in TICK.findall(text):
            for w in WORD.findall(tok):
                if w in kwset:
                    found.add(w)
        return sorted(found)
    declared = scan(it["tag"])
    if declared or "no single keyword" in it["tag"]:
        return declared
    return scan(it["head"])


# the 🎚️ prose without its tier-kind prefix ("happy path: ", "common error: ")
KIND = re.compile(r"^(happy path|common error|on-par speed|reasonable time|[a-z][^:`]{0,40}): ")


def what_is_open(it):
    return KIND.sub("", it["tag"]).strip() or it["head"]


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
        for w in item_keywords(it, kwset):
            gaps[w].add((base_tier(it["tier"]), it["line"]))
    return {k: v for k, v in gaps.items() if v}    # a plain dict: a lookup must not CREATE a key


# The tier a keyword has REACHED, from the open gaps alone: an open TIER n item
# naming it means it has not reached n, so it stands at n-1 (0 = happy path
# broken or keyword missing). No open gap means NO KNOWN GAP -- not a tier. The
# "reached" column becomes a measurement only when gate rows declare their
# keyword (step (c)); until then this is the honest ceiling on what is known.
# 🔴 TIER 0 = NO TIER ESTABLISHED (Joost, 2026-09-13: "let's call no tier
# established tier 0 to make it clear"). EVERY keyword in this tree is TIER 0
# today, and the text after it says only what is KNOWN AGAINST it -- an open item,
# a gap the sweep sees, or how many rows agree. None of that is attainment:
# attainment needs BREADTH (enough agreement points to cover a verb's real forms)
# and NON-VACUITY (a mutation check showing the rows would go red if it broke),
# and no keyword has been shown to have either. The old labels read as a ladder
# ("1 — happy path only") and implied a rung had been climbed.
REACHED = {1: "TIER 0 — open TIER 1 item (happy path broken or keyword MISSING)",
           2: "TIER 0 — open TIER 2 item (works, but not in reasonable time)",
           3: "TIER 0 — open TIER 3 item (a common error situation is wrong)",
           4: "TIER 0 — open TIER 4 item (slower than the reference)",
           5: "TIER 0 — open TIER 5 item (an exhaustive error case is wrong)",
           "kwgap": "TIER 0 — a gap kwsweep SEES that no open item files (DIVERGENT/MISSING)",
           # 🔴 NOT TIERS (Joost, 2026-09-13: "kwsweep SUPPORTED is not evidence
           # for tier 1"). A SUPPORTED verdict says zerobas and the reference
           # produced the same output FOR ONE INPUT. That is one agreement point,
           # not a reached tier -- and agreement can be vacuous: `CSAVE` once
           # scored SUPPORTED on an EMPTY capture, and four of the five
           # silent-failure modes are ways two machines agree about nothing.
           "kw1": "TIER 0 — no known gap; ONE happy-path row agrees",
           "kw3": "TIER 0 — no known gap; a happy-path AND an error row agree"}
GROUP_ORDER = ["kwgap", 1, 2, 3, 4, 5, "kw1", "kw3", None]


KWSWEEP_PIN = os.path.join(ROOT, "build", "kwsweep-verdicts.json")


def stmt_keyword(stmt, kwset):
    """The keyword a kwsweep row is ABOUT: the first keyword token in its crunch
    statement (`a=abs(-5)` -> ABS, `a$=mid$("hi",1,1)` -> MID$, `A=1` -> None)."""
    for w in WORD.findall(stmt.upper()):
        if w in kwset:
            return w
    return None


def kwsweep_evidence(kws, path=KWSWEEP_PIN):
    """keyword -> kwsweep verdict from the last battery's pin, or {} if none.
    WEAK rows are excluded, as kwsweep's own tally excludes them."""
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except (OSError, ValueError):
        return {}
    kwset = set(kws)
    out = {}
    for key, r in pin.get("rows", {}).items():
        if r.get("weak"):
            continue
        kw = stmt_keyword(r.get("stmt", ""), kwset)
        if kw and kw not in out:
            out[kw] = r["verdict"]
    return out


def kwsweep_t3(kws, path=KWSWEEP_PIN):
    """The keywords a SUPPORTED `PROVES-T3:` row speaks for.

    🎚️ TIER 3 is "handles the most common error situations", and a row that
    declares `PROVES-T3:` is claiming to exercise one — a claim the sweep then
    SCORES against the reference like any other row. A row that merely exists
    proves TIER 1; this is the rung above it, and it is separate evidence rather
    than a stronger reading of the same row (D-KWT3, Joost 2026-09-13: "add more
    tests for each keyword proving the tier")."""
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except (OSError, ValueError):
        return set()
    kwset = set(kws)
    out = set()
    for _key, r in pin.get("rows", {}).items():
        if r.get("weak") or r.get("proves") != "T3" or r.get("verdict") != "SUPPORTED":
            continue
        kw = stmt_keyword(r.get("stmt", ""), kwset)
        if kw:
            out.add(kw)
    return out


def keyword_tiers(its, kws, evidence=None):
    """keyword -> (worst open tier 1..5 or None, sorted item lines, evidence).

    `evidence` is the kwsweep verdict for the keyword, if any. It only ever
    speaks for a keyword with NO open item: a SUPPORTED verdict there is
    "TIER 1 reached (kwsweep)"; a DIVERGENT/MISSING verdict there is a gap
    nobody has filed, and is printed as exactly that."""
    gaps = kw_gaps(its, kws)
    ev = kwsweep_evidence(kws) if evidence is None else evidence
    out = {}
    for kw in kws:
        if kw in gaps:
            worst = min(TIERS.index(t) for t, _ in gaps[kw]) + 1
            out[kw] = (worst, sorted({l for _, l in gaps[kw]}), ev.get(kw))
        else:
            out[kw] = (None, [], ev.get(kw))
    return out


def reached_group(g, e, t3=False):
    """The bucket a keyword prints under, from its gap tier and its evidence."""
    if g is not None:
        return g                                  # 1..5: stuck below that tier
    if e == "SUPPORTED":
        # A PROVES-T3 row is the rung above a happy-path row: same keyword, a
        # SECOND row that scored an ERROR situation against the reference.
        return "kw3" if t3 else "kw1"
    if e in ("DIVERGENT", "MISSING", "SILENT-GAP", "EXTRA"):
        return "kwgap"                            # a gap kwsweep sees and nobody filed
    return None                                   # no known gap, no evidence


def fmt_items(its, kws, tiers_only=True, width=70):
    """Keyword FIRST, prose last (Joost, 2026-09-10: "I would expect the keyword
    to be prominent, now I have to find it in the item prose")."""
    kwset = set(kws)
    keep = [it for it in its if (base_tier(it["tier"]) in TIERS) or not tiers_only]
    order = TIERS + CLASSES + ["UNTAGGED"]
    rows = []
    for it in keep:
        k = item_keywords(it, kwset)
        rows.append((order.index(base_tier(it["tier"])), k[0] if k else "~", it["line"], it, k))
    rows.sort(key=lambda r: r[:3])
    # the keyword column is the point of the view, so it is never truncated:
    # sized to the longest list in THIS run (the first cut cut "ATTR$ CMD COPY
    # DSKI$ D" at 22 characters, which defeats the reason the column exists)
    kwcol = max([len(" ".join(k)) for *_, k in rows] + [1])
    out, last = [], None
    for _, _, _, it, k in rows:
        t = base_tier(it["tier"])
        if t != last:
            out.append(f"\n{t}")
            last = t
        kw = " ".join(k) or "—"
        w = what_is_open(it)
        if len(w) > width:
            w = w[:width - 1] + "…"
        out.append(f"  {kw:{kwcol}} {it['marker']} {it['line']:>6}  {w}")
    return "\n".join(out)


def fmt_keywords(its, kws, evidence=None):
    kt = keyword_tiers(its, kws, evidence)
    t3 = kwsweep_t3(kws)
    groups = defaultdict(list)
    for kw, (g, _, e) in kt.items():
        groups[reached_group(g, e, kw in t3)].append(kw)
    out = []
    for g in GROUP_ORDER:
        if g is None or not groups[g]:
            continue
        out.append(f"{REACHED[g]:58} {len(groups[g]):3}  " + " ".join(sorted(groups[g])))
    none = sorted(groups[None])
    out.append(f"{'no known gap (NOT a tier -- no item, no kwsweep row)':58} {len(none):3}  " + " ".join(none))
    out.append("")
    ev_n = sum(1 for _, (_, _, e) in kt.items() if e)
    out.append(f"kwsweep evidence: {ev_n} keyword(s) from {KWSWEEP_PIN if ev_n else 'NO PIN -- run make kwsweep (it runs in every battery)'}")
    out.append(f"{len(kws)} keywords. A keyword with no open item and no kwsweep row has NO KNOWN GAP, "
               "which is not a reached tier: the reached column is measured only when gate rows "
               "declare their keyword (step (c)).")
    return "\n".join(out)


FOOTER = ("**\"No open gap\" is not \"verified\", and a kwsweep verdict is NOT a reached "
          "tier** (Joost, 2026-09-13). `SUPPORTED` "
          "means zerobas and the reference produced the same output *for one input* — one "
          "agreement point. It is not \"the happy path works\", and agreement can be "
          "vacuous: `CSAVE` once scored SUPPORTED on an empty capture, and four of the "
          "five silent-failure modes are ways two machines agree about nothing. "
          "**Every row above is TIER 0**: nothing is established. An open TIER n item says a "
          "defect is FILED at n, not that n-1 was reached; a row that agrees is one agreement "
          "point. Establishing a tier needs BREADTH — agreement points covering a verb's real "
          "forms, not one expression — AND NON-VACUITY, a mutation check showing those rows go "
          "red if the keyword breaks. Neither has been demonstrated for any keyword.")


def fmt_markdown(its, kws, evidence=None, t3=None):
    """🔴 `evidence`/`t3` are INJECTABLE because S14 was not hermetic: it built its
    markdown from the LIVE build/kwsweep-verdicts.json, so the expected `LOF` row
    changed the moment a sweep re-ran and gave LOF a verdict (it gained a
    `; kwsweep SUPPORTED` suffix). The test had been passing on the pin's contents,
    not on the formatter's behaviour [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]."""
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
            "## Every keyword and its tier", "",
            "**Every keyword is TIER 0: no tier is established for any of them.** The text "
            "beside each says only what is KNOWN AGAINST it — an open item at tier n, a gap "
            "the sweep sees, or how many rows agree. None of that is attainment.", "",
            "| established tier, and what is known against it | n | keywords |", "|---|---|---|"]
    kt = keyword_tiers(its, kws, evidence)
    t3 = kwsweep_t3(kws) if t3 is None else t3
    groups = defaultdict(list)
    for kw, (g, _, e) in kt.items():
        groups[reached_group(g, e, kw in t3)].append(kw)
    for g in GROUP_ORDER:
        if g is None or not groups[g]:
            continue
        out.append(f"| {REACHED[g]} | {len(groups[g])} | " + " ".join(f"`{k}`" for k in sorted(groups[g])) + " |")
    none = sorted(groups[None])
    out.append(f"| no known gap (no item, no kwsweep row — unverified) | {len(none)} | " + " ".join(f"`{k}`" for k in none) + " |")
    out += ["", FOOTER, "", "### Alphabetical", "", "| keyword | reached | evidence |", "|---|---|---|"]
    for kw in sorted(kws):
        g, lines, e = kt[kw]
        grp = reached_group(g, e, kw in t3)
        if grp is None:
            out.append(f"| `{kw}` | TIER 0 | no known gap, no row |")
        elif grp == "kw1":
            out.append(f"| `{kw}` | TIER 0 | no known gap; 1 row agrees |")
        elif grp == "kw3":
            # D-KWT3: the rung above kw1 -- a SECOND row, scoring an error
            # situation. `g` is None for both, so this arm must come before the
            # one below, which indexes REACHED by the GAP tier.
            out.append(f"| `{kw}` | TIER 0 | no known gap; 2 rows agree (happy + error) |")
        elif grp == "kwgap":
            out.append(f"| `{kw}` | GAP, unfiled | kwsweep {e} and no open item |")
        else:
            # the cell is always TIER 0 now; what varies is the text beside it
            out.append(f"| `{kw}` | TIER 0 | open TIER {g} item, TODO.md {', '.join(map(str, lines))}"
                       + (f"; kwsweep {e}" if e else "") + " |")
    out += ["",
            "## Open items, keyword first", "",
            "| keyword | tier | who | what is open | TODO.md |", "|---|---|---|---|---|"]
    kwset = set(kws)
    rows = []
    for it in its:
        if base_tier(it["tier"]) in TIERS:
            k = item_keywords(it, kwset)
            rows.append((TIERS.index(base_tier(it["tier"])), k[0] if k else "~", it["line"], it, k))
    rows.sort(key=lambda r: r[:3])
    for _, _, _, it, k in rows:
        kw = ", ".join(f"`{x}`" for x in k) or "—"
        w = what_is_open(it).replace("|", "\\|")
        out.append(f"| {kw} | {base_tier(it['tier'])} | {it['marker']} | {w} | {it['line']} |")
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
    nest = nested_open(open(TODO, encoding="utf-8").read())
    if nest:
        print(f"  \u26a0\ufe0f {len(nest)} NESTED open checkbox(es) carry no tier and no marker -- "
              "read them; a keyword they name is NOT 'no known gap':")
        for ln, head in nest:
            print(f"       {ln:>6}  {head}")
    print(f"  {'open':10} {len(its):3}    keywords: {len(kws)} "
          f"({len(kwtable_keywords())} in kwtable.inc + {len(kws) - len(kwtable_keywords())} filed as missing)")
    if a.keywords:
        print("\nEVERY KEYWORD, by the tier it has reached (from the open gaps):\n")
        print(fmt_keywords(its, kws))
    else:
        print(fmt_items(its, kws, tiers_only=not a.all))
        if not a.all:
            print(f"\n({sum(1 for it in its if base_tier(it['tier']) not in TIERS)} "
                  "APPARATUS/BUDGET/STANDING/OTHER items hidden — `--all` shows them; "
                  "`--keywords` for the per-keyword view)")
    return 0


def selftest():
    fake = """## Open — x
- [ ] 🔴 **`LOF` RETURNS −256 FOR A BIG FILE — and `PUT#1,255`
      extends it.** see also `CLEAR` in passing.
      🎚️ TIER 1 — happy path: `LOF` and `PUT#1,255`
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
        "ZZZ" not in g and "no known gap (NOT a tier -- no item, no kwsweep row)" in fmt_keywords(its, kws)
        and fmt_keywords(its, kws).split("\n")[-1].startswith("8 keywords"))
    arm("S9 summary counts UNTAGGED separately", ("UNTAGGED", 1) in summary(its))
    arm("S11 a keyword named only in the BODY does not count", "CLEAR" not in g)
    arm("S10 the real kwtable parses to 150+ keywords", len(kwtable_keywords()) >= 150)
    arm("S23 a nested `- [ ]` is reported with its line, a top-level one is not",
        nested_open("- [ ] top\n      - [ ] **inner** x\n- [x] done\n") == [(2, "**inner** x")])
    landed = [k for k in KNOWN_MISSING if k in kwtable_keywords()]
    arm("S12 no KNOWN_MISSING keyword has landed in kwtable.inc (else delete it from the list)"
        + (f" -- LANDED: {landed}" if landed else ""), not landed)
    arm("S13 the denominator is kwtable + the missing set", len(keywords()) == len(kwtable_keywords()) + len(KNOWN_MISSING))
    its[2]["tag"] = "TIER 5 — depth (no single keyword)"
    arm("S16 a tag that says 'no single keyword' overrides a headline that names one",
        item_keywords(its[2], set(kws)) == [])
    its[2]["tag"] = "TIER 5 — `DIM` depth"
    arm("S17 a tag that declares a keyword wins over the headline's", item_keywords(its[2], set(kws + ["DIM"])) == ["DIM"])
    its[2]["tag"] = "TIER 5 — depth"
    arm("S18 a tag that declares nothing falls back to the headline", item_keywords(its[2], set(kws)) == ["DEF", "FN"])
    arm("S15 an item's keywords are sorted and the tier-kind prefix is stripped from its prose",
        item_keywords(its[0], set(kws)) == ["LOF", "PUT"] and what_is_open(its[0]) == "`LOF` and `PUT#1,255`")
    kt = keyword_tiers(its, kws, evidence={"ZZZ": "SUPPORTED", "AND": "DIVERGENT", "LOF": "SUPPORTED"})
    arm("S19 a keyword's reached tier is one below its worst open gap; no gap is None",
        kt["LOF"][:2] == (1, [2]) and kt["DEF"][:2] == (5, [9]) and kt["ZZZ"][:2] == (None, []))
    arm("S21 kwsweep evidence upgrades a no-gap keyword to reached-1, surfaces an unfiled gap, and never overrides an open item",
        reached_group(*kt["ZZZ"][::2]) == "kw1" and reached_group(*kt["AND"][::2]) == "kwgap"
        and reached_group(*kt["LOF"][::2]) == 1)
    arm("S22 a kwsweep row's keyword is the first keyword token of its statement",
        stmt_keyword("a=abs(-5)", {"ABS", "A"} - {"A"}) == "ABS" and stmt_keyword('a$=mid$("hi",1,1)', {"MID$"}) == "MID$"
        and stmt_keyword("A=1", {"ABS"}) is None)
    arm("S20 the full list names every keyword exactly once", sorted(kt) == sorted(kws))
    md = fmt_markdown(its, kws, evidence={}, t3=set())
    _s14 = [("summary row", "| TIER 1 | works correctly in the happy path | 1 |" in md),
            ("LOF row", "| `LOF` | TIER 0 | open TIER 1 item, TODO.md 2 |" in md),
            ("ZZZ row", "| `ZZZ` | TIER 0 | no known gap, no row |" in md),
            ("honesty footer", "not \"verified\"" in md),
            ("open-items row", "| `LOF`, `PUT` | TIER 1 | 🤖 | `LOF` and `PUT#1,255` | 2 |" in md)]
    for _n, _c in _s14:
        if not _c:
            print("   S14 clause failed:", _n)
    arm("S14 markdown carries the summary, the keyword rows and the honesty footer",
        all(c for _, c in _s14))
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
