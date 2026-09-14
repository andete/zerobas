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
           "kw1c": "TIER 0 — no known gap; ONE row agrees, and it is CONNECTED "
                   "(a knife cut makes it notice)",
           "kw3": "TIER 0 — no known gap; a happy-path AND an error row agree",
           "kw3c": "TIER 0 — no known gap; two rows agree, and the keyword is "
                   "CONNECTED (a knife cut makes it notice)",
           "t1": "TIER 1 — REACHED: knife-proven CONNECTED, every authored FORM "
                 "covered by an agreeing row, and no open item",
           # 🔴 NOT A GAP. MSX1 has no bare `ON`, `DEF`, `GET`, `PUT` or `USING`
           # statement -- each exists only inside a composite, so "no row of its
           # own" is the truth about the language, not a hole. `INPUT` is NOT in
           # this bucket although it lost its rows the same way: bare console
           # `INPUT "x";A$` is real and has never had a row, and that IS a hole.
           "kwcomp": "TIER 0 — no BARE statement form; exercised only as a "
                     "composite (see the composite section)",
           # 🎚️ Joost, 2026-09-14: "Drop them and mark them". A particle is a
           # TOKEN the reference tokenises, never a statement a user can write, so
           # it is counted in the TOKEN denominator and marked here rather than
           # silently vanishing from the sheet.
           "kwpart": "NOT A STATEMENT — a syntax particle of another statement; "
                     "counted in the TOKEN denominator, not the STATEMENT one"}
GROUP_ORDER = ["t1", "kwgap", 1, 2, 3, 4, 5, "kw1", "kw1c", "kw3", "kw3c",
               "kwcomp", "kwpart", None]


KWSWEEP_PIN = os.path.join(ROOT, "build", "kwsweep-verdicts.json")
KNIFE_PIN = os.path.join(ROOT, "scratchpad", "kwknife-connected.json")


def knife_connected(path=KNIFE_PIN):
    """The keywords a knife cut has shown a row NOTICES (D-KWKNIFE).

    🔴 CONNECTED IS NOT VERIFIED. The cut disables the keyword's dispatch
    entirely, so a row that notices is CONNECTED to it — a total failure is seen.
    It says nothing about whether a SUBTLE defect would be, and nothing about
    BREADTH. Read as attainment it would repeat exactly the mistake TIER 0 exists
    to correct.

    🔴 AND THE READER NOW CHECKS THE FINGERPRINT THE WRITER RECORDS (D-KWPINLOSS
    2026-09-13). `kwknife.record`'s own docstring promised that *"a pin whose
    fingerprint no longer matches the built ROM describes a machine that no longer
    exists, and the reader says so"* — and this reader did not read the field at
    all. The writer's guarantee and the reader's behaviour were two sections of one
    mechanism disagreeing on the load-bearing rule, with the docstring carrying the
    half that was not implemented.
    🔴 A DEGENERATE PIN IS REFUSED, NOT AVERAGED IN. Measured the same day: a
    `make kwcover` run cleaned `build/`, where this pin then lived, and the 91-
    keyword reading came back as ONE row — from which this function would have
    returned a set of size 1 and the table would have printed a perfectly plausible
    ladder. That is the `kwcover` SUITE_FLOOR failure exactly, so it gets the same
    answer: refuse, say nothing was measured, and name the command that rebuilds it.
    """
    import hashlib, json
    IMAGES = ("build/zerobas-main-eu.rom", "build/sub.rom", "build/disk.rom",
              "build/basic-reloc.rom")
    try:
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except (OSError, ValueError):
        return set()                        # no measurement, and none claimed
    rows = pin.get("rows", {})
    live = " ".join((hashlib.sha256(open(os.path.join(ROOT, p), "rb").read())
                     .hexdigest()[:8] if os.path.exists(os.path.join(ROOT, p))
                     else "ABSENT") for p in IMAGES)
    if pin.get("rom_fingerprint") not in (None, live):
        raise SystemExit(
            f"tier_table: REFUSING the knife pin at {path} — it was measured "
            f"against {pin.get('rom_fingerprint')} and the built ROMs "
            f"are now {live}. It describes a machine that no longer "
            f"exists. "
            f"Re-run `python3 scratchpad/kwknife.py --all` and `--allfn`.")
    ROW_FLOOR = 20
    if 0 < len(rows) < ROW_FLOOR:
        raise SystemExit(
            f"tier_table: REFUSING the knife pin at {path} — it holds "
            f"{len(rows)} row(s), below the floor of {ROW_FLOOR}. A full sweep "
            f"covers the whole statement and function keyword sets, so a handful "
            f"of rows is not a thin measurement, it is a DIFFERENT one (an ad-hoc "
            f"debugging run, or a pin that was destroyed and partly rewritten). "
            f"NOTHING IS CLAIMED CONNECTED — re-run `python3 "
            f"scratchpad/kwknife.py --all` and `--allfn`.")
    # 🎚️ D-KWSTMTDEN: a cut proves the STATEMENT its row is about load-bearing,
    # not only the keyword that was cut. `ON GOTO` is connected because cutting
    # `ON` made `ongoto` go red; `PRINT USING` can be connected NO OTHER WAY,
    # since `USING`'s token is not in stmt_table to cut. Both names are returned,
    # so a keyword does not lose connectedness by also speaking for a composite.
    out = {kw for kw, r in rows.items() if r.get("connected")}
    out |= {r["subject"] for r in rows.values()
            if r.get("connected") and r.get("subject")}
    # ⚠️ `rows` IS KEYED BY KEYWORD AND THE LAST CUT WINS, so its `subject` field
    # holds only the most recent one. The `subjects` map is where a keyword that
    # speaks for SEVERAL statements keeps them all -- ON alone speaks for three.
    out |= {st for st, r in pin.get("subjects", {}).items() if r.get("connected")}
    return out


