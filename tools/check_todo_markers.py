#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MARKGATE gate — every OPEN item in TODO.md carries exactly one pick-up marker.

TODO.md's own header states the invariant ("EVERY OPEN ITEM CARRIES A PICK-UP
MARKER, AND THE MARKER SAYS WHO HAS TO BE IN THE ROOM") and, until this gate, the
only thing that could check it was `scratchpad/classify_open.py --count`, which
**nothing ran**. It had therefore failed silently at least three times: on
2026-08-27 (three items `- [ ]`, unmarked, and ending "✅ DONE" -- the loop would
have re-picked finished work), on 2026-09-01 (three more), and again today.

🔴 AND THE READOUT THAT CAUGHT THOSE SAW HALF OF TODAY'S. `--count`'s rule is
"the block contains a line starting with a marker emoji". Measured 2026-09-05
against the rule below: it reported **4** unmarked and there were **8**. The four
it missed were counted as MARKED on a line that merely BEGINS with the emoji --

    🔭 **ONLY THE IMPLEMENTATION DECISION IS LEFT** -- whether to spend the ~7 B
    🙋 NEEDS A DECISION -- the mechanism (partition vs merge) is Joost's call
    🙋 **(b) IS STILL YOURS** -- which of the 104 earn a battery slot is a

-- prose that names a bucket in passing, and in one case (D-INTERPSPEED) a
`🙋 ... / 🤖 ...` PAIR splitting the item's two halves, which the loose rule
counted as BOTH buckets at once. 🎯 The class is [[readout-blind-to-its-own-subject]]
sharpened: the instrument did not merely miss them, it **scored them into the
tallies it prints**, so a loop reading "🤖 59" was reading a number with an
unmarked item inside it. Misfiling toward 🤖 is the expensive direction --
TODO.md says so itself -- and that is the direction this failed in.

⚠️ THE ARITHMETIC HID IT. `--count` printed `open blocks 107, markers 105`, and
2 is not 4: two blocks carried a marker emoji TWICE (a `🤖`/`🙋` table cell inside
a scoreboard), so 4 missing and 2 double-counted netted to a plausible-looking
gap of 2. [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

## The rule

A pick-up marker is `<emoji> <NAME> —` at the start of a line, optionally
`**`-bolded, where the emoji and the NAME are the SAME bucket. Requiring the name
is what separates a marker from prose about a bucket; requiring the pairing is
what rejects `🙋 BLOCKED ON JOOST` (a scoreboard row, not a `⛔ BLOCKED` marker).
The separator may be `—` or `:`.

Everything else beginning with a marker emoji is fine and stays fine -- prose is
allowed to mention a bucket. This gate reports the gap between the two rules
rather than policing it, because that gap is exactly what made the old readout
wrong and is worth being able to see.

## What is a failure

  * an open block with NO marker              -- unclassified, and the loop's
                                                 rule is that unclassified is
                                                 NOT autonomous
  * an open block with MORE THAN ONE bucket   -- ties go to 🙋; the file has to
                                                 say which, not both
  * the two denominators disagreeing          -- this file's block splitter vs
                                                 `tools/todo_inventory.py`. A
                                                 second, uncross-checked
                                                 membership list is how
                                                 `run_gates.py` came to disagree
                                                 with the Makefile.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The vocabulary. 🔁 STANDING is not a work bucket: it marks a RULING of Joost's
# kept open so it stays visible (the oracle-split rule, the speed sequencing).
# Those are not pickable and must not be counted among the 🤖 -- before this gate
# they were simply unmarked, which is the same hole by another route.
BUCKETS = {
    "\U0001f916": "AUTONOMOUS",       # 🤖
    "\U0001f52d": "SCOUT-THEN-ASK",   # 🔭
    "\U0001f64b": "NEEDS-JOOST",      # 🙋
    "⛔": "BLOCKED",              # ⛔
    "\U0001f501": "STANDING",         # 🔁
}
PICKABLE = ("\U0001f916",)

MARKER = {
    m: re.compile(r"^[ \t]*" + m + r" \*{0,2}" + re.escape(n) + r"\*{0,2}[ ,]*[—:]", re.M)
    for m, n in BUCKETS.items()
}
# The old rule, kept so the gate can PRINT the gap rather than assert it away.
LOOSE = {m: re.compile(r"^[ \t]*" + m + r" ", re.M) for m in BUCKETS}

BLOCK_SPLIT = re.compile(r"\n(?=- \[[ x]\] )")


def blocks(text):
    """Open top-level blocks, as (line number, text)."""
    out, pos = [], 0
    for b in BLOCK_SPLIT.split(text):
        line = text.count("\n", 0, pos) + 1
        pos += len(b) + 1
        if b.startswith("- [ ] "):
            out.append((line, b))
    return out


def inventory_open_count(path):
    """The OTHER denominator, so the two cannot drift apart unnoticed.

    🔴 ONLY FOR THE REAL FILE. `todo_inventory.py` reads TODO.md whatever it is
    handed, so on a fixture it answers about the tree instead -- and the first
    run of this selftest had FOUR arms passing on that mismatch rather than on
    their own subject [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    """
    if os.path.abspath(path) != os.path.join(ROOT, "TODO.md"):
        return None
    tmp = os.path.join(tempfile.gettempdir(), "todo_markers_inv.json")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "todo_inventory.py"),
                        "--json", tmp], capture_output=True, cwd=os.path.dirname(path) or ".")
    if r.returncode != 0 or not os.path.exists(tmp):
        return None
    return sum(1 for x in json.load(open(tmp))
               if x["depth"] == 0 and x["state"] == "open")


