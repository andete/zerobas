#!/usr/bin/env python3
"""Which OPEN items look FINISHED? The `- [ ]` that should be `- [x]`.

TODO.md's header records the failure twice: items that were finished work still
spelled `- [ ]`, invisible to the pick-up rule only because nobody re-read them.
This is a heuristic SHORTLIST, never a verdict -- every hit is read by hand.

An item is a candidate when it carries a completion marker (✅/🟢 FIXED/CLOSED/
LANDED/SHIPS) AND its remaining text names no open scope (no "STILL OPEN",
"remains", "NEXT:", "not fixed", "🙋", "unpriced", "open question").
"""
import json, re, subprocess, sys
subprocess.run([sys.executable, "tools/todo_inventory.py", "--json",
                "/tmp/zerobas/inv_close.json"], capture_output=True)
inv = [x for x in json.load(open("/tmp/zerobas/inv_close.json"))
       if x["depth"] == 0 and x["state"] == "open"]
L = open("TODO.md", encoding="utf-8").read().splitlines()
# 🔴 THE *DONE* SIDE MISSES TOO, AND ITS MISSES ARE SILENT. The first run's
# vocabulary had no `ANSWERED`, so `⚠️ NOTHING IN 360 ROWS PINS THE TENANT'S
# GRPACX STORE` -- which carries `✅ READ AND ANSWERED ... VERDICT: KEEP THE
# WRITE` and no open scope at all -- was never even shortlisted. A false NEGATIVE
# here is worse than the false positives, because nothing prints it.
DONE = re.compile(r"(✅|🟢)\s*\*?\*?(FIXED|CLOSED|LANDED|SHIPS|SHIPPED|DONE|"
                  r"BUILT AND GATED|CONVERTED|ANSWERED|VERDICT|RESOLVED|"
                  r"SETTLED|RE-VALIDATED|CLOSED THE)", re.I)
# 🔴 THE FIRST RUN SHORTLISTED 7 AND 3 WERE STILL OPEN -- a 43% false rate, every
# one of them because the block spelled its residual in a form this pattern did
# not carry: "STILL OWED", "REVISED: 1 done. 6 need...", and a "priced" that the
# `unpriced` alternative could not see. The vocabulary below is what those three
# taught it, and the banner still says SHORTLIST for the ones it will miss next.
OPEN = re.compile(r"STILL OPEN|STILL NOT|STILL OWED|remains open|\bNEXT:|"
                  r"not fixed|🙋|unpriced|not priced|OPEN QUESTION|stays open|"
                  r"what is left|WHAT IS NOT DONE|is not closed|"
                  r"REVISED:|to be re-filed|\bremain\b|\bremains\b|"
                  r"needs? (a|an|another|to be)", re.I)
hits = []
for x in inv:
    body = "\n".join(L[x["start"] - 1:x["end"]])
    if DONE.search(body) and not OPEN.search(body):
        h = re.sub(r"[*`~]", "", x["headline"])
        h = re.sub(r"^[^A-Za-z`]*", "", h)
        hits.append((x["id"], x["start"], h[:66]))
print(f"{len(inv)} open items; {len(hits)} look FINISHED and unclosed:")
for i, ln, h in hits:
    print(f"  {i}  TODO.md:{ln}  {h}")
print("\n⚠️ A SHORTLIST, NOT A VERDICT — read each block before closing it.")