def composite_names():
    """Every authored NON-KEYWORD statement name -- composites plus the ones no
    derivation can reach (`PRINT #`) -- or an empty set without kwforms."""
    try:
        import kwforms
    except ImportError:
        return set()
    return kwforms.subject_names()


def known_subject(name, kwset):
    """True when `name` is something this table can actually score: a keyword in
    the 159-entry table, or an authored composite statement name."""
    return name in kwset or name in composite_names()


def stmt_subject(stmt, kwset, declared=None):
    """The STATEMENT a crunch body is about: a composite name, else the keyword.

    🔴 A DECLARED SUBJECT WINS, BECAUSE DERIVATION IS WRONG ON REAL ROWS -- see
    `basic_probe_kwsweep.row_subject`, which lists the three shapes it cannot see
    (`using`'s body never says PRINT; `#` is punctuation; the exec line is
    apparatus). A declared name that this table cannot score is REFUSED OUT LOUD
    and the derived subject is used instead: a typo must not silently move a row
    off its keyword and into a bucket nothing ever counts.

    🎚️ D-KWCOMPOSITE (Joost, 2026-09-14). `stmt_keyword` below returns the FIRST
    keyword token, which is the wrong granularity for a composite: `ON KEY GOSUB`
    and `ON n GOTO` share nothing but a token, and `LINE INPUT` and
    `LINE (x,y)-(x,y)` are different statements entirely -- so tiering the first
    token would let a graphics row vouch for console input. It is also what let
    `ON` reach TIER 1 on three rows speaking for three of its EIGHT composites.
    ⚠️ The composite is matched over EVERY keyword in the body, not the first two
    adjacent ones: `ON 2 GOTO 20,30` has an expression between its two keywords."""
    if declared:
        if known_subject(declared, kwset):
            return declared
        print("\u26a0\ufe0f  tier_table: row declares SUBJECT:%s, which is neither a "
              "keyword in the table nor an authored composite -- IGNORED, the "
              "subject is derived from the crunch body instead" % declared,
              file=sys.stderr)
    try:
        import kwforms
    except ImportError:
        return stmt_keyword(stmt, kwset)
    words = [w for w in WORD.findall(stmt.upper()) if w in kwset]
    return kwforms.composite_name(words) or stmt_keyword(stmt, kwset)


def stmt_keyword(stmt, kwset):
    """The keyword a kwsweep row is ABOUT: the first keyword token in its crunch
    statement (`a=abs(-5)` -> ABS, `a$=mid$("hi",1,1)` -> MID$, `A=1` -> None)."""
    for w in WORD.findall(stmt.upper()):
        if w in kwset:
            return w
    return None