def check(path="TODO.md", quiet=False):
    text = open(path, encoding="utf-8").read()
    bs = blocks(text)
    bad, tally, gap = [], {m: 0 for m in BUCKETS}, []

    for line, b in bs:
        head = b.splitlines()[0][6:86]
        hit = sorted(m for m, rx in MARKER.items() if rx.search(b))
        loose = sorted(m for m, rx in LOOSE.items() if rx.search(b))
        if loose != hit:
            gap.append((line, "".join(loose) or "-", "".join(hit) or "-", head))
        if not hit:
            bad.append((line, "NO MARKER", head))
        elif len(hit) > 1:
            bad.append((line, "MULTI " + "".join(hit) + " (ties go to 🙋)", head))
        else:
            tally[hit[0]] += 1

    inv = inventory_open_count(path)
    if inv is not None and inv != len(bs):
        bad.append((0, f"DENOMINATORS DISAGREE: this splitter {len(bs)}, "
                       f"todo_inventory.py {inv}", ""))

    if not quiet:
        print(f"{len(bs)} open blocks"
              + (f" (todo_inventory.py agrees: {inv})" if inv is not None else ""))
        for m, n in BUCKETS.items():
            print(f"  {m}  {n:<14s} {tally[m]:4d}"
                  + ("   <- the /loop picks from here" if m in PICKABLE else ""))
        if gap:
            print(f"\n{len(gap)} block(s) where a marker EMOJI appears without being a "
                  f"marker (informational -- prose may name a bucket):")
            for line, lo, ti, head in gap:
                print(f"  line {line:5d}  emoji={lo:<10s} marker={ti:<10s} {head}")
    if bad:
        print("\n\U0001f534 UNCLASSIFIED OR AMBIGUOUS OPEN ITEM(S):")
        for line, why, head in bad:
            print(f"  line {line:5d}  {why}" + (f"  {head}" if head else ""))
        return 1
    return 0


# --- selftest ---------------------------------------------------------------
# Every arm is a fixture, never TODO.md: a gate whose selftest reads the live
# file goes green the day the file is fixed and can never fail again.
OK_ONE = "- [ ] **X**\n      \U0001f916 AUTONOMOUS — a gate settles it.\n"
ARMS = [
    ("a marker in the disciplined shape passes", OK_ONE, 0),
    ("bolded and colon-separated forms pass",
     "- [ ] **X**\n      \U0001f64b **NEEDS-JOOST** — his call.\n"
     "- [ ] **Y**\n      ⛔ BLOCKED: no fixture.\n", 0),
    ("an unmarked open block fails",
     "- [ ] **X**\n      it says nothing about who.\n", 1),
    # 🔴 THE ARM THE OLD READOUT WOULD HAVE PASSED. Reverting MARKER to LOOSE
    # makes this one go green, which is how the tightening was verified rather
    # than assumed.
    ("prose beginning with a marker emoji is NOT a marker",
     "- [ ] **X**\n      \U0001f52d **ONLY THE DECISION IS LEFT** — spend 7 B?\n", 1),
    ("a mismatched emoji/name pair is not a marker",
     "- [ ] **X**\n      \U0001f64b BLOCKED ON JOOST — 7 rows\n", 1),
    ("two buckets in one block fail",
     "- [ ] **X**\n      \U0001f916 AUTONOMOUS — half of it.\n"
     "      \U0001f64b NEEDS-JOOST — the other half.\n", 1),
    ("a CLOSED block needs no marker",
     "- [x] **X**\n      done, no marker.\n" + OK_ONE, 0),
    ("\U0001f501 STANDING is a marker but not a work bucket",
     "- [ ] **X**\n      \U0001f501 STANDING — a ruling of his, kept visible.\n", 0),
]


def selftest():
    import io
    import contextlib
    fails = 0
    for name, body, want in ARMS:
        p = os.path.join(tempfile.gettempdir(), "todo_markers_arm.md")
        open(p, "w", encoding="utf-8").write(body)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = check(p, quiet=True)
        ok = got == want
        fails += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}  (want rc={want}, got {got})")
        if not ok:
            print("        " + buf.getvalue().replace("\n", "\n        "))
    print(f"{len(ARMS) - fails}/{len(ARMS)} selftest arms pass")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(check())
