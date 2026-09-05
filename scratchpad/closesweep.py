#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which OPEN items look FINISHED? The `- [ ]` that should be `- [x]`.

TODO.md's header records the failure repeatedly: items that were finished work
still spelled `- [ ]`, invisible to the pick-up rule only because nobody re-read
them. Two more landed on 2026-09-05 — the RAM free-space item, whose own text had
said *"⇒ THE ITEM IS CLOSED"* for a day, and the `a.spr` blindness item,
re-verified that morning with nothing owed.

🔴 AND THIS TOOL FOUND NEITHER. It printed **0 candidates from 96 open items**
on the very run that followed both hand-finds. Two independent faults, and the
diagnosis is the reason for the rewrite below:

  1. THE POSITIVE SIGNAL WAS A WORD LIST, AND THE FILE'S VOCABULARY IS NOT ONE.
     **49 of 96 open blocks carry a ✅/🟢 followed by capitals**; the old
     `DONE` pattern matched **8**. The words after the tick are `MEASURED`,
     `RE-MEASURED`, `RE-VERIFIED`, `CHARACTERISED`, `SCOUTED`, `SWEPT`,
     `WITNESSED`, `INSTRUMENTED`, `ADOPTED`, `DECIDED` — and, 60 times,
     `THE` / `AND` / `ALSO` / `ALL` / `BOTH`, which carry no verb at all. No list
     was ever going to hold that, and each miss is SILENT.
  2. THE NEGATIVE SIGNAL CONTAINED A TOKEN THAT ALSO APPEARS IN CLOSURES.
     `STILL NOT` suppressed the `a.spr` item on the sentence *"**Still not** a
     reason to change `a.spr`"* — a DISPOSITION saying nothing is owed. Seven of
     the eight `STILL NOT` blocks read "still not established / settled / priced
     / measured / landed / enough" and really are residuals; only the
     "still not a <noun>" shape is the other thing.

🎯 SO THE TEST IS INVERTED. The question is no longer *"does it announce
completion?"* but **"does it name any outstanding work?"** — because in this file
an item with a residual always SPELLS the residual, while a finished one may say
so in any words at all. The closure marker is kept only as a RANK, never as a
gate, so a block that quietly finished without announcing it is still shortlisted.

A false POSITIVE here costs one read. A false NEGATIVE is invisible, which is why
the whole design leans the other way — and why `--selftest` pins both of the
2026-09-05 hand-finds as known-answer arms, so the next vocabulary edit cannot
lose them again without going red.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚠️ THE RESIDUAL VOCABULARY. This is still a word list and still rots — the
# difference is which way it fails: a residual spelled in a word missing from here
# produces a shortlisted item that a human reads and rejects, not a silent drop.
OPEN = re.compile(
    # 🔴 `STILL NOT` NEEDS THE NEXT WORD. "still not settled" is a residual;
    # "still not A REASON to change it" is a disposition, and that one sentence
    # is what hid the a.spr item from every run of this tool.
    r"STILL NOT\s+\*{0,2}(?!a\b|an\b|the\b)|"
    r"STILL OPEN|STILL OWED|remains open|\bNEXT:|"
    r"not fixed|🙋|unpriced|not priced|OPEN QUESTION|stays open|"
    r"what is left|WHAT IS NOT DONE|is not closed|"
    r"REVISED:|to be re-filed|\bremain\b|\bremains\b|"
    # Added 2026-09-05 after reading the first 17-item shortlist by hand: two of
    # the five ranked candidates were genuinely open and spelled their residual
    # in words this list did not carry -- `➡️ REMAINING: 68` (a standing measure,
    # not a closure) and `widening the default is unblocked, and IT IS THE FIX`.
    r"REMAINING:|it is the fix|BEFORE widening|"
    r"needs? (a|an|another|to be)", re.I)

TICK = re.compile(r"✅|🟢")

# 🎯 A STRUCTURAL FILTER, WORTH MORE THAN ANY WORD. An item whose pick-up marker
# is 🙋 / 🔭 / ⛔ / 🔁 is BY DEFINITION waiting on somebody -- a decision, a scope
# call, a fixture, or a standing ruling of Joost's kept visible on purpose. None
# of those can be "finished but unticked", so none belongs on a shortlist of
# items to close. This removed the preflight-SCAN_DIRS entry, which had done
# everything it asked for and ends "it is a scope call, and it is his".
NOT_MINE = re.compile(r"^[ \t]*(🙋|🔭|⛔|🔁) ", re.M)