def pin_rows(path=KWSWEEP_PIN):
    """(n_rows, why) for the kwsweep pin -- the INPUT every evidence column reads.

    🔴 THE GENERATOR PRODUCED A PLAUSIBLE FULL DOCUMENT FROM AN EMPTY PIN, and
    nothing said so (D-TIERDOC, measured 2026-09-14): every `kwsweep_*` reader
    swallows OSError/ValueError and returns {}, so a missing or half-written pin
    renders as "139 keywords have no row" and the four TIER 1 awards silently
    disappear. That is the documented worst shape an instrument can have -- a
    plausible table from an input it misread -- and the answer is the same one
    `kwcover` uses: REFUSE on a degenerate input rather than answer from it."""
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except OSError as e:
        return 0, f"cannot read {path}: {e}"
    except ValueError as e:
        return 0, f"{path} is not valid JSON (half-written?): {e}"
    n = len(pin.get("rows", {}))
    return n, ("written %s, %d row(s)" % (pin.get("written", "?"), n) if n
               else f"{path} holds NO rows")


def kwsweep_evidence(kws, path=KWSWEEP_PIN):
    """STATEMENT -> kwsweep verdict from the last battery's pin, or {} if none.
    WEAK rows are excluded, as kwsweep's own tally excludes them.

    🎚️ KEYED BY SUBJECT, NOT BY FIRST KEYWORD (D-KWSUBJECT, 2026-09-14). Joost:
    "bare print and print # and print using have a different function". So the two
    `PRINT USING` rows are evidence for `PRINT USING` and for NOTHING ELSE -- they
    used to be credited to `USING`, a token that is not even in `stmt_table` and
    can never be cut, which made the table read as if USING had been exercised.
    ⚠️ THIS MAKES THE TABLE LOOK WORSE ON PURPOSE. `USING`, `INPUT` and `GET` lose
    the only rows they had; the rows are not gone, they moved to the statement
    they actually drive, which the composite section renders separately. A keyword
    whose evidence was really a composite's had no evidence of its own."""
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
        kw = stmt_subject(r.get("stmt", ""), kwset, r.get("subject"))
        if kw and kw not in out:
            out[kw] = r["verdict"]
    return out


def kwsweep_forms(kws, path=KWSWEEP_PIN):
    """keyword -> the set of DISTINCT `FORM:` names its SUPPORTED rows declare.

    🔴 THIS EXISTS BECAUSE `kwsweep_evidence` ABOVE KEEPS ONE ROW PER KEYWORD AND
    THROWS THE REST AWAY (`if kw not in out`). That is right for a verdict -- the
    column says whether the keyword has an agreeing row -- but it means the table
    could never count anything, and 33 breadth rows written on 2026-09-13/14 were
    invisible to it beyond the first per keyword.
    🎚️ Only SUPPORTED rows count. A DIVERGENT row exercises the form and FAILS it,
    which is the opposite of evidence, and a WEAK row is excluded here for the same
    reason kwsweep's own tally excludes it."""
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except (OSError, ValueError):
        return {}
    kwset = set(kws)
    out: dict[str, set] = {}
    for key, r in pin.get("rows", {}).items():
        if r.get("weak") or r.get("verdict") != "SUPPORTED" or not r.get("form"):
            continue
        kw = stmt_subject(r.get("stmt", ""), kwset, r.get("subject"))
        if kw:
            out.setdefault(kw, set()).add(r["form"])
    return out


def tier1_status(kw, forms_seen, connected, has_open_item):
    """Joost's TIER 1 rule (2026-09-14): CONNECTED + N distinct FORMS + no open item.

    Returns (reached, why) where reached is True only when all three hold.
    ⚠️ A keyword with NO authored form list is UNRATED, never satisfied -- absence
    of a bar is not a bar of zero (the `kwcover` refusal, applied to this table)."""
    try:
        import kwforms
    except ImportError:
        return False, "no form table"
    need = kwforms.forms_for(kw)
    if not need:
        return False, "UNRATED — no authored form list"
    missing = [f for f in need if f not in forms_seen]
    if has_open_item:
        return False, "an open TIER 1 item stands against it"
    if not connected:
        return False, "not knife-proven CONNECTED"
    if missing:
        return False, ("%d/%d forms — missing %s"
                       % (len(need) - len(missing), len(need), " ".join(missing)))
    return True, "CONNECTED, %d/%d forms, no open item" % (len(need), len(need))


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


def particles():
    """Syntax particles -- see kwforms.PARTICLES. Tokens, never statements."""
    try:
        import kwforms
    except ImportError:
        return frozenset()
    return kwforms.PARTICLES


def operators():
    """Expression operators -- see kwforms.OPERATORS. Never statements either, but
    each has behaviour of its own, so they STAY in the statement denominator."""
    try:
        import kwforms
    except ImportError:
        return frozenset()
    return kwforms.OPERATORS


