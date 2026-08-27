#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Classify the open TODO items by WHO HAS TO BE THERE, not by what they touch.

Three buckets, so a /loop when Joost is away picks only from the first:

  🤖 AUTONOMOUS   the reference (or a gate) can settle it; no judgement of his
                  is required to finish it correctly.
  🔭 SCOUT-THEN-ASK  the DECISION is his, but the measuring and pricing in front
                  of it are not -- the loop can hand him a priced choice.
  🙋 NEEDS-JOOST  a decision that is his: what to evict from a scarce page, a
                  refactor with no oracle, a charter question, a retirement.
  ⛔ BLOCKED      cannot be started by either of us right now -- an idle host, a
                  fixture that does not exist, apparatus that must be built first.

🔴 TIES GO TO NEEDS-JOOST. Misfiling toward AUTONOMOUS is the expensive error:
it is an agent making a call that was his, unattended. Misfiling the other way
only costs a question.

⚠️ THIS IS A HEURISTIC OVER THE BLOCK TEXT, NOT A READING OF EACH ITEM. It is
here to be argued with -- every row prints the signal that decided it.
"""
import json, re, subprocess, sys

subprocess.run([sys.executable, "tools/todo_inventory.py", "--json",
                "/tmp/zerobas/inv_cls.json"], capture_output=True)
B = [x for x in json.load(open("/tmp/zerobas/inv_cls.json"))
     if x["depth"] == 0 and x["state"] == "open"]
L = open("TODO.md").read().splitlines()

# --- signals that make an item HIS. Ordered: the first hit decides and is shown.
# ⚠️ ORDER MATTERS AND THE GENERIC SIGNAL GOES LAST. The first cut put
# "page-1 budget" first, and because it fires on the bare word "carve" or
# "budget" it captured items whose REAL reason was perf-with-no-oracle or a
# charter question -- the bucket was right and the stated reason was wrong,
# which is worse than useless in a list meant to be argued with.
NEEDS = [
    ("retire / delete", re.compile(r"\bretir|\bdelete\b|\bwithdraw|awaits a HUMAN", re.I)),
    ("charter / scope", re.compile(
        r"charter|out of scope|in scope|DECLINED|DEFERRED to Phase|far future|"
        r"requires a charter", re.I)),
    ("refactor, no oracle", re.compile(
        r"SHOULD PROBABLY|REGIONALISE|toward the reference|namespaces|"
        r"design (choice|question)|two rules", re.I)),
    ("no oracle can settle it", re.compile(
        r"slower than|NO GATE MEASURES TIME|cannot be measured|"
        r"no reference|neither reference", re.I)),
    ("page-1 budget", re.compile(
        r"page 1 is \d+ B free|main page 1|\bcarve\b|\bevict|PROMOTE", re.I)),
]

# Autonomous work that EXISTS INSIDE a his-decision item: measure it, price it,
# build the discriminating row. 🎯 THIS IS THE MOST USEFUL BUCKET -- the loop can
# do all the scouting unattended and leave him a PRICED decision instead of an
# open question. It is how this project already works ("carve -> spend").
SCOUTABLE = re.compile(
    r"Not priced|not priced|Not scouted|UNMEASURED|unmeasured|"
    r"no row drives it|is in \*\*no gate\*\*|needs a row|not in any gate", re.I)
BLOCKED = [
    ("needs an idle host", re.compile(r"idle host|contended|wall time|periodic stall", re.I)),
    ("needs a fixture", re.compile(r"fixture|needs cassette support|tape fixture|"
                                   r"needs a disk|DOS boot", re.I)),
    ("apparatus must be built", re.compile(
        r"apparatus this probe does not have|instrument does not exist|"
        r"needs a .*readout|no apparatus", re.I)),
]


def first(sigs, text):
    for name, rx in sigs:
        m = rx.search(text)
        if m:
            return name, m.group(0)[:40]
    return None, None


# 🔴 HAND CORRECTIONS, read from the block rather than matched. The heuristic
# put these three in NEEDS-JOOST on a signal that was not their reason:
#   T-4857B9  README "Limitations" is stale -- the CHARTER it disagrees with is
#             already settled (faithful full MSX1 BASIC), so bringing the prose
#             into line is bookkeeping, not a scope decision.
#   T-DDBFFA  its own body says "💰 0 ROM bytes; apparatus".
#   T-70A01E  delivery guards; apparatus, no ROM bytes.
# An override list is honest; tuning the regex until it agrees is fitting the
# answer you already have.
OVERRIDE = {
    "T-4857B9": ("🤖 AUTONOMOUS", "the charter it contradicts is already settled"),
    "T-DDBFFA": ("🤖 AUTONOMOUS", "its own body prices it at 0 ROM bytes"),
    "T-70A01E": ("🤖 AUTONOMOUS", "apparatus, no ROM bytes"),
}

rows = []
for x in B:
    body = "\n".join(L[x["start"] - 1:x["end"]])
    bn, bw = first(BLOCKED, body)
    nn, nw = first(NEEDS, body)
    if x["id"] in OVERRIDE:
        b_, why = OVERRIDE[x["id"]]
        rows.append((b_, f"hand-corrected: {why}", "", x))
    elif bn:
        rows.append(("⛔ BLOCKED", bn, bw, x))
    elif nn and SCOUTABLE.search(body):
        rows.append(("🔭 SCOUT-THEN-ASK", f"{nn}, but unpriced/unmeasured first", nw, x))
    elif nn:
        rows.append(("🙋 NEEDS-JOOST", nn, nw, x))
    else:
        rows.append(("🤖 AUTONOMOUS", "no his-decision signal found", "", x))

import collections
c = collections.Counter(r[0] for r in rows)
print(f"{len(B)} open items")
ORDER = ("🤖 AUTONOMOUS", "🔭 SCOUT-THEN-ASK", "🙋 NEEDS-JOOST", "⛔ BLOCKED")
for k in ORDER:
    print(f"  {c[k]:4d}  {k}")
for k in ("🙋 NEEDS-JOOST", "🔭 SCOUT-THEN-ASK", "⛔ BLOCKED", "🤖 AUTONOMOUS"):
    print(f"\n=== {k}")
    for bucket, sig, word, x in rows:
        if bucket != k:
            continue
        h = re.sub(r"[*`~]", "", x["headline"])
        h = re.sub(r"^[^A-Za-z`]*", "", h)
        print(f"  {x['id']}  [{sig}] {h[:74]}")
json.dump({x["id"]: {"bucket": b, "signal": s, "matched": w}
           for b, s, w, x in rows}, open("scratchpad/open_buckets.json", "w"), indent=1)


# --- `--count`: recount the markers actually in TODO.md ---------------------
# 🔴 THE HEADER TABLE'S `n` COLUMN ROTS, AND ON 2026-08-27 IT WAS WRONG BY 12 IN
# ONE BUCKET. It is a hand copy of a number the file itself carries -- exactly the
# class D-WALLIT gated for build symbols, in a place no gate reads. The table now
# carries a DATE and names this mode; run it rather than quoting it.
# It also enforces the header's own stated invariant (every open item is marked):
# three items on 2026-08-27 were `- [ ]` with no marker AND ended "✅ DONE", so the
# loop would have re-picked finished work.
def _count(path="TODO.md"):
    import re as _re
    s = open(path).read()
    marks = ("🤖", "🔭", "🙋", "⛔")
    c = {m: 0 for m in marks}
    opened, unmarked = 0, []
    for b in _re.split(r"\n(?=- \[[ x]\] )", s):
        if not b.startswith("- [ ] "):
            continue
        opened += 1
        hit = False
        for m in marks:
            if _re.search(r"^\s*" + m + r" ", b, _re.M):
                c[m] += 1
                hit = True
        if not hit:
            unmarked.append(b.splitlines()[0][:70])
    for m in marks:
        print(f"  {m}  {c[m]}")
    print(f"  open blocks {opened}, markers {sum(c.values())}")
    if unmarked:
        print("🔴 UNMARKED OPEN ITEM(S) -- unclassified, NOT autonomous:")
        for u in unmarked:
            print("   ", u)
        return 1
    return 0


if __name__ == "__main__" and "--count" in sys.argv:
    raise SystemExit(_count())