def blocks(path=None, inv_json=None):
    path = path or os.path.join(ROOT, "TODO.md")
    inv_json = inv_json or "/tmp/zerobas/inv_close.json"
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "todo_inventory.py"),
                    "--json", inv_json], capture_output=True,
                   cwd=os.path.dirname(path) or ".")
    inv = [x for x in json.load(open(inv_json))
           if x["depth"] == 0 and x["state"] == "open"]
    L = open(path, encoding="utf-8").read().splitlines()
    return [(x, "\n".join(L[x["start"] - 1:x["end"]])) for x in inv]


def shortlist(items):
    """(has_tick, line, headline) for every open block naming NO residual."""
    out = []
    for x, body in items:
        if OPEN.search(body) or NOT_MINE.search(body):
            continue
        h = re.sub(r"[*`~]", "", x["headline"])
        out.append((bool(TICK.search(body)), x["start"], h[:70]))
    out.sort(key=lambda r: (not r[0], r[1]))
    return out


def main():
    items = blocks()
    hits = shortlist(items)
    ticked = sum(1 for x, b in items if TICK.search(b))
    print(f"{len(items)} open items; {ticked} carry a completion marker; "
          f"{len(hits)} name NO residual and are the shortlist:")
    for t, ln, h in hits:
        print(f"  {'✅' if t else '  '} TODO.md:{ln:6d}  {h}")
    print("\n⚠️ A SHORTLIST, NOT A VERDICT — read each block before closing it. "
          "The marker column is a RANK, not the test: an unticked row can still "
          "be finished, which is exactly what the old positive-signal design "
          "could not see.")
    return 0


# --- selftest ---------------------------------------------------------------
# 🔴 EVERY ARM IS A REAL SENTENCE FROM TODO.md, and the first two are the
# 2026-09-05 hand-finds this tool missed. An arm here is what stops the next
# vocabulary edit dropping them again in silence.
ARMS = [
    ("the a.spr disposition is NOT a residual (the STILL NOT fault)",
     "⚠️ **Still not a reason to change `a.spr`**, and this run is the "
     "evidence for that rather than an argument.", True),
    ("an unannounced closure is still shortlisted (no tick at all)",
     "⇒ **THE ITEM IS CLOSED** — both halves gated, 108/108.", True),
    ("\"still not settled\" IS a residual",
     "🔴 **STILL NOT SETTLED** — matching R-FLOOD still means something.", False),
    ("\"still not priced\" IS a residual",
     "Still not priced, but priced against the right thing now.", False),
    ("\"still not measured\" IS a residual",
     "how the reader finds a logical line's START is still NOT measured.", False),
    ("a raise-hand inside the body is a residual",
     "✅ LANDED. 🙋 which of the 104 earn a battery slot is his call.", False),
    ("\"needs a fixture\" is a residual",
     "✅ MEASURED. It needs a fixture before it can be gated.", False),
    ("a plain finished block with a tick is shortlisted",
     "✅ **RE-VERIFIED 2026-09-05** — the covering claim still holds.", True),
    ("a standing MEASURE is a residual, not a closure",
     "✅ RE-SWEPT. ➡️ **REMAINING: 68**, of which 48 may not want this shape.", False),
    ("\"it is the fix\" names work not yet done",
     "✅ That reason is now spent, so widening is unblocked, and it is the fix.", False),
]

# The structural filter has its own arms: it is a different question from the
# residual vocabulary and must fail separately.
MARKER_ARMS = [
    ("a 🔭 SCOUT-THEN-ASK item is never a close candidate",
     "      🔭 SCOUT-THEN-ASK — the walk is DONE; the scope call is his.", False),
    ("a 🙋 NEEDS-JOOST item is never a close candidate",
     "      🙋 NEEDS-JOOST — his call.", False),
    ("a 🔁 STANDING ruling is kept visible on purpose",
     "      🔁 STANDING (Joost, 2026-09-04) — a ruling, not a task.", False),
    ("a 🤖 AUTONOMOUS item IS a close candidate",
     "      🤖 AUTONOMOUS — the reference or a gate settles it.", True),
    ("a marker emoji in PROSE is not a marker",
     "the 🙋 column of the scoreboard counts 32 items.", True),
]


def selftest():
    fails = 0
    for name, body, want in ARMS:
        got = not bool(OPEN.search(body))
        ok = got == want
        fails += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}  "
              f"(want shortlisted={want}, got {got})")
    for name, body, want in MARKER_ARMS:
        got = not bool(NOT_MINE.search(body))
        ok = got == want
        fails += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}  "
              f"(want shortlisted={want}, got {got})")
    n = len(ARMS) + len(MARKER_ARMS)
    print(f"{n - fails}/{n} selftest arms pass")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