def no_bare_form():
    """Keywords MSX1 has no bare statement form for -- see kwforms.NO_BARE_FORM."""
    try:
        import kwforms
    except ImportError:
        return frozenset()
    return kwforms.NO_BARE_FORM


def reached_group(g, e, t3=False, conn=False, tier1=False, nobare=False,
                  particle=False):
    """The bucket a keyword prints under, from its gap tier and its evidence.

    🎚️ `tier1` is Joost's rule satisfied (2026-09-14): CONNECTED + N distinct
    FORMS + no open item. It is the ONLY way this function returns anything but a
    TIER 0 bucket, and it is passed in rather than recomputed here so the caller
    owns the three clauses -- the table must never award a tier from evidence it
    inferred on the spot."""
    # 🔴 BEFORE EVERY OTHER ARM. A particle is not a statement, so no tier it
    # might otherwise land in means anything -- and a particle that happened to
    # have an agreeing row would otherwise print as "1 row agrees" beside real
    # statements, which is the claim this class exists to stop making.
    if particle:
        return "kwpart"
    if tier1:
        return "t1"
    if g is not None:
        return g                                  # 1..5: stuck below that tier
    if e == "SUPPORTED":
        # A PROVES-T3 row is the rung above a happy-path row: same keyword, a
        # SECOND row that scored an ERROR situation against the reference.
        if t3:
            return "kw3c" if conn else "kw3"
        return "kw1c" if conn else "kw1"
    if e in ("DIVERGENT", "MISSING", "SILENT-GAP", "EXTRA"):
        return "kwgap"                            # a gap kwsweep sees and nobody filed
    if nobare:
        return "kwcomp"          # no bare form exists -- a row of its own cannot
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


def statements(kws=None):
    """The STATEMENT denominator: everything a user can actually WRITE.

    🎚️ JOOST, 2026-09-14, of the composite section's "deliberately not in the
    159-keyword denominator": *"why not? They should have the same TIER and
    tests"*. He is right, and the exclusion was a PRESENTATION worry (splitting
    `ON` into eight would "inflate the count by renaming") rather than a
    correctness one.
    🎯 THE 159 IS A **TOKEN** DENOMINATOR -- basic/kwtable.inc -- and `ON ERROR
    GOTO` is ONE STATEMENT made of THREE tokens. Counting tokens is a proxy for
    "how much of MSX BASIC works" and it breaks down exactly where composites
    exist: it says `ON` is one thing to get right when it is eight.
    So there are TWO denominators, each right for its own question, and neither
    replaces the other:
      * TOKEN (159, `keywords()`): is every token in the table implemented?
        Guarded by selftest S20, which is NOT to be weakened to move a count.
      * STATEMENT (this): how much of the LANGUAGE works? 159 minus the five
        keywords with no bare statement form -- `DEF GET ON PUT USING`, which
        would otherwise double-count against their own composites -- plus the
        composite and channel statement names.
    ⚠️ A STATED IMPRECISION RATHER THAN A HIDDEN ONE: this set still counts SYNTAX
    PARTICLES (`THEN`, `TO`, `STEP`, `ELSE`, `AS`, `OFF`) as statements. They are
    not. Removing them is re-tiering the keyword umbrella, which is ruled out, so
    the count carries the flaw openly instead of being quietly adjusted."""
    kws = keywords() if kws is None else kws
    return sorted((set(kws) - set(no_bare_form()) - set(particles()))
                  | composite_names())


def tier1_statements(stmts=None, conn=None, forms=None, kws=None):
    """TIER 1 over the STATEMENT denominator -- composites included.

    ⚠️ `forms` and the open-item lookup are still computed over the KEYWORD set,
    because that is what the pin and TODO.md are keyed by; only the set being
    AWARDED over changes."""
    kws = keywords() if kws is None else kws
    stmts = statements(kws) if stmts is None else stmts
    conn = knife_connected() if conn is None else conn
    forms = kwsweep_forms(kws) if forms is None else forms
    out = set()
    for st in stmts:
        ok, _ = tier1_status(st, forms.get(st, set()), st in conn, False)
        if ok:
            out.add(st)
    return out


def blocks_tier1(entry):
    """Does this keyword_tiers entry hold an open item that blocks TIER 1?

    🔴 ONLY A TIER **1** ITEM DOES, AND READING IT AS "ANY OPEN ITEM" WAS MY
    MISTAKE (corrected 2026-09-14). Joost's rule says "no open item", and Joost's
    TIER LADDER says what the tiers mean: HAPPY PATH -> REASONABLE TIME -> COMMON
    ERRORS -> ON-PAR SPEED -> EVERY ERROR. **An item at tier n says tier n is not
    reached. It says nothing about tier n-1.** A keyword that is SLOWER THAN THE
    REFERENCE can have a perfect happy path -- the TIER 4 item on `FOR`/`GOTO`
    says so in its own text: *"the interpreter is 2.5-3.8x slower (TIER 2,
    reasonable time, is met)"*.
    🎯 MEASURED COST OF THE MISTAKE: 15 statements were held out of TIER 1 by items
    that are not about the happy path at all -- eleven at TIER 5 (an exhaustive
    error case), three at TIER 4 (speed) and one at TIER 3 (a common error).
    ⚠️ The tuple is `(tier, lines, evidence)` and `(None, [], 'SUPPORTED')` is
    TRUTHY, so this reads the FIRST element -- the trap selftest S28 pins."""
    return entry is not None and entry[0] == 1


def tier1_keywords(kws, conn=None, forms=None):
    """The keywords Joost's TIER 1 rule awards, computed ONCE for every caller.

    ⚠️ The open-item clause reads `kt[kw][0] is not None`, NOT `bool(kt[kw])` --
    the entry is a TUPLE `(tier, lines, evidence)` and `(None, [], 'SUPPORTED')` is
    TRUTHY, so a truthiness test marks EVERY keyword as carrying an open item. That
    bug reported PSET as blocked by an item it does not have, and only comparing it
    against PAINT (which really does carry a TIER 4 item) exposed it."""
    conn = knife_connected() if conn is None else conn
    forms = kwsweep_forms(kws) if forms is None else forms
    out = set()
    for kw in kws:
        ok, _ = tier1_status(kw, forms.get(kw, set()), kw in conn, False)
        if ok:
            out.add(kw)
    return out


def fmt_keywords(its, kws, evidence=None):
    kt = keyword_tiers(its, kws, evidence)
    t3 = kwsweep_t3(kws)
    conn = knife_connected()
    t1 = {kw for kw in tier1_keywords(kws, conn)
          if not blocks_tier1(kt.get(kw))}
    nobare = no_bare_form()
    parts = particles()
    forms = kwsweep_forms(kws)
    groups = defaultdict(list)
    for kw, (g, _, e) in kt.items():
        groups[reached_group(g, e, kw in t3, kw in conn, kw in t1,
                             kw in nobare, kw in parts)].append(kw)
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


def _composite_section(kws, evidence=None, conn=None):
    """The statements that are NOT single keywords, and why none is awarded yet.

    🎚️ D-KWCOMPOSITE/D-KWSUBJECT (Joost, 2026-09-14). `ON ERROR GOTO`, `PRINT #`
    and their siblings are statements in their own right with their own N -- but
    they are NOT in the 159-keyword denominator and must never be, or the count of
    what this tree implements would inflate itself by renaming. So they get their
    own section, and the rows that drive them are rendered HERE rather than being
    credited to whichever keyword happens to come first.
    🔴 NONE OF THEM CAN REACH TIER 1 TODAY, and the reason is worth printing rather
    than leaving as a blank: `knife_connected()` is keyed by the stmt_table entry a
    cut removes, and a composite has no entry of its own to cut (`USING`'s token
    $E4 is not in stmt_table at all). Until a composite-aware cut exists, the
    non-vacuity half of the bar is unproven for every one of them -- which is a
    missing instrument, not a passing grade."""
    try:
        import kwforms
    except ImportError:
        return []
    names = sorted(kwforms.subject_names())
    if not names:
        return []
    kwset = set(kws)
    ev = kwsweep_evidence(kws) if evidence is None else evidence
    forms = kwsweep_forms(kws)
    conn = knife_connected() if conn is None else conn
    awarded = tier1_statements(names, conn, forms, kws)
    out = ["", "## Composite and channel statements", "",
           "**First-class statements, counted in the STATEMENT denominator** "
           "(Joost, 2026-09-14: *\"why not? They should have the same TIER and "
           "tests\"*). Each has its own forms, its own N and its own tier, on the "
           "same bar as a keyword. The earlier exclusion was a PRESENTATION worry "
           "\u2014 that splitting `ON` into eight would inflate the count by "
           "renaming \u2014 and that is not a reason to measure the wrong thing: "
           "`ON ERROR GOTO` is ONE statement made of THREE tokens, so a TOKEN "
           "count says `ON` is one thing to get right when it is eight.", "",
           "\U0001f52a **CONNECTEDNESS COMES FROM THE CUT THE STATEMENT'S OWN ROW "
           "RESPONDS TO**, not from a token of its own. Cutting `ON`'s dispatch "
           "entry makes `ongoto` go red, and that row's subject is `ON GOTO`. "
           "`PRINT USING` can be connected NO OTHER WAY \u2014 `USING`'s token is "
           "not in `stmt_table` to cut.", "",
           "| statement | reached | forms | rows agree | what is missing |",
           "|---|---|---|---|---|"]
    for n in names:
        need = kwforms.forms_for(n)
        seen = sorted(forms.get(n, set()))
        agree = ev.get(n) or "\u2014"
        miss = []
        if not need:
            miss.append("no authored form list (UNRATED)")
        else:
            gap = [f for f in need if f not in seen]
            if gap:
                miss.append("missing " + " ".join(gap))
        if n not in conn:
            miss.append("not knife-proven CONNECTED")
        reached = "**TIER 1**" if n in awarded else "TIER 0"
        nf = "%d/%d" % (len(seen), len(need)) if need else "\u2014"
        out.append("| `%s` | %s | %s | %s | %s |"
                   % (n, reached, nf, agree, "; ".join(miss) or "\u2014"))
    return out


def fmt_markdown(its, kws, evidence=None, t3=None, connected=None):
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
    # ⚠️ BOUND BEFORE THE DOCUMENT IS BUILT, because the denominator
    # section prints counts derived from them. They used to be bound
    # halfway down, which made that section an UnboundLocalError.
    kt = keyword_tiers(its, kws, evidence)
    t3 = kwsweep_t3(kws) if t3 is None else t3
    conn = knife_connected() if connected is None else connected
    t1 = {kw for kw in tier1_keywords(kws, conn)
          if not blocks_tier1(kt.get(kw))}
    nobare = no_bare_form()
    parts = particles()
    forms = kwsweep_forms(kws)

    out = ["# zerobas — priority-tier status", "",
           "Generated by `make tiers-md` from the `🎚️` tag on every open "
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
            "## Two denominators, and which question each answers", "",
            "**TOKEN \u2014 %d** (`basic/kwtable.inc`): is every token in the table "
            "implemented? That is what the per-keyword sections below count.\n"
            "**STATEMENT \u2014 %d**: how much of the LANGUAGE works? The %d "
            "keywords that have a bare statement form (`DEF`, `GET`, `ON`, `PUT` "
            "and `USING` do not, and would double-count against their own "
            "composites) plus the %d composite and channel statements. "
            "**%d of them have reached TIER 1.**\n\n"
            "\u2702\ufe0f SYNTAX PARTICLES ARE OUT (Joost, 2026-09-14: *\"Drop them and "
            "mark them\"*). `THEN`, `ELSE`, `TO`, `STEP` and `OFF` appear only "
            "INSIDE another statement and have nothing of their own to get right, "
            "so they are counted as TOKENS and marked in the table rather than "
            "inflating the statement count with things a user cannot write. "
            "(`AS` is not in this tree's table at all.)\n"
            "\u26a0\ufe0f THE OPERATORS STAY, MARKED. `AND OR NOT XOR EQV IMP MOD` are "
            "never statements either, but unlike a particle each HAS BEHAVIOUR OF "
            "ITS OWN worth tiering \u2014 `A AND B` has a truth table to get right and "
            "`THEN` has nothing."
            % (len(kws), len(statements(kws)),
               len(set(kws) - set(no_bare_form()) - set(particles())),
               len(composite_names()),
               len(tier1_statements(statements(kws), conn, forms, kws))), "",
            "## Every keyword and its tier", "",
            "**Every keyword is TIER 0: no tier is established for any of them.** The text "
            "beside each says only what is KNOWN AGAINST it — an open item at tier n, a gap "
            "the sweep sees, or how many rows agree. None of that is attainment.", "",
            "| established tier, and what is known against it | n | keywords |", "|---|---|---|"]
    groups = defaultdict(list)
    for kw, (g, _, e) in kt.items():
        groups[reached_group(g, e, kw in t3, kw in conn, kw in t1,
                             kw in nobare, kw in parts)].append(kw)
    for g in GROUP_ORDER:
        if g is None or not groups[g]:
            continue
        out.append(f"| {REACHED[g]} | {len(groups[g])} | " + " ".join(f"`{k}`" for k in sorted(groups[g])) + " |")
    none = sorted(groups[None])
    out.append(f"| no known gap (no item, no kwsweep row — unverified) | {len(none)} | " + " ".join(f"`{k}`" for k in none) + " |")
    out += ["", FOOTER, "", "### Alphabetical", "", "| keyword | reached | evidence |", "|---|---|---|"]
    for kw in sorted(kws):
        g, lines, e = kt[kw]
        grp = reached_group(g, e, kw in t3, kw in conn, kw in t1, kw in nobare,
                            kw in parts)
        import kwforms
        _need = kwforms.forms_for(kw)
        if grp == "t1":
            _n = len(_need)
            out.append(f"| `{kw}` | **TIER 1** | CONNECTED; "
                       f"{'its 1 form agrees' if _n == 1 else f'all {_n} forms agree'}"
                       f"; no open item |")
        elif _need and g is None:
            # ⚠️ `and g is None`: when an open item ALSO stands against the keyword,
            # the arm below keeps the cell that names the item and its TODO.md
            # line. `tier1_status` would print "an open TIER item stands against
            # it" and drop the citation, which is the more useful half.
            # 🎚️ A KEYWORD WITH AN AUTHORED BAR SAYS HOW FAR SHORT IT IS. Without
            # this, `LOCATE` at 3 of 4 forms printed "1 row agrees, connected" --
            # the same cell as a keyword with one row and no bar at all, which
            # hides the single most useful thing the table knows: WHICH form is
            # missing. `tier1_status` already computes the sentence; the only bug
            # was not printing it.
            _ok, _why = tier1_status(kw, forms.get(kw, set()), kw in conn,
                                     g is not None)
            out.append(f"| `{kw}` | TIER 0 | {_why} |")
        elif grp == "kwpart":
            out.append(f"| `{kw}` | \u2014 | a syntax particle, not a statement |")
        elif grp == "kwcomp":
            out.append(f"| `{kw}` | TIER 0 | no bare form; only as a composite"
                       + (", connected" if kw in conn else "") + " |")
        elif grp is None:
            out.append(f"| `{kw}` | TIER 0 | no known gap, no row |")
        elif grp == "kw1":
            out.append(f"| `{kw}` | TIER 0 | no known gap; 1 row agrees |")
        elif grp == "kw1c":
            out.append(f"| `{kw}` | TIER 0 | no known gap; 1 row agrees, connected |")
        elif grp == "kw3c":
            out.append(f"| `{kw}` | TIER 0 | no known gap; 2 rows agree, connected |")
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
    out += _composite_section(kws, evidence, conn)
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
    ap.add_argument("--allow-no-pin", action="store_true",
                    help="render --markdown even with no kwsweep pin (the "
                         "evidence columns will be empty and WRONG)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    its = items(open(TODO, encoding="utf-8").read())
    kws = keywords()
    if a.markdown:
        # 🔴 REFUSE RATHER THAN RENDER FROM A PIN THAT ISN'T THERE -- see
        # `pin_rows`. The document is mostly evidence columns; without the pin it
        # is a confident table of nothing, and it would pass every gate.
        n, why = pin_rows()
        if not n and not a.allow_no_pin:
            print("\U0001f534 tier_table --markdown REFUSES: the kwsweep pin is "
                  "unusable (%s).\n   The evidence columns come from it, so the "
                  "document would claim every keyword has no row.\n   Run `make "
                  "kwsweep` first, or pass --allow-no-pin if you really want the "
                  "item half alone." % why, file=sys.stderr)
            return 2
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
    # 🎚️ D-KWTIER1: Joost's rule, and the three ways it must REFUSE.
    _need = set(__import__("kwforms").forms_for("PSET") or ())
    arm("S26 TIER 1 needs CONNECTED, every authored form, and no open item",
        tier1_status("PSET", _need, True, False)[0] is True
        and tier1_status("PSET", _need, False, False)[0] is False       # not connected
        and tier1_status("PSET", _need, True, True)[0] is False         # an open item
        and tier1_status("PSET", set(list(_need)[:-1]), True, False)[0] is False)
    arm("S27 a keyword with NO authored form list is UNRATED, never satisfied",
        tier1_status("ZZQNOSUCH", {"a", "b", "c"}, True, False) == (
            False, "UNRATED — no authored form list"))
    # 🔴 THE TRUTHY-TUPLE TRAP: keyword_tiers' entry is (tier, lines, evidence), and
    # `(None, [], 'SUPPORTED')` is TRUTHY -- testing `bool(entry)` marks EVERY
    # keyword as carrying an open item. Measured: it reported PSET blocked by an
    # item it does not have, and only a comparison against PAINT (which really does
    # carry one) exposed it.
    arm("S28 the open-item clause reads the tuple's FIRST element, not its truthiness",
        bool((None, [], "SUPPORTED")) is True
        and ((None, [], "SUPPORTED")[0] is not None) is False)
    # 🎚️ D-KWSUBJECT: a row may DECLARE the statement it is about, because
    # derivation cannot see `#` (punctuation) and `using "##"` never says PRINT.
    # ⚠️ THE REAL TABLE, not this selftest's fixture `kws` -- `known_subject` asks
    # whether a name is scoreable, and the fixture holds three invented keywords.
    _kwset = set(kwtable_keywords())
    arm("S29 a DECLARED subject wins over the one derived from the crunch body",
        stmt_subject("input#1,a$", _kwset) == "INPUT"
        and stmt_subject("input#1,a$", _kwset, "INPUT #") == "INPUT #"
        and stmt_subject('using "##"', _kwset, "PRINT USING") == "PRINT USING")
    # 🔴 A TYPO MUST NOT CREATE A BUCKET NOTHING COUNTS. Adopting an unknown name
    # would move the row off its keyword AND out of every tally, silently -- the
    # `kwcover` lesson: refuse a degenerate input rather than answer from it.
    arm("S30 a declared subject that names nothing scoreable is REFUSED, not adopted",
        stmt_subject('using "##"', _kwset, "PRINT USNIG") == "USING"
        and known_subject("PRINT USING", _kwset) is True
        and known_subject("PRINT #", _kwset) is True
        and known_subject("PRINT USNIG", _kwset) is False)
    # 🎚️ D-KWSTMTDEN: the STATEMENT denominator, and the two selftests that keep
    # it from drifting into the TOKEN one.
    _st = statements(kws)
    arm("S31 the statement set is the keywords MINUS the bare-formless PLUS the "
        "composites, each exactly once",
        len(_st) == len(set(_st))
        and set(_st) == (set(kws) - set(no_bare_form())) | composite_names()
        and not (set(_st) & set(no_bare_form()))
        and composite_names() <= set(_st))
    # 🔴 THE POINT OF THE WHOLE SLICE: before D-KWSTMTDEN a composite could not be
    # awarded AT ALL, because the award iterated the keyword table and no composite
    # is in it. A form list and a knife cut were not enough.
    arm("S32 a COMPOSITE can be awarded, and is refused for the same three reasons "
        "a keyword is",
        tier1_status("ON GOTO", {"index-goto"}, True, False)[0] is True
        and tier1_status("ON GOTO", {"index-goto"}, False, False)[0] is False
        and tier1_status("ON GOTO", {"index-goto"}, True, True)[0] is False
        and tier1_status("ON GOTO", set(), True, False)[0] is False)
    # 🎚️ Joost, 2026-09-14: particles are TOKENS, never statements.
    # ⚠️ THE REAL TABLE AGAIN, not the fixture `kws` -- the same trap S29/S30 fell
    # into: the fixture holds three invented keywords and no particles at all, so
    # every clause below would pass vacuously.
    _real = set(kwtable_keywords())
    arm("S33 every particle is in the TOKEN set and in NO case in the STATEMENT set",
        particles() <= _real
        and not (particles() & set(statements(_real)))
        and operators() <= set(statements(_real)))
    # 🔴 AN ITEM AT TIER n BLOCKS TIER n, NOT TIER n-1 (corrected 2026-09-14).
    # Reading "no open item" as "no open item AT ANY TIER" held 15 statements out
    # of TIER 1 on items that say nothing about the happy path -- the TIER 4 item
    # on FOR/GOTO says so in its own text: "TIER 2, reasonable time, is met".
    arm("S34 only a TIER 1 item blocks TIER 1",
        blocks_tier1((1, [7], "SUPPORTED")) is True
        and blocks_tier1((3, [7], "SUPPORTED")) is False
        and blocks_tier1((4, [7], "SUPPORTED")) is False
        and blocks_tier1((5, [7], "SUPPORTED")) is False
        and blocks_tier1((None, [], "SUPPORTED")) is False
        and blocks_tier1(None) is False)
    md = fmt_markdown(its, kws, evidence={}, t3=set(), connected=set())
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
